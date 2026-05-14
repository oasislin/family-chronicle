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
  is_placeholder: boolean;
  placeholder_reason: string;
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
  is_inferred?: boolean;
  created_at: string;
}

export interface FamilyGraph {
  people: Person[];
  events: Event[];
  relationships: Relationship[];
  ambiguities: Ambiguity[]; // 原有的原始歧义（可用于调试或向后兼容）
  tasks?: InteractionTask[]; // 新增：统一的交互任务流
}

// 冲突检测结果
export interface ConflictItem {
  level: 'none' | 'ambiguous' | 'blocking';
  type: string;
  message: string;
  affected_entities: string[];
  suggestions: string[];
  actions?: Action[];
  can_override: boolean;
}

export interface Action {
  label: string;
  action: string;
  target_id?: string;
  payload?: any;
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

// AI解析结果 (旧版本，保留兼容)
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

// --- 新版交互式抽取模型 ---

export interface AIExtractionEntity {
  temp_id: string;
  name: string;
  gender: 'M' | 'F' | 'UNKNOWN';
  matched_db_id: string | null;
  is_new: boolean;
  confidence: number;
  reason?: string;
}

export interface AIExtractionRelationship {
  source_ref: string; // temp_id or person_id
  target_ref: string; // temp_id or person_id
  natural_language_desc: string;
  kinship_type?: string | null;
}

export interface AIExtractionEvent {
  date?: string;
  location?: string;
  description: string;
  involved_refs: string[]; // list of refs
}

// 推导歧义类型
export enum AmbiguityType {
  COUPLED_PARENT_MISSING = "COUPLED_PARENT_MISSING",
  COMPOSITE_PATH_AMBIGUITY = "COMPOSITE_PATH_AMBIGUITY"
}

export type Ambiguity = 
  | {
      type: 'COUPLED_PARENT_MISSING';
      key: string;
      nodes: [string, string];
      message: string;
      suggestion: {
        person_a: string;
        person_b: string;
        type: string;
        attributes: Record<string, any>;
      };
    }
  | {
      type: 'COMPOSITE_PATH_AMBIGUITY';
      key: string;
      nodes: [string, string];
      message: string;
      person_a: string;
      person_b: string;
      rel_type: string;
      step_index: number;
      step_label: string;
      current_node_id: string;
      questionType?: 'CHOICE' | 'YES_NO' | 'INPUT';
      candidates: Array<{ id: string; name: string; is_placeholder: boolean }>;
      actions?: Action[];
    }
  | {
      type: 'LOGIC_CONFLICT';
      key: string;
      message: string;
      conflicts: string[];
      actions?: Action[];
    };

export interface InteractionTask {
  id: string;
  category: 'ambiguity' | 'conflict' | 'clarification' | 'suggestion';
  message: string;
  type: 'single_choice' | 'multi_choice' | 'yes_no' | 'input_text';
  options: Array<{
    label: string;
    action: string;
    payload?: any;
    target_id?: string;
  }>;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface AIExtractionResult {
  entities: AIExtractionEntity[];
  relationships: AIExtractionRelationship[];
  events: AIExtractionEvent[];
  reply_message: string;
  clarification_questions: string[];
  ambiguous_derivations?: Ambiguity[];
  tasks?: InteractionTask[];
}

export interface ExtractionCommitRequest {
  family_id: string;
  confirmed_entities: Array<{
    temp_id: string;
    name: string;
    gender: 'M' | 'F' | 'UNKNOWN';
    action: 'CREATE' | 'LINK_EXISTING';
    matched_db_id?: string;
    tags?: string[];
    attributes?: Record<string, any>;
    notes?: string;
  }>;
  confirmed_relationships: AIExtractionRelationship[];
  confirmed_events: AIExtractionEvent[];
  resolutions?: Record<string, string>; // key -> target_id
  extra_actions?: Array<{
    person_a: string;
    person_b: string;
    type: string;
    action: 'ADD_EDGE' | 'REJECT_EDGE';
    attributes?: Record<string, any>;
  }>;
}

// 统一任务处理请求
export interface TaskResolutionRequest {
  family_id: string;
  task_id: string;
  action: string;
  payload?: any;
  target_id?: string;
}
