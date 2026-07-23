/* ===========================================================
   session.js — call requireSession() at the top of any page
   that needs the user to be logged in. Confirms the session
   cookie is valid by asking the backend, and returns the
   logged-in user's info (email, name, role).
   =========================================================== */

async function requireSession() {
  let res;
  try {
    res = await fetch(PROXY_URL + "/api/me", { credentials: "include" });
  } catch (err) {
    // Network hiccup / server momentarily unreachable — this is NOT proof
    // the user is logged out, so don't throw them back to the login page.
    console.error("Session check could not reach the server:", err);
    return null;
  }

  if (res.status === 401 || res.status === 403) {
    // Genuinely not signed in — send them to the login page.
    window.location.href = "/index.html";
    return null;
  }

  if (!res.ok) {
    console.error("Session check failed with status", res.status);
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
