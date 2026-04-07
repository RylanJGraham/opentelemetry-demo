'use client';

import { useState } from 'react';
import { ChevronLeft, ChevronRight, Monitor, MousePointer, AlertCircle } from 'lucide-react';

interface Activity {
  type: string;
  message: string;
  time: string;
}

interface ActivitySidebarProps {
  activities: Activity[];
}

export function ActivitySidebar({ activities }: ActivitySidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  const getIcon = (type: string) => {
    switch (type) {
      case 'screen': return <Monitor className="w-4 h-4 text-blue-400" />;
      case 'action': return <MousePointer className="w-4 h-4 text-green-400" />;
      case 'error': return <AlertCircle className="w-4 h-4 text-red-400" />;
      default: return <div className="w-4 h-4 rounded-full bg-slate-500" />;
    }
  };

  if (collapsed) {
    return (
      <div className="w-12 bg-slate-800 border-r border-slate-700 flex flex-col items-center py-4">
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    );
  }

  return (
    <aside className="w-80 bg-slate-800 border-r border-slate-700 flex flex-col">
      {/* Header */}
      <div className="h-12 border-b border-slate-700 flex items-center justify-between px-4">
        <span className="font-medium text-sm">Live Activity</span>
        <button
          onClick={() => setCollapsed(true)}
          className="p-1 hover:bg-slate-700 rounded transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* Activity Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {activities.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-8">
            No activity yet. Start exploration to see live updates.
          </p>
        ) : (
          activities.map((activity, i) => (
            <div
              key={i}
              className="flex items-start gap-3 p-3 bg-slate-900 rounded-lg border border-slate-700/50"
            >
              {getIcon(activity.type)}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-slate-200 truncate">{activity.message}</p>
                <p className="text-xs text-slate-500 mt-1">{activity.time}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}
