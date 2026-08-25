// Shared API helper. All routes are same-origin (Flask serves the frontend),
// so cookies (Flask session) travel automatically with { credentials: 'same-origin' }.
const API = {
  async _call(method, path, body) {
    const res = await fetch(path, {
      method,
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = null;
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (!res.ok) {
      const err = new Error((data && data.error) || `Request failed (${res.status})`);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  },
  get(path) { return this._call("GET", path); },
  post(path, body) { return this._call("POST", path, body); },
};

async function requireAuth() {
  const { user } = await API.get("/api/auth/me");
  if (!user) {
    window.location.href = "/login.html";
    return null;
  }
  return user;
}

function fmtSeconds(totalSeconds) {
  const s = Math.max(0, Math.round(totalSeconds));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

function roundLabel(key) {
  const labels = {
    resume_screening: "Resume Screening",
    aptitude: "Aptitude",
    dsa: "DSA / Coding",
    technical: "Technical Interview",
    project_defense: "Project Defense",
    hr: "HR / Behavioral",
  };
  return labels[key] || key;
}
