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
  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
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

export function createCampaign(websiteId, name, variants, token) {
  return request('/api/popups/campaigns', {
    method: 'POST',
    token,
    body: JSON.stringify({ website_id: websiteId, name, variants }),
  });
}

export function updatePopupVersion(versionId, config, token) {
  return request(`/api/popups/versions/${versionId}`, {
    method: 'PATCH',
    token,
    body: JSON.stringify({ config }),
  });
}

export function regeneratePopupVersion(versionId, instruction, token) {
  return request(`/api/popups/versions/${versionId}/regenerate`, {
    method: 'POST',
    token,
    body: JSON.stringify({ instruction }),
  });
}

export function uploadPopupImage(file, token) {
  const formData = new FormData();
  formData.append('image', file);
  return request('/api/popups/images', {
    method: 'POST',
    token,
    body: formData,
  });
}

export function publishCampaign(campaignId, versionId, token) {
  return request(`/api/popups/campaigns/${campaignId}/publish`, {
    method: 'POST',
    token,
    body: JSON.stringify({ version_id: versionId }),
  });
}

export function getCampaignAnalytics(campaignId, token) {
  return request(`/api/popups/campaigns/${campaignId}/analytics`, { token });
}

export function getCampaignSubscribers(campaignId, token) {
  return request(`/api/popups/campaigns/${campaignId}/subscribers`, { token });
}

export function deleteCampaignSubscriber(campaignId, subscriberId, token) {
  return request(`/api/popups/campaigns/${campaignId}/subscribers/${subscriberId}`, {
    method: 'DELETE',
    token,
  });
}

export async function exportCampaignSubscribers(campaignId, token) {
  let response;
  try {
    response = await fetch(`/api/popups/campaigns/${campaignId}/subscribers.csv`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    throw new Error('Can’t reach the API. Start the backend and try again.');
  }
  if (!response.ok) throw new Error(`Could not export subscribers (${response.status})`);
  return response.blob();
}