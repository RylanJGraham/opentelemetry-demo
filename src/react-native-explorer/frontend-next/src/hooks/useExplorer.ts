import { useState, useEffect, useCallback, useRef } from 'react';

export type Node = { id: string; name?: string; screen_type?: string; screenshot_path?: string; [key: string]: any };
export type Edge = { id: number; source: string; target: string; action_type: string; [key: string]: any };
export type GraphData = { nodes: Node[]; edges: Edge[] };
export type StatusData = { state: string; message: string; total_screens: number; total_transitions: number; total_actions: number };
export type FeedItem = { type: string; message: string; time: Date };

export function useExplorer() {
  const [status, setStatus] = useState<StatusData>({ state: 'disconnected', message: '', total_screens: 0, total_transitions: 0, total_actions: 0 });
  const [graph, setGraph] = useState<GraphData>({ nodes: [], edges: [] });
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const ws = useRef<WebSocket | null>(null);

  const addFeedItem = useCallback((type: string, message: string) => {
    setFeed((prev) => [{ type, message, time: new Date() }, ...prev].slice(0, 50));
  }, []);

  const refreshGraph = useCallback(async () => {
    try {
      const res = await fetch('/api/graph');
      if (!res.ok) throw new Error('API Error');
      const data = await res.json();
      
      const fixedEdges = (data.edges || [])
        .filter((e: any) => e.source && e.target)
        .map((e: any) => ({
          ...e,
          source: typeof e.source === 'object' ? e.source.id : e.source,
          target: typeof e.target === 'object' ? e.target.id : e.target,
        }));
      
      setGraph({ nodes: data.nodes || [], edges: fixedEdges });
    } catch (e) {
      console.error('Failed to fetch graph', e);
    }
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const s = await res.json();
        setStatus(s);
      }
    } catch (e) {
      console.error('Failed to fetch status', e);
    }
  }, []);

  useEffect(() => {
    refreshGraph();
    refreshStatus();

    const connectWs = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/live`;
      const socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        addFeedItem('system', '🔌 Connected to Unified API server');
      };

      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          
          if (msg.type === 'status') {
            setStatus(msg.data);
          } else if (msg.type === 'new_screen') {
            addFeedItem('new-screen', `📱 New screen: ${msg.data?.name || 'Unknown'}`);
            refreshGraph(); // Safe re-fetch all
          } else if (msg.type === 'action') {
            addFeedItem('action', `👆 TAP: ${msg.data?.action || 'Unknown Action'}`);
            refreshGraph(); // Fetch new edges safely
          } else if (msg.type === 'error') {
            addFeedItem('error', `❌ Error: ${msg.data}`);
          }
        } catch (e) {}
      };

      socket.onclose = () => {
        addFeedItem('system', '⚠️ Disconnected from server. Reconnecting...');
        setTimeout(connectWs, 3000);
      };

      ws.current = socket;
    };

    connectWs();
    return () => ws.current?.close();
  }, [refreshGraph, refreshStatus, addFeedItem]);

  const sendCommand = async (url: string) => {
    try {
      await fetch(url, { method: 'POST' });
    } catch (e) {
      console.error('Command failed', e);
    }
  };

  return { status, graph, feed, refreshGraph, refreshStatus, sendCommand };
}
