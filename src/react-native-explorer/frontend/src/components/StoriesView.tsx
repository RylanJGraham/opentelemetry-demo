'use client';

import { useEffect, useState } from 'react';
import { Plus, Trash2, Play, Save, BookOpen } from 'lucide-react';
import { api } from '@/lib/api';
import type { Story, Screen } from '@/types';

export function StoriesView() {
  const [stories, setStories] = useState<Story[]>([]);
  const [screens, setScreens] = useState<Screen[]>([]);
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [newStoryName, setNewStoryName] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [storiesData, screensData] = await Promise.all([
        api.getStories(),
        api.getScreens(),
      ]);
      setStories(storiesData);
      setScreens(screensData);
    } catch (e) {
      console.error('Failed to load data:', e);
    }
  };

  const createStory = async () => {
    if (!newStoryName.trim()) return;
    
    try {
      await fetch('/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newStoryName, steps: [] }),
      });
      
      setNewStoryName('');
      setIsCreating(false);
      loadData();
    } catch (e) {
      console.error('Failed to create story:', e);
    }
  };

  const deleteStory = async (id: string) => {
    if (!confirm('Delete this story?')) return;
    
    try {
      await api.deleteStory?.(id) || fetch(`/api/stories/${id}`, { method: 'DELETE' });
      setSelectedStory(null);
      loadData();
    } catch (e) {
      console.error('Failed to delete story:', e);
    }
  };

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <div className="w-72 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-lg">Stories</h2>
            <button
              onClick={() => setIsCreating(true)}
              className="p-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          
          {isCreating && (
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Story name..."
                value={newStoryName}
                onChange={(e) => setNewStoryName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                autoFocus
                onKeyDown={(e) => e.key === 'Enter' && createStory()}
              />
              <div className="flex gap-2">
                <button
                  onClick={createStory}
                  className="flex-1 py-1 bg-green-600 hover:bg-green-700 rounded text-sm transition-colors"
                >
                  Create
                </button>
                <button
                  onClick={() => setIsCreating(false)}
                  className="flex-1 py-1 bg-slate-700 hover:bg-slate-600 rounded text-sm transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
        
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {stories.length === 0 ? (
            <p className="text-slate-500 text-sm text-center py-8">
              No stories yet. Create one to get started.
            </p>
          ) : (
            stories.map((story) => (
              <div
                key={story.id}
                onClick={() => setSelectedStory(story)}
                className={`p-3 rounded-lg cursor-pointer transition-colors flex items-center justify-between group ${
                  selectedStory?.id === story.id
                    ? 'bg-blue-600'
                    : 'hover:bg-slate-700'
                }`}
              >
                <div className="flex items-center gap-3">
                  <BookOpen className="w-4 h-4 opacity-60" />
                  <span className="font-medium text-sm truncate">{story.name}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteStory(story.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-600 rounded transition-all"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 overflow-y-auto">
        {selectedStory ? (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold">{selectedStory.name}</h2>
                <p className="text-slate-400 text-sm mt-1">
                  Created {new Date(selectedStory.created_at * 1000).toLocaleDateString()}
                </p>
              </div>
              <div className="flex gap-2">
                <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
                  <Save className="w-4 h-4" />
                  Save
                </button>
                <button className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg transition-colors">
                  <Play className="w-4 h-4" />
                  Run
                </button>
              </div>
            </div>

            {/* Steps */}
            <div className="space-y-4">
              {selectedStory.steps?.length === 0 ? (
                <div className="text-center py-12 bg-slate-800/50 rounded-lg border border-dashed border-slate-700">
                  <p className="text-slate-400">No steps yet</p>
                  <p className="text-slate-500 text-sm mt-2">
                    Drag screens here or add actions to build your story
                  </p>
                </div>
              ) : (
                selectedStory.steps?.map((step, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-4 p-4 bg-slate-800 rounded-lg border border-slate-700"
                  >
                    <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center font-bold text-sm">
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">{step.action}</p>
                      <p className="text-slate-400 text-sm">{step.annotation}</p>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Available Screens */}
            <div className="mt-8">
              <h3 className="font-bold mb-4">Available Screens</h3>
              <div className="grid grid-cols-4 gap-4">
                {screens.slice(0, 8).map((screen) => (
                  <div
                    key={screen.id}
                    className="bg-slate-800 rounded-lg overflow-hidden border border-slate-700 hover:border-blue-500 cursor-pointer transition-colors"
                  >
                    {screen.screenshot_path ? (
                      <img
                        src={api.getScreenshotUrl(screen.screenshot_path)}
                        alt={screen.name}
                        className="w-full aspect-[9/16] object-cover"
                      />
                    ) : (
                      <div className="w-full aspect-[9/16] bg-slate-900 flex items-center justify-center text-2xl">
                        📱
                      </div>
                    )}
                    <p className="p-2 text-xs truncate">{screen.name}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <BookOpen className="w-16 h-16 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400 text-lg">Select a story to view details</p>
              <p className="text-slate-500 text-sm mt-2">Or create a new story to get started</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
