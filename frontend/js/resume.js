/**
 * HireMind AI — Resume Intelligence Controller (Module A)
 */

document.addEventListener('DOMContentLoaded', () => {
  const uploadForm = document.getElementById('resume-upload-form');
  const fileInput = document.getElementById('resume-file-input');
  const dropZone = document.getElementById('drop-zone');
  const jdInput = document.getElementById('target-jd-input');
  const rewriteBtn = document.getElementById('btn-rewrite-bullet');

  if (dropZone && fileInput) {
    dropZone.addEventListener('click', () => fileInput.click());
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.borderColor = 'var(--color-primary)'; });
    dropZone.addEventListener('dragleave', () => { dropZone.style.borderColor = 'var(--border-subtle)'; });
    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.style.borderColor = 'var(--border-subtle)';
      if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        handleFileUpload();
      }
    });
    fileInput.addEventListener('change', handleFileUpload);
  }

  if (rewriteBtn) {
    rewriteBtn.addEventListener('click', handleBulletRewrite);
  }
});

async function handleFileUpload() {
  const fileInput = document.getElementById('resume-file-input');
  const jdInput = document.getElementById('target-jd-input');
  const statusEl = document.getElementById('pipeline-status');
  const resultsEl = document.getElementById('analysis-results');

  if (!fileInput.files || fileInput.files.length === 0) return;
  const file = fileInput.files[0];

  const formData = new FormData();
  formData.append('file', file);
  if (jdInput && jdInput.value.trim()) {
    formData.append('job_description', jdInput.value.trim());
  }

  if (statusEl) {
    statusEl.style.display = 'block';
    statusEl.innerHTML = `
      <div class="glass-card" style="text-align:center; padding:2rem;">
        <div style="font-size:2rem; margin-bottom:1rem; animation:spin 2s linear infinite;">⚡</div>
        <h3>Executing Multi-Agent Resume Analysis...</h3>
        <p style="color:var(--text-muted); margin-top:0.5rem;" id="agent-step-text">Ingesting document & layout coordinates via ParsingAgent...</p>
      </div>
    `;
  }
  if (resultsEl) resultsEl.style.display = 'none';

  try {
    // Step simulation
    setTimeout(() => { const s = document.getElementById('agent-step-text'); if (s) s.textContent = 'Grounding canonical skills against kb_skills_taxonomy...'; }, 1000);
    setTimeout(() => { const s = document.getElementById('agent-step-text'); if (s) s.textContent = 'Calculating ATS+ 105-point analytical rubric...'; }, 2200);

    const result = await API.uploadResume(formData);
    
    // Save last analyzed resume ID in localStorage for IntervAI session
    localStorage.setItem('hiremind_resume_id', result.resume_id);
    localStorage.setItem('hiremind_candidate_profile', JSON.stringify(result));

    if (statusEl) statusEl.style.display = 'none';
    if (resultsEl) {
      resultsEl.style.display = 'block';
      renderAnalysisResults(result);
    }
  } catch (err) {
    if (statusEl) {
      statusEl.innerHTML = `
        <div class="glass-card" style="border-color:var(--color-red); padding:1.5rem; text-align:center;">
          <h4 style="color:var(--color-red);">Analysis Failed</h4>
          <p style="color:var(--text-muted); margin-top:0.5rem;">${err.message}</p>
        </div>
      `;
    }
  }
}

