'use client';

import { useState, useEffect } from 'react';
import { Header } from '@/components/Header';
import { GraphView } from '@/components/GraphView';
import { GalleryView } from '@/components/GalleryView';
import { StoriesView } from '@/components/StoriesView';
import { ActivitySidebar } from '@/components/ActivitySidebar';
import { api } from '@/lib/api';
import type { ExplorationStatus, ViewType } from '@/types';

export default function Home() {
  const [currentView, setCurrentView] = useState<ViewType>('graph');
  const [status, setStatus] = useState<ExplorationStatus>({
    state: 'idle',
    screens_found: 0,
    actions_taken: 0,
    duration_seconds: 0,
  });
  const [activities, setActivities] = useState<{type: string; message: string; time: string}[]>([]);

  useEffect(() => {
    // Connect WebSocket
    api.connectWebSocket();
    
    // Handle real-time updates
    api.onMessage((event, data) => {
      switch (event) {
        case 'state_change':
          setStatus(prev => ({ ...prev, state: data.state }));
          break;
        case 'new_screen':
          setStatus(prev => ({ ...prev, screens_found: data.screens_found }));
          addActivity('screen', `Discovered: ${data.name}`);
          break;
        case 'action':
          setStatus(prev => ({ ...prev, actions_taken: data.actions_taken }));
          addActivity('action', `${data.type} on ${data.element || 'element'}`);
          break;
        case 'status':
          setStatus(data);
          break;
      }
    });

    // Initial status poll
    api.getStatus().then(setStatus).catch(() => {});

    return () => {
      api.disconnectWebSocket();
    };
  }, []);

  const addActivity = (type: string, message: string) => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setActivities(prev => [{ type, message, time }, ...prev].slice(0, 50));
  };

  const handleStart = async () => {
    await api.startExploration();
    addActivity('system', 'Exploration started');
  };

  const handlePause = async () => {
    await api.pauseExploration();
    addActivity('system', 'Exploration paused');
  };

  const handleResume = async () => {
    await api.resumeExploration();
    addActivity('system', 'Exploration resumed');
  };

  const handleStop = async () => {
    await api.stopExploration();
    addActivity('system', 'Exploration stopped');
  };

  return (
    <div className="h-screen flex flex-col bg-slate-900">
      <Header
        currentView={currentView}
        onViewChange={setCurrentView}
        status={status}
        onStart={handleStart}
        onPause={handlePause}
        onResume={handleResume}
        onStop={handleStop}
      />
      
      <div className="flex-1 flex overflow-hidden">
        <ActivitySidebar activities={activities} />
        
        <main className="flex-1 relative">
          {currentView === 'graph' && <GraphView />}
          {currentView === 'gallery' && <GalleryView />}
          {currentView === 'stories' && <StoriesView />}
        </main>
      </div>
    </div>
  );
}
