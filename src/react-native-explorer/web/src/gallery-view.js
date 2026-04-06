/**
 * Gallery View — Screenshot grid with search and filter.
 */

import { getScreens, getScreenshotUrl } from './api.js';

let allScreens = [];

/** Initialize the gallery view. */
export function initGalleryView() {
  const searchInput = document.getElementById('gallery-search');
  const filterSelect = document.getElementById('gallery-filter');

  searchInput.addEventListener('input', () => renderGallery());
  filterSelect.addEventListener('change', () => renderGallery());

  refreshGallery();
}

/** Refresh gallery data from API. */
export async function refreshGallery() {
  try {
    allScreens = await getScreens();
    renderGallery();
  } catch (e) {
    console.log('[Gallery] No data yet:', e.message);
  }
}

/** Add a screen to the gallery without full refresh. */
export function addScreenToGallery(screen) {
  if (!allScreens.find((s) => s.id === screen.id)) {
    allScreens.push(screen);
    renderGallery();
  }
}

/** Render the filtered/searched gallery grid. */
function renderGallery() {
  const grid = document.getElementById('gallery-grid');
  const searchTerm = document.getElementById('gallery-search').value.toLowerCase();
  const filterType = document.getElementById('gallery-filter').value;

  let filtered = allScreens;

  if (searchTerm) {
    filtered = filtered.filter(
      (s) =>
        (s.name || '').toLowerCase().includes(searchTerm) ||
        (s.description || '').toLowerCase().includes(searchTerm)
    );
  }

  if (filterType !== 'all') {
    filtered = filtered.filter((s) => s.screen_type === filterType);
  }

  if (filtered.length === 0) {
    grid.innerHTML = '<p class="empty-state">No screens found</p>';
    return;
  }

  grid.innerHTML = filtered
    .map(
      (screen) => `
    <div class="gallery-card" data-screen-id="${screen.id}">
      ${
        screen.screenshot_path
          ? `<img class="gallery-card-image" src="${getScreenshotUrl(screen.screenshot_path)}" alt="${screen.name}" loading="lazy" />`
          : `<div class="gallery-card-image" style="display:flex;align-items:center;justify-content:center;font-size:2rem;">📱</div>`
      }
      <div class="gallery-card-info">
        <div class="gallery-card-name">${screen.name || 'Unknown'}</div>
        <div class="gallery-card-meta">
          <span class="gallery-card-type">${screen.screen_type || 'unknown'}</span>
          <span>${screen.element_count || 0} elements</span>
        </div>
      </div>
    </div>
  `
    )
    .join('');

  // Click to expand (could open a modal in the future)
  grid.querySelectorAll('.gallery-card').forEach((card) => {
    card.addEventListener('click', () => {
      const screenId = card.dataset.screenId;
      const screen = allScreens.find((s) => s.id === screenId);
      if (screen && screen.screenshot_path) {
        // Switch to graph view and highlight this node
        const graphTab = document.querySelector('[data-view="graph"]');
        if (graphTab) graphTab.click();
      }
    });
  });
}

/** Get all screens (for story builder). */
export function getAllScreens() {
  return allScreens;
}
