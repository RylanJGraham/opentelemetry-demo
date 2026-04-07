'use client';

import { useEffect, useState } from 'react';
import { Search, Filter } from 'lucide-react';
import { api } from '@/lib/api';
import type { Screen } from '@/types';

export function GalleryView() {
  const [screens, setScreens] = useState<Screen[]>([]);
  const [filtered, setFiltered] = useState<Screen[]>([]);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadScreens();
    const interval = setInterval(loadScreens, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let result = screens;
    
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(s => 
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q)
      );
    }
    
    if (filter !== 'all') {
      result = result.filter(s => s.screen_type === filter);
    }
    
    setFiltered(result);
  }, [screens, search, filter]);

  const loadScreens = async () => {
    try {
      const data = await api.getScreens();
      setScreens(data);
    } catch (e) {
      console.error('Failed to load screens:', e);
    } finally {
      setLoading(false);
    }
  };

  const screenTypes = ['all', ...Array.from(new Set(screens.map(s => s.screen_type)))];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col p-6">
      {/* Toolbar */}
      <div className="flex items-center gap-4 mb-6">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            placeholder="Search screens..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-slate-400" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {screenTypes.map(type => (
              <option key={type} value={type}>
                {type === 'all' ? 'All Types' : type.charAt(0).toUpperCase() + type.slice(1)}
              </option>
            ))}
          </select>
        </div>
        
        <div className="text-slate-400 text-sm">
          {filtered.length} of {screens.length} screens
        </div>
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-slate-400 text-lg">
              {screens.length === 0 ? 'No screens discovered yet' : 'No screens match your search'}
            </p>
            {screens.length === 0 && (
              <p className="text-slate-500 text-sm mt-2">Start exploration to capture screens</p>
            )}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 overflow-y-auto">
          {filtered.map((screen) => (
            <div
              key={screen.id}
              className="bg-slate-800 rounded-lg overflow-hidden border border-slate-700 hover:border-blue-500 transition-colors group"
            >
              {/* Screenshot */}
              <div className="aspect-[9/16] bg-slate-900 relative overflow-hidden">
                {screen.screenshot_path ? (
                  <img
                    src={api.getScreenshotUrl(screen.screenshot_path)}
                    alt={screen.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-4xl">
                    📱
                  </div>
                )}
                
                {/* Overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              
              {/* Info */}
              <div className="p-3">
                <h3 className="font-medium text-sm truncate">{screen.name}</h3>
                <div className="flex items-center justify-between mt-2 text-xs text-slate-400">
                  <span className="capitalize px-2 py-1 bg-slate-700 rounded">
                    {screen.screen_type}
                  </span>
                  <span>{screen.element_count} elements</span>
                </div>
                <div className="flex items-center justify-between mt-2 text-xs text-slate-500">
                  <span>{screen.visit_count} visits</span>
                  {screen.fully_explored && (
                    <span className="text-green-400">✓ Explored</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
