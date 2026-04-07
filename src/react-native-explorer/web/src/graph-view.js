/**
 * Graph View — Interactive D3.js force-directed graph of screens and transitions.
 */

import * as d3 from 'd3';
import { getGraph, getScreen, getScreenshotUrl } from './api.js';

let simulation = null;
let svg = null;
let graphGroup = null;
let currentData = { nodes: [], edges: [] };

/** Initialize the graph view. */
export function initGraphView() {
  svg = d3.select('#graph-svg');
  const container = document.getElementById('graph-container');
  const width = container.clientWidth;
  const height = container.clientHeight;

  svg.attr('viewBox', [0, 0, width, height]);

  // Zoom behavior
  const zoom = d3.zoom()
    .scaleExtent([0.2, 4])
    .on('zoom', (event) => {
      graphGroup.attr('transform', event.transform);
    });

  svg.call(zoom);

  graphGroup = svg.append('g').attr('class', 'graph-group');

  // Arrow marker for edges
  svg.append('defs').append('marker')
    .attr('id', 'arrow')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 35)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', 'hsl(210, 15%, 35%)');

  // Detail panel close
  document.getElementById('detail-close').addEventListener('click', () => {
    document.getElementById('detail-panel').classList.remove('open');
  });

  // Init simulation
  simulation = d3.forceSimulation()
    .force('link', d3.forceLink().id((d) => d.id).distance(250))
    .force('charge', d3.forceManyBody().strength(-800))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(70));

  // Load initial data
  refreshGraph();
}

/** Refresh graph data from API. */
export async function refreshGraph() {
  try {
    const data = await getGraph();
    const container = document.getElementById('graph-container');
    const w = container.clientWidth || 800, h = container.clientHeight || 600;
    const oldNodes = new Map(currentData.nodes.map(n => [n.id, n]));
    
    data.nodes.forEach(n => {
       const old = oldNodes.get(n.id);
       if (old && old.x !== undefined && old.y !== undefined) {
           n.x = old.x;
           n.y = old.y;
           n.vx = old.vx;
           n.vy = old.vy;
           n.fx = old.fx;
           n.fy = old.fy;
       } else {
           n.x = (w/2) + (Math.random() - 0.5) * w * 0.8;
           n.y = (h/2) + (Math.random() - 0.5) * h * 0.8;
       }
    });
    currentData = data;
    renderGraph(data);
  } catch (e) {
    console.log('[Graph] No data yet or API unavailable:', e.message);
  }
}

/** Add a single node/edge without full refresh. */
export function addNode(screen) {
  if (currentData.nodes.find((n) => n.id === screen.id)) return;
  const container = document.getElementById('graph-container');
  const w = container.clientWidth || 800, h = container.clientHeight || 600;
  // Offset slightly from center to prevent perfect Z-stacking
  screen.x = (w/2) + (Math.random() - 0.5) * 100;
  screen.y = (h/2) + (Math.random() - 0.5) * 100;
  currentData.nodes.push(screen);
  renderGraph(currentData);
}

export function addEdge(transition) {
  currentData.edges.push(transition);
  renderGraph(currentData);
}

