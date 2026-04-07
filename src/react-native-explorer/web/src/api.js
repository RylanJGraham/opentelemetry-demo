/**
 * API client — talks to the Python Explorer server.
 */

const API_BASE = '/api';
let ws = null;
let wsListeners = [];

/** Fetch JSON from the API. */
async function fetchJSON(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

/** POST JSON to the API. */
async function postJSON(path, data) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

/** DELETE request. */
async function deleteReq(path) {
  const res = await fetch(`${API_BASE}${path}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

// ── Public API ───────────────────────────────────────────────────────

export async function getGraph() {
  return fetchJSON('/graph');
}

export async function getScreens() {
  return fetchJSON('/screens');
}

export async function getScreen(screenId) {
  return fetchJSON(`/screens/${screenId}`);
}

export function getScreenshotUrl(filename) {
  return `${API_BASE}/screenshots/${filename}`;
}

export async function getStatus() {
  return fetchJSON('/status');
}

export async function getStories() {
  return fetchJSON('/stories');
}

export async function createStory(storyData) {
  return postJSON('/stories', storyData);
}

export async function deleteStory(storyId) {
  return deleteReq(`/stories/${storyId}`);
}

export async function clearStorage() {
  return deleteReq('/storage');
}

export async function agentStart() {
  return postJSON('/agent/start', {});
}

export async function agentPause() {
  return postJSON('/agent/pause', {});
}

export async function agentStop() {
  return postJSON('/agent/stop', {});
}

// ── WebSocket ────────────────────────────────────────────────────────

export function connectWebSocket(onMessage) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/live`;

  function connect() {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('[WS] Connected');
      onMessage({ type: 'ws_connected' });
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        onMessage(msg);
        wsListeners.forEach((fn) => fn(msg));
      } catch (e) {
        console.error('[WS] Parse error:', e);
      }
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected, reconnecting in 3s...');
      onMessage({ type: 'ws_disconnected' });
      setTimeout(connect, 3000);
    };

    ws.onerror = (e) => {
      console.error('[WS] Error:', e);
    };
  }

  connect();
}

export function addWsListener(fn) {
  wsListeners.push(fn);
  return () => {
    wsListeners = wsListeners.filter((f) => f !== fn);
  };
}
