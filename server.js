/* ===========================================================
   session.js — call requireSession() at the top of any page
   that needs the user to be logged in. Confirms the session
   cookie is valid by asking the backend, and returns the
   logged-in user's info (email, name, role).

   Any failure now shows a visible on-page message instead of
   silently doing nothing — so a broken page always tells you
   why, rather than just staying blank.
   =========================================================== */

function showSessionError(message) {
  let banner = document.getElementById("sessionErrorBanner");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "sessionErrorBanner";
    banner.style.cssText = [
      "position:fixed", "top:0", "left:0", "right:0", "z-index:9999",
      "background:#D64545", "color:#fff", "padding:12px 20px",
      "font-family:-apple-system,'Segoe UI',sans-serif", "font-size:14px",
      "text-align:center"
    ].join(";");
    document.body.prepend(banner);
  }
  banner.textContent = message;
}

async function requireSession() {
  let res;
  try {
    res = await fetch(PROXY_URL + "/api/me", { credentials: "include" });
  } catch (err) {
    console.error("Session check could not reach the server:", err);
    showSessionError(`Could not reach the server at ${PROXY_URL}. Is it running?`);
    return null;
  }

  if (res.status === 401 || res.status === 403) {
    // Genuinely not signed in — send them to the login page.
    window.location.href = "/index.html";
    return null;
  }

  if (!res.ok) {
    let details = "";
    try { details = JSON.stringify(await res.json()); } catch { /* ignore */ }
    console.error("Session check failed with status", res.status, details);
    showSessionError(`Server error (${res.status}) while checking your session. ${details}`);
    return null;
  }

  return await res.json();
}

async function logout(redirectTo = "/index.html") {
  try {
    await fetch(PROXY_URL + "/auth/logout", { method: "POST", credentials: "include" });
  } finally {
    window.location.href = redirectTo;
  }
}

function initials(name) {
  if (!name) return "?";
  return name.split(" ").map(p => p[0]).slice(0, 2).join("").toUpperCase();
}
