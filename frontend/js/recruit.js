/**
 * HireMind AI — Recruiter Portal Controller (Module C)
 */

let selectedJobId = null;

document.addEventListener('DOMContentLoaded', async () => {
  const createJobBtn = document.getElementById('btn-create-job');
  const batchUploadBtn = document.getElementById('btn-batch-upload');
  const genAssessmentBtn = document.getElementById('btn-gen-assessment');

  if (createJobBtn) createJobBtn.addEventListener('click', handleCreateJob);
  if (batchUploadBtn) batchUploadBtn.addEventListener('click', handleBatchUpload);
  if (genAssessmentBtn) genAssessmentBtn.addEventListener('click', handleGenerateAssessment);

  await loadJobsList();
});

async function loadJobsList() {
  const jobSelect = document.getElementById('active-jobs-select');
  const jobsListContainer = document.getElementById('company-jobs-list');

  try {
    const res = await API.listJobs();
    const jobs = res.jobs || [];

    if (jobSelect) {
      jobSelect.innerHTML = jobs.map(j => `<option value="${j.id}">${j.title} (${j.department || 'Engineering'})</option>`).join('');
      if (jobs.length > 0) {
        selectedJobId = jobs[0].id;
        loadCandidatesForJob(selectedJobId);
      }
      jobSelect.addEventListener('change', (e) => {
        selectedJobId = e.target.value;
        loadCandidatesForJob(selectedJobId);
      });
    }

    if (jobsListContainer) {
      if (jobs.length === 0) {
        jobsListContainer.innerHTML = `<p style="color:var(--text-subtle);">No job postings created yet. Create a job above to begin candidate batch screening.</p>`;
        return;
      }
      jobsListContainer.innerHTML = jobs.map(j => `
        <div class="glass-card" style="padding:1rem 1.25rem; margin-bottom:0.75rem; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <strong style="color:#fff; font-size:1rem;">${j.title}</strong>
            <span style="font-size:0.8rem; color:var(--text-muted); margin-left:0.5rem;">${j.department}</span>
            <div style="font-size:0.8rem; color:var(--text-subtle); margin-top:0.25rem;">
              Required Skills: ${(j.parsed_requirements?.required_skills || []).slice(0, 4).join(', ')}
            </div>
          </div>
          <span class="badge badge-green">Active</span>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load jobs:', err);
  }
}

async function handleCreateJob() {
  const titleEl = document.getElementById('new-job-title');
  const deptEl = document.getElementById('new-job-dept');
  const jdEl = document.getElementById('new-job-jd');
  const statusBox = document.getElementById('create-job-status');

  const title = titleEl ? titleEl.value.trim() : '';
  const dept = deptEl ? deptEl.value.trim() : 'Engineering';
  const jdText = jdEl ? jdEl.value.trim() : '';

  if (!title || !jdText) {
    alert('Please enter a Job Title and Job Description.');
    return;
  }

  if (statusBox) {
    statusBox.style.display = 'block';
    statusBox.innerHTML = `<p style="color:var(--text-muted);">Parsing JD requirements and archetype weighting via JDParsingAgent...</p>`;
  }

  try {
    const res = await API.createJob({ title, department: dept, jd_text: jdText });
    if (statusBox) {
      statusBox.innerHTML = `<div style="color:var(--color-green); font-weight:600;">✓ Job created successfully with ${res.job?.parsed_requirements?.required_skills?.length || 0} extracted required skills.</div>`;
    }
    await loadJobsList();
  } catch (err) {
    if (statusBox) {
      statusBox.innerHTML = `<div style="color:var(--color-red);">❌ Error creating job: ${err.message}</div>`;
    }
  }
}

async function handleBatchUpload() {
  const filesInput = document.getElementById('batch-resumes-input');
  const statusBox = document.getElementById('batch-status');

  if (!selectedJobId) {
    alert('Please select or create a Job Posting first.');
    return;
  }

  if (!filesInput || !filesInput.files || filesInput.files.length === 0) {
    alert('Please select one or more candidate resume files (PDF/DOCX).');
    return;
  }

  const formData = new FormData();
  formData.append('job_id', selectedJobId);
  for (let i = 0; i < filesInput.files.length; i++) {
    formData.append('files', filesInput.files[i]);
  }

  if (statusBox) {
    statusBox.style.display = 'block';
    statusBox.innerHTML = `
      <div class="glass-card" style="text-align:center; padding:1.5rem;">
        <h4>Processing Batch Screening Pipeline...</h4>
        <p style="color:var(--text-muted); margin-top:0.5rem;">Executing BulkMatchAgent & RankingAgent across ${filesInput.files.length} resumes with tenant isolation...</p>
      </div>
    `;
  }

  try {
    const res = await API.screenBatchResumes(formData);
    if (statusBox) {
      statusBox.innerHTML = `<div style="color:var(--color-green); font-weight:600; margin-bottom:1rem;">✓ Successfully screened and ranked ${res.total_candidates_processed} candidate resumes!</div>`;
    }
    renderRankedCandidatesTable(res.rankings || []);
  } catch (err) {
    if (statusBox) {
      statusBox.innerHTML = `<div style="color:var(--color-red);">❌ Batch screening failed: ${err.message}</div>`;
    }
  }
}

async function loadCandidatesForJob(jobId) {
  if (!jobId) return;
  try {
    const res = await API.listJobCandidates(jobId);
    renderRankedCandidatesTable(res.candidates || []);
  } catch (err) {
    console.error('Failed to load job candidates:', err);
  }
}

function renderRankedCandidatesTable(candidates) {
  const container = document.getElementById('candidates-table-container');
  if (!container) return;

  if (candidates.length === 0) {
    container.innerHTML = `<p style="color:var(--text-subtle); text-align:center; padding:2rem;">No candidate resumes uploaded for this job yet. Use the batch uploader above to screen applicants.</p>`;
    return;
  }

  container.innerHTML = `
    <table class="table-custom">
      <thead>
        <tr>
          <th>Candidate</th>
          <th>Match Score</th>
          <th>AI Screening Tier</th>
          <th>Explainable Evidence Justification</th>
          <th>Matched Skills</th>
        </tr>
      </thead>
      <tbody>
        ${candidates.map(c => {
          const cat = c.ranking_category || (c.match_score >= 80 ? 'Strong Match' : (c.match_score >= 60 ? 'Review Needed' : 'Weak Match'));
          const badgeClass = cat === 'Strong Match' ? 'badge-green' : (cat === 'Review Needed' ? 'badge-amber' : 'badge-red');
          const matchedList = c.matched_required_skills || [];
          return `
            <tr>
              <td>
                <strong style="color:#fff;">${c.candidate_name}</strong>
                <div style="font-size:0.8rem; color:var(--text-subtle);">${c.email || 'applicant@example.com'}</div>
              </td>
              <td>
                <span class="mono-num" style="font-size:1.15rem; font-weight:800; color:#fff;">${c.match_score}%</span>
              </td>
              <td>
                <span class="badge ${badgeClass}">${cat}</span>
              </td>
              <td>
                <div style="font-size:0.88rem; color:var(--text-muted); max-width:340px;">
                  ${c.justification || c.evidence_summary?.justification || 'Evaluated against job requirements with skill synonym matching.'}
                </div>
              </td>
              <td>
                <div style="display:flex; flex-wrap:wrap; gap:0.25rem;">
                  ${matchedList.slice(0, 3).map(s => `<span class="badge badge-blue" style="font-size:0.7rem;">${s}</span>`).join('')}
                </div>
              </td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
  `;
}

async function handleGenerateAssessment() {
  if (!selectedJobId) {
    alert('Please select a job first.');
    return;
  }

  const durationEl = document.getElementById('assessment-duration-input');
  const previewBox = document.getElementById('assessment-preview-container');
  const duration = durationEl ? parseInt(durationEl.value) : 30;

  if (previewBox) {
    previewBox.style.display = 'block';
    previewBox.innerHTML = `<p style="color:var(--text-muted);">Retrieving calibrated technical & aptitude questions from kb_interview_questions...</p>`;
  }

  try {
    const res = await API.generateAssessment(selectedJobId, duration);
    const test = res.assessment || {};
    const questions = test.questions || [];

    if (previewBox) {
      previewBox.innerHTML = `
        <div class="glass-card" style="padding:1.5rem; margin-top:1rem; border-left:3px solid var(--color-accent);">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
            <h4 style="color:#fff;">${test.title || 'Screening Assessment'} (${test.duration_minutes || 30} mins)</h4>
            <span class="badge badge-purple">${questions.length} Calibrated Questions</span>
          </div>
          <div style="display:flex; flex-direction:column; gap:1rem;">
            ${questions.map((q, idx) => `
              <div style="background:rgba(255,255,255,0.02); padding:1rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle);">
                <div style="display:flex; justify-content:space-between; font-size:0.82rem; color:var(--text-muted); margin-bottom:0.35rem;">
                  <span>Question ${idx + 1} (${q.topic})</span>
                  <span class="badge badge-subtle">${q.difficulty}</span>
                </div>
                <p style="font-size:0.92rem; color:#fff; margin-bottom:0.5rem;">${q.question}</p>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.4rem; font-size:0.85rem; color:var(--text-muted);">
                  ${(q.options || []).map((opt, oIdx) => `
                    <div style="padding:0.4rem 0.6rem; border-radius:4px; background:${oIdx === q.correct_option ? 'rgba(16,185,129,0.1)' : 'rgba(255,255,255,0.02)'}; color:${oIdx === q.correct_option ? '#34d399' : 'inherit'};">
                      ${String.fromCharCode(65 + oIdx)}) ${opt}
                    </div>
                  `).join('')}
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }
  } catch (err) {
    if (previewBox) {
      previewBox.innerHTML = `<p style="color:var(--color-red);">Error generating assessment: ${err.message}</p>`;
    }
  }
}
