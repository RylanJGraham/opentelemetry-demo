'use client';

import React, { useState, useRef, useEffect } from 'react';
import { GraphData, Node } from '@/hooks/useExplorer';
import { Play, Save, Trash2, GripVertical, ChevronRight, Wand2, AtSign } from 'lucide-react';

export default function StoryBuilder({ data }: { data: GraphData }) {
  const [storySteps, setStorySteps] = useState<Node[]>([]);
  const [prompt, setPrompt] = useState("");
  const [showMentionMenu, setShowMentionMenu] = useState(false);
  const [mentionQuery, setMentionQuery] = useState("");
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const filteredNodes = data.nodes.filter(n => n.name && n.name.toLowerCase().includes(mentionQuery.toLowerCase()));

  const handlePromptChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setPrompt(val);

    const words = val.split(/[\s\n]+/);
    const lastWord = words[words.length - 1];

    if (lastWord.startsWith("@")) {
      setShowMentionMenu(true);
      setMentionQuery(lastWord.slice(1).toLowerCase());
    } else {
      setShowMentionMenu(false);
    }
  };

  const insertMention = (node: Node) => {
    const words = prompt.split(/([\s\n]+)/);
    // last valid word is at the end, replace it
    for (let i = words.length - 1; i >= 0; i--) {
      if (words[i].startsWith("@")) {
        words[i] = `@${node.name?.replace(/\s+/g, '_')} `;
        break;
      }
    }
    
    setPrompt(words.join(""));
    setShowMentionMenu(false);
    
    // Automatically append to visual steps if not already there consecutively
    if (storySteps.length === 0 || storySteps[storySteps.length - 1].id !== node.id) {
      setStorySteps(prev => [...prev, node]);
    }

    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const addStep = (node: Node) => {
    setStorySteps([...storySteps, node]);
  };

  const removeStep = (index: number) => {
    const newSteps = [...storySteps];
    newSteps.splice(index, 1);
    setStorySteps(newSteps);
  };

  return (
    <div className="flex h-full w-full gap-6">
      
      {/* Left Area: Natural Language Prompter & Output */}
      <div className="flex-1 flex flex-col gap-6">
        
        {/* Scenario Editor */}
        <div className="flex-1 flex flex-col bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm relative">
          <div className="border-b border-slate-800 bg-slate-900/50 p-4 flex items-center justify-between">
            <h2 className="font-semibold text-slate-200 flex items-center gap-2">
              <Wand2 size={16} className="text-indigo-400" />
              NL Scenario Prompt
            </h2>
            <div className="flex gap-2">
              <button className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-md transition-colors text-xs font-medium flex items-center gap-2">
                <Save size={14} /> Save Draft
              </button>
              <button className="p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-md transition-colors text-xs font-semibold flex items-center gap-2 shadow-lg shadow-indigo-900/20">
                <Play size={14} fill="currentColor" /> Generate E2E Script
              </button>
            </div>
          </div>
          
          <div className="flex-1 relative p-6">
            <div className="absolute top-8 left-8 text-slate-500 pointer-events-none flex items-center gap-1 opacity-50">
               {prompt.length === 0 && <span>Type natural language or use <kbd className="bg-slate-800 px-1.5 py-0.5 rounded text-xs">@</kbd> to reference screens...</span>}
            </div>
            
            <textarea
              ref={textareaRef}
              value={prompt}
              onChange={handlePromptChange}
              placeholder=""
              className="w-full h-full bg-transparent text-slate-200 text-lg leading-relaxed focus:outline-none resize-none placeholder-slate-600 font-medium"
            />

            {/* Mention Dropdown */}
            {showMentionMenu && (
              <div className="absolute left-8 bottom-32 w-64 max-h-60 overflow-y-auto bg-slate-800 border border-slate-700 rounded-lg shadow-2xl z-50">
                <div className="p-2 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-700/50">
                  Link Node
                </div>
                {filteredNodes.length > 0 ? (
                  filteredNodes.map(node => (
                    <button
                      key={node.id}
                      onClick={() => insertMention(node)}
                      className="w-full text-left px-4 py-3 hover:bg-indigo-600 transition-colors flex items-center gap-3 border-b border-slate-700/30 last:border-0"
                    >
                      <img src={`/api/screenshots/${node.screenshot_path}`} className="w-8 h-12 object-cover rounded shadow-sm bg-slate-900" alt="" />
                      <div className="flex flex-col overflow-hidden">
                        <span className="truncate text-sm font-medium text-slate-200">{node.name}</span>
                        <span className="truncate text-xs text-slate-500">{node.screen_type}</span>
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="p-4 text-sm text-slate-500 text-center">No matching screens found</div>
                )}
              </div>
            )}
          </div>
          
          {/* Action Footer */}
          <div className="p-3 border-t border-slate-800 bg-slate-900/80 flex items-center gap-4 text-sm text-slate-400">
            <div className="flex items-center gap-1">
              <AtSign size={14} className="text-slate-500" /> Connect screens via mentions
            </div>
          </div>
        </div>

      </div>

      {/* Right Area: Visual Sequence Builder */}
      <div className="w-96 flex flex-col gap-6">
        
        {/* Visual Graph Sequence */}
        <div className="flex-1 border border-slate-800 bg-slate-900 rounded-xl flex flex-col overflow-hidden shadow-sm">
          <div className="p-4 border-b border-slate-800 bg-slate-900/50 flex justify-between items-center">
            <h3 className="font-semibold text-sm text-slate-200">Execution Sequence</h3>
            <span className="text-xs font-medium text-slate-500 bg-slate-800 px-2 py-1 rounded">{storySteps.length} Steps</span>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
            {storySteps.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 gap-3 border-2 border-dashed border-slate-800 rounded-xl p-6 text-center">
                <GripVertical size={24} className="opacity-20" />
                <p className="text-sm">Sequence empty.<br/>Type @ in prompt or select from gallery to add steps.</p>
              </div>
            ) : (
              storySteps.map((step, idx) => (
                <div key={`${step.id}-${idx}`} className="group relative bg-slate-800 border border-slate-700/50 p-2 rounded-lg flex items-center gap-3 hover:border-indigo-500/50 transition-colors shadow-sm">
                  <div className="cursor-grab p-1 text-slate-600 hover:text-slate-400">
                    <GripVertical size={16} />
                  </div>
                  
                  <div className="w-8 h-12 bg-slate-950 rounded shadow-inner overflow-hidden shrink-0 border border-slate-700">
                    {step.screenshot_path ? (
                      <img src={`/api/screenshots/${step.screenshot_path}`} className="w-full h-full object-cover" alt="" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-slate-800 text-[8px]">?</div>
                    )}
                  </div>
                  
                  <div className="flex-1 min-w-0 flex flex-col justify-center">
                    <div className="flex items-center gap-2">
                       <span className="bg-slate-950 text-slate-400 text-[10px] font-bold px-1.5 py-0.5 rounded leading-none">{idx + 1}</span>
                       <span className="text-sm font-medium text-slate-200 truncate">{step.name || 'Unknown Screen'}</span>
                    </div>
                  </div>
                  
                  <button 
                    onClick={() => removeStep(idx)}
                    className="p-2 text-slate-600 hover:text-rose-400 hover:bg-rose-500/10 rounded transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 size={14} />
                  </button>

                  {/* Flow Arrow */}
                  {idx < storySteps.length - 1 && (
                    <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 text-slate-600 z-10 w-6 h-6 flex items-center justify-center bg-slate-900 border border-slate-800 rounded-full">
                       <ChevronRight size={12} className="rotate-90" />
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Gallery / Node Picker Picker */}
        <div className="h-64 border border-slate-800 bg-slate-900 rounded-xl flex flex-col overflow-hidden shadow-sm">
          <div className="p-3 border-b border-slate-800 bg-slate-900/50">
             <h3 className="font-semibold text-sm text-slate-200">Available Nodes</h3>
          </div>
          <div className="flex-1 overflow-x-auto overflow-y-hidden p-3 flex gap-3 pb-4">
             {data.nodes.map(node => (
               <button 
                 key={'gallery-'+node.id}
                 onClick={() => addStep(node)}
                 className="flex flex-col items-center gap-2 shrink-0 group w-20"
               >
                 <div className="w-full aspect-[9/16] bg-slate-300 rounded shadow-md overflow-hidden border-2 border-transparent group-hover:border-indigo-500 transition-colors relative">
                    <img src={`/api/screenshots/${node.screenshot_path}`} className="w-full h-full object-cover" alt="" />
                    <div className="absolute inset-0 bg-indigo-500/0 group-hover:bg-indigo-500/20 flex items-center justify-center transition-all">
                      <Plus className="text-white opacity-0 group-hover:opacity-100 drop-shadow-md" />
                    </div>
                 </div>
                 <span className="text-xs text-slate-400 truncate w-full text-center group-hover:text-slate-200">{node.name}</span>
               </button>
             ))}
          </div>
        </div>

      </div>
    </div>
  );
}
