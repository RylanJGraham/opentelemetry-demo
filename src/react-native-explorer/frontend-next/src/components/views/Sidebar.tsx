'use client';

import { StatusData, FeedItem } from '@/hooks/useExplorer';
import { Play, Pause, Square, Trash2 } from 'lucide-react';
import { useCallback, useState, useEffect } from 'react';

export default function Sidebar({ 
  status, 
  feed, 
  sendCommand 
}: { 
  status: StatusData, 
  feed: FeedItem[],
  sendCommand: (url: string) => Promise<void>
}) {
  const [liveImage, setLiveImage] = useState('/api/live-screenshot');
  const [imgKey, setImgKey] = useState<number>(0);

  // Poll live screenshot when exploring
  useEffect(() => {
    const fetchImage = async () => {
      try {
        const res = await fetch('/api/live-screenshot');
        if (res.ok) {
          const data = await res.json();
          if (data.image) setLiveImage(data.image);
        }
      } catch (error) {}
    };

    // Load initial frame if not exploring yet
    if (status.state !== 'exploring') {
       fetchImage();
    }

    const interval = setInterval(() => {
      if (status.state === 'exploring') {
        fetchImage();
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [status.state]);

  return (
    <div className="w-80 h-full bg-slate-900 border-l border-slate-800 flex flex-col shrink-0">
      <div className="p-4 border-b border-slate-800">
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">Emulator Sync</h2>
        <div className="aspect-[9/16] bg-black rounded-lg overflow-hidden relative border border-slate-700">
          <img 
            src={liveImage} 
            alt="Device Live View" 
            className="w-full h-full object-contain"
            onError={(e) => { e.currentTarget.style.display = 'none'; }}
            onLoad={(e) => { e.currentTarget.style.display = 'block'; }}
          />
          <div className="absolute inset-0 flex items-center justify-center text-slate-500 pointer-events-none" style={{ zIndex: -1 }}>
            No Signal
          </div>
        </div>
      </div>

      <div className="flex p-4 gap-2 border-b border-slate-800">
        <button 
          onClick={() => sendCommand('/api/agent/start')}
          className={`flex-1 py-2 px-3 rounded flex items-center justify-center gap-2 text-sm font-medium transition-colors ${status.state === 'exploring' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}
        >
          <Play size={16} /> Play
        </button>
        <button 
          onClick={() => sendCommand('/api/agent/pause')}
          className={`flex-1 py-2 px-3 rounded flex items-center justify-center gap-2 text-sm font-medium transition-colors ${status.state === 'paused' ? 'bg-amber-600 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'}`}
        >
          <Pause size={16} /> Pause
        </button>
        <button 
          onClick={() => sendCommand('/api/agent/stop')}
          disabled={status.state === 'idle'}
          className="flex-1 py-2 px-3 rounded flex items-center justify-center gap-2 text-sm font-medium bg-slate-800 text-slate-300 hover:bg-red-900/50 hover:text-red-400 disabled:opacity-50 transition-colors"
        >
          <Square size={16} /> Stop
        </button>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="p-3 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
          <h3 className="text-xs font-semibold text-slate-400 uppercase">Activity Log</h3>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-xs">
          {feed.length === 0 ? (
            <p className="text-slate-600 italic">No activity yet...</p>
          ) : (
            feed.map((item, i) => (
              <div key={i} className="flex flex-col gap-1">
                <span className="text-slate-500">{item.time.toLocaleTimeString()}</span>
                <span className={`leading-relaxed ${
                  item.type === 'error' ? 'text-red-400' : 
                  item.type === 'new-screen' ? 'text-emerald-400' : 
                  item.type === 'system' ? 'text-indigo-400' : 'text-slate-300'
                }`}>{item.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
