// 人物类型
export interface Person {
  id: string;
  name: string;
  gender: 'male' | 'female' | 'unknown';
  birth_date?: string;
  death_date?: string;
  birth_place?: string;
  current_residence?: string;
  tags: string[];
  notes?: string;
  story?: string;
  created_at: string;
  updated_at: string;
}

// 事件类型
export interface Event {
  id: string;
  type: string;
  description: string;
  date?: string;
  date_accuracy: 'exact' | 'year' | 'approximate' | 'unknown';
  location?: string;
  participants: Array<{
    person_id: string;
    role: string;
  }>;
  source?: string;
  confidence: 'high' | 'medium' | 'low' | 'uncertain';
  created_at: string;
}

// 关系类型
export interface Relationship {
  id: string;
  person1_id: string;
  person2_id: string;
  type: string;
  subtype?: string;
  start_date?: string;
  end_date?: string;
  attributes: Record<string, any>;
  event_id?: string;
  notes?: string;
  created_at: string;
}

// 家族图谱
export interface FamilyGraph {
  people: Person[];
  events: Event[];
  relationships: Relationship[];
}

// 冲突检测结果
export interface ConflictItem {
  level: 'none' | 'ambiguous' | 'blocking';
  type: string;
  message: string;
  affected_entities: string[];
  suggestions: string[];
  can_override: boolean;
}

export interface ConflictResult {
  has_conflicts: boolean;
  has_blocking: boolean;
  has_ambiguous: boolean;
  can_proceed: boolean;
  requires_clarification: boolean;
  conflicts: ConflictItem[];
  warnings: ConflictItem[];
  summary: string;
}

// API响应类型
export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  timestamp: string;
}

// AI解析结果
export interface AIParseResult {
  entities: Array<{
    type: 'person';
    name: string;
    temp_id: string;
    gender: 'male' | 'female' | 'unknown';
    birth_year?: string;
    death_year?: string;
    tags: string[];
    confidence: 'high' | 'medium' | 'low';
    source_text?: string;
  }>;
  events: Array<{
    type: string;
    description: string;
    date?: string;
    date_accuracy: string;
    participants: Array<{
      temp_id: string;
      role: string;
    }>;
    confidence: string;
  }>;
  relationships: Array<{
    person1_temp_id: string;
    person2_temp_id: string;
    type: string;
    subtype?: string;
    confidence: string;
  }>;
  metadata: {
    parsing_confidence: number;
    ambiguous_references: string[];
    suggested_questions: string[];
  };
}
