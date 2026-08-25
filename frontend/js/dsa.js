const params = new URLSearchParams(window.location.search);
const MODE = params.get("mode") === "simulation" ? "simulation" : "practice";
const TRACK = params.get("track") || "default";

let currentProblem = null;
let timerInterval = null;
let deadline = null;

const timerEl = document.getElementById("timer");

async function init() {
  const user = await requireAuth();
  if (!user) return;

  document.getElementById("mode-pill").textContent = MODE.toUpperCase();
  document.getElementById("mode-pill").className = "pill " + (MODE === "simulation" ? "pill-hard" : "pill-easy");

  document.getElementById("run-btn").addEventListener("click", runTests);
  document.getElementById("submit-code-btn").addEventListener("click", submitCode);
  document.getElementById("retry-btn").addEventListener("click", () => window.location.reload());
  document.getElementById("random-btn").addEventListener("click", () => beginProblem(null));

  if (MODE === "practice") {
    await showPicker();
  } else {
    document.getElementById("intro-view").style.display = "block";
    document.getElementById("intro-note").textContent =
      `Simulation Mode — clear this round's cutoff to unlock the Technical Interview. (Track: ${TRACK})`;
    document.getElementById("start-sim-btn").addEventListener("click", () => beginProblem(null));
  }
}

async function showPicker() {
  const data = await API.get("/api/dsa/problems");
  const list = document.getElementById("problem-list");
  list.innerHTML = data.problems.map(p => `
    <div class="card card-hover" style="cursor:pointer; padding:16px;" data-id="${p.id}">
      <div class="row-between" style="margin-bottom:6px;">
        <strong style="font-size:0.95rem;">${p.title}</strong>
        <span class="pill pill-${p.difficulty}">${p.difficulty}</span>
      </div>
      <div class="text-faint mono" style="font-size:0.78rem;">${p.topic}</div>
    </div>
  `).join("");
  list.querySelectorAll("[data-id]").forEach(el => {
    el.addEventListener("click", () => beginProblem(parseInt(el.dataset.id, 10)));
  });
  document.getElementById("picker-view").style.display = "block";
}

async function beginProblem(problemId) {
  try {
    const data = await API.post("/api/dsa/start", { mode: MODE, track: TRACK, problem_id: problemId });
    currentProblem = data.problem;

    document.getElementById("picker-view").style.display = "none";
    document.getElementById("intro-view").style.display = "none";
    document.getElementById("editor-view").style.display = "block";

    renderProblem(currentProblem);
    deadline = Date.now() + currentProblem.time_limit_seconds * 1000;
    startTimer();
  } catch (err) {
    alert(err.message);
    if (err.status === 403) window.location.href = "/dashboard.html";
  }
}

function startTimer() {
  clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    const remaining = (deadline - Date.now()) / 1000;
    if (remaining <= 0) {
      clearInterval(timerInterval);
      timerEl.textContent = "00:00";
      submitCode();
      return;
    }
    timerEl.textContent = fmtSeconds(remaining);
    timerEl.classList.toggle("is-low", remaining < 60);
  }, 500);
}

function renderProblem(p) {
  document.getElementById("p-title").textContent = p.title;
  document.getElementById("p-difficulty").textContent = p.difficulty;
  document.getElementById("p-difficulty").className = "pill pill-" + p.difficulty;
  document.getElementById("p-topic").textContent = p.topic;
  document.getElementById("p-statement").textContent = p.statement;
  document.getElementById("p-examples").innerHTML = p.examples.map(ex => `
    <pre><strong>Input:</strong> ${ex.input}\n<strong>Output:</strong> ${ex.output}</pre>
  `).join("");
  document.getElementById("code-editor").value = p.starter_code;
  document.getElementById("run-results-card").style.display = "none";
}

async function runTests() {
  const code = document.getElementById("code-editor").value;
  const runBtn = document.getElementById("run-btn");
  runBtn.disabled = true;
  runBtn.textContent = "Running…";
  try {
    const data = await API.post("/api/dsa/run", { code, problem_id: currentProblem.id });
    const card = document.getElementById("run-results-card");
    const container = document.getElementById("run-results");
    card.style.display = "block";

    if (data.error) {
      container.innerHTML = `<div class="test-result fail">${data.error}</div>`;
    } else {
      container.innerHTML = data.results.map((r, i) => `
        <div class="test-result ${r.passed ? "pass" : "fail"}">
          <span class="status-light ${r.passed ? "is-cleared" : "is-danger"}"></span>
          Test ${i + 1}: ${r.passed ? "Passed" : `Failed — expected ${JSON.stringify(r.expected)}, got ${JSON.stringify(r.actual)}${r.error ? " (" + r.error + ")" : ""}`}
        </div>
      `).join("");
    }
  } catch (err) {
    alert(err.message);
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = "Run tests";
  }
}

async function submitCode() {
  clearInterval(timerInterval);
  const code = document.getElementById("code-editor").value;
  const btn = document.getElementById("submit-code-btn");
  btn.disabled = true;
  btn.textContent = "Submitting…";
  try {
    const result = await API.post("/api/dsa/submit", { code });
    renderResult(result);
  } catch (err) {
    alert(err.message);
    btn.disabled = false;
    btn.textContent = "Submit";
  }
}

function renderResult(result) {
  document.getElementById("editor-view").style.display = "none";
  document.getElementById("result-view").style.display = "block";

  const scoreEl = document.getElementById("result-score");
  scoreEl.textContent = `${result.score}%`;
  scoreEl.classList.add(result.passed ? "is-pass" : "is-fail");

  const verdictEl = document.getElementById("result-verdict");
  if (result.execution_error) {
    verdictEl.textContent = `Execution error: ${result.execution_error}`;
    verdictEl.style.color = "var(--danger)";
  } else if (MODE === "simulation") {
    verdictEl.textContent = result.passed ? "✓ Cleared — Technical Interview unlocked" : `✕ Below cutoff (${result.cutoff}%)`;
    verdictEl.style.color = result.passed ? "var(--success)" : "var(--danger)";
  } else {
    verdictEl.textContent = result.passed ? "Above cutoff benchmark" : "Below cutoff benchmark";
    verdictEl.style.color = "var(--text-faint)";
  }

  document.getElementById("bd-correctness").textContent = `${result.correctness}%`;
  document.getElementById("bd-complexity").textContent = `${result.complexity}%`;
  document.getElementById("bd-quality").textContent = `${result.code_quality}%`;
  document.getElementById("bd-speed").textContent = `${result.speed}%`;
  document.getElementById("bd-tests").textContent = `${result.tests_passed} / ${result.tests_total}`;
}

init();
