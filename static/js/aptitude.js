/**
 * HireMind AI — Aptitude Test Controller
 */

let testQuestions = [];
let currentIndex = 0;
let userAnswers = {};
let timerInterval = null;
let secondsRemaining = 15 * 60;

document.addEventListener('DOMContentLoaded', async () => {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get('mode') || 'practice';

  await loadTestQuestions(mode);

  const prevBtn = document.getElementById('btn-prev-q');
  const nextBtn = document.getElementById('btn-next-q');
  const submitBtn = document.getElementById('btn-submit-aptitude');

  if (prevBtn) prevBtn.addEventListener('click', () => navigateQuestion(-1));
  if (nextBtn) nextBtn.addEventListener('click', () => navigateQuestion(1));
  if (submitBtn) submitBtn.addEventListener('click', handleSubmitTest);
});

async function loadTestQuestions(mode) {
  const container = document.getElementById('aptitude-quiz-container');
  try {
    const data = await API.getAptitudeQuestions(mode);
    testQuestions = data.questions || [];

    if (testQuestions.length === 0) {
      if (container) container.innerHTML = `<p style="color:var(--text-red);">No questions available.</p>`;
      return;
    }

    startTimer(data.duration_minutes || 15);
    renderQuestion(0);
    renderQuestionPalette();
  } catch (err) {
    if (container) {
      container.innerHTML = `
        <div class="glass-card" style="border-color:var(--color-red); padding:2rem; text-align:center;">
          <h3 style="color:var(--color-red);">Access Locked</h3>
          <p style="color:var(--text-muted); margin-top:0.5rem;">${err.message}</p>
          <a href="/dashboard" class="btn btn-secondary" style="margin-top:1rem;">Return to Dashboard</a>
        </div>
      `;
    }
  }
}

function startTimer(durationMinutes) {
  secondsRemaining = durationMinutes * 60;
  const timerEl = document.getElementById('test-timer-display');

  clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    secondsRemaining--;
    if (secondsRemaining <= 0) {
      clearInterval(timerInterval);
      handleSubmitTest();
      return;
    }

    const mins = Math.floor(secondsRemaining / 60);
    const secs = secondsRemaining % 60;
    if (timerEl) {
      timerEl.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
  }, 1000);
}

function renderQuestion(index) {
  if (index < 0 || index >= testQuestions.length) return;
  currentIndex = index;

  const q = testQuestions[currentIndex];
  const qNumEl = document.getElementById('current-q-num');
  const qTopicEl = document.getElementById('current-q-topic');
  const qDiffEl = document.getElementById('current-q-diff');
  const qTextEl = document.getElementById('current-q-text');
  const optionsEl = document.getElementById('current-options-container');

  if (qNumEl) qNumEl.textContent = `Question ${currentIndex + 1} of ${testQuestions.length}`;
  if (qTopicEl) qTopicEl.textContent = q.topic.toUpperCase();
  if (qDiffEl) qDiffEl.textContent = q.difficulty.toUpperCase();
  if (qTextEl) qTextEl.textContent = q.question;

  if (optionsEl) {
    const chosen = userAnswers[String(q.id)];
    optionsEl.innerHTML = q.options.map((opt, oIdx) => `
      <label class="glass-card" style="display:flex; align-items:center; gap:1rem; padding:1rem 1.25rem; margin-bottom:0.75rem; cursor:pointer; background:${chosen === oIdx ? 'rgba(99,102,241,0.15)' : 'var(--bg-glass-card)'}; border-color:${chosen === oIdx ? 'var(--color-primary)' : 'var(--border-subtle)'};">
        <input type="radio" name="opt-${q.id}" value="${oIdx}" ${chosen === oIdx ? 'checked' : ''} onchange="handleOptionSelect(${q.id}, ${oIdx})" style="accent-color:var(--color-primary);">
        <span style="font-size:0.95rem; color:#fff;"><strong>${String.fromCharCode(65 + oIdx)}.</strong> ${opt}</span>
      </label>
    `).join('');
  }

  // Update navigation button states
  const prevBtn = document.getElementById('btn-prev-q');
  const nextBtn = document.getElementById('btn-next-q');
  if (prevBtn) prevBtn.disabled = (currentIndex === 0);
  if (nextBtn) nextBtn.disabled = (currentIndex === testQuestions.length - 1);

  renderQuestionPalette();
}

function handleOptionSelect(qId, optionIdx) {
  userAnswers[String(qId)] = optionIdx;
  renderQuestion(currentIndex);
}

function navigateQuestion(delta) {
  renderQuestion(currentIndex + delta);
}

function renderQuestionPalette() {
  const paletteEl = document.getElementById('question-palette');
  if (!paletteEl) return;

  paletteEl.innerHTML = testQuestions.map((q, idx) => {
    const isAnswered = userAnswers[String(q.id)] !== undefined;
    const isCurrent = (idx === currentIndex);
    return `
      <button onclick="renderQuestion(${idx})" style="width:36px; height:36px; border-radius:8px; border:1px solid ${isCurrent ? 'var(--color-accent)' : 'var(--border-subtle)'}; background:${isAnswered ? 'rgba(16,185,129,0.2)' : 'rgba(255,255,255,0.03)'}; color:${isAnswered ? '#34d399' : '#fff'}; font-weight:700; cursor:pointer;">
        ${idx + 1}
      </button>
    `;
  }).join('');
}

