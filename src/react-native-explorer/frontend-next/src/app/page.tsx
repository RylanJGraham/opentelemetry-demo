'use client';

import { useState } from 'react';
import { useExplorer } from '@/hooks/useExplorer';
import { LayoutDashboard, Image as ImageIcon, BookOpen, Activity } from 'lucide-react';
import GraphView from '@/components/views/GraphView';
import GalleryView from '@/components/views/GalleryView';
import Sidebar from '@/components/views/Sidebar';
import StoryBuilder from '@/components/views/StoryBuilder';
import NodeInspector from '@/components/views/NodeInspector';

export default function Dashboard() {
  const { status, graph, feed, refreshGraph, sendCommand } = useExplorer();
  const [activeTab, setActiveTab] = useState<'graph' | 'gallery' | 'stories'>('graph');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-200 overflow-hidden font-sans">
      
      {/* Left Sidebar (Emulator & Logs) */}
      <Sidebar status={status} feed={feed} sendCommand={sendCommand} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 border-r border-slate-800">
        
        {/* Top Navigation */}
        <header className="h-16 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between px-6 shrink-0 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <Activity className="text-indigo-500" />
            <h1 className="font-bold text-lg tracking-tight shrink-0 mr-8">React Native Explorer</h1>
            
            <nav className="flex space-x-1">
              <button 
                onClick={() => setActiveTab('graph')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'graph' ? 'bg-indigo-500/10 text-indigo-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
              >
                <LayoutDashboard size={16} /> Graph
              </button>
              <button 
                onClick={() => setActiveTab('gallery')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'gallery' ? 'bg-indigo-500/10 text-indigo-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
              >
                <ImageIcon size={16} /> Gallery
              </button>
              <button 
                onClick={() => setActiveTab('stories')}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'stories' ? 'bg-indigo-500/10 text-indigo-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'}`}
              >
                <BookOpen size={16} /> Stories
              </button>
            </nav>
          </div>

          <div className="flex items-center gap-6">
            <div className="flex gap-4 text-xs font-semibold uppercase tracking-wider text-slate-400">
              <span className="flex items-center gap-2">Screens <span className="text-white text-sm bg-slate-800 px-2 py-0.5 rounded">{status.total_screens}</span></span>
              <span className="flex items-center gap-2">Transitions <span className="text-white text-sm bg-slate-800 px-2 py-0.5 rounded">{status.total_transitions}</span></span>
            </div>
            <div className="flex items-center gap-2">
              <span className="relative flex h-3 w-3">
                {status.state === 'exploring' && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
                <span className={`relative inline-flex rounded-full h-3 w-3 ${status.state === 'exploring' ? 'bg-emerald-500' : status.state === 'paused' ? 'bg-amber-500' : 'bg-slate-600'}`}></span>
              </span>
              <span className="text-xs uppercase font-medium text-slate-400 w-20">{status.state}</span>
            </div>
          </div>
        </header>

        {/* Tab Content */}
        <main className="flex-1 p-6 overflow-hidden relative">
          {activeTab === 'graph' && <GraphView data={graph} onNodeSelect={setSelectedNodeId} />}
          {activeTab === 'gallery' && <GalleryView data={graph} onNodeSelect={setSelectedNodeId} />}
          {activeTab === 'stories' && <StoryBuilder data={graph} />}
        </main>
      </div>

      {/* Right Node Inspector */}
      <NodeInspector nodeId={selectedNodeId} graph={graph} onClose={() => setSelectedNodeId(null)} />
      
    </div>
  );
}
