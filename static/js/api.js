/**
 * HireMind AI — Central API Client
 */

const API = {
  async request(endpoint, options = {}) {
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    if (options.body instanceof FormData) {
      delete config.headers['Content-Type'];
    }

    try {
      const res = await fetch(endpoint, config);
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.message || data.error || `HTTP Error ${res.status}`);
      }
      return data;
    } catch (err) {
      console.error(`[API Error] ${endpoint}:`, err);
      throw err;
    }
  },

  // Auth
  signup: (payload) => API.request('/api/auth/signup', { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload) => API.request('/api/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  getMe: () => API.request('/api/auth/me'),

  // Dashboard
  getProgress: (userId, track) => API.request(`/api/dashboard/progress?user_id=${userId || ''}&track=${track || 'default'}`),
  getReadiness: (userId) => API.request(`/api/dashboard/readiness?user_id=${userId || ''}`),
  getEvaluations: () => API.request('/api/dashboard/evaluations'),

  // Resume Intelligence (Module A)
  uploadResume: (formData) => API.request('/api/resume/analyze', { method: 'POST', body: formData }),
  improveBullet: (bulletText, roleContext) => API.request('/api/resume/improve-bullet', { method: 'POST', body: JSON.stringify({ bullet_text: bulletText, role_context: roleContext }) }),

  // Interview Simulator (Module B)
  generateInterviewPlan: (payload) => API.request('/api/interview/generate-questions', { method: 'POST', body: JSON.stringify(payload) }),
  startInterview: (sessionId, voicePref) => API.request('/api/interview/start', { method: 'POST', body: JSON.stringify({ session_id: sessionId, voice_preference: voicePref }) }),
  submitInterviewAnswer: (sessionId, qId, answerText) => API.request('/api/interview/answer', { method: 'POST', body: JSON.stringify({ session_id: sessionId, question_bank_id: qId, answer_text: answerText }) }),
  endInterview: (sessionId) => API.request('/api/interview/end', { method: 'POST', body: JSON.stringify({ session_id: sessionId }) }),

  // Aptitude Round
  getAptitudeQuestions: (mode) => API.request(`/api/aptitude/questions?mode=${mode || 'practice'}`),
  submitAptitudeTest: (payload) => API.request('/api/aptitude/submit', { method: 'POST', body: JSON.stringify(payload) }),

  // DSA Round
  getDSAProblems: (mode) => API.request(`/api/dsa/problems?mode=${mode || 'practice'}`),
  getDSAProblemDetail: (id) => API.request(`/api/dsa/problems/${id}`),
  runDSACode: (problemId, code) => API.request('/api/dsa/run', { method: 'POST', body: JSON.stringify({ problem_id: problemId, code }) }),
  submitDSACode: (payload) => API.request('/api/dsa/submit', { method: 'POST', body: JSON.stringify(payload) }),

  // Recruiter Portal (Module C)
  createJob: (payload) => API.request('/api/recruit/jobs', { method: 'POST', body: JSON.stringify(payload) }),
  listJobs: (companyId) => API.request(`/api/recruit/jobs?company_id=${companyId || ''}`),
  screenBatchResumes: (formData) => API.request('/api/recruit/screen-batch', { method: 'POST', body: formData }),
  listJobCandidates: (jobId) => API.request(`/api/recruit/candidates?job_id=${jobId}`),
  generateAssessment: (jobId, duration) => API.request('/api/recruit/generate-assessment', { method: 'POST', body: JSON.stringify({ job_id: jobId, duration_minutes: duration }) })
};

window.API = API;