async function handleSubmitTest() {
  clearInterval(timerInterval);
  const timeTaken = (15 * 60) - secondsRemaining;
  const params = new URLSearchParams(window.location.search);
  const mode = params.get('mode') || 'practice';

  const container = document.getElementById('aptitude-quiz-container');
  const resultsContainer = document.getElementById('aptitude-results-card');

  if (container) container.style.display = 'none';
  if (resultsContainer) {
    resultsContainer.style.display = 'block';
    resultsContainer.innerHTML = `<div class="glass-card" style="text-align:center; padding:2rem;"><h3>Grading Aptitude Round...</h3></div>`;
  }

  try {
    const res = await API.submitAptitudeTest({
      answers: userAnswers,
      time_taken_sec: timeTaken,
      mode: mode
    });

    if (resultsContainer) {
      resultsContainer.innerHTML = `
        <div class="glass-card" style="padding:2.5rem;">
          <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-subtle); padding-bottom:1.5rem; margin-bottom:1.5rem;">
            <div>
              <h2>Aptitude Round Results</h2>
              <p style="color:var(--text-muted); margin-top:0.25rem;">
                ${res.passed ? '🎉 Congratulations! You cleared the Aptitude round cutoff.' : 'Keep practicing. You did not meet the simulation cutoff.'}
              </p>
            </div>
            <div class="score-circle" style="width:110px; height:110px; border-color:${res.passed ? 'var(--color-green)' : 'var(--color-red)'};">
              <div class="score-num" style="color:${res.passed ? 'var(--color-green)' : 'var(--color-red)'};">${res.score}</div>
              <div class="score-denom">OUT OF 100</div>
            </div>
          </div>

          <div class="grid-3" style="margin-bottom:2rem;">
            <div class="glass-card" style="padding:1.25rem; text-align:center;">
              <span style="font-size:0.8rem; color:var(--text-muted);">ACCURACY (60% Wt)</span>
              <div class="mono-num" style="font-size:1.8rem; color:#fff; margin-top:0.35rem;">${res.accuracy}%</div>
              <span style="font-size:0.8rem; color:var(--text-subtle);">${res.correct_count} / ${res.total_questions} correct</span>
            </div>
            <div class="glass-card" style="padding:1.25rem; text-align:center;">
              <span style="font-size:0.8rem; color:var(--text-muted);">SPEED (20% Wt)</span>
              <div class="mono-num" style="font-size:1.8rem; color:#fff; margin-top:0.35rem;">${res.speed}%</div>
              <span style="font-size:0.8rem; color:var(--text-subtle);">${Math.floor(timeTaken / 60)}m ${timeTaken % 60}s elapsed</span>
            </div>
            <div class="glass-card" style="padding:1.25rem; text-align:center;">
              <span style="font-size:0.8rem; color:var(--text-muted);">DIFFICULTY (20% Wt)</span>
              <div class="mono-num" style="font-size:1.8rem; color:#fff; margin-top:0.35rem;">${res.difficulty}%</div>
              <span style="font-size:0.8rem; color:var(--text-subtle);">Calibrated weighting</span>
            </div>
          </div>

          <h4 style="color:#fff; margin-bottom:1rem;">Question Review & Explanations</h4>
          <div style="display:flex; flex-direction:column; gap:0.75rem; max-height:400px; overflow-y:auto; padding-right:0.5rem; margin-bottom:2rem;">
            ${(res.details || []).map((d, i) => `
              <div style="background:rgba(255,255,255,0.02); border:1px solid ${d.is_correct ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}; border-radius:var(--radius-md); padding:1rem 1.25rem;">
                <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
                  <strong style="color:#fff;">Q${i + 1}: ${d.question}</strong>
                  <span class="badge ${d.is_correct ? 'badge-green' : 'badge-red'}">${d.is_correct ? 'Correct' : 'Incorrect'}</span>
                </div>
                <div style="font-size:0.85rem; color:var(--text-muted); margin-top:0.25rem;">
                  Your Answer: ${d.user_choice !== undefined ? 'Option ' + String.fromCharCode(65 + d.user_choice) : 'Skipped'} | Correct: Option ${String.fromCharCode(65 + d.correct_option)}
                </div>
                <div style="font-size:0.82rem; color:var(--text-subtle); margin-top:0.4rem; background:rgba(0,0,0,0.3); padding:0.5rem; border-radius:4px;">
                  💡 ${d.explanation}
                </div>
              </div>
            `).join('')}
          </div>

          <div style="display:flex; justify-content:center; gap:1rem;">
            <a href="/dashboard" class="btn btn-primary">Return to Roadmap Dashboard</a>
          </div>
        </div>
      `;
    }
  } catch (err) {
    alert(`Submission error: ${err.message}`);
  }
}
