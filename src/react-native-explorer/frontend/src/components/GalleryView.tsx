'use client';

import { useEffect, useState } from 'react';
import { Search, Filter, X, Calendar, Hash, Eye, CheckCircle } from 'lucide-react';
import { api } from '@/lib/api';
import type { Screen, Element } from '@/types';

export function GalleryView() {
  const [screens, setScreens] = useState<Screen[]>([]);
  const [filtered, setFiltered] = useState<Screen[]>([]);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [selectedScreen, setSelectedScreen] = useState<Screen | null>(null);
  const [elements, setElements] = useState<Element[]>([]);

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
        s.description?.toLowerCase().includes(q)
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

  const handleScreenClick = async (screen: Screen) => {
    setSelectedScreen(screen);
    try {
      const details = await api.getScreen(screen.id);
      setElements(details.elements || []);
    } catch (e) {
      console.error('Failed to load screen details:', e);
      setElements([]);
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
              onClick={() => handleScreenClick(screen)}
              className="bg-slate-800 rounded-lg overflow-hidden border border-slate-700 hover:border-blue-500 transition-colors group cursor-pointer"
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

      {/* Modal */}
      {selectedScreen && (
        <div 
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedScreen(null)}
        >
          <div 
            className="bg-slate-900 rounded-xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col md:flex-row"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Left: Screenshot */}
            <div className="flex-1 bg-black flex items-center justify-center p-4 overflow-auto">
              {selectedScreen.screenshot_path ? (
                <img
                  src={api.getScreenshotUrl(selectedScreen.screenshot_path)}
                  alt={selectedScreen.name}
                  className="max-h-[80vh] max-w-full object-contain rounded-lg shadow-2xl"
                />
              ) : (
                <div className="text-8xl">📱</div>
              )}
            </div>

            {/* Right: Info */}
            <div className="w-full md:w-96 bg-slate-800 flex flex-col max-h-[50vh] md:max-h-[90vh]">
              {/* Header */}
              <div className="p-4 border-b border-slate-700 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold">{selectedScreen.name}</h2>
                  <p className="text-sm text-slate-400">{selectedScreen.id}</p>
                </div>
                <button
                  onClick={() => setSelectedScreen(null)}
                  className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Scrollable Content */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {/* Quick Stats */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-900 rounded-lg p-3">
                    <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
                      <Hash className="w-3 h-3" />
                      Type
                    </div>
                    <span className="capitalize font-medium">{selectedScreen.screen_type}</span>
                  </div>
                  <div className="bg-slate-900 rounded-lg p-3">
                    <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
                      <Eye className="w-3 h-3" />
                      Visits
                    </div>
                    <span className="font-medium">{selectedScreen.visit_count}</span>
                  </div>
                  <div className="bg-slate-900 rounded-lg p-3">
                    <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
                      <CheckCircle className="w-3 h-3" />
                      Elements
                    </div>
                    <span className="font-medium">{selectedScreen.element_count}</span>
                  </div>
                  <div className="bg-slate-900 rounded-lg p-3">
                    <div className="flex items-center gap-2 text-slate-400 text-xs mb-1">
                      <Calendar className="w-3 h-3" />
                      First Seen
                    </div>
                    <span className="font-medium text-xs">
                      {new Date(selectedScreen.first_seen * 1000).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                {/* Status */}
                <div className="bg-slate-900 rounded-lg p-3">
                  <span className="text-slate-400 text-xs block mb-1">Status</span>
                  <div className="flex items-center gap-2">
                    {selectedScreen.fully_explored ? (
                      <>
                        <span className="w-2 h-2 bg-green-500 rounded-full" />
                        <span className="text-green-400">Fully Explored</span>
                      </>
                    ) : (
                      <>
                        <span className="w-2 h-2 bg-yellow-500 rounded-full" />
                        <span className="text-yellow-400">Partially Explored</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Description */}
                {selectedScreen.description && (
                  <div className="bg-slate-900 rounded-lg p-3">
                    <span className="text-slate-400 text-xs block mb-1">Description</span>
                    <p className="text-sm">{selectedScreen.description}</p>
                  </div>
                )}

                {/* AI Confidence */}
                {selectedScreen.ai_confidence > 0 && (
                  <div className="bg-slate-900 rounded-lg p-3">
                    <span className="text-slate-400 text-xs block mb-2">AI Confidence</span>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 bg-slate-700 rounded-full h-2">
                        <div 
                          className="bg-blue-500 h-2 rounded-full transition-all"
                          style={{ width: `${selectedScreen.ai_confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium">
                        {Math.round(selectedScreen.ai_confidence * 100)}%
                      </span>
                    </div>
                  </div>
                )}

                {/* Flags */}
                <div className="flex gap-2">
                  {selectedScreen.is_modal && (
                    <span className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded-full text-xs">
                      Modal
                    </span>
                  )}
                  {selectedScreen.requires_auth && (
                    <span className="px-3 py-1 bg-red-500/20 text-red-400 rounded-full text-xs">
                      Requires Auth
                    </span>
                  )}
                  {selectedScreen.is_error_state && (
                    <span className="px-3 py-1 bg-red-500/20 text-red-400 rounded-full text-xs">
                      Error State
                    </span>
                  )}
                </div>

                {/* Elements List */}
                {elements.length > 0 && (
                  <div className="bg-slate-900 rounded-lg overflow-hidden">
                    <div className="px-3 py-2 bg-slate-800 border-b border-slate-700">
                      <h4 className="font-medium text-sm">Elements ({elements.length})</h4>
                    </div>
                    <div className="max-h-48 overflow-y-auto">
                      {elements.slice(0, 15).map((el, idx) => (
                        <div key={el.id} className="px-3 py-2 border-b border-slate-800 text-sm">
                          <div className="flex items-center justify-between">
                            <span className="font-medium truncate flex-1">
                              {el.label || el.text_content || `Element ${idx + 1}`}
                            </span>
                            <span className="text-xs text-slate-400 ml-2 capitalize">
                              {el.normalized_type || el.element_type}
                            </span>
                          </div>
                          {el.semantic_type && (
                            <span className="text-xs text-blue-400 block">{el.semantic_type}</span>
                          )}
                          <div className="text-xs text-slate-500 mt-1">
                            ({el.x}, {el.y}) {el.interacted && '✓ tapped'}
                          </div>
                        </div>
                      ))}
                      {elements.length > 15 && (
                        <div className="px-3 py-2 text-center text-xs text-slate-500">
                          + {elements.length - 15} more elements
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
