'use client';

import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { api } from '@/lib/api';
import type { GraphData, GraphNode, GraphEdge } from '@/types';

export function GraphView() {
  const svgRef = useRef<SVGSVGElement>(null);
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [loading, setLoading] = useState(true);

  // Load graph data
  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getGraph();
        setGraph(data);
      } catch (e) {
        console.error('Failed to load graph:', e);
      } finally {
        setLoading(false);
      }
    };
    load();

    // Refresh every 5 seconds
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, []);

  // Render D3 graph
  useEffect(() => {
    if (!svgRef.current || graph.nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    // Create zoom group
    const g = svg.append('g');

    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
          g.attr('transform', event.transform);
        })
    );

    // Simulation
    const simulation = d3.forceSimulation<GraphNode>(graph.nodes as any)
      .force('link', d3.forceLink<GraphNode, any>(graph.edges as any).id((d: any) => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-500))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(50));

    // Draw edges
    const link = g.append('g')
      .selectAll('line')
      .data(graph.edges)
      .enter()
      .append('line')
      .attr('stroke', '#64748b')
      .attr('stroke-width', 2)
      .attr('class', 'graph-link');

    // Draw nodes
    const node = g.append('g')
      .selectAll('g')
      .data(graph.nodes)
      .enter()
      .append('g')
      .attr('class', 'graph-node')
      .call(
        d3.drag<any, GraphNode>()
          .on('start', (event, d: any) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d: any) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d: any) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      )
      .on('click', (event, d) => {
        event.stopPropagation();
        setSelectedNode(d);
      });

    // Node circles
    node.append('circle')
      .attr('r', 32)
      .attr('fill', (d: GraphNode) => {
        if (d.fully_explored) return '#059669';
        if (d.visit_count > 1) return '#d97706';
        return '#3b82f6';
      })
      .attr('stroke', (d: GraphNode) => {
        if (d.fully_explored) return '#34d399';
        if (d.visit_count > 1) return '#fbbf24';
        return '#60a5fa';
      })
      .attr('stroke-width', 3);

    // Node icons
    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '5')
      .attr('font-size', '24')
      .text((d: GraphNode) => {
        const icons: Record<string, string> = {
          authentication: '🔒',
          list: '📋',
          detail: '📄',
          settings: '⚙️',
          navigation: '🧭',
          form: '📝',
          modal: '💬',
          error: '❌',
        };
        return icons[d.type] || '📱';
      });

    // Node labels
    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', 50)
      .attr('fill', '#e2e8f0')
      .attr('font-size', '12')
      .attr('font-weight', '500')
      .text((d: GraphNode) => d.name.length > 20 ? d.name.slice(0, 20) + '...' : d.name);

    // Update positions
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });

    return () => {
      simulation.stop();
    };
  }, [graph]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* Graph Area */}
      <div className="flex-1 relative">
        <svg
          ref={svgRef}
          className="w-full h-full"
          style={{ minHeight: '600px' }}
        />
        
        {graph.nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <p className="text-slate-400 text-lg">No screens discovered yet</p>
              <p className="text-slate-500 text-sm mt-2">Start exploration to build the graph</p>
            </div>
          </div>
        )}
      </div>

      {/* Detail Panel */}
      {selectedNode && (
        <div className="w-80 bg-slate-800 border-l border-slate-700 p-4 overflow-y-auto">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-lg">{selectedNode.name}</h3>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-slate-400 hover:text-white"
            >
              ✕
            </button>
          </div>
          
          {selectedNode.screenshot && (
            <img
              src={api.getScreenshotUrl(selectedNode.screenshot)}
              alt={selectedNode.name}
              className="w-full rounded-lg mb-4"
            />
          )}
          
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Type:</span>
              <span className="capitalize">{selectedNode.type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Visits:</span>
              <span>{selectedNode.visit_count}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Status:</span>
              <span className={selectedNode.fully_explored ? 'text-green-400' : 'text-yellow-400'}>
                {selectedNode.fully_explored ? 'Explored' : 'Partial'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
