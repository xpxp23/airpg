export interface User {
  id: string;
  username: string;
  email: string;
  avatar_url?: string;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Game {
  id: string;
  creator_id: string;
  title?: string;
  status: "lobby" | "active" | "paused" | "finished" | "abandoned";
  current_chapter: number;
  max_players: number;
  is_public: boolean;
  invite_code?: string;
  started_at?: string;
  finished_at?: string;
  created_at: string;
  player_count: number;
  uploaded_story?: string;
  ai_summary?: AISummary;
  duration_hint?: string;
  target_duration_minutes?: number;
}

export interface AISummary {
  title: string;
  genre: string;
  tone: string;
  scenes: Scene[];
  preset_characters: PresetCharacter[];
  main_goal: string;
  chapter_plan: ChapterPlan[];
  initial_state: {
    narrative: string;
    starting_location: string;
    available_hooks: string[];
  };
}

export interface Scene {
  id: string;
  name: string;
  description: string;
  connections: string[];
  secrets: string;
}

export interface PresetCharacter {
  id: string;
  name: string;
  description: string;
  background: string;
  skills: string[];
  personality: string;
  starting_location: string;
}

export interface ChapterPlan {
  chapter: number;
  title: string;
  goal: string;
  target_scene: string;
  approximate_duration_ratio: number;
  key_events: string[];
}

export interface Character {
  id: string;
  game_id: string;
  player_id?: string;
  name: string;
  description?: string;
  background?: string;
  status_effects: CharacterStatus;
  location?: string;
  is_alive: boolean;
  created_at: string;
}

export interface CharacterStatus {
  health?: number;
  items?: string[];
  injuries?: Array<{
    type: string;
    severity?: number;
    speed_penalty?: number;
  }>;
  skills?: Record<string, number>;
}

export interface GameAction {
  id: string;
  game_id: string;
  character_id: string;
  player_id: string;
  action_type: "normal" | "cooperation" | "interaction";
  input_text: string;
  public_snippet?: string;
  wait_seconds: number;
  started_at: string;
  finish_at: string;
  completed_at?: string;
  result_narrative?: string;
  result_effects?: Record<string, any>;
  difficulty?: string;
  risk?: string;
  is_cooperation: boolean;
  cooperation_target_id?: string;
  modifiers: Array<Record<string, any>>;
  status: "pending" | "completed" | "interrupted" | "cancelled";
  created_at: string;
  remaining_seconds?: number;
}

export interface GameEvent {
  id: string;
  game_id: string;
  type: string;
  timestamp: string;
  data: Record<string, any>;
  is_visible: boolean;
  created_at: string;
}
