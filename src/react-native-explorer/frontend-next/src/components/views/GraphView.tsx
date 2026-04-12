'use client';

import { useRef, useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { GraphData } from '@/hooks/useExplorer';

const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false });

export default function GraphView({ data, onNodeSelect }: { data: GraphData, onNodeSelect: (id: string) => void }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const graphRef = useRef<any>(null);
  const imageCache = useRef<Record<string, HTMLImageElement>>({});

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Preload images into cache
  useEffect(() => {
    data.nodes.forEach(node => {
      if (node.screenshot_path && !imageCache.current[node.id]) {
        const img = new Image();
        img.src = `/api/screenshots/${node.screenshot_path}`;
        imageCache.current[node.id] = img;
      }
    });

    if (graphRef.current) {
      // Adjusted node spacing
      graphRef.current.d3Force('charge').strength(-1000);
      graphRef.current.d3Force('link').distance(250);
      graphRef.current.d3ReheatSimulation();
    }
  }, [data]);

  const drawCubicNode = (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const size = 30; // base size
    const img = imageCache.current[node.id];

    // Draw background placeholder or image
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(node.x - size / 2, node.y - size / 2, size, size * 1.5, 4);
    ctx.clip();

    if (img && img.complete) {
      // Draw image
      ctx.drawImage(img, node.x - size / 2, node.y - size / 2, size, size * 1.5);
    } else {
      ctx.fillStyle = '#1e293b';
      ctx.fill();
    }

    // Draw stroke
    ctx.lineWidth = 1.5 / globalScale;
    ctx.strokeStyle = node.screen_type === 'home' ? '#10b981' : node.screen_type === 'profile' ? '#f59e0b' : '#6366f1';
    ctx.stroke();
    ctx.restore();

    // Draw label
    if (globalScale > 0.4) {
      const label = node.name || 'Unknown Screen';
      ctx.font = `600 ${10 / globalScale}px Sans-Serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = 'rgba(15, 23, 42, 0.95)'; // Very dark slate
      const textWidth = ctx.measureText(label).width;
      const paddingX = 8 / globalScale;
      const paddingY = 6 / globalScale;

      ctx.beginPath();
      ctx.roundRect(node.x - textWidth / 2 - paddingX, node.y + (size * 1.5) / 2 + 6 / globalScale, textWidth + paddingX * 2, 12 / globalScale + paddingY * 2, 4 / globalScale);
      ctx.fill();

      ctx.fillStyle = '#ffffff'; // Pure white text
      ctx.fillText(label, node.x, node.y + (size * 1.5) / 2 + 6 / globalScale + paddingY + 1 / globalScale);
    }
  };

  const drawLinkLabel = (link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    if (globalScale < 1) return; // Only draw labels when zoomed in
    const start = link.source;
    const end = link.target;
    if (typeof start !== 'object' || typeof end !== 'object') return;

    let icon = '';
    if (link.action_type === 'tap') icon = '👆 ';
    else if (link.action_type === 'scroll') icon = '↕️ ';
    else if (link.action_type === 'input') icon = '⌨️ ';

    let text = link.action_type || 'tap';

    // Attempt to parse action_detail to get click label
    if (link.action_detail) {
      try {
        const detail = JSON.parse(link.action_detail);
        if (detail.label) text = detail.label;
        else if (detail.element_id) text = `id: ${detail.element_id.split('_').pop()}`;
      } catch (e) { }
    }

    // Truncate extremely long link texts
    if (text.length > 35) {
      text = text.substring(0, 32) + '...';
    }

    // Combine icon and text
    text = icon + text;

    const x = start.x + (end.x - start.x) / 2;
    const y = start.y + (end.y - start.y) / 2;

    ctx.font = `500 ${12 / globalScale}px Sans-Serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // Background pill
    ctx.fillStyle = '#0f172a'; // darker background for more contrast
    const textWidth = ctx.measureText(text).width;
    const paddingX = 8 / globalScale;
    const paddingY = 6 / globalScale;

    ctx.beginPath();
    ctx.roundRect(x - textWidth / 2 - paddingX, y - (12 / globalScale) / 2 - paddingY, textWidth + paddingX * 2, 12 / globalScale + paddingY * 2, 6 / globalScale);
    ctx.fill();
    ctx.strokeStyle = '#3b82f6'; // Bright blue border for links!
    ctx.lineWidth = 1.5 / globalScale;
    ctx.stroke();

    ctx.fillStyle = '#ffffff'; // Pure white text
    ctx.fillText(text, x, y);
  };

  return (
    <div ref={containerRef} className="w-full h-full bg-slate-950 rounded-xl overflow-hidden shadow-inner flex items-center justify-center">
      {data.nodes.length === 0 ? (
        <div className="text-slate-500 flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-slate-700 border-t-indigo-500 rounded-full animate-spin"></div>
          <p>Waiting for screens...</p>
        </div>
      ) : (
        <ForceGraph2D
          ref={graphRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={{ nodes: data.nodes, links: data.edges }}
          nodeId="id"
          nodeCanvasObject={drawCubicNode}
          linkCanvasObjectMode={() => 'after'}
          linkCanvasObject={drawLinkLabel}
          onNodeClick={(node) => onNodeSelect(node.id as string)}
          linkColor={() => 'rgba(255,255,255,0.2)'}
          linkWidth={4}
          linkDirectionalArrowLength={12}
          linkDirectionalArrowRelPos={1}
          dagLevelDistance={200}
          cooldownTicks={100}
        />
      )}
    </div>
  );
}