function renderAnalysisResults(data) {
  const scores = data.ats_scores || {};
  const personal = data.personal_info || {};
  const skills = data.skill_profile || {};
  const improvements = data.top_improvements || [];
  const jdMatch = data.job_match;

  // Header & Candidate Info
  const candNameEl = document.getElementById('cand-name');
  if (candNameEl) candNameEl.textContent = personal.name || 'Candidate';
  const candSummaryEl = document.getElementById('cand-summary');
  if (candSummaryEl) candSummaryEl.textContent = data.ai_summary || '';

  // ATS+ Overall Score
  const scoreNumEl = document.getElementById('ats-overall-num');
  if (scoreNumEl) scoreNumEl.textContent = Math.round(scores.overall_score || 0);

  // Rubric Bars
  const maxRubric = {
    'ats_compatibility': { max: 15, label: 'ATS Compatibility' },
    'resume_structure': { max: 15, label: 'Resume Structure' },
    'keyword_relevance': { max: 20, label: 'Keyword / Job Relevance' },
    'content_quality': { max: 15, label: 'Content Quality & Verbs' },
    'skills_representation': { max: 10, label: 'Skills Categorization' },
    'quantified_impact': { max: 10, label: 'Quantified Impact' },
    'completeness': { max: 10, label: 'Section Completeness' },
    'readability_consistency': { max: 5, label: 'Readability & Layout' }
  };

  const rubricContainer = document.getElementById('rubric-bars-container');
  if (rubricContainer) {
    rubricContainer.innerHTML = Object.entries(maxRubric).map(([k, meta]) => {
      const val = scores[k] || 0;
      const pct = Math.round((val / meta.max) * 100);
      return `
        <div class="rubric-bar">
          <div class="rubric-header">
            <span>${meta.label}</span>
            <span class="mono-num">${val} / ${meta.max} pts</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" style="width: ${pct}%;"></div>
          </div>
        </div>
      `;
    }).join('');
  }

  // Categorized Skills Cloud
  const skillsContainer = document.getElementById('skills-cloud-container');
  if (skillsContainer && skills.categorized_skills) {
    skillsContainer.innerHTML = Object.entries(skills.categorized_skills).map(([cat, list]) => {
      if (!list || list.length === 0) return '';
      return `
        <div style="margin-bottom:1rem;">
          <h5 style="color:var(--text-muted); font-size:0.85rem; margin-bottom:0.5rem;">${cat.toUpperCase()}</h5>
          <div style="display:flex; flex-wrap:wrap; gap:0.4rem;">
            ${list.map(s => `<span class="badge badge-blue">${s}</span>`).join('')}
          </div>
        </div>
      `;
    }).join('');
  }

  // Top Improvements List
  const impContainer = document.getElementById('improvements-list-container');
  if (impContainer) {
    impContainer.innerHTML = improvements.map(imp => `
      <div class="glass-card" style="padding:1rem 1.25rem; margin-bottom:0.75rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
          <span style="font-weight:700; color:#fff;">#${imp.priority} ${imp.title}</span>
          <span class="badge badge-amber">+${imp.impact_score} pts potential</span>
        </div>
        <p style="font-size:0.88rem; color:var(--text-muted);">${imp.description}</p>
      </div>
    `).join('');
  }

  // JD Match Section (if provided)
  const jdSection = document.getElementById('jd-match-section');
  if (jdSection) {
    if (jdMatch) {
      jdSection.style.display = 'block';
      const jdScoreEl = document.getElementById('jd-match-score');
      if (jdScoreEl) jdScoreEl.textContent = `${jdMatch.jd_match_score}%`;
      const jdSummaryEl = document.getElementById('jd-match-summary');
      if (jdSummaryEl) jdSummaryEl.textContent = jdMatch.fit_summary || '';
      
      const matchedSkillsEl = document.getElementById('jd-matched-skills');
      if (matchedSkillsEl) {
        matchedSkillsEl.innerHTML = (jdMatch.matched_required_skills || []).map(s => `<span class="badge badge-green">✓ ${s}</span>`).join(' ');
      }
      const missingSkillsEl = document.getElementById('jd-missing-skills');
      if (missingSkillsEl) {
        missingSkillsEl.innerHTML = (jdMatch.missing_required_skills || []).map(s => `<span class="badge badge-red">✗ ${s}</span>`).join(' ');
      }
    } else {
      jdSection.style.display = 'none';
    }
  }

  // Agent Audit Evidence Box
  const auditContainer = document.getElementById('resume-audit-evidence');
  if (auditContainer && data.agent_audit) {
    auditContainer.innerHTML = `
      <div class="glass-card" style="border-left:3px solid var(--color-primary); padding:1.25rem;">
        <h4 style="font-size:1rem; margin-bottom:0.75rem; color:#fff;">🛡️ Multi-Agent Explainability Citations</h4>
        <ul style="list-style:none; font-size:0.85rem; color:var(--text-muted); line-height:1.7;">
          <li>• <strong>ParsingAgent:</strong> ${data.agent_audit.parsing_agent?.citations?.[0] || 'Layout extracted'}</li>
          <li>• <strong>SkillExtractionAgent:</strong> ${data.agent_audit.skill_extraction_agent?.citations?.[0] || 'Taxonomy grounded'}</li>
          <li>• <strong>ATSScoringAgent:</strong> ${data.agent_audit.ats_scoring_agent?.citations?.[0] || 'Rubric scored'}</li>
          <li>• <strong>ImprovementAgent:</strong> ${data.agent_audit.improvement_agent?.citations?.[0] || 'Grounded in kb_resume_best_practices'}</li>
        </ul>
      </div>
    `;
  }
}

async function handleBulletRewrite() {
  const inputEl = document.getElementById('single-bullet-input');
  const roleEl = document.getElementById('bullet-role-context');
  const resultBox = document.getElementById('bullet-rewrite-result');

  if (!inputEl || !inputEl.value.trim()) return;
  const original = inputEl.value.trim();
  const role = roleEl ? roleEl.value.trim() : 'Software Engineer';

  if (resultBox) {
    resultBox.style.display = 'block';
    resultBox.innerHTML = `<p style="color:var(--text-muted); font-size:0.9rem;">Rewriting with Google XYZ formula via ImprovementAgent...</p>`;
  }

  try {
    const res = await API.improveBullet(original, role);
    const item = res.result || {};
    const citations = res.evidence?.citations || [];

    if (resultBox) {
      resultBox.innerHTML = `
        <div class="bullet-card">
          <div style="font-size:0.8rem; color:var(--text-subtle); margin-bottom:0.4rem;">ORIGINAL BULLET:</div>
          <div class="bullet-original">"${original}"</div>
          <div style="font-size:0.8rem; color:var(--color-green); margin-bottom:0.4rem;">GOOGLE XYZ FORMULA REWRITE (Grounded in kb_resume_best_practices):</div>
          <div class="bullet-improved">${item.improved}</div>
          <div style="font-size:0.78rem; color:var(--text-muted); margin-top:0.5rem;">
            🔍 Citations: ${citations[0] || 'Google XYZ formula applied'}
          </div>
        </div>
      `;
    }
  } catch (err) {
    if (resultBox) {
      resultBox.innerHTML = `<p style="color:var(--color-red);">Rewrite error: ${err.message}</p>`;
    }
  }
}
