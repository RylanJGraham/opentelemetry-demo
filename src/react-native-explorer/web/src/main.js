/**
 * Main entry point — App initialization, view routing, WebSocket handling.
 */

import { connectWebSocket, getStatus, clearStorage, agentStart, agentPause, agentStop, getLiveScreenshot } from './api.js';
import { initGraphView, refreshGraph, addNode, addEdge } from './graph-view.js';
import { initGalleryView, refreshGallery, addScreenToGallery } from './gallery-view.js';
import { initStoryBuilder, refreshStories, refreshPickerScreens } from './story-builder.js';

// ── View routing ─────────────────────────────────────────────────────

const views = ['graph', 'gallery', 'stories'];
let currentView = 'graph';

function switchView(viewName) {
  if (!views.includes(viewName)) return;
  currentView = viewName;

  // Update tab states
  document.querySelectorAll('.nav-tab').forEach((tab) => {
    tab.classList.toggle('active', tab.dataset.view === viewName);
  });

  // Show/hide views
  document.querySelectorAll('.view').forEach((view) => {
    view.classList.toggle('active', view.id === `view-${viewName}`);
  });

  // Refresh data when switching
  if (viewName === 'graph') {
    refreshGraph();
    // Auto-open sidebar on graph view
    const sidebar = document.getElementById('activity-sidebar');
    if (sidebar) sidebar.classList.remove('collapsed');
  }
  if (viewName === 'gallery') refreshGallery();
  if (viewName === 'stories') {
    refreshStories();
    refreshPickerScreens();
  }
}

// ── Status updates ───────────────────────────────────────────────────

function updateStatusUI(status) {
  const dot = document.getElementById('status-dot');
  const text = document.getElementById('status-text');

  const state = status.state || 'idle';
  dot.className = `status-dot ${state}`;
  text.textContent = status.message || state;

  // Update control buttons active state
  const btnStart = document.getElementById('btn-agent-start');
  const btnPause = document.getElementById('btn-agent-pause');
  const btnStop = document.getElementById('btn-agent-stop');

  if (btnStart) btnStart.classList.toggle('active', state === 'exploring');
  if (btnPause) btnPause.classList.toggle('active', state === 'paused');
  if (btnStop) btnStop.disabled = (state === 'idle');

  // Control live screenshot polling based on agent state
  if (state === 'exploring' || state === 'connecting') {
    startLiveScreenshot();
  } else if (state === 'idle' || state === 'complete') {
    stopLiveScreenshot();
  }

  // Update stats
  if (status.total_screens !== undefined) {
    document.getElementById('stat-screens').textContent = status.total_screens || '0';
  }
  if (status.total_transitions !== undefined) {
    document.getElementById('stat-transitions').textContent = status.total_transitions || '0';
  }
  if (status.total_actions !== undefined) {
    document.getElementById('stat-actions').textContent = status.total_actions || '0';
  }
}

// ── Activity feed ────────────────────────────────────────────────────

const MAX_FEED_ITEMS = 50;

