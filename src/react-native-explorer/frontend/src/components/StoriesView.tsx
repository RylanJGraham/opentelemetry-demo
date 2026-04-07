'use client';

import { useEffect, useState } from 'react';
import { 
  Plus, Trash2, Play, Save, BookOpen, Pause, Square, 
  ChevronRight, CheckCircle, XCircle, Clock, MoreVertical,
  Radio, Activity, Terminal
} from 'lucide-react';
import { api } from '@/lib/api';
import type { Story, Execution, Screen } from '@/types';

export function StoriesView() {
  const [stories, setStories] = useState<Story[]>([]);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [screens, setScreens] = useState<Screen[]>([]);
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);
  const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [newStoryName, setNewStoryName] = useState('');
  const [activeTab, setActiveTab] = useState<'stories' | 'executions'>('stories');
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionStepByStep, setExecutionStepByStep] = useState(false);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadExecutions, 2000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [storiesData, executionsData, screensData] = await Promise.all([
        api.getStories(),
        api.getExecutions(),
        api.getScreens(),
      ]);
      setStories(storiesData);
      setExecutions(executionsData.executions);
      setScreens(screensData);
    } catch (e) {
      console.error('Failed to load data:', e);
    }
  };

  const loadExecutions = async () => {
    try {
      const data = await api.getExecutions();
      setExecutions(data.executions);
    } catch (e) {
      console.error('Failed to load executions:', e);
    }
  };

  const createStory = async () => {
    if (!newStoryName.trim()) return;
    
    try {
      await api.createStory({ name: newStoryName, steps: [] });
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
      await api.deleteStory(id);
      setSelectedStory(null);
      loadData();
    } catch (e) {
      console.error('Failed to delete story:', e);
    }
  };

  const executeStory = async (storyId: string) => {
    try {
      setIsExecuting(true);
      await api.executeStory(storyId, executionStepByStep);
      loadData();
      setActiveTab('executions');
    } catch (e) {
      console.error('Failed to execute story:', e);
      alert('Failed to start execution');
    } finally {
      setIsExecuting(false);
    }
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return '--';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'running':
        return <Radio className="w-4 h-4 text-blue-400 animate-pulse" />;
      case 'paused':
        return <Pause className="w-4 h-4 text-yellow-400" />;
      default:
        return <Clock className="w-4 h-4 text-slate-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500/20 text-green-400 border-green-500/30';
      case 'failed':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'running':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'paused':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <div className="w-80 bg-slate-800 border-r border-slate-700 flex flex-col">
        {/* Tabs */}
        <div className="flex border-b border-slate-700">
          <button
            onClick={() => setActiveTab('stories')}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'stories'
                ? 'bg-slate-700 text-white border-b-2 border-blue-500'
                : 'text-slate-400 hover:text-white hover:bg-slate-750'
            }`}
          >
            <BookOpen className="w-4 h-4 inline mr-2" />
            Stories
          </button>
          <button
            onClick={() => setActiveTab('executions')}
            className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === 'executions'
                ? 'bg-slate-700 text-white border-b-2 border-blue-500'
                : 'text-slate-400 hover:text-white hover:bg-slate-750'
            }`}
          >
            <Activity className="w-4 h-4 inline mr-2" />
            Executions
          </button>
        </div>

        {/* Stories List */}
        {activeTab === 'stories' && (
          <>
            <div className="p-4 border-b border-slate-700">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-bold text-lg">Test Stories</h2>
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
                    onClick={() => { setSelectedStory(story); setSelectedExecution(null); }}
                    className={`p-3 rounded-lg cursor-pointer transition-colors flex items-center justify-between group ${
                      selectedStory?.id === story.id
                        ? 'bg-blue-600'
                        : 'hover:bg-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <BookOpen className="w-4 h-4 opacity-60 flex-shrink-0" />
                      <div className="min-w-0">
                        <span className="font-medium text-sm truncate block">{story.name}</span>
                        <span className="text-xs opacity-60">{story.steps?.length || 0} steps</span>
                      </div>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteStory(story.id);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-600 rounded transition-all flex-shrink-0"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </>
        )}

        {/* Executions List */}
        {activeTab === 'executions' && (
          <>
            <div className="p-4 border-b border-slate-700">
              <h2 className="font-bold text-lg">Recent Runs</h2>
              <p className="text-xs text-slate-400 mt-1">
                {executions.filter(e => e.status === 'running').length} running
              </p>
            </div>
            
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {executions.length === 0 ? (
                <p className="text-slate-500 text-sm text-center py-8">
                  No executions yet. Run a story to see results.
                </p>
              ) : (
                executions.map((exec) => (
                  <div
                    key={exec.id}
                    onClick={() => { setSelectedExecution(exec); setSelectedStory(null); }}
                    className={`p-3 rounded-lg cursor-pointer transition-colors ${
                      selectedExecution?.id === exec.id
                        ? 'bg-blue-600'
                        : 'hover:bg-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-sm truncate">{exec.story_name || exec.story_id}</span>
                      {getStatusIcon(exec.status)}
                    </div>
                    <div className="flex items-center gap-2 text-xs opacity-60">
                      <span className={`px-2 py-0.5 rounded border ${getStatusColor(exec.status)}`}>
                        {exec.status}
                      </span>
                      <span>{formatDuration(exec.duration_ms)}</span>
                    </div>
                    {exec.status === 'completed' && (
                      <div className="flex items-center gap-3 mt-2 text-xs">
                        <span className="text-green-400">✓ {exec.passed_steps}</span>
                        {exec.failed_steps > 0 && (
                          <span className="text-red-400">✗ {exec.failed_steps}</span>
                        )}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 overflow-y-auto">
        {/* Story Detail View */}
        {selectedStory && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold">{selectedStory.name}</h2>
                <p className="text-slate-400 text-sm mt-1">
                  Created {new Date(selectedStory.created_at * 1000).toLocaleDateString()}
                  {selectedStory.priority && (
                    <span className={`ml-3 px-2 py-0.5 rounded text-xs ${
                      selectedStory.priority === 'high' ? 'bg-red-500/20 text-red-400' :
                      selectedStory.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-slate-500/20 text-slate-400'
                    }`}>
                      {selectedStory.priority}
                    </span>
                  )}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2 text-sm text-slate-400">
                  <input
                    type="checkbox"
                    checked={executionStepByStep}
                    onChange={(e) => setExecutionStepByStep(e.target.checked)}
                    className="rounded border-slate-600"
                  />
                  Step-by-step
                </label>
                <button 
                  onClick={() => executeStory(selectedStory.id)}
                  disabled={isExecuting}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
                >
                  <Play className="w-4 h-4" />
                  {isExecuting ? 'Starting...' : 'Run'}
                </button>
              </div>
            </div>

            {/* Steps */}
            <div className="space-y-4 mb-8">
              <h3 className="font-semibold text-slate-300">Steps</h3>
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
                      <p className="font-medium capitalize">{step.action}</p>
                      <p className="text-slate-400 text-sm">
                        {step.element_query?.label || step.element_id || step.screen_id || 'No target'}
                        {step.assertion && (
                          <span className="text-blue-400 ml-2">Assert: {step.assertion}</span>
                        )}
                      </p>
                    </div>
                    {step.data && Object.keys(step.data).length > 0 && (
                      <code className="text-xs bg-slate-900 px-2 py-1 rounded">
                        {JSON.stringify(step.data)}
                      </code>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Execution History */}
            {selectedStory.executions && selectedStory.executions.length > 0 && (
              <div>
                <h3 className="font-semibold text-slate-300 mb-4">Execution History</h3>
                <div className="space-y-2">
                  {selectedStory.executions.slice(0, 5).map((exec) => (
                    <div key={exec.id} className="flex items-center gap-4 p-3 bg-slate-800/50 rounded-lg">
                      {getStatusIcon(exec.status)}
                      <span className="text-sm">{formatDate(exec.started_at)}</span>
                      <span className={`px-2 py-0.5 rounded text-xs border ${getStatusColor(exec.status)}`}>
                        {exec.status}
                      </span>
                      <span className="text-sm text-slate-400">{formatDuration(exec.duration_ms)}</span>
                      {exec.passed_steps > 0 && (
                        <span className="text-green-400 text-sm">{exec.passed_steps} passed</span>
                      )}
                      {exec.failed_steps > 0 && (
                        <span className="text-red-400 text-sm">{exec.failed_steps} failed</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

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
        )}

        {/* Execution Detail View */}
        {selectedExecution && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold">Execution Details</h2>
                <p className="text-slate-400 text-sm mt-1">
                  {selectedExecution.story_name || selectedExecution.story_id}
                </p>
              </div>
              <div className={`px-4 py-2 rounded-lg border ${getStatusColor(selectedExecution.status)}`}>
                {selectedExecution.status.toUpperCase()}
              </div>
            </div>

            {/* Execution Stats */}
            <div className="grid grid-cols-4 gap-4 mb-8">
              <div className="bg-slate-800 p-4 rounded-lg">
                <p className="text-slate-400 text-sm">Duration</p>
                <p className="text-xl font-bold">{formatDuration(selectedExecution.duration_ms)}</p>
              </div>
              <div className="bg-slate-800 p-4 rounded-lg">
                <p className="text-slate-400 text-sm">Steps Passed</p>
                <p className="text-xl font-bold text-green-400">{selectedExecution.passed_steps}</p>
              </div>
              <div className="bg-slate-800 p-4 rounded-lg">
                <p className="text-slate-400 text-sm">Steps Failed</p>
                <p className="text-xl font-bold text-red-400">{selectedExecution.failed_steps}</p>
              </div>
              <div className="bg-slate-800 p-4 rounded-lg">
                <p className="text-slate-400 text-sm">Total Steps</p>
                <p className="text-xl font-bold">{selectedExecution.total_steps}</p>
              </div>
            </div>

            <p className="text-slate-500 text-center py-8">
              Detailed step results coming soon...
            </p>
          </div>
        )}

        {/* Empty State */}
        {!selectedStory && !selectedExecution && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              {activeTab === 'stories' ? (
                <>
                  <BookOpen className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                  <p className="text-slate-400 text-lg">Select a story to view details</p>
                  <p className="text-slate-500 text-sm mt-2">Or create a new story to get started</p>
                </>
              ) : (
                <>
                  <Terminal className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                  <p className="text-slate-400 text-lg">Select an execution to view details</p>
                  <p className="text-slate-500 text-sm mt-2">Run a story to see results here</p>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
