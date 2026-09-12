/**
 * HireMind AI — Live Interview Simulator Controller (Module B)
 * Handles Web Speech Recognition, SpeechSynthesis, Waveform Animation, and Follow-up turns.
 */

let currentSessionId = null;
let currentQuestionId = null;
let speechRecognizer = null;
let isRecording = false;

document.addEventListener('DOMContentLoaded', () => {
  const initBtn = document.getElementById('btn-init-interview');
  const startBtn = document.getElementById('btn-start-interview');
  const micBtn = document.getElementById('btn-mic-toggle');
  const submitAnswerBtn = document.getElementById('btn-submit-answer');
  const endSessionBtn = document.getElementById('btn-end-session');

  if (initBtn) initBtn.addEventListener('click', handleInitializeSession);
  if (startBtn) startBtn.addEventListener('click', handleStartInterview);
  if (micBtn) micBtn.addEventListener('click', toggleMicRecording);
  if (submitAnswerBtn) submitAnswerBtn.addEventListener('click', handleSubmitAnswer);
  if (endSessionBtn) endSessionBtn.addEventListener('click', handleEndInterview);

  initSpeechRecognition();
});

function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn('Web Speech API is not supported in this browser. Falling back to text input.');
    return;
  }

  speechRecognizer = new SpeechRecognition();
  speechRecognizer.continuous = true;
  speechRecognizer.interimResults = true;
  speechRecognizer.lang = 'en-US';

  speechRecognizer.onresult = (event) => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      transcript += event.results[i][0].transcript;
    }
    const answerInput = document.getElementById('candidate-answer-input');
    if (answerInput) {
      answerInput.value = transcript;
    }
  };

  speechRecognizer.onerror = (err) => {
    console.error('Speech recognition error:', err);
    stopMicRecording();
  };

  speechRecognizer.onend = () => {
    if (isRecording) {
      speechRecognizer.start();
    }
  };
}

function toggleMicRecording() {
  if (!speechRecognizer) {
    alert('Voice input is not supported in this browser. Please type your response.');
    return;
  }

  if (isRecording) {
    stopMicRecording();
  } else {
    startMicRecording();
  }
}

function startMicRecording() {
  try {
    isRecording = true;
    speechRecognizer.start();
    const micBtn = document.getElementById('btn-mic-toggle');
    const waveEl = document.getElementById('waveform-anim');
    if (micBtn) micBtn.classList.add('recording');
    if (waveEl) waveEl.classList.add('waveform-active');
  } catch (err) {
    console.error('Mic start error:', err);
  }
}

function stopMicRecording() {
  isRecording = false;
  try { speechRecognizer.stop(); } catch (e) {}
  const micBtn = document.getElementById('btn-mic-toggle');
  const waveEl = document.getElementById('waveform-anim');
  if (micBtn) micBtn.classList.remove('recording');
  if (waveEl) waveEl.classList.remove('waveform-active');
}

function speakQuestionText(text, voicePref = 'male') {
  if (!window.speechSynthesis) return;
  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.0;
  utterance.pitch = voicePref === 'female' ? 1.2 : 0.95;

  const waveEl = document.getElementById('waveform-anim');
  utterance.onstart = () => { if (waveEl) waveEl.classList.add('waveform-active'); };
  utterance.onend = () => { if (waveEl && !isRecording) waveEl.classList.remove('waveform-active'); };

  window.speechSynthesis.speak(utterance);
}

async function handleInitializeSession() {
  const roleInput = document.getElementById('target-role-select');
  const trackInput = document.getElementById('company-track-select');
  const statusBox = document.getElementById('setup-status');
  
  // Use last parsed resume ID or default
  const resumeId = localStorage.getItem('hiremind_resume_id') || 'dev-resume-default';
  const targetRole = roleInput ? roleInput.value : 'Software Engineer';
  const companyTrack = trackInput ? trackInput.value : 'default';

  const params = new URLSearchParams(window.location.search);
  const mode = params.get('mode') || 'practice';

  if (statusBox) {
    statusBox.style.display = 'block';
    statusBox.innerHTML = `<p style="color:var(--text-muted);">Generating grounded question bank via InterviewPlanningAgent & kb_interview_questions...</p>`;
  }

  try {
    const res = await API.generateInterviewPlan({
      resume_id: resumeId,
      target_role: targetRole,
      company_track: companyTrack,
      mode: mode
    });

    currentSessionId = res.session_id;
    if (statusBox) {
      statusBox.innerHTML = `
        <div style="color:var(--color-green); font-weight:600;">
          ✓ Question bank ready (${res.questions_count} questions generated). Grounded in real FAANG/Tier-1 question sets.
        </div>
      `;
    }

    const setupCard = document.getElementById('interview-setup-card');
    const startBtn = document.getElementById('btn-start-interview');
    if (setupCard) setupCard.style.display = 'none';
    if (startBtn) startBtn.style.display = 'inline-flex';

    // Auto-start
    handleStartInterview();
  } catch (err) {
    if (statusBox) {
      statusBox.innerHTML = `<div style="color:var(--color-red); font-weight:600;">❌ ${err.message}</div>`;
    }
  }
}

