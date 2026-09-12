/**
 * HireMind AI — DSA Practice & Sandbox Controller
 */

let currentProblem = null;
let startTime = null;

document.addEventListener('DOMContentLoaded', async () => {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get('mode') || 'practice';

  await loadProblemsList(mode);

  const runBtn = document.getElementById('btn-run-code');
  const submitBtn = document.getElementById('btn-submit-code');
  const codeArea = document.getElementById('code-editor-textarea');

  if (runBtn) runBtn.addEventListener('click', handleRunCode);
  if (submitBtn) submitBtn.addEventListener('click', handleSubmitCode);

  // Tab key indentation support in textarea
  if (codeArea) {
    codeArea.addEventListener('keydown', (e) => {
      if (e.key === 'Tab') {
        e.preventDefault();
        const start = codeArea.selectionStart;
        const end = codeArea.selectionEnd;
        codeArea.value = codeArea.value.substring(0, start) + '    ' + codeArea.value.substring(end);
        codeArea.selectionStart = codeArea.selectionEnd = start + 4;
      }
    });
  }
});

async function loadProblemsList(mode) {
  const problemSelect = document.getElementById('dsa-problem-select');
  const container = document.getElementById('dsa-container');

  try {
    const data = await API.getDSAProblems(mode);
    const problems = data.problems || [];

    if (problemSelect) {
      problemSelect.innerHTML = problems.map(p => `
        <option value="${p.id}">${p.title} (${p.difficulty.toUpperCase()} - ${p.topic})</option>
      `).join('');

      if (problems.length > 0) {
        loadProblemDetail(problems[0].id);
      }

      problemSelect.addEventListener('change', (e) => {
        loadProblemDetail(parseInt(e.target.value));
      });
    }
  } catch (err) {
    if (container) {
      container.innerHTML = `
        <div class="glass-card" style="border-color:var(--color-red); padding:2rem; text-align:center;">
          <h3 style="color:var(--color-red);">Round Locked</h3>
          <p style="color:var(--text-muted); margin-top:0.5rem;">${err.message}</p>
          <a href="/dashboard" class="btn btn-secondary" style="margin-top:1rem;">Return to Roadmap</a>
        </div>
      `;
    }
  }
}

async function loadProblemDetail(problemId) {
  try {
    const problem = await API.getDSAProblemDetail(problemId);
    currentProblem = problem;
    startTime = Date.now();

    const titleEl = document.getElementById('problem-title');
    const diffBadge = document.getElementById('problem-diff-badge');
    const topicBadge = document.getElementById('problem-topic-badge');
    const statementEl = document.getElementById('problem-statement');
    const examplesEl = document.getElementById('problem-examples');
    const codeArea = document.getElementById('code-editor-textarea');
    const consoleEl = document.getElementById('test-console-output');

    if (titleEl) titleEl.textContent = problem.title;
    if (diffBadge) {
      diffBadge.textContent = problem.difficulty.toUpperCase();
      diffBadge.className = `badge ${problem.difficulty === 'easy' ? 'badge-green' : (problem.difficulty === 'medium' ? 'badge-amber' : 'badge-red')}`;
    }
    if (topicBadge) topicBadge.textContent = problem.topic;
    if (statementEl) statementEl.innerHTML = problem.statement;

    if (examplesEl && problem.examples) {
      examplesEl.innerHTML = problem.examples.map((ex, i) => `
        <div style="background:rgba(0,0,0,0.3); padding:0.75rem 1rem; border-radius:var(--radius-sm); margin-bottom:0.5rem; font-family:var(--font-mono); font-size:0.85rem;">
          <div style="color:var(--text-muted);">Example ${i + 1}:</div>
          <div style="color:#fff;">Input: ${ex.input}</div>
          <div style="color:#38bdf8;">Output: ${ex.output}</div>
        </div>
      `).join('');
    }

    if (codeArea) {
      codeArea.value = problem.starter_code || '';
    }
    if (consoleEl) {
      consoleEl.innerHTML = `Sandbox ready. Click 'Run' to test against public cases, or 'Submit' to grade.`;
    }
  } catch (err) {
    console.error('Failed to load problem detail:', err);
  }
}

