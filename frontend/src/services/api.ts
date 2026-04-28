import axios from 'axios';
import {
  ApiResponse,
  Person,
  Event,
  Relationship,
  FamilyGraph,
  ConflictResult,
  AIParseResult,
} from '../types';

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,  // 2分钟，AI解析可能较慢
});

// 家族管理
export const familyApi = {
  // 创建家族
  create: async (name: string): Promise<ApiResponse<{ family_id: string; name: string }>> => {
    const response = await api.post(`/families?name=${encodeURIComponent(name)}`);
    return response.data;
  },

  // 获取家族列表
  list: async (): Promise<ApiResponse<Array<{ family_id: string; file_path: string; last_modified: string }>>> => {
    const response = await api.get('/families');
    return response.data;
  },

  // 导出数据
  export: async (familyId: string): Promise<ApiResponse<FamilyGraph>> => {
    const response = await api.get(`/families/${familyId}/export`);
    return response.data;
  },

  // 导入数据
  import: async (familyId: string, data: FamilyGraph): Promise<ApiResponse<any>> => {
    const response = await api.post(`/families/${familyId}/import`, data);
    return response.data;
  },
};

// 人物管理
export const personApi = {
  // 创建人物
  create: async (familyId: string, person: Partial<Person>): Promise<ApiResponse<{ person_id: string; person: Person }>> => {
    const response = await api.post(`/families/${familyId}/people`, person);
    return response.data;
  },

  // 获取人物列表
  list: async (familyId: string, filters?: { name?: string; tag?: string; show_placeholders?: boolean }): Promise<ApiResponse<Person[]>> => {
    const params = new URLSearchParams();
    if (filters?.name) params.append('name', filters.name);
    if (filters?.tag) params.append('tag', filters.tag);
    if (filters?.show_placeholders) params.append('show_placeholders', 'true');
    const response = await api.get(`/families/${familyId}/people?${params.toString()}`);
    return response.data;
  },

  // 获取人物详情
  get: async (familyId: string, personId: string): Promise<ApiResponse<{
    person: Person;
    relationships: Relationship[];
    events: Event[];
  }>> => {
    const response = await api.get(`/families/${familyId}/people/${personId}`);
    return response.data;
  },

  // 更新人物
  update: async (familyId: string, personId: string, data: Partial<Person>): Promise<ApiResponse<{ person: Person }>> => {
    const response = await api.put(`/families/${familyId}/people/${personId}`, data);
    return response.data;
  },

  // 删除人物
  delete: async (familyId: string, personId: string): Promise<ApiResponse<any>> => {
    const response = await api.delete(`/families/${familyId}/people/${personId}`);
    return response.data;
  },
};

// 事件管理
export const eventApi = {
  // 创建事件
  create: async (familyId: string, event: Partial<Event>): Promise<ApiResponse<{ event_id: string; event: Event }>> => {
    const response = await api.post(`/families/${familyId}/events`, event);
    return response.data;
  },

  // 获取事件列表
  list: async (familyId: string, filters?: { type?: string; year?: number }): Promise<ApiResponse<Event[]>> => {
    const params = new URLSearchParams();
    if (filters?.type) params.append('type', filters.type);
    if (filters?.year) params.append('year', filters.year.toString());
    const response = await api.get(`/families/${familyId}/events?${params.toString()}`);
    return response.data;
  },
};

// 关系管理
export const relationshipApi = {
  // 创建关系
  create: async (familyId: string, relationship: Partial<Relationship>): Promise<ApiResponse<{ relationship_id: string; relationship: Relationship }>> => {
    const response = await api.post(`/families/${familyId}/relationships`, relationship);
    return response.data;
  },

  // 获取关系列表
  list: async (familyId: string, filters?: { person_id?: string; type?: string }): Promise<ApiResponse<Relationship[]>> => {
    const params = new URLSearchParams();
    if (filters?.person_id) params.append('person_id', filters.person_id);
    if (filters?.type) params.append('type', filters.type);
    const response = await api.get(`/families/${familyId}/relationships?${params.toString()}`);
    return response.data;
  },

  // 删除关系
  delete: async (familyId: string, relId: string): Promise<ApiResponse<any>> => {
    const response = await api.delete(`/families/${familyId}/relationships/${relId}`);
    return response.data;
  },
};

// AI解析
export const aiApi = {
  // 解析文本
  parse: async (text: string, familyId?: string): Promise<ApiResponse<{
    parsed_data: AIParseResult;
    prompt_used: { system: string; user: string };
  }>> => {
    const response = await api.post('/ai/parse', { text, family_id: familyId });
    return response.data;
  },

  // 获取提示词（调试用）
  getPrompt: async (text: string): Promise<ApiResponse<{ system_prompt: string; user_prompt: string }>> => {
    const response = await api.get(`/ai/prompt?text=${encodeURIComponent(text)}`);
    return response.data;
  },

  // --- 交互式提取 (Phase 3) ---
  extract: async (text: string, familyId: string): Promise<ApiResponse<any>> => {
    const response = await api.post('/chat/extract', { text, family_id: familyId });
    return response.data;
  },

  commit: async (familyId: string, commitData: any): Promise<ApiResponse<{ actions: string[] }>> => {
    const response = await api.post('/chat/commit', { family_id: familyId, ...commitData });
    return response.data;
  },
};