function addFeedItem(type, message) {
  const feed = document.getElementById('feed-items');
  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const item = document.createElement('div');
  item.className = `feed-item ${type}`;
  item.innerHTML = `<span class="feed-item-time">${timeStr}</span> ${escapeHtml(message)}`;

  feed.prepend(item);

  // Trim old items
  while (feed.children.length > MAX_FEED_ITEMS) {
    feed.removeChild(feed.lastChild);
  }
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ── WebSocket message handler ────────────────────────────────────────

function handleWsMessage(msg) {
  switch (msg.type) {
    case 'ws_connected':
      updateStatusUI({ state: 'connecting', message: 'Connected to server' });
      addFeedItem('', '🔌 Connected to explorer server');
      break;

    case 'ws_disconnected':
      updateStatusUI({ state: 'idle', message: 'Disconnected' });
      addFeedItem('', '⚡ Disconnected from server');
      break;

    case 'status':
      if (msg.data) {
        updateStatusUI(msg.data);
      }
      break;

    case 'new_screen':
      if (msg.data) {
        const name = msg.data.name || 'Unknown';
        addFeedItem('new-screen', `📱 New screen: ${name}`);
        addNode(msg.data);
        addScreenToGallery(msg.data);

        // 🔧 Force UI re-render
        if (currentView === 'graph') refreshGraph();
        if (currentView === 'gallery') refreshGallery();

        // Update transition count
        const transEl = document.getElementById('stat-screens'); // Fix: link to screens stat
        if (transEl) transEl.textContent = parseInt(transEl.textContent || '0') + 1;
      }
      break;

    case 'new_transition':
      if (msg.data) {
        addFeedItem('', `🔗 Transition: ${msg.data.from} → ${msg.data.to}`);
        addEdge(msg.data);

        // 🔧 Force Graph re-render
        if (currentView === 'graph') refreshGraph();

        // Update transition count
        const transEl = document.getElementById('stat-transitions');
        if (transEl) transEl.textContent = parseInt(transEl.textContent || '0') + 1;
      }
      break;

    case 'action':
      if (msg.data) {
        const action = msg.data;
        const actionIcons = {
          tap: '👆',
          back: '⬅️',
          swipe: '📜',
          type: '⌨️',
          done: '✅',
          skip: '⏭️',
        };
        const icon = actionIcons[action.action] || '▶️';
        addFeedItem(
          `action-${action.action}`,
          `${icon} ${action.action.toUpperCase()}: ${action.reason || ''}`
        );
      }
      break;

    default:
      console.log('[WS] Unknown message type:', msg.type);
  }
}

// ── Feed toggle ──────────────────────────────────────────────────────

function initSidebarToggle() {
  const sidebar = document.getElementById('activity-sidebar');
  const toggle = document.getElementById('sidebar-toggle');

  toggle?.addEventListener('click', () => {
    const isCollapsed = sidebar.classList.toggle('collapsed');
    toggle.textContent = isCollapsed ? '▶' : '◀';
  });
}

// ── Initialization ───────────────────────────────────────────────────

function init() {
  // Setup view routing
  document.querySelectorAll('.nav-tab').forEach((tab) => {
    tab.addEventListener('click', () => switchView(tab.dataset.view));
  });

  // Initialize views
  initGraphView();
  initGalleryView();
  initStoryBuilder();
  initSidebarToggle();

  // Button Listeners
  // Agent Control Listeners
  document.getElementById('btn-agent-start')?.addEventListener('click', async () => {
    await agentStart();
    updateStatusUI({ state: 'exploring', message: 'Resuming...' });
  });

  document.getElementById('btn-agent-pause')?.addEventListener('click', async () => {
    await agentPause();
    updateStatusUI({ state: 'paused', message: 'Pausing...' });
  });

  document.getElementById('btn-agent-stop')?.addEventListener('click', async () => {
    if (confirm('Stop the agent exploration?')) {
      await agentStop();
      updateStatusUI({ state: 'idle', message: 'Stopped' });
    }
  });

  document.getElementById('btn-clear-storage')?.addEventListener('click', async () => {
    if (confirm('Are you sure you want to completely clear the UI storage and graph database?')) {
      await clearStorage();
      window.location.reload();
    }
  });

  // Connect WebSocket for live updates
  connectWebSocket(handleWsMessage);

  // Poll status initially
  getStatus()
    .then(updateStatusUI)
    .catch(() => {
      updateStatusUI({ state: 'idle', message: 'Waiting for agent...' });
    });

  // Periodic graph refresh (every 10s)
  setInterval(() => {
    if (currentView === 'graph') refreshGraph();
  }, 10000);

  console.log('🔍 React Native Explorer UI initialized');
}

// ── Live Screenshot Polling ──────────────────────────────────────────

let liveScreenshotInterval = null;

function startLiveScreenshot() {
  if (liveScreenshotInterval) return;
  liveScreenshotInterval = setInterval(async () => {
    try {
      const result = await getLiveScreenshot();
      if (result && result.image) {
        const img = document.getElementById('live-screenshot-img');
        const placeholder = document.getElementById('live-placeholder');
        if (img) {
          img.src = result.image;
          img.style.display = 'block';
        }
        if (placeholder) placeholder.style.display = 'none';
      }
    } catch {
      // Emulator not connected yet — keep placeholder
    }
  }, 3000);
}

function stopLiveScreenshot() {
  if (liveScreenshotInterval) {
    clearInterval(liveScreenshotInterval);
    liveScreenshotInterval = null;
  }
}

// Start
document.addEventListener('DOMContentLoaded', init);
