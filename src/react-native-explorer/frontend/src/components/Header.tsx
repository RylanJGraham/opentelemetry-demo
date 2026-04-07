'use client';

import { Play, Pause, Square, Activity, Image, BookOpen, Search } from 'lucide-react';
import type { ExplorationStatus, ViewType } from '@/types';

interface HeaderProps {
  currentView: ViewType;
  onViewChange: (view: ViewType) => void;
  status: ExplorationStatus;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
}

const tabs: { id: ViewType; label: string; icon: typeof Activity }[] = [
  { id: 'graph', label: 'Graph', icon: Activity },
  { id: 'gallery', label: 'Gallery', icon: Image },
  { id: 'stories', label: 'Stories', icon: BookOpen },
];

export function Header({ currentView, onViewChange, status, onStart, onPause, onResume, onStop }: HeaderProps) {
  const isExploring = status.state === 'exploring';
  const isPaused = status.state === 'paused';
  const isIdle = status.state === 'idle' || status.state === 'complete';

  const getStatusColor = () => {
    switch (status.state) {
      case 'exploring': return 'bg-green-500 animate-pulse';
      case 'paused': return 'bg-yellow-500';
      case 'error': return 'bg-red-500';
      case 'connecting': return 'bg-blue-500 animate-pulse';
      default: return 'bg-gray-500';
    }
  };

  return (
    <header className="h-16 bg-slate-800 border-b border-slate-700 flex items-center justify-between px-4">
      {/* Left: Logo + Nav */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <Search className="w-6 h-6 text-blue-400" />
          <h1 className="text-xl font-bold">Explorer</h1>
        </div>
        
        <nav className="flex items-center gap-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = currentView === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onViewChange(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Right: Controls + Stats */}
      <div className="flex items-center gap-6">
        {/* Control Buttons */}
        <div className="flex items-center gap-2">
          {isIdle && (
            <button
              onClick={onStart}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <Play className="w-4 h-4" />
              Start
            </button>
          )}
          
          {isExploring && (
            <button
              onClick={onPause}
              className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <Pause className="w-4 h-4" />
              Pause
            </button>
          )}
          
          {isPaused && (
            <button
              onClick={onResume}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <Play className="w-4 h-4" />
              Resume
            </button>
          )}
          
          {!isIdle && (
            <button
              onClick={onStop}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <Square className="w-4 h-4" />
              Stop
            </button>
          )}
        </div>

        {/* Status Indicator */}
        <div className="flex items-center gap-3 px-4 py-2 bg-slate-900 rounded-lg">
          <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
          <span className="text-sm font-medium capitalize text-slate-200">
            {status.state}
          </span>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-4">
          <div className="text-center">
            <div className="text-lg font-bold text-white">{status.screens_found}</div>
            <div className="text-xs text-slate-400 uppercase tracking-wide">Screens</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-white">{status.actions_taken}</div>
            <div className="text-xs text-slate-400 uppercase tracking-wide">Actions</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-white">
              {Math.floor(status.duration_seconds / 60)}:{(status.duration_seconds % 60).toString().padStart(2, '0')}
            </div>
            <div className="text-xs text-slate-400 uppercase tracking-wide">Time</div>
          </div>
        </div>
      </div>
    </header>
  );
}
