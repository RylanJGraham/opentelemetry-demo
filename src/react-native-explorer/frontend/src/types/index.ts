export interface Screen {
  id: string;
  name: string;
  screen_type: string;
  description: string;
  screenshot_path: string;
  element_count: number;
  first_seen: number;
  last_seen: number;
  visit_count: number;
  fully_explored: boolean;
}

export interface Element {
  id: string;
  screen_id: string;
  element_type: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  interacted: boolean;
  confidence: number;
}

export interface Transition {
  id: number;
  from_screen_id: string;
  to_screen_id?: string;
  element_id?: string;
  action_type: string;
  timestamp: number;
}

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  screenshot?: string;
  visit_count: number;
  fully_explored: boolean;
}

export interface GraphEdge {
  id: number;
  source: string;
  target?: string;
  action: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ExplorationStatus {
  state: 'idle' | 'connecting' | 'exploring' | 'paused' | 'error' | 'complete';
  current_screen?: string;
  screens_found: number;
  actions_taken: number;
  duration_seconds: number;
}

export interface Story {
  id: string;
  name: string;
  description: string;
  created_at: number;
  updated_at: number;
  steps: StoryStep[];
}

export interface StoryStep {
  screen_id: string;
  action: string;
  annotation?: string;
}

export type ViewType = 'graph' | 'gallery' | 'stories';
