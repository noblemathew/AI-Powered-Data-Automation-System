/* ===========================================================
   server.js — One Portal backend (SQL Server edition).
   =========================================================== */

import "dotenv/config";
import express from "express";
import cors from "cors";
import cookieParser from "cookie-parser";
import path from "path";
import { fileURLToPath } from "url";
import { exec } from "child_process";
import { promisify } from "util";

import { query } from "./db.js";
import { registerAuthRoutes, requireSession } from "./auth.js";

const execAsync = promisify(exec);
const __dirname = path.dirname(fileURLToPath(import.meta.url));

const app = express();
const PORT = process.env.PORT || 3000;
const FRONTEND_ORIGIN = process.env.FRONTEND_ORIGIN || "http://localhost:3000";

app.use(cors({ origin: FRONTEND_ORIGIN, credentials: true }));
app.use(express.json());
app.use(cookieParser());

registerAuthRoutes(app);

function callerManagerId(user) {
  return user.role === "manager" ? user.id : user.m_id;
}

/* ---------------- Projects ---------------- */

app.get("/api/projects", requireSession, async (req, res) => {
  const managerId = callerManagerId(req.user);
  const rows = await query(
    `SELECT p.id, p.name,
            (SELECT COUNT(*) FROM project_tools pt WHERE pt.project_id = p.id) AS tool_count
     FROM projects p
     WHERE p.m_id = @managerId
     ORDER BY p.id DESC`,
    { managerId }
  );
  res.json(rows);
});

app.get("/api/projects/:id", requireSession, async (req, res) => {
  const managerId = callerManagerId(req.user);
  const rows = await query(
    "SELECT * FROM projects WHERE id = @id AND m_id = @managerId",
    { id: req.params.id, managerId }
  );
  if (rows.length === 0) return res.status(404).json({ error: "Project not found" });
  res.json(rows[0]);
});

app.post("/api/projects", requireSession, async (req, res) => {
  if (req.user.role !== "manager") return res.status(403).json({ error: "Only managers can create projects" });
  const { name } = req.body || {};
  if (!name?.trim()) return res.status(400).json({ error: "Project name is required" });

  const rows = await query(
    "INSERT INTO projects (name, m_id) OUTPUT INSERTED.id AS id VALUES (@name, @managerId)",
    { name: name.trim(), managerId: req.user.id }
  );
  res.status(201).json({ id: rows[0].id, name: name.trim() });
});

app.delete("/api/projects/:id", requireSession, async (req, res) => {
  if (req.user.role !== "manager") return res.status(403).json({ error: "Only managers can delete projects" });

  const rows = await query(
    "SELECT * FROM projects WHERE id = @id AND m_id = @managerId",
    { id: req.params.id, managerId: req.user.id }
  );
  if (rows.length === 0) return res.status(404).json({ error: "Project not found" });

  await query("DELETE FROM project_tools WHERE project_id = @id", { id: req.params.id });
  await query("DELETE FROM projects WHERE id = @id", { id: req.params.id });
  res.status(204).send();
});

/* ---------------- Tools (per project) ---------------- */

app.get("/api/projects/:id/tools", requireSession, async (req, res) => {
  const managerId = callerManagerId(req.user);

  const owns = await query("SELECT id FROM projects WHERE id = @id AND m_id = @managerId", { id: req.params.id, managerId });
  if (owns.length === 0) return res.status(404).json({ error: "Project not found" });

  const tools = await query(
    `SELECT t.id, t.slug, t.name, t.description
     FROM project_tools pt
     JOIN tools t ON t.id = pt.tool_id
     WHERE pt.project_id = @id
     ORDER BY t.id`,
    { id: req.params.id }
  );
  res.json(tools);
});

/* ---------------- Employees (team members) ---------------- */

app.get("/api/employees", requireSession, async (req, res) => {
  if (req.user.role !== "manager") return res.status(403).json({ error: "Only managers can view team lists" });
  const rows = await query("SELECT id, email, display_name FROM employees WHERE m_id = @managerId ORDER BY id", { managerId: req.user.id });
  res.json(rows);
});

app.post("/api/employees", requireSession, async (req, res) => {
  if (req.user.role !== "manager") return res.status(403).json({ error: "Only managers can add team members" });
  const { email, display_name } = req.body || {};
  if (!email?.trim()) return res.status(400).json({ error: "Email is required" });

  const existing = await query("SELECT id FROM employees WHERE email = @email", { email: email.trim() });
  if (existing.length > 0) return res.status(409).json({ error: "That email is already added" });

  // New employees need a password too — a manager-set temporary one for now,
  // since there's no self-service invite flow yet. Worth swapping for a
  // proper "set your own password on first login" flow later.
  const bcrypt = (await import("bcryptjs")).default;
  const tempPasswordHash = await bcrypt.hash("ChangeMe123!", 10);

  const rows = await query(
    `INSERT INTO employees (email, display_name, password_hash, m_id)
     OUTPUT INSERTED.id AS id
     VALUES (@email, @displayName, @passwordHash, @managerId)`,
    { email: email.trim(), displayName: display_name || null, passwordHash: tempPasswordHash, managerId: req.user.id }
  );
  res.status(201).json({ id: rows[0].id, email: email.trim(), temp_password: "ChangeMe123!" });
});

