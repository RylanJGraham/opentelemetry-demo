'use client';

import { GraphData } from '@/hooks/useExplorer';
import { X, Search } from 'lucide-react';

export default function NodeInspector({ 
  nodeId, 
  graph, 
  onClose 
}: { 
  nodeId: string | null; 
  graph: GraphData; 
  onClose: () => void 
}) {
  if (!nodeId) return null;

  const node = graph.nodes.find(n => n.id === nodeId);
  if (!node) return null;

  const elements = node.elements || [];

  return (
    <div className="w-80 h-full bg-slate-900 border-l border-slate-800 flex flex-col shrink-0">
      <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
        <h2 className="text-sm font-semibold text-slate-200">Node Inspector</h2>
        <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
          <X size={16} />
        </button>
      </div>

      <div className="p-4 border-b border-slate-800 shrink-0">
        <div className="aspect-[9/16] bg-black rounded-lg overflow-hidden relative shadow-inner border border-slate-700">
          {node.screenshot_path ? (
            <img 
              src={`/api/screenshots/${node.screenshot_path}`} 
              alt={node.name} 
              className="w-full h-full object-contain"
            />
          ) : (
             <div className="w-full h-full flex items-center justify-center text-slate-700">No Image</div>
          )}
        </div>
      </div>

      <div className="p-4 border-b border-slate-800 shrink-0">
        <h3 className="text-lg font-bold text-white mb-1">{node.name || 'Unknown Screen'}</h3>
        <p className="text-xs text-indigo-400 uppercase tracking-widest font-semibold mb-2">{node.screen_type || 'unclassified'}</p>
        <p className="text-xs text-slate-400 leading-relaxed max-h-24 overflow-y-auto custom-scrollbar">
          {node.description || 'No AI description available for this screen.'}
        </p>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="px-4 py-2 bg-slate-900 border-b border-slate-800 flex justify-between items-center">
          <h4 className="text-xs font-semibold text-slate-400 uppercase">DOM Elements ({node.element_count || elements.length})</h4>
        </div>
        <div className="flex-1 overflow-y-auto p-2 font-mono text-[10px] space-y-1 custom-scrollbar hover:pr-1">
          {elements.length === 0 ? (
            <p className="p-2 text-slate-500 italic text-center">No elements parsed.</p>
          ) : (
            elements.map((el: any) => (
              <div key={el.id} className="p-2 bg-slate-800/50 rounded flex flex-col gap-1 border border-slate-800 hover:border-indigo-500/50 transition-colors">
                <div className="flex justify-between items-start">
                  <span className="text-indigo-300 font-bold truncate max-w-[180px]">{el.label || el.text_content || 'Unnamed'}</span>
                  <span className="text-slate-500 shrink-0">{el.element_type}</span>
                </div>
                <div className="text-slate-400 flex justify-between">
                  <span className="truncate">id: {el.id.split('_').pop()}</span>
                  <span>[{el.x},{el.y}]</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