// 冲突检测
export const conflictApi = {
  // 检查冲突
  check: async (familyId: string, newData: any): Promise<ApiResponse<ConflictResult>> => {
    const response = await api.post('/conflict/check', { family_id: familyId, new_data: newData });
    return response.data;
  },

  // 批量检查冲突
  checkBatch: async (familyId: string, dataList: any[]): Promise<ApiResponse<{
    results: Array<ConflictResult & { index: number }>;
    summary: { total: number; clean: number; ambiguous: number; blocking: number };
  }>> => {
    const response = await api.post(`/conflict/check-batch?family_id=${familyId}`, dataList);
    return response.data;
  },

  // 获取冲突类型
  getTypes: async (): Promise<ApiResponse<{
    levels: Array<{ value: string; label: string; description: string }>;
    types: Array<{ value: string; name: string }>;
  }>> => {
    const response = await api.get('/conflict/types');
    return response.data;
  },
};

// 健康检查
export const healthApi = {
  check: async (): Promise<{ status: string; timestamp: string }> => {
    const response = await api.get('/health');
    return response.data;
  },
};

// 自动导入（核心：一件半事）
export const autoImportApi = {
  // 自动导入 AI 解析结果
  run: async (familyId: string, parsedData: any, answers?: Record<string, string>): Promise<ApiResponse<{
    auto_saved: boolean;
    actions: string[];
    questions: Array<{
      id: string;
      type: string;
      message: string;
      entity?: any;
      candidates?: Array<{ id: string; name: string; score: number }>;
    }>;
    pending_data?: any;
    id_mapping?: Record<string, string>;
  }>> => {
    const response = await api.post(`/families/${familyId}/auto-import`, {
      parsed_data: parsedData,
      answers: answers || {},
    });
    return response.data;
  },
};

// 关系推导（全量补全）
export const deriveApi = {
  run: async (familyId: string): Promise<ApiResponse<{
    derived_relationships: string[];
    total_relationships: number;
  }>> => {
    const response = await api.post(`/families/${familyId}/derive`);
    return response.data;
  },
};

// 传记生成
export const biographyApi = {
  // 为单个人物生成传记
  generate: async (familyId: string, personId: string): Promise<ApiResponse<{ person_id: string; story: string }>> => {
    const response = await api.post(`/families/${familyId}/people/${personId}/biography`);
    return response.data;
  },

  // 批量生成所有人物传记
  generateAll: async (familyId: string): Promise<ApiResponse<{ updated: string[] }>> => {
    const response = await api.post(`/families/${familyId}/biography/batch`);
    return response.data;
  },
};

// 意图检测（判断是否为合并指令）
export const intentApi = {
  detect: async (text: string, familyId?: string): Promise<ApiResponse<{
    is_merge: boolean;
    name_a?: string;
    name_b?: string;
  }>> => {
    const response = await api.post('/ai/detect-intent', { text, family_id: familyId });
    return response.data;
  },
};

// 编辑历史
export const historyApi = {
  get: async (familyId: string, personId?: string, limit: number = 50): Promise<ApiResponse<Array<{
    id: string;
    timestamp: string;
    action: string;
    actor: string;
    target_type: string;
    target_id: string;
    target_name: string;
    before: any;
    after: any;
    summary: string;
  }>>> => {
    const params = new URLSearchParams();
    if (personId) params.append('person_id', personId);
    params.append('limit', limit.toString());
    const response = await api.get(`/families/${familyId}/history?${params.toString()}`);
    return response.data;
  },
};

// 人物合并预览
export const mergePreviewApi = {
  run: async (familyId: string, primaryId: string, secondaryId: string): Promise<ApiResponse<{
    primary: { person: Person; relationship_count: number; event_count: number; relationships: Array<{ id: string; type: string; other_person_id: string; other_person_name: string }> };
    secondary: { person: Person; relationship_count: number; event_count: number; relationships: Array<{ id: string; type: string; other_person_id: string; other_person_name: string }> };
    overlap_relationships: string[];
    will_delete_secondary: boolean;
  }>> => {
    const response = await api.post(`/families/${familyId}/merge-preview`, {
      primary_id: primaryId,
      secondary_id: secondaryId,
    });
    return response.data;
  },
};

// 人物合并
export const mergeApi = {
  run: async (familyId: string, primaryId: string, secondaryId: string): Promise<ApiResponse<{
    actions: string[];
    primary: Person;
  }>> => {
    const response = await api.post(`/families/${familyId}/merge`, {
      primary_id: primaryId,
      secondary_id: secondaryId,
    });
    return response.data;
  },
};

// 称谓查询
export const kinshipApi = {
  resolve: async (familyId: string, personAId: string, personBId: string): Promise<ApiResponse<{
    label: string;
    source: string;
    path: Array<{ op: string; gender: string; label: string }>;
    compressed: string[];
    analysis: Record<string, any>;
  }>> => {
    const response = await api.get(`/families/${familyId}/resolve/${personAId}/${personBId}`);
    return response.data;
  },
};
