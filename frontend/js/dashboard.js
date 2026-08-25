const ROUND_ENTRY_PATHS = {
  aptitude: "/practice/aptitude.html",
  dsa: "/practice/dsa.html",
};
const LIVE_ROUNDS = new Set(["aptitude", "dsa"]);
const PRACTICE_ROUNDS = ["aptitude", "dsa", "technical", "project_defense", "hr"];

let currentTrack = "default";

async function init() {
  const user = await requireAuth();
  if (!user) return;
  document.getElementById("nav-user").textContent = user.full_name || user.email;

  document.getElementById("logout-link").addEventListener("click", async (e) => {
    e.preventDefault();
    await API.post("/api/auth/logout");
    window.location.href = "/login.html";
  });

  document.getElementById("mode-toggle").addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-mode]");
    if (!btn) return;
    document.querySelectorAll("#mode-toggle button").forEach(b => b.classList.remove("is-active"));
    btn.classList.add("is-active");
    const mode = btn.dataset.mode;
    document.getElementById("simulation-view").style.display = mode === "simulation" ? "block" : "none";
    document.getElementById("practice-view").style.display = mode === "practice" ? "block" : "none";
  });

  await loadDashboard();
}

async function loadDashboard() {
  const data = await API.get(`/api/dashboard?track=${currentTrack}`);
  renderSimulationTrack(data.simulation);
  renderSimulationCards(data.simulation);
  renderPracticeCards(data.practice);
  document.getElementById("track-name").textContent = `TRACK: ${currentTrack.toUpperCase()}`;
}

function renderSimulationTrack(rounds) {
  const rail = document.getElementById("track-rail");
  rail.innerHTML = rounds.map(r => `
    <div class="track-node is-${r.status}">
      <span class="status-light is-${r.status}"></span>
      <div class="round-name">${roundLabel(r.round)}</div>
      <div class="round-score">${r.best_score != null ? r.best_score + "%" : "—"} / cutoff ${r.cutoff}%</div>
    </div>
  `).join("");
}

function renderSimulationCards(rounds) {
  const container = document.getElementById("simulation-cards");
  container.innerHTML = rounds
    .filter(r => r.round !== "resume_screening")
    .map(r => {
      const isLive = LIVE_ROUNDS.has(r.round);
      const locked = r.status === "locked";
      const entryPath = ROUND_ENTRY_PATHS[r.round];
      let actionHtml;
      if (!isLive) {
        actionHtml = `<button class="btn btn-secondary btn-sm" disabled>Coming soon</button>`;
      } else if (locked) {
        actionHtml = `<button class="btn btn-secondary btn-sm" disabled>Locked</button>`;
      } else {
        const cta = r.status === "cleared" ? "Retry round" : "Enter round";
        actionHtml = `<a href="${entryPath}?mode=simulation&track=${currentTrack}" class="btn btn-primary btn-sm">${cta}</a>`;
      }
      return `
        <div class="card round-card">
          <div class="status-row" style="margin-bottom:10px;">
            <span class="status-light is-${r.status}"></span>
            <span class="status-label is-${r.status}">${r.status}</span>
          </div>
          <div class="round-title">${roundLabel(r.round)}</div>
          <div class="round-meta">CUTOFF ${r.cutoff}%</div>
          <div class="round-stats">
            <div class="round-stat"><div class="num">${r.best_score != null ? r.best_score + "%" : "—"}</div><div class="label">Best score</div></div>
          </div>
          ${actionHtml}
        </div>`;
    }).join("");
}

function renderPracticeCards(practice) {
  const container = document.getElementById("practice-cards");
  container.innerHTML = PRACTICE_ROUNDS.map(round => {
    const stats = practice[round] || { attempts: 0, best_score: null, last_score: null };
    const isLive = LIVE_ROUNDS.has(round);
    const entryPath = ROUND_ENTRY_PATHS[round];
    const actionHtml = isLive
      ? `<a href="${entryPath}?mode=practice" class="btn btn-primary btn-sm">Practice now</a>`
      : `<button class="btn btn-secondary btn-sm" disabled>Coming soon</button>`;
    return `
      <div class="card round-card">
        <div class="round-title">${roundLabel(round)}</div>
        <div class="round-meta">${stats.attempts} attempt${stats.attempts === 1 ? "" : "s"}</div>
        <div class="round-stats">
          <div class="round-stat"><div class="num">${stats.best_score != null ? stats.best_score + "%" : "—"}</div><div class="label">Best</div></div>
          <div class="round-stat"><div class="num">${stats.last_score != null ? stats.last_score + "%" : "—"}</div><div class="label">Last</div></div>
        </div>
        ${actionHtml}
      </div>`;
  }).join("");
}

init();
