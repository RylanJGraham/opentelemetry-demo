/**
 * Story Builder — Create user stories by arranging screens in sequence.
 */

import { getScreens, getStories, createStory, deleteStory, getScreenshotUrl } from './api.js';

let stories = [];
let currentStory = { name: '', steps: [] };
let availableScreens = [];

/** Initialize the story builder. */
export function initStoryBuilder() {
  document.getElementById('btn-new-story').addEventListener('click', newStory);
  document.getElementById('btn-save-story').addEventListener('click', saveCurrentStory);
  document.getElementById('btn-export-story').addEventListener('click', exportCurrentStory);

  const commandInput = document.getElementById('story-command');
  if (commandInput) {
    commandInput.addEventListener('input', handleCommandInput);
    commandInput.addEventListener('keydown', handleCommandKeydown);
  }

  refreshStories();
  refreshPickerScreens();
}

/** Refresh stories list from API. */
export async function refreshStories() {
  try {
    stories = await getStories();
    renderStoriesList();
  } catch (e) {
    console.log('[Stories] No data yet:', e.message);
  }
}

/** Refresh the screen picker. */
export async function refreshPickerScreens() {
  try {
    availableScreens = await getScreens();
    renderPicker();
  } catch (e) {
    console.log('[Stories] No screens for picker:', e.message);
  }
}

/** Create a new empty story. */
function newStory() {
  currentStory = { name: '', steps: [] };
  document.getElementById('story-title').value = '';
  renderCanvas();
}

/** Save the current story. */
async function saveCurrentStory() {
  const name = document.getElementById('story-title').value.trim();
  if (!name) {
    alert('Please enter a story name');
    return;
  }

  currentStory.name = name;

  try {
    await createStory(currentStory);
    await refreshStories();
  } catch (e) {
    console.error('Failed to save story:', e);
    alert('Failed to save story');
  }
}

/** Export story as JSON download. */
function exportCurrentStory() {
  const name = document.getElementById('story-title').value.trim() || 'story';
  const blob = new Blob([JSON.stringify(currentStory, null, 2)], {
    type: 'application/json',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${name.replace(/\s+/g, '_').toLowerCase()}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

/** Render the stories sidebar list. */
function renderStoriesList() {
  const list = document.getElementById('stories-list');

  if (stories.length === 0) {
    list.innerHTML = '<p class="empty-state">No stories yet</p>';
    return;
  }

  list.innerHTML = stories
    .map(
      (story) => `
    <div class="story-item" data-story-id="${story.id}">
      <span>${story.name || 'Untitled'}</span>
      <button class="story-item-delete" data-delete-id="${story.id}">✕</button>
    </div>
  `
    )
    .join('');

  // Click to load story
  list.querySelectorAll('.story-item').forEach((item) => {
    item.addEventListener('click', (e) => {
      if (e.target.classList.contains('story-item-delete')) return;
      const storyId = item.dataset.storyId;
      const story = stories.find((s) => s.id === storyId);
      if (story) {
        currentStory = { ...story };
        document.getElementById('story-title').value = story.name || '';
        renderCanvas();
        // Mark active
        list.querySelectorAll('.story-item').forEach((i) => i.classList.remove('active'));
        item.classList.add('active');
      }
    });
  });

  // Delete buttons
  list.querySelectorAll('.story-item-delete').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const storyId = btn.dataset.deleteId;
      if (confirm('Delete this story?')) {
        try {
          await deleteStory(storyId);
          await refreshStories();
        } catch (e) {
          console.error('Failed to delete story:', e);
        }
      }
    });
  });
}

/** Render the story canvas (sequence of screens). */
function renderCanvas() {
  const canvas = document.getElementById('story-canvas');

  if (!currentStory.steps || currentStory.steps.length === 0) {
    canvas.innerHTML =
      '<p class="empty-state">Drag screens from below or click them to add steps</p>';
    return;
  }

  const stepsHtml = currentStory.steps
    .map((step, i) => {
      const screen = availableScreens.find((s) => s.id === step.screenId);
      const name = screen ? screen.name : step.screenId;
      const imgSrc = screen && screen.screenshot_path
        ? getScreenshotUrl(screen.screenshot_path)
        : '';

      const arrowHtml = i < currentStory.steps.length - 1
        ? '<div class="story-step-arrow">→</div>'
        : '';

      return `
        <div class="story-step" data-step-index="${i}">
          <button class="story-step-remove" data-remove-index="${i}">✕</button>
          ${imgSrc ? `<img class="story-step-image" src="${imgSrc}" alt="${name}" />` : ''}
          <div class="story-step-info">${name}</div>
        </div>
        ${arrowHtml}
      `;
    })
    .join('');

  canvas.innerHTML = stepsHtml;

  // Remove buttons
  canvas.querySelectorAll('.story-step-remove').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const idx = parseInt(btn.dataset.removeIndex, 10);
      currentStory.steps.splice(idx, 1);
      renderCanvas();
    });
  });
}

