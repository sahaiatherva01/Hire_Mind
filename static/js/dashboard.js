/**
 * HireMind AI — Dashboard Controller
 */

document.addEventListener('DOMContentLoaded', async () => {
  const user = JSON.parse(localStorage.getItem('hiremind_user') || 'null') || { id: 'u-dev-001', full_name: 'Candidate' };
  
  const greetingEl = document.getElementById('user-greeting');
  if (greetingEl) greetingEl.textContent = user.full_name || 'Candidate';

  await loadReadiness(user.id);
  await loadSimulationTrack(user.id);
  await loadRecentEvaluations();

  // Track Selector change
  const trackSelect = document.getElementById('track-select');
  if (trackSelect) {
    trackSelect.addEventListener('change', (e) => {
      loadSimulationTrack(user.id, e.target.value);
    });
  }
});

async function loadReadiness(userId) {
  try {
    const data = await API.getReadiness(userId);
    const scoreVal = document.getElementById('readiness-score');
    const tierVal = document.getElementById('readiness-tier');
    
    if (scoreVal) scoreVal.textContent = Math.round(data.overall_readiness || 0);
    if (tierVal) {
      tierVal.textContent = data.tier || 'Ready for Evaluation';
      tierVal.style.color = data.status_color || 'var(--color-primary)';
    }

    // Render category mini meters
    const breakdownEl = document.getElementById('readiness-breakdown');
    if (breakdownEl && data.breakdown) {
      breakdownEl.innerHTML = Object.entries(data.breakdown).map(([round, score]) => `
        <div style="background: rgba(255,255,255,0.03); padding: 0.75rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
          <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:0.25rem;">
            <span style="color:var(--text-muted);">${round.replace('_', ' ').toUpperCase()}</span>
            <span class="mono-num" style="color:#fff;">${score !== null ? score + '%' : 'Pending'}</span>
          </div>
          <div class="progress-track" style="height:4px;">
            <div class="progress-fill" style="width: ${score || 0}%;"></div>
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load readiness:', err);
  }
}

async function loadSimulationTrack(userId, track = 'default') {
  try {
    const data = await API.getProgress(userId, track);
    const railEl = document.getElementById('track-rail-container');
    if (!railEl) return;

    const roundIcons = {
      'resume_screening': '📄',
      'aptitude': '🧠',
      'dsa': '💻',
      'technical': '⚡',
      'project_defense': '🛡️',
      'hr': '🤝'
    };

    const roundLinks = {
      'resume_screening': '/resume',
      'aptitude': '/practice/aptitude.html?mode=simulation',
      'dsa': '/practice/dsa.html?mode=simulation',
      'technical': '/interview?mode=simulation',
      'project_defense': '/interview?mode=simulation',
      'hr': '/interview?mode=simulation'
    };

    railEl.innerHTML = `
      <div class="track-rail">
        ${data.rounds.map((r, i) => {
          const roundKey = r.round_name || r.round_id;
          const isDone = r.status === 'completed' || r.status === 'cleared';
          const href = r.unlocked ? roundLinks[roundKey] || '#' : 'javascript:void(0);';
          const displayName = r.display_name || (roundKey ? roundKey.replace('_', ' ').toUpperCase() : `Round ${i+1}`);
          return `
            <a href="${href}" class="track-step ${isDone ? 'cleared' : r.status}" title="${r.status === 'locked' ? 'Locked — Clear previous round cutoff to unlock' : 'Click to start ' + displayName}">
              <div class="track-node">
                ${isDone ? '✓' : roundIcons[roundKey] || (i + 1)}
              </div>
              <span class="track-label">${displayName}</span>
              <span class="badge ${isDone ? 'badge-green' : (r.status === 'unlocked' ? 'badge-amber' : 'badge-subtle')}" style="font-size:0.7rem;">
                ${isDone ? (r.score !== null ? r.score + '% (Passed)' : 'Completed') : (r.status === 'unlocked' ? 'Unlocked (' + r.cutoff + '% Cutoff)' : 'Locked')}
              </span>
            </a>
          `;
        }).join('')}
      </div>
    `;
  } catch (err) {
    console.error('Failed to load track progression:', err);
  }
}

async function loadRecentEvaluations() {
  try {
    const data = await API.getEvaluations();
    const listEl = document.getElementById('evaluations-list');
    if (!listEl) return;

    if (!data.evaluations || data.evaluations.length === 0) {
      listEl.innerHTML = `<p style="color:var(--text-subtle); text-align:center; padding:1.5rem;">No agent evaluations recorded yet. Run a round or resume analysis to generate audit citations.</p>`;
      return;
    }

    listEl.innerHTML = data.evaluations.slice(0, 5).map(ev => {
      const citations = ev.evidence_json?.citations || [];
      const logs = ev.retrieval_logs || [];
      return `
        <div class="glass-card" style="padding:1.25rem; margin-bottom:1rem; border-left: 3px solid var(--color-primary);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
            <div style="display:flex; align-items:center; gap:0.5rem;">
              <span class="badge badge-purple">${ev.agent_name}</span>
              <span style="font-size:0.85rem; color:var(--text-muted);">${ev.entity_type}</span>
            </div>
            <span class="badge badge-blue">Confidence: ${Math.round(ev.confidence * 100)}%</span>
          </div>
          <p style="font-size:0.9rem; color:#fff; margin-bottom:0.5rem;">${ev.evidence_json?.reasoning || 'Evaluation completed.'}</p>
          ${logs.length > 0 ? `
            <div style="font-size:0.78rem; color:var(--text-subtle); background:rgba(0,0,0,0.25); padding:0.4rem 0.6rem; border-radius:var(--radius-sm);">
              📚 RAG Collection Grounded: <strong style="color:var(--color-accent);">${logs[0]?.collection || 'knowledge_base'}</strong> (Matched ${logs[0]?.matched_ids?.length || 0} items)
            </div>
          ` : ''}
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load evaluations:', err);
  }
}