async function handleStartInterview() {
  if (!currentSessionId) return;

  const roomCard = document.getElementById('interview-room-card');
  const voicePref = document.getElementById('voice-pref-select')?.value || 'male';

  try {
    const data = await API.startInterview(currentSessionId, voicePref);
    currentQuestionId = data.question_id;

    if (roomCard) roomCard.style.display = 'block';

    renderActiveQuestion(data.question_text, data.stage, data.topic);
    speakQuestionText(data.question_text, voicePref);
  } catch (err) {
    alert(`Failed to start interview: ${err.message}`);
  }
}

function renderActiveQuestion(questionText, stage = 'technical', topic = 'General') {
  const qTextEl = document.getElementById('active-question-text');
  const stageBadgeEl = document.getElementById('active-stage-badge');
  const topicBadgeEl = document.getElementById('active-topic-badge');
  const answerInput = document.getElementById('candidate-answer-input');

  if (qTextEl) qTextEl.textContent = questionText;
  if (stageBadgeEl) stageBadgeEl.textContent = `Stage: ${stage.toUpperCase()}`;
  if (topicBadgeEl) topicBadgeEl.textContent = `Topic: ${topic}`;
  if (answerInput) {
    answerInput.value = '';
    answerInput.focus();
  }
}

async function handleSubmitAnswer() {
  const answerInput = document.getElementById('candidate-answer-input');
  const statusEl = document.getElementById('turn-status');
  const answerText = answerInput ? answerInput.value.trim() : '';

  if (!answerText) {
    alert('Please enter or speak your answer before submitting.');
    return;
  }

  stopMicRecording();

  if (statusEl) {
    statusEl.innerHTML = `<span style="color:var(--text-muted);">Evaluating answer with Stage Specialist Agent...</span>`;
  }

  try {
    const res = await API.submitInterviewAnswer(currentSessionId, currentQuestionId, answerText);

    // Append completed turn to history
    appendTranscriptTurn('Candidate', answerText);

    if (res.session_complete) {
      if (statusEl) statusEl.innerHTML = `<span style="color:var(--color-green); font-weight:600;">Interview session concluded!</span>`;
      handleEndInterview();
      return;
    }

    // Check if it's a follow-up probe (CROSS_QUESTION)
    if (res.is_followup) {
      if (statusEl) {
        statusEl.innerHTML = `
          <div class="badge badge-amber" style="margin-bottom:0.5rem;">⚡ Specialist Agent Follow-up Probe Triggered</div>
        `;
      }
    } else {
      if (statusEl) statusEl.innerHTML = '';
    }

    currentQuestionId = res.question_id;
    renderActiveQuestion(res.question_text, res.stage, res.topic);
    speakQuestionText(res.question_text);
    appendTranscriptTurn('Interviewer', res.question_text, res.is_followup);

  } catch (err) {
    if (statusEl) {
      statusEl.innerHTML = `<span style="color:var(--color-red);">Error: ${err.message}</span>`;
    }
  }
}

function appendTranscriptTurn(speaker, text, isFollowup = false) {
  const transcriptList = document.getElementById('transcript-history');
  if (!transcriptList) return;

  const bubble = document.createElement('div');
  bubble.className = `transcript-bubble ${speaker.toLowerCase()}`;
  bubble.innerHTML = `
    <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:0.35rem;">
      <strong style="color:${speaker === 'Interviewer' ? 'var(--color-accent)' : 'var(--color-green)'};">${speaker} ${isFollowup ? '(Deep Probe Follow-up)' : ''}</strong>
      <span style="color:var(--text-subtle);">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
    </div>
    <p style="font-size:0.92rem; color:#fff;">${text}</p>
  `;
  transcriptList.prepend(bubble);
}

