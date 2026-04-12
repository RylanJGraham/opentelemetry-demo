'use client';

import { useState } from 'react';
import { GraphData } from '@/hooks/useExplorer';

export default function GalleryView({ data, onNodeSelect }: { data: GraphData, onNodeSelect: (id: string) => void }) {
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  const screens = data.nodes
    .filter(n => filter === 'all' || n.screen_type === filter)
    .filter(n => (n.name || '').toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="h-full flex flex-col gap-4">
      <div className="flex gap-4 p-4 bg-slate-900/50 rounded-lg border border-slate-800">
        <input 
          type="text" 
          placeholder="Search screens..." 
          className="bg-slate-800 text-white px-4 py-2 rounded-md flex-1 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select 
          className="bg-slate-800 text-white px-4 py-2 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="all">All Types</option>
          <option value="home">Home</option>
          <option value="list">Lists</option>
          <option value="detail">Details</option>
          <option value="profile">Profile</option>
        </select>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 pb-20">
          {screens.map(screen => (
            <div key={screen.id} onClick={() => onNodeSelect(screen.id)} className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden hover:border-indigo-500 transition-colors group cursor-pointer shadow-lg hover:shadow-indigo-500/10">
              <div className="aspect-[9/16] relative bg-slate-950 overflow-hidden">
                {screen.screenshot_path ? (
                  <img src={`/api/screenshots/${screen.screenshot_path}`} alt={screen.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-slate-700">No Image</div>
                )}
              </div>
              <div className="p-3">
                <h3 className="text-sm font-semibold truncate text-slate-200">{screen.name}</h3>
                <p className="text-xs text-slate-500 capitalize">{screen.screen_type || 'Unknown'}</p>
                <p className="text-xs text-slate-500 mt-1">{screen.id.split('_').slice(-1)[0]}</p>
              </div>
            </div>
          ))}
        </div>
        {screens.length === 0 && (
          <div className="text-center text-slate-500 mt-20">No screens found.</div>
        )}
      </div>
    </div>
  );
}
