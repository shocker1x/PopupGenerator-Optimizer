const TOKEN_KEY = 'fieldnote_access_token';

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

async function request(path, { token, ...options } = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body) headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  let response;
  try {
    response = await fetch(path, { ...options, headers });
  } catch {
    throw new Error('Can’t reach the API. Start the backend and try again.');
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = typeof payload.detail === 'string'
      ? payload.detail
      : `Request failed (${response.status})`;
    throw new Error(message);
  }
  return payload;
}

export function authenticate(email, password, createAccount = false) {
  if (createAccount) {
    return request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }).then(() => request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }));
  }
  return request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export function analyzeWebsite(url, token) {
  return request('/api/websites/analyze', {
    method: 'POST',
    token,
    body: JSON.stringify({ url }),
  });
}

export function generatePopups(analysis, token) {
  return request('/api/popups/generate', {
    method: 'POST',
    token,
    body: JSON.stringify({ analysis }),
  });
}