async function handleEndInterview() {
  if (!currentSessionId) return;

  const roomCard = document.getElementById('interview-room-card');
  const reportCard = document.getElementById('debrief-report-card');
  if (roomCard) roomCard.style.display = 'none';
  if (reportCard) {
    reportCard.style.display = 'block';
    reportCard.innerHTML = `<div class="glass-card" style="text-align:center; padding:2rem;"><h3>Compiling Bar-Raiser Debrief Report...</h3></div>`;
  }

  try {
    const report = await API.endInterview(currentSessionId);
    renderDebriefReport(report);
  } catch (err) {
    if (reportCard) {
      reportCard.innerHTML = `<div class="glass-card" style="color:var(--color-red);">Error finalizing report: ${err.message}</div>`;
    }
  }
}

function renderDebriefReport(report) {
  const reportCard = document.getElementById('debrief-report-card');
  if (!reportCard) return;

  const overall = report.overall_score || 8.0;
  const topics = report.topic_scores || [];
  const strengths = report.strengths || [];
  const improvements = report.improvement_recommendations || [];

  reportCard.innerHTML = `
    <div class="glass-card" style="padding:2.5rem;">
      <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-subtle); padding-bottom:1.5rem; margin-bottom:1.5rem;">
        <div>
          <h2>Executive Interview Debrief Report</h2>
          <p style="color:var(--text-muted); margin-top:0.25rem;">Multi-Agent Evaluated & Grounded in Bar-Raiser Rubrics</p>
        </div>
        <div class="score-circle" style="width:110px; height:110px; border-color:var(--color-green);">
          <div class="score-num" style="color:var(--color-green);">${overall}</div>
          <div class="score-denom">OUT OF 10.0</div>
        </div>
      </div>

      <div style="margin-bottom:2rem;">
        <h4 style="color:#fff; margin-bottom:0.5rem;">Executive Summary</h4>
        <p style="color:var(--text-main); line-height:1.7; background:rgba(255,255,255,0.02); padding:1.25rem; border-radius:var(--radius-md); border:1px solid var(--border-subtle);">
          ${report.summary_text || 'Solid interview performance demonstrating good conceptual grasp and clear communication.'}
        </p>
      </div>

      <div style="margin-bottom:2rem;">
        <h4 style="color:#fff; margin-bottom:1rem;">Topic & Competency Breakdown</h4>
        <div style="display:flex; flex-direction:column; gap:0.85rem;">
          ${topics.map(t => `
            <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:1rem 1.25rem;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
                <strong style="color:#fff;">${t.topic}</strong>
                <span class="badge ${t.score >= 8 ? 'badge-green' : (t.score >= 6.5 ? 'badge-amber' : 'badge-red')}">${t.score} / 10.0</span>
              </div>
              <p style="font-size:0.88rem; color:var(--text-muted); margin-bottom:0.4rem;">${t.justification || ''}</p>
              ${t.evidence_excerpt ? `
                <div style="font-size:0.8rem; color:var(--text-subtle); font-style:italic; border-left:2px solid var(--border-glass); padding-left:0.6rem;">
                  "${t.evidence_excerpt}"
                </div>
              ` : ''}
            </div>
          `).join('')}
        </div>
      </div>

      <div class="grid-2" style="margin-bottom:2rem;">
        <div class="glass-card" style="padding:1.25rem;">
          <h4 style="color:var(--color-green); margin-bottom:0.75rem;">✓ Top Strengths</h4>
          <ul style="list-style:none; line-height:1.8; font-size:0.9rem; color:var(--text-main);">
            ${strengths.map(s => `<li>• ${s}</li>`).join('')}
          </ul>
        </div>
        <div class="glass-card" style="padding:1.25rem;">
          <h4 style="color:var(--color-amber); margin-bottom:0.75rem;">⚡ Targeted Improvements</h4>
          <ul style="list-style:none; line-height:1.8; font-size:0.9rem; color:var(--text-main);">
            ${improvements.map(imp => `<li>• ${imp}</li>`).join('')}
          </ul>
        </div>
      </div>

      <div style="display:flex; justify-content:center; gap:1rem;">
        <a href="/dashboard" class="btn btn-primary">Return to Readiness Dashboard</a>
      </div>
    </div>
  `;
}
