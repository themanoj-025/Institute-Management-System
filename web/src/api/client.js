const API_BASE = '/v1';

let refreshPromise = null;

/**
 * Get stored access token.
 */
export function getToken() {
  return localStorage.getItem('bbims_token');
}

/**
 * Store access token.
 */
export function setToken(token) {
  localStorage.setItem('bbims_token', token);
}

/**
 * Clear auth state.
 */
export function clearAuth() {
  localStorage.removeItem('bbims_token');
  localStorage.removeItem('bbims_user');
}

/**
 * Get stored user info.
 */
export function getUser() {
  try {
    const raw = localStorage.getItem('bbims_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/**
 * Store user info.
 */
export function setUser(user) {
  localStorage.setItem('bbims_user', JSON.stringify(user));
}

/**
 * Parse JWT payload (without verification).
 */
function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64));
  } catch {
    return null;
  }
}

/**
 * Check if token is expired or about to expire (within 5 minutes).
 */
export function isTokenExpired(token) {
  const payload = parseJwt(token);
  if (!payload || !payload.exp) return true;
  return (payload.exp * 1000) < (Date.now() + 5 * 60 * 1000);
}

/**
 * Refresh the access token.
 */
async function refreshToken() {
  const token = getToken();
  if (!token) throw new Error('No token to refresh');

  const resp = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!resp.ok) {
    clearAuth();
    throw new Error('Token refresh failed');
  }

  const data = await resp.json();
  setToken(data.access_token);
  return data.access_token;
}

/**
 * Make an authenticated API request.
 * Automatically handles token refresh on 401 responses.
 */
export async function apiRequest(path, options = {}) {
  const { method = 'GET', body, params, raw = false } = options;

  let token = getToken();
  const headers = { ...options.headers };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (body && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  let url = `${API_BASE}${path}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.set(key, value);
      }
    });
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
  }

  let resp = await fetch(url, {
    method,
    headers,
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });

  // Auto-refresh on 401
  if (resp.status === 401 && token && !options._retry) {
    if (!refreshPromise) {
      refreshPromise = refreshToken().finally(() => {
        refreshPromise = null;
      });
    }

    try {
      const newToken = await refreshPromise;
      headers['Authorization'] = `Bearer ${newToken}`;
      resp = await fetch(url, {
        method,
        headers,
        body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
      });
    } catch {
      clearAuth();
      window.location.href = '/login';
      throw new Error('Session expired');
    }
  }

  if (raw) return resp;

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ error: { message: resp.statusText } }));
    const error = new Error(err?.error?.message || `Request failed: ${resp.status}`);
    error.status = resp.status;
    error.code = err?.error?.code;
    throw error;
  }

  return resp.json();
}

# Convenience wrappers

export const api = {
  get: (path, params) => apiRequest(path, { params }),
  post: (path, body) => apiRequest(path, { method: 'POST', body }),
  put: (path, body) => apiRequest(path, { method: 'PUT', body }),
  patch: (path, body) => apiRequest(path, { method: 'PATCH', body }),
  delete: (path) => apiRequest(path, { method: 'DELETE' }),
};

# Auth endpoints

export async function login(username, password) {
  const data = await apiRequest('/auth/login', {
    method: 'POST',
    body: { username, password },
  });
  // Login returns {status: "otp_required", user_id, role} — NO JWT yet.
  // The JWT is obtained after OTP verification. We temporarily store
  // user_id and role in sessionStorage so they survive until verifyOtp.
  if (data.status === 'otp_required') {
    sessionStorage.setItem('bbims_login_user_id', String(data.user_id));
    sessionStorage.setItem('bbims_login_role', data.role);
  }
  return data;
}

export async function verifyOtp(userId, otp) {
  const data = await apiRequest('/auth/verify-otp', {
    method: 'POST',
    body: { user_id: userId, otp },
  });
  // verify-otp returns { access_token, role, user }
  if (data.access_token) {
    setToken(data.access_token);
    setUser(data.user);
    // Clean up temporary login state
    sessionStorage.removeItem('bbims_login_user_id');
    sessionStorage.removeItem('bbims_login_role');
  }
  return data;
}

export async function logout() {
  try {
    await apiRequest('/auth/logout', { method: 'POST' });
  } catch {
    // Ignore logout errors
  }
  clearAuth();
}

# Password Reset endpoints

export async function forgotPassword(email) {
  return apiRequest('/auth/forgot-password', {
    method: 'POST',
    body: { email },
  });
}

export async function resetPassword(userId, token, newPassword) {
  return apiRequest('/auth/reset-password', {
    method: 'POST',
    body: { user_id: userId, token, new_password: newPassword },
  });
}

# Student endpoints

export async function fetchStudents(params = {}) {
  return api.get('/students', params);
}

export async function fetchStudent(id) {
  return api.get(`/students/${id}`);
}

export async function updateStudent(id, data) {
  return api.patch(`/students/${id}`, data);
}

# Analytics endpoints

export async function fetchAtRiskStudents(params = {}) {
  return api.get('/analytics/at-risk', params);
}

export async function fetchRiskExplanation(studentId) {
  return api.get(`/analytics/students/${studentId}/risk-explanation`);
}

export async function fetchDashboardKpis() {
  return api.get('/analytics/dashboard-kpis');
}

export async function fetchAnalyticsSummary() {
  return api.get('/analytics/summary');
}

# Fee endpoints

export async function fetchFees(params = {}) {
  return api.get('/fees', params);
}

export async function recordPayment(data) {
  return api.post('/fees/payment', data);
}

# Placement endpoints

export async function fetchPlacements(params = {}) {
  return api.get('/placements', params);
}

# Attendance endpoints

export async function fetchAttendance(params = {}) {
  return api.get('/attendance', params);
}

export async function recordAttendance(records) {
  return api.post('/attendance/bulk', records);
}

# Result endpoints

export async function fetchResults(params = {}) {
  return api.get('/results', params);
}

export async function recordResults(records) {
  return api.post('/results/bulk', records);
}

# Leave endpoints

export async function fetchLeaves(params = {}) {
  return api.get('/leaves', params);
}

export async function applyLeave(data) {
  return api.post('/leaves', data);
}

# Notice endpoints

export async function fetchNotices(params = {}) {
  return api.get('/notices', params);
}

# Feedback endpoints

export async function fetchFeedback(params = {}) {
  return api.get('/feedback', params);
}

export async function submitFeedback(data) {
  return api.post('/feedback', data);
}

# Staff endpoints

export async function fetchStaff(params = {}) {
  return api.get('/staff', params);
}

export async function fetchStaffMember(id) {
  return api.get(`/staff/${id}`);
}

export async function createStaff(data) {
  return api.post('/staff', data);
}

export async function updateStaff(id, data) {
  return api.patch(`/staff/${id}`, data);
}

export async function deleteStaff(id) {
  return api.delete(`/staff/${id}`);
}

# Course endpoints

export async function fetchCourses(params = {}) {
  return api.get('/courses', params);
}

export async function fetchCourse(id) {
  return api.get(`/courses/${id}`);
}

export async function createCourse(data) {
  return api.post('/courses', data);
}

export async function updateCourse(id, data) {
  return api.patch(`/courses/${id}`, data);
}

export async function deleteCourse(id) {
  return api.delete(`/courses/${id}`);
}

# Config endpoints (admin)

export async function fetchRiskThresholds() {
  return api.get('/admin/config/risk-thresholds');
}

export async function updateRiskThresholds(thresholds) {
  return api.put('/admin/config/risk-thresholds', { thresholds });
}