app.delete("/api/employees/:id", requireSession, async (req, res) => {
  if (req.user.role !== "manager") return res.status(403).json({ error: "Only managers can remove team members" });

  const rows = await query("SELECT * FROM employees WHERE id = @id AND m_id = @managerId", { id: req.params.id, managerId: req.user.id });
  if (rows.length === 0) return res.status(404).json({ error: "Team member not found" });

  await query("DELETE FROM employees WHERE id = @id", { id: req.params.id });
  res.status(204).send();
});

/* -----------------------------------------------------------
   Webscraper tool proxy — unchanged from the original build.
   ----------------------------------------------------------- */

const FLOW_URL = process.env.POWER_AUTOMATE_URL;
const TOKEN_RESOURCE = process.env.TOKEN_RESOURCE || "https://service.flow.microsoft.com/";

async function getFlowToken() {
  const { stdout } = await execAsync(`az account get-access-token --resource ${TOKEN_RESOURCE}`);
  const parsed = JSON.parse(stdout);
  if (!parsed.accessToken) throw new Error("No accessToken in az CLI output");
  return parsed.accessToken;
}

app.post("/api/extract", requireSession, async (req, res) => {
  const { company, url } = req.body || {};
  if (!company || !url) return res.status(400).json({ error: "Both 'company' and 'url' are required." });
  if (!FLOW_URL) return res.status(500).json({ error: "Server is missing POWER_AUTOMATE_URL — set it in server/.env" });

  let token;
  try {
    token = await getFlowToken();
  } catch (err) {
    console.error("Token fetch failed:", err.message);
    return res.status(401).json({
      error: "Could not get an Azure AD token. Run `az login` in this server's terminal, then try again.",
      details: err.message
    });
  }

  try {
    const flowRes = await fetch(FLOW_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ company, url })
    });

    const text = await flowRes.text();
    let body;
    try { body = JSON.parse(text); } catch { body = { raw: text }; }

    if (!flowRes.ok) return res.status(502).json({ error: `Flow responded with ${flowRes.status}`, details: body });
    res.json(body);
  } catch (err) {
    console.error(err);
    res.status(502).json({ error: "Could not reach the Power Automate flow", details: String(err) });
  }
});

app.get("/api/health", async (req, res) => {
  let dbOk = false;
  try { await query("SELECT 1 AS ok"); dbOk = true; } catch { /* leave false */ }
  res.json({ ok: true, dbOk, flowConfigured: Boolean(FLOW_URL) });
});

/* -----------------------------------------------------------
   Interview Assessment tool proxy — same auth pattern as the
   webscraper's /api/extract above (reuses getFlowToken()), just
   pointed at this tool's own Power Automate flow. The tool's
   own page sends whatever payload it already builds (candidate
   details, question bank, transcript, etc.) — forwarded as-is.
   ----------------------------------------------------------- */

const INTERVIEW_FLOW_URL = process.env.INTERVIEW_FLOW_URL;

app.post("/api/interview-evaluate", requireSession, async (req, res) => {
  if (!INTERVIEW_FLOW_URL) {
    return res.status(500).json({ error: "Server is missing INTERVIEW_FLOW_URL — set it in server/.env" });
  }

  let token;
  try {
    token = await getFlowToken();
  } catch (err) {
    console.error("Token fetch failed:", err.message);
    return res.status(401).json({
      error: "Could not get an Azure AD token. Run `az login` in this server's terminal, then try again.",
      details: err.message
    });
  }

  try {
    const flowRes = await fetch(INTERVIEW_FLOW_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify(req.body)
    });

    const text = await flowRes.text();
    let body;
    try { body = JSON.parse(text); } catch { body = { raw: text }; }

    if (!flowRes.ok) return res.status(502).json({ error: `Flow responded with ${flowRes.status}`, details: body });
    res.json(body);
  } catch (err) {
    console.error(err);
    res.status(502).json({ error: "Could not reach the Power Automate flow", details: String(err) });
  }
});

/* ---------------- Serve the static frontend ---------------- */
app.use(express.static(path.join(__dirname, "..")));

app.listen(PORT, () => {
  console.log(`One Portal backend running at http://localhost:${PORT}`);
});
