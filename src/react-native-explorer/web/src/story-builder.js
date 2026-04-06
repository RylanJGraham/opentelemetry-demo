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
