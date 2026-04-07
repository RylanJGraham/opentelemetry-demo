const API_URL = process.env.NEXT_PUBLIC_AGENT_URL || 'http://127.0.0.1:5100';

import type { 
  Screen, 
  Element, 
  Transition, 
  GraphData, 
  ExplorationStatus, 
  Story, 
  Execution,
  ExecutionResult 
} from '@/types';

class ApiClient {
  private ws: WebSocket | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private messageHandlers: ((event: string, data: any) => void)[] = [];

  // === Health & Status ===
  
  async getStatus(): Promise<{ exploration: ExplorationStatus; execution: any; vision: any }> {
    const res = await fetch(`${API_URL}/api/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async getHealth(): Promise<{ status: string; exploration_state: string; execution_state: string }> {
    const res = await fetch(`${API_URL}/api/health`);
    return res.json();
  }

  // === Exploration API ===

  async startExploration(maxScreens?: number, useAi: boolean = true): Promise<any> {
    const res = await fetch(`${API_URL}/api/exploration/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ max_screens: maxScreens, use_ai: useAi }),
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

  // === Screens API ===

  async getScreens(screenType?: string, limit: number = 100): Promise<Screen[]> {
    const url = new URL(`${API_URL}/api/screens`);
    if (screenType) url.searchParams.set('screen_type', screenType);
    url.searchParams.set('limit', limit.toString());
    
    const res = await fetch(url.toString());
    const data = await res.json();
    return data.screens;
  }

  async getScreen(id: string): Promise<Screen & { 
    elements: Element[]; 
    outgoing_transitions: Transition[];
    incoming_transitions: Transition[];
  }> {
    const res = await fetch(`${API_URL}/api/screens/${id}`);
    return res.json();
  }

  async getScreenElements(screenId: string, interactiveOnly: boolean = false): Promise<Element[]> {
    const url = new URL(`${API_URL}/api/screens/${screenId}/elements`);
    url.searchParams.set('interactive_only', interactiveOnly.toString());
    const res = await fetch(url.toString());
    const data = await res.json();
    return data.elements;
  }

  // === Graph API ===

  async getGraph(): Promise<GraphData> {
    const res = await fetch(`${API_URL}/api/graph`);
    return res.json();
  }

  async getGraphStats(): Promise<any> {
    const res = await fetch(`${API_URL}/api/graph/stats`);
    return res.json();
  }

  async findPath(fromScreen: string, toScreen: string): Promise<any> {
    const url = new URL(`${API_URL}/api/graph/path`);
    url.searchParams.set('from_screen', fromScreen);
    url.searchParams.set('to_screen', toScreen);
    const res = await fetch(url.toString());
    return res.json();
  }

  // === Gallery API ===

  async getGallery(screenType?: string, clusterBy: string = 'type'): Promise<any> {
    const url = new URL(`${API_URL}/api/gallery`);
    if (screenType) url.searchParams.set('screen_type', screenType);
    url.searchParams.set('cluster_by', clusterBy);
    const res = await fetch(url.toString());
    return res.json();
  }

  async getClusters(): Promise<any> {
    const res = await fetch(`${API_URL}/api/gallery/clusters`);
    return res.json();
  }

  // === Stories API ===

  async getStories(): Promise<Story[]> {
    const res = await fetch(`${API_URL}/api/stories`);
    const data = await res.json();
    return data.stories;
  }

  async getStory(id: string): Promise<Story & { executions: any[] }> {
    const res = await fetch(`${API_URL}/api/stories/${id}`);
    return res.json();
  }

  async createStory(story: { 
    name: string; 
    description?: string; 
    steps?: any[];
    tags?: string[];
    priority?: string;
  }): Promise<{ id: string; status: string }> {
    const res = await fetch(`${API_URL}/api/stories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(story),
    });
    return res.json();
  }

  async updateStory(id: string, updates: Partial<Story>): Promise<any> {
    const res = await fetch(`${API_URL}/api/stories/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    return res.json();
  }

  async deleteStory(id: string): Promise<any> {
    const res = await fetch(`${API_URL}/api/stories/${id}`, { method: 'DELETE' });
    return res.json();
  }

  async addStep(storyId: string, step: {
    action: string;
    screen_id?: string;
    element_id?: string;
    element_query?: any;
    data?: any;
    expected?: string;
    assertion?: string;
  }): Promise<any> {
    const res = await fetch(`${API_URL}/api/stories/${storyId}/steps`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(step),
    });
    return res.json();
  }

  // === Story Execution API ===

  async executeStory(storyId: string, stepByStep: boolean = false): Promise<{
    execution_id: string;
    story_id: string;
    status: string;
  }> {
    const res = await fetch(`${API_URL}/api/stories/${storyId}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step_by_step: stepByStep }),
    });
    return res.json();
  }

  async getExecutions(limit: number = 20): Promise<{ executions: Execution[] }> {
    const url = new URL(`${API_URL}/api/executions`);
    url.searchParams.set('limit', limit.toString());
    const res = await fetch(url.toString());
    return res.json();
  }

  async getExecution(executionId: string): Promise<Execution & { steps: any[]; story_steps: any[] }> {
    const res = await fetch(`${API_URL}/api/executions/${executionId}`);
    return res.json();
  }

  async controlExecution(executionId: string, action: 'pause' | 'resume' | 'stop' | 'step'): Promise<any> {
    const res = await fetch(`${API_URL}/api/executions/${executionId}/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    });
    return res.json();
  }

  // === Screenshots ===

  getScreenshotUrl(filename: string): string {
    return `${API_URL}/api/screenshots/${filename}`;
  }

  getExecutionScreenshotUrl(executionId: string, filename: string): string {
    return `${API_URL}/api/executions/${executionId}/screenshots/${filename}`;
  }

  // === Reset ===

  async resetDatabase(): Promise<any> {
    const res = await fetch(`${API_URL}/api/reset?confirm=true`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  // === WebSocket for real-time updates ===

  connectWebSocket(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

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
