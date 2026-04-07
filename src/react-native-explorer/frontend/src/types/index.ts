export interface Screen {
  id: string;
  name: string;
  screen_type: string;
  description: string;
  screenshot_path: string;
  content_hash?: string;
  perceptual_hash?: string;
  structure_hash?: string;
  element_structure_hash?: string;
  element_count: number;
  first_seen: number;
  last_seen: number;
  visit_count: number;
  fully_explored: boolean;
  ai_confidence: number;
  is_modal: boolean;
  is_error_state: boolean;
  requires_auth: boolean;
  depth_from_home: number;
  parent_screen_id?: string;
}

export interface Element {
  id: string;
  screen_id: string;
  element_type: string;
  normalized_type?: string;
  semantic_type?: string;
  label: string;
  text_content?: string;
  hint?: string;
  accessibility_id?: string;
  resource_id?: string;
  x: number;
  y: number;
  width: number;
  height: number;
  center_x?: number;
  center_y?: number;
  enabled: boolean;
  clickable: boolean;
  focusable: boolean;
  checked?: boolean;
  confidence: number;
  interacted: boolean;
  interaction_count: number;
  interaction_result?: string;
  purpose?: string;
  is_primary_action: boolean;
}

export interface Transition {
  id: number;
  from_screen_id: string;
  to_screen_id?: string;
  from_screen_name?: string;
  to_screen_name?: string;
  element_id?: string;
  action_type: string;
  action_detail?: string;
  timestamp: number;
  success: boolean;
  duration_ms?: number;
  is_back_navigation: boolean;
  is_modal_dismiss: boolean;
}

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  screenshot?: string;
  visit_count: number;
  fully_explored: boolean;
  is_modal: boolean;
  requires_auth: boolean;
  element_count: number;
}

export interface GraphEdge {
  id: number;
  source: string;
  target?: string;
  action: string;
  element_id?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ExplorationStatus {
  state: 'idle' | 'connecting' | 'exploring' | 'paused' | 'error' | 'complete';
  current_screen?: string;
  current_depth?: number;
  screens_found: number;
  screens_from_cache: number;
  transitions_found: number;
  actions_taken: number;
  duration_seconds: number;
  ai_api_calls: number;
  ai_cache_hits: number;
  ai_cache_hit_rate: number;
}

export interface StoryStep {
  action: string;
  screen_id?: string;
  element_id?: string;
  element_query?: {
    type?: string;
    label?: string;
    text?: string;
    semantic_type?: string;
  };
  data?: any;
  expected?: string;
  assertion?: string;
}

export interface Story {
  id: string;
  name: string;
  description: string;
  tags: string[];
  priority: 'high' | 'medium' | 'low';
  created_at: number;
  updated_at: number;
  steps: StoryStep[];
  executions?: Execution[];
}

export interface Execution {
  id: string;
  story_id: string;
  story_name?: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: number;
  completed_at?: number;
  duration_ms?: number;
  success?: boolean;
  passed_steps: number;
  failed_steps: number;
  total_steps: number;
  triggered_by: string;
  environment?: string;
}

export interface ExecutionStep {
  id: number;
  execution_id: string;
  step_number: number;
  action_type: string;
  target_screen_id?: string;
  target_element_id?: string;
  action_data?: string;
  expected_result?: string;
  status: 'pending' | 'running' | 'passed' | 'failed' | 'skipped';
  started_at?: number;
  completed_at?: number;
  duration_ms?: number;
  actual_screen_id?: string;
  screenshot_path?: string;
  error_message?: string;
  assertion_passed?: boolean;
  assertion_details?: string;
}

export interface ExecutionResult {
  execution_id: string;
  story_id: string;
  status: 'completed' | 'failed' | 'cancelled';
  passed_steps: number;
  failed_steps: number;
  total_steps: number;
  duration_ms: number;
  error_summary?: string;
}

export type ViewType = 'graph' | 'gallery' | 'stories' | 'executions';

export interface GalleryCluster {
  type: string;
  screens: Screen[];
}

export interface NavigationPath {
  from: string;
  to: string;
  path: string[];
  actions: any[];
  distance: number;
}
