const API_URL = process.env.NEXT_PUBLIC_AGENT_URL || 'http://127.0.0.1:5100';

class ApiClient {
  private ws: WebSocket | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private messageHandlers: ((event: string, data: any) => void)[] = [];

  // REST API
  async getStatus(): Promise<ExplorationStatus> {
    const res = await fetch(`${API_URL}/api/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async startExploration(maxScreens?: number): Promise<any> {
    const res = await fetch(`${API_URL}/api/exploration/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ max_screens: maxScreens }),
    });
    return res.json();
  }

  async pauseExploration(): Promise<any> {
    const res = await fetch(`${API_URL}/api/exploration/pause`, { method: 'POST' });
    return res.json();
  }

  async resumeExploration(): Promise<any> {
    const res = await fetch(`${API_URL}/api/exploration/resume`, { method: 'POST' });
    return res.json();
  }

  async stopExploration(): Promise<any> {
    const res = await fetch(`${API_URL}/api/exploration/stop`, { method: 'POST' });
    return res.json();
  }

  async getScreens(): Promise<Screen[]> {
    const res = await fetch(`${API_URL}/api/screens`);
    const data = await res.json();
    return data.screens;
  }

  async getScreen(id: string): Promise<Screen & { elements: Element[]; transitions: Transition[] }> {
    const res = await fetch(`${API_URL}/api/screens/${id}`);
    return res.json();
  }

  async getGraph(): Promise<GraphData> {
    const res = await fetch(`${API_URL}/api/graph`);
    return res.json();
  }

  async getStories(): Promise<Story[]> {
    const res = await fetch(`${API_URL}/api/stories`);
    const data = await res.json();
    return data.stories;
  }

  getScreenshotUrl(filename: string): string {
    return `${API_URL}/api/screenshots/${filename}`;
  }

  // WebSocket for real-time updates
  connectWebSocket(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    // Connect directly to agent server (not through Next.js)
    const wsUrl = 'ws://127.0.0.1:5100/ws';
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('[WS] Connected to agent');
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this.messageHandlers.forEach(h => h(msg.event, msg.data));
      } catch (e) {
        console.error('[WS] Parse error:', e);
      }
    };

    this.ws.onclose = () => {
      console.log('[WS] Disconnected, reconnecting...');
      this.reconnectTimer = setTimeout(() => this.connectWebSocket(), 3000);
    };

    this.ws.onerror = (err) => {
      console.error('[WS] Error:', err);
    };
  }

  disconnectWebSocket(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  onMessage(handler: (event: string, data: any) => void): void {
    this.messageHandlers.push(handler);
  }

  sendCommand(action: string, data?: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action, data }));
    }
  }
}

export const api = new ApiClient();

// Types for import
import type { Screen, Element, Transition, GraphNode, GraphEdge, GraphData, ExplorationStatus, Story, StoryStep } from '@/types';