async function handleRunCode() {
  if (!currentProblem) return;
  const code = document.getElementById('code-editor-textarea')?.value || '';
  const consoleEl = document.getElementById('test-console-output');

  if (consoleEl) consoleEl.innerHTML = `<span style="color:var(--text-muted);">Executing in isolated Python sandbox...</span>`;

  try {
    const res = await API.runDSACode(currentProblem.id, code);
    renderConsoleResults(res, false);
  } catch (err) {
    if (consoleEl) consoleEl.innerHTML = `<span style="color:var(--color-red);">Error: ${err.message}</span>`;
  }
}

async function handleSubmitCode() {
  if (!currentProblem) return;
  const code = document.getElementById('code-editor-textarea')?.value || '';
  const consoleEl = document.getElementById('test-console-output');
  const params = new URLSearchParams(window.location.search);
  const mode = params.get('mode') || 'practice';

  const timeTaken = Math.round((Date.now() - (startTime || Date.now())) / 1000);

  if (consoleEl) consoleEl.innerHTML = `<span style="color:var(--text-muted);">Grading full test suite (Public + Hidden test cases)...</span>`;

  try {
    const res = await API.submitDSACode({
      problem_id: currentProblem.id,
      code: code,
      time_taken_sec: timeTaken,
      mode: mode
    });
    renderConsoleResults(res.execution, true, res.score_details);
  } catch (err) {
    if (consoleEl) consoleEl.innerHTML = `<span style="color:var(--color-red);">Submission error: ${err.message}</span>`;
  }
}

function renderConsoleResults(execRes, isSubmit = false, scoreDetails = null) {
  const consoleEl = document.getElementById('test-console-output');
  if (!consoleEl) return;

  const passed = execRes.all_passed;
  let html = `
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;">
      <span class="badge ${passed ? 'badge-green' : 'badge-red'}" style="font-size:0.85rem;">
        ${passed ? '✓ ALL TEST CASES PASSED' : '✗ SOME TEST CASES FAILED'} (${execRes.passed_tests}/${execRes.total_tests})
      </span>
      <span style="font-size:0.8rem; color:var(--text-subtle);">Avg Runtime: ${execRes.average_runtime_ms} ms</span>
    </div>
  `;

  if (isSubmit && scoreDetails) {
    html += `
      <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-subtle); border-radius:var(--radius-sm); padding:0.75rem 1rem; margin-bottom:0.75rem;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="color:#fff;">DSA Round Score: ${scoreDetails.score} / 100</strong>
          <span class="badge ${scoreDetails.passed ? 'badge-green' : 'badge-red'}">${scoreDetails.passed ? 'Cutoff Cleared' : 'Below Cutoff'}</span>
        </div>
        <div style="display:grid; grid-template-columns:repeat(4, 1fr); gap:0.5rem; font-size:0.78rem; color:var(--text-muted); margin-top:0.5rem;">
          <div>Correctness: ${scoreDetails.correctness}%</div>
          <div>Complexity: ${scoreDetails.complexity}%</div>
          <div>Code Quality: ${scoreDetails.code_quality}%</div>
          <div>Speed: ${scoreDetails.speed}%</div>
        </div>
      </div>
    `;
  }

  html += `<div style="display:flex; flex-direction:column; gap:0.4rem;">`;
  (execRes.details || []).forEach(d => {
    html += `
      <div style="padding:0.4rem 0.6rem; border-radius:4px; background:${d.passed ? 'rgba(16,185,129,0.08)' : 'rgba(239,68,68,0.08)'}; font-size:0.8rem;">
        Test ${d.test_index}: ${d.passed ? '<span style="color:#34d399;">Passed</span>' : '<span style="color:#f87171;">Failed (' + (d.error || 'Expected: ' + JSON.stringify(d.expected) + ', Got: ' + JSON.stringify(d.actual)) + ')</span>'}
      </div>
    `;
  });
  html += `</div>`;

  consoleEl.innerHTML = html;
}