/** Render the screen picker at the bottom. */
function renderPicker() {
  const grid = document.getElementById('picker-grid');

  if (availableScreens.length === 0) {
    grid.innerHTML = '<p class="empty-state" style="padding:16px;">No screens available</p>';
    return;
  }

  grid.innerHTML = availableScreens
    .map(
      (screen) => `
    <div class="picker-card" data-screen-id="${screen.id}">
      ${
        screen.screenshot_path
          ? `<img class="picker-card-image" src="${getScreenshotUrl(screen.screenshot_path)}" alt="${screen.name}" loading="lazy" />`
          : `<div class="picker-card-image" style="display:flex;align-items:center;justify-content:center;">📱</div>`
      }
      <div class="picker-card-name">${screen.name || 'Unknown'}</div>
    </div>
  `
    )
    .join('');

  // Click to add to story
  grid.querySelectorAll('.picker-card').forEach((card) => {
    card.addEventListener('click', () => {
      const screenId = card.dataset.screenId;
      if (!currentStory.steps) currentStory.steps = [];
      currentStory.steps.push({ screenId, annotation: '' });
      renderCanvas();
    });
  });
}

/** Handle typing in the command console. */
let suggestionIdx = -1;
let filteredSuggestions = [];

function handleCommandInput(e) {
  const text = e.target.value;
  const cursor = e.target.selectionStart;
  const lastAt = text.lastIndexOf('@', cursor - 1);
  const suggestionsBox = document.getElementById('suggestions');

  if (lastAt !== -1 && !/\s/.test(text.slice(lastAt + 1, cursor))) {
    const query = text.slice(lastAt + 1, cursor).toLowerCase();
    
    // Generate suggestions: screens + elements from last screen in story
    const lastScreenId = currentStory.steps.length > 0 ? currentStory.steps[currentStory.steps.length-1].screenId : null;
    let pool = availableScreens.map(s => ({ name: s.name, id: s.id, type: 'screen' }));
    
    if (lastScreenId) {
       const screen = availableScreens.find(s => s.id === lastScreenId);
       if (screen && screen.elements) {
         pool = [...pool, ...screen.elements.map(el => ({ name: el.label || el.type, id: el.id, type: 'element' }))];
       }
    }

    filteredSuggestions = pool.filter(p => p.name.toLowerCase().includes(query)).slice(0, 8);

    if (filteredSuggestions.length > 0) {
      renderSuggestions(filteredSuggestions, lastAt);
      return;
    }
  }
  suggestionsBox.style.display = 'none';
  suggestionIdx = -1;
}

function renderSuggestions(list, atPos) {
  const box = document.getElementById('suggestions');
  box.innerHTML = list.map((item, i) => `
    <div class="suggestion-item ${i === suggestionIdx ? 'active' : ''}" data-idx="${i}">
       <span>@${item.name}</span>
       <span class="suggestion-item-type">${item.type}</span>
    </div>
  `).join('');
  box.style.display = 'block';

  box.querySelectorAll('.suggestion-item').forEach(el => {
    el.addEventListener('click', () => applySuggestion(list[el.dataset.idx], atPos));
  });
}

function handleCommandKeydown(e) {
  const box = document.getElementById('suggestions');
  if (box.style.display === 'block') {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      suggestionIdx = (suggestionIdx + 1) % filteredSuggestions.length;
      renderSuggestions(filteredSuggestions);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      suggestionIdx = (suggestionIdx - 1 + filteredSuggestions.length) % filteredSuggestions.length;
      renderSuggestions(filteredSuggestions);
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      if (suggestionIdx >= 0) applySuggestion(filteredSuggestions[suggestionIdx]);
    } else if (e.key === 'Escape') {
      box.style.display = 'none';
    }
  } else if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    parseCommand(e.target.value);
    e.target.value = '';
  }
}

function applySuggestion(item) {
  const input = document.getElementById('story-command');
  const text = input.value;
  const cursor = input.selectionStart;
  const lastAt = text.lastIndexOf('@', cursor - 1);
  
  const before = text.slice(0, lastAt);
  const after = text.slice(cursor);
  input.value = before + '@' + item.name + ' ' + after;
  input.focus();
  document.getElementById('suggestions').style.display = 'none';
  
  // If it's a screen, add to story
  if (item.type === 'screen') {
    if (!currentStory.steps) currentStory.steps = [];
    currentStory.steps.push({ screenId: item.id, annotation: '' });
    renderCanvas();
  }
}

function parseCommand(cmd) {
  // Enhanced parser: "@Home tap @Settings"
  const screenMatches = cmd.match(/@([\w\s]+)/g);
  if (!screenMatches) return;

  const steps = [];
  let currentStep = null;

  // Split by words/tags and iterate
  const tokens = cmd.split(/\s+/);
  let lastAction = 'tap';

  tokens.forEach(token => {
    if (token.startsWith('@')) {
      const name = token.slice(1).replace(/[,.;]$/, '');
      
      // Check if it's a known screen
      const screen = availableScreens.find(s => s.name.toLowerCase() === name.toLowerCase());
      if (screen) {
        currentStep = { screenId: screen.id, annotation: cmd, actions: [] };
        steps.push(currentStep);
      } else if (currentStep) {
        // Assume it's an element on the current screen
        // In a real app we'd find the element ID here
        currentStep.actions.push({ type: lastAction, elementLabel: name });
        currentStep.annotation += ` [${lastAction} ${name}]`;
      }
    } else if (['tap', 'click', 'press', 'type', 'swipe'].includes(token.toLowerCase())) {
      lastAction = token.toLowerCase();
    }
  });

  if (steps.length > 0) {
    if (!currentStory.steps) currentStory.steps = [];
    currentStory.steps.push(...steps);
    renderCanvas();
  }
}