/** Render the graph with D3. */
function renderGraph(data) {
  const { nodes, edges } = data;
  if (!nodes.length) return;

  const container = document.getElementById('graph-container');
  const width = container.clientWidth;
  const height = container.clientHeight;

  // Clear previous
  graphGroup.selectAll('*').remove();

  // Links
  const link = graphGroup.append('g')
    .selectAll('line')
    .data(edges)
    .join('line')
    .attr('class', 'edge-line')
    .attr('marker-end', 'url(#arrow)');

  // Edge labels
  const edgeLabels = graphGroup.append('g')
    .selectAll('text')
    .data(edges)
    .join('text')
    .attr('class', 'edge-label')
    .text((d) => d.action_type || '');

  // Node groups
  const node = graphGroup.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .attr('class', 'node-group')
    .call(drag(simulation))
    .on('click', (event, d) => showScreenDetail(d))
    .on('dblclick', (event, d) => {
      // Double click to unpin
      delete d.fx;
      delete d.fy;
      d3.select(event.currentTarget).classed('pinned', false);
      simulation.alpha(0.3).restart();
    });

  // Hover tooltip
  node.append('title')
    .text((d) => `${d.name}\n${d.screen_type} • ${d.element_count || 0} elements\n(Double-click to unpin)`);

  // Node circles
  node.append('circle')
    .attr('class', 'node-circle')
    .attr('r', 32)
    .attr('fill', (d) => {
      if (d.fully_explored) return 'hsl(155, 75%, 20%)';
      if (d.visit_count > 1) return 'hsl(38, 95%, 25%)';
      return 'hsl(210, 15%, 20%)';
    })
    .attr('stroke', (d) => {
      if (d.fully_explored) return 'hsl(155, 75%, 50%)';
      if (d.visit_count > 1) return 'hsl(38, 95%, 55%)';
      return 'hsl(210, 15%, 45%)';
    })
    .attr('stroke-width', 2.5);

  // Node icon
  node.append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', '-0.1em')
    .attr('font-size', '20px')
    .attr('pointer-events', 'none')
    .text((d) => {
      const types = {
        authentication: '🔒',
        list: '📋',
        detail: '📄',
        settings: '⚙️',
        navigation: '🧭',
        form: '📝',
        modal: '💬',
        error: '❌',
        unknown: '📱',
      };
      return types[d.screen_type] || '📱';
    });

  // Node labels
  node.append('text')
    .attr('class', 'node-label')
    .attr('dy', 50)
    .text((d) => truncate(d.name, 22));

  // Secondary label (status)
  node.append('text')
    .attr('class', 'node-label-sub')
    .attr('dy', 18)
    .attr('text-anchor', 'middle')
    .text((d) => d.element_count ? `${d.element_count} el` : '');

  // Update simulation
  const validIds = new Set(nodes.map(n => n.id));
  const validEdges = edges.filter(e => validIds.has(e.source) && validIds.has(e.target));

  simulation.nodes(nodes);
  simulation.force('link').links(validEdges.map((e) => ({
    source: e.source,
    target: e.target,
  })));
  simulation.alpha(0.8).restart();

  simulation.on('tick', () => {
    link
      .attr('x1', (d) => d.source.x)
      .attr('y1', (d) => d.source.y)
      .attr('x2', (d) => d.target.x)
      .attr('y2', (d) => d.target.y);

    edgeLabels
      .attr('x', (d) => (d.source.x + d.target.x) / 2)
      .attr('y', (d) => (d.source.y + d.target.y) / 2);

    node.attr('transform', (d) => `translate(${d.x},${d.y})`);
  });
}

/** Show screen details in the sidebar. */
async function showScreenDetail(screenData) {
  const panel = document.getElementById('detail-panel');
  const content = document.getElementById('detail-content');

  try {
    const detail = await getScreen(screenData.id);

    const screenshotHtml = detail.screenshot_path
      ? `<img class="detail-screenshot" src="${getScreenshotUrl(detail.screenshot_path)}" alt="${detail.name}" />`
      : '';

    const elementsHtml = (detail.elements || []).map((el) => `
      <div class="element-item">
        <span class="element-item-type">${el.element_type}</span>
        <span class="element-item-label">${el.label || 'unnamed'}</span>
        <span class="element-item-status ${el.interacted ? 'interacted' : 'pending'}"></span>
      </div>
    `).join('');

    content.innerHTML = `
      ${screenshotHtml}
      <div class="detail-name">${detail.name}</div>
      <span class="detail-type">${detail.screen_type}</span>
      <p class="detail-desc">${detail.description || 'No description'}</p>
      <div class="detail-section-title">Elements (${(detail.elements || []).length})</div>
      <div class="element-list">${elementsHtml || '<p class="detail-placeholder">No elements</p>'}</div>
    `;
  } catch (e) {
    content.innerHTML = `<p class="detail-placeholder">Failed to load details</p>`;
  }

  panel.classList.add('open');
}

/** D3 drag behavior. */
function drag(simulation) {
  return d3.drag()
    .on('start', (event, d) => {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
      d3.select(event.sourceEvent.currentTarget).classed('grabbing', true);
    })
    .on('drag', (event, d) => {
      d.fx = event.x;
      d.fy = event.y;
    })
    .on('end', (event, d) => {
      if (!event.active) simulation.alphaTarget(0);
      d3.select(event.sourceEvent.currentTarget).classed('grabbing', false);
      d3.select(event.sourceEvent.currentTarget).classed('pinned', true);
      // Leaves d.fx and d.fy set so the node remains pinned where dropped!
    });
}

function truncate(str, len) {
  if (!str) return '';
  return str.length > len ? str.slice(0, len) + '…' : str;
}
