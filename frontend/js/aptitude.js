const params = new URLSearchParams(window.location.search);
const MODE = params.get("mode") === "simulation" ? "simulation" : "practice";
const TRACK = params.get("track") || "default";

let questions = [];
let answers = {};       // { questionId: optionIndex }
let currentIndex = 0;
let timeLimitSeconds = 900;
let timerInterval = null;
let deadline = null;

const introView = document.getElementById("intro-view");
const questionView = document.getElementById("question-view");
const resultView = document.getElementById("result-view");
const timerEl = document.getElementById("timer");

async function init() {
  const user = await requireAuth();
  if (!user) return;

  document.getElementById("mode-pill").textContent = MODE.toUpperCase();
  document.getElementById("mode-pill").className = "pill " + (MODE === "simulation" ? "pill-hard" : "pill-easy");
  document.getElementById("intro-mode-note").textContent = MODE === "simulation"
    ? `Simulation Mode — you need to clear this round's cutoff to unlock DSA. (Track: ${TRACK})`
    : "Practice Mode — this attempt doesn't affect round unlocking.";

  document.getElementById("start-btn").addEventListener("click", startRound);
  document.getElementById("prev-btn").addEventListener("click", () => navigate(-1));
  document.getElementById("next-btn").addEventListener("click", () => navigate(1));
  document.getElementById("submit-btn").addEventListener("click", submitRound);
  document.getElementById("retry-btn").addEventListener("click", () => window.location.reload());
}

async function startRound() {
  try {
    const data = await API.post("/api/aptitude/start", { mode: MODE, track: TRACK });
    questions = data.questions;
    timeLimitSeconds = data.time_limit_seconds;
    answers = {};
    currentIndex = 0;

    introView.style.display = "none";
    questionView.style.display = "block";

    deadline = Date.now() + timeLimitSeconds * 1000;
    startTimer();
    renderQuestion();
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
      submitRound();
      return;
    }
    timerEl.textContent = fmtSeconds(remaining);
    timerEl.classList.toggle("is-low", remaining < 60);
  }, 500);
}

function renderQuestion() {
  const q = questions[currentIndex];
  document.getElementById("q-progress").textContent =
    `QUESTION ${currentIndex + 1} / ${questions.length}`;
  document.getElementById("q-progress-fill").style.width =
    `${((currentIndex) / questions.length) * 100}%`;

  document.getElementById("q-topic-pill").textContent = `${q.topic} · ${q.difficulty}`;
  document.getElementById("q-topic-pill").className =
    "pill pill-" + q.difficulty;
  document.getElementById("q-text").textContent = q.question;

  const optionsEl = document.getElementById("q-options");
  optionsEl.innerHTML = q.options.map((opt, i) => `
    <div class="option ${answers[q.id] === i ? "is-selected" : ""}" data-idx="${i}">
      <span class="option-key">${String.fromCharCode(65 + i)}</span>
      <span>${opt}</span>
    </div>
  `).join("");

  optionsEl.querySelectorAll(".option").forEach(el => {
    el.addEventListener("click", () => {
      answers[q.id] = parseInt(el.dataset.idx, 10);
      renderQuestion();
    });
  });

  document.getElementById("prev-btn").style.visibility = currentIndex === 0 ? "hidden" : "visible";
  const isLast = currentIndex === questions.length - 1;
  document.getElementById("next-btn").style.display = isLast ? "none" : "inline-flex";
  document.getElementById("submit-btn").style.display = isLast ? "inline-flex" : "none";
}

function navigate(delta) {
  currentIndex = Math.max(0, Math.min(questions.length - 1, currentIndex + delta));
  renderQuestion();
}

async function submitRound() {
  clearInterval(timerInterval);
  document.getElementById("submit-btn").disabled = true;

  const payloadAnswers = {};
  Object.keys(answers).forEach(qid => { payloadAnswers[qid] = answers[qid]; });

  try {
    const result = await API.post("/api/aptitude/submit", { answers: payloadAnswers });
    renderResult(result);
  } catch (err) {
    alert(err.message);
  }
}

function renderResult(result) {
  questionView.style.display = "none";
  resultView.style.display = "block";

  const scoreEl = document.getElementById("result-score");
  scoreEl.textContent = `${result.score}%`;
  scoreEl.classList.add(result.passed ? "is-pass" : "is-fail");

  const verdictEl = document.getElementById("result-verdict");
  if (MODE === "simulation") {
    verdictEl.textContent = result.passed ? "✓ Cleared — DSA unlocked" : `✕ Below cutoff (${result.cutoff}%)`;
    verdictEl.style.color = result.passed ? "var(--success)" : "var(--danger)";
  } else {
    verdictEl.textContent = result.passed ? "Above cutoff benchmark" : "Below cutoff benchmark";
    verdictEl.style.color = "var(--text-faint)";
  }

  document.getElementById("bd-accuracy").textContent = `${result.accuracy}%`;
  document.getElementById("bd-speed").textContent = `${result.speed}%`;
  document.getElementById("bd-difficulty").textContent = `${result.difficulty}%`;
  document.getElementById("bd-correct").textContent = `${result.correct_count} / ${result.total_questions}`;

  if (result.weak_topics && result.weak_topics.length) {
    document.getElementById("weak-areas-card").style.display = "block";
    document.getElementById("weak-topics").innerHTML = result.weak_topics
      .map(t => `<span class="topic-tag">${t}</span>`).join("");
  }

  const reviewList = document.getElementById("review-list");
  reviewList.innerHTML = result.per_question.map((pq, i) => {
    const q = questions.find(q => q.id === pq.id);
    const optionsHtml = q.options.map((opt, idx) => {
      let cls = "option";
      if (idx === pq.correct_answer) cls += " is-correct";
      else if (idx === pq.given_answer && !pq.correct) cls += " is-wrong";
      return `<div class="${cls}"><span class="option-key">${String.fromCharCode(65+idx)}</span><span>${opt}</span></div>`;
    }).join("");
    return `
      <div class="card" style="padding:18px;">
        <div class="row-between" style="margin-bottom:10px;">
          <span class="text-faint" style="font-family:var(--font-mono); font-size:0.78rem;">Q${i+1} · ${pq.topic}</span>
          <span class="status-light ${pq.correct ? "is-cleared" : "is-danger"}"></span>
        </div>
        <p style="color:var(--text); margin-bottom:12px;">${q.question}</p>
        ${optionsHtml}
        ${pq.explanation ? `<p class="text-dim" style="margin-top:12px; font-size:0.85rem;">${pq.explanation}</p>` : ""}
      </div>`;
  }).join("");
}

init();
