import React, { useState, useEffect } from 'react';
import { Person, AIExtractionResult, ExtractionCommitRequest } from '../types';
import ExtractionConfirmCard from './ExtractionConfirmCard';

export interface FeedMessage {
  id: string;
  type: 'parsing' | 'success' | 'question' | 'error' | 'suggestion' | 'extraction';
  timestamp: number;
  content: {
    // success
    actions?: string[];
    // question — common
    questionId?: string;
    message?: string;
    questionType?: string;  // person_match | person_name | logic_conflict | ai_low_confidence | relationship_direction
    // question — person_match
    candidates?: Array<{ id: string; name: string; score: number; reason?: string }>;
    allowNew?: boolean;
    // question — logic_conflict
    conflictInfo?: { field: string; old_value: string; new_value: string };
    // question — relationship_direction
    directionOptions?: Array<{ id: string; label: string; desc: string }>;
    // question — entity_confirm
    entity?: any;
    // success — action delete callback
    onActionDelete?: (action: string, actionType: string) => void;
    // error
    error?: string;
    // suggestion
    suggestion?: string;
    // parsing
    text?: string;
    // extraction
    extractionData?: AIExtractionResult;
    // common natural language result
    replyMessage?: string;
    // debug info for extraction
    debugInfo?: {
      prompt_used: { system: string; user: string };
      raw_response: string;
    };
  };
  onAnswer?: (questionId: string, answer: string) => void;
  onConfirmExtraction?: (commitData: ExtractionCommitRequest) => void;
  onCancelExtraction?: () => void;
  onRetry?: () => void;
  allPeople?: Person[];
}

interface MessageFeedProps {
  messages: FeedMessage[];
}

const MessageFeed: React.FC<MessageFeedProps> = ({ messages }) => {
  if (messages.length === 0) {
    return (
      <div className="flex flex-col h-full bg-gray-50 border-l border-gray-200">
        <div className="px-4 py-3 border-b border-gray-200 bg-white">
          <h3 className="font-medium text-gray-700 text-sm">💬 消息</h3>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-400 px-6">
            <div className="text-3xl mb-2">👂</div>
            <p className="text-sm">我在听...</p>
            <p className="text-xs mt-1">输入家族叙事，我来帮你整理</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-50 border-l border-gray-200">
      <div className="px-4 py-3 border-b border-gray-200 bg-white flex-shrink-0">
        <h3 className="font-medium text-gray-700 text-sm">💬 消息</h3>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.map((msg) => (
          <MessageCard key={msg.id} message={msg} />
        ))}
      </div>
    </div>
  );
};

const MessageCard: React.FC<{ message: FeedMessage }> = ({ message }) => {
  switch (message.type) {
    case 'parsing':
      return <ParsingCard message={message} />;
    case 'success':
      return <SuccessCard message={message} />;
    case 'question':
      return <QuestionCard message={message} />;
    case 'error':
      return <ErrorCard message={message} />;
    case 'suggestion':
      return <SuggestionCard message={message} />;
    case 'extraction':
      return <ExtractionWrapper message={message} />;
    default:
      return null;
  }
};

// 交互式提取确认包装组件
const ExtractionWrapper: React.FC<{ message: FeedMessage }> = ({ message }) => {
  const [confirmed, setConfirmed] = useState(false);
  const { extractionData, allPeople = [] } = message.content;

  if (confirmed) {
    return (
      <div className="bg-white border border-green-200 rounded-lg p-3 shadow-sm">
        <div className="text-xs text-green-600 font-medium mb-2 flex items-center gap-1">
          <span>✅ 提取结果已确认</span>
        </div>
        {extractionData?.reply_message && (
          <p className="text-sm text-gray-700 leading-relaxed italic border-l-2 border-blue-200 pl-2">
            "{extractionData.reply_message}"
          </p>
        )}
      </div>
    );
  }

  if (!extractionData) return null;

  return (
    <ExtractionConfirmCard
      data={extractionData}
      allPeople={allPeople}
      debugInfo={message.content.debugInfo}
      onConfirm={(commitData) => {
        setConfirmed(true);
        if (message.onConfirmExtraction) {
          message.onConfirmExtraction(commitData);
        }
      }}
      onCancel={() => {
        setConfirmed(true);
        if (message.onCancelExtraction) {
          message.onCancelExtraction();
        }
      }}
    />
  );
};

// 解析中
const ParsingCard: React.FC<{ message: FeedMessage }> = ({ message }) => (
  <div className="bg-white rounded-lg border border-gray-200 p-3 shadow-sm">
    <div className="flex items-center gap-2">
      <svg className="animate-spin h-4 w-4 text-primary-500" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
      <span className="text-sm text-gray-600">🤖 正在解析并整理...</span>
    </div>
    {message.content.text && (
      <p className="text-xs text-gray-400 mt-1 truncate">{message.content.text}</p>
    )}
  </div>
);

// 成功入库 — 支持逐条审查/删除
const SuccessCard: React.FC<{ message: FeedMessage }> = ({ message }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [deletedIdx, setDeletedIdx] = useState<Set<number>>(new Set());

  // 5秒后自动收起
  useEffect(() => {
    const timer = setTimeout(() => setCollapsed(true), 5000);
    return () => clearTimeout(timer);
  }, []);

  const actions = message.content.actions || [];
  const onActionDelete = message.content.onActionDelete;

  // 解析操作类型
  const parseAction = (action: string) => {
    if (action.startsWith('新增人物')) return { type: 'create_person', color: 'blue' };
    if (action.startsWith('关联人物')) return { type: 'match_person', color: 'gray' };
    if (action.startsWith('更新')) return { type: 'update', color: 'amber' };
    if (action.startsWith('新增关系') || action.startsWith('推导关系')) return { type: 'relationship', color: 'purple' };
    if (action.startsWith('新增事件')) return { type: 'event', color: 'green' };
    if (action.startsWith('校验修复')) return { type: 'validator', color: 'orange' };
    if (action.startsWith('跳过')) return { type: 'skip', color: 'gray' };
    if (action.startsWith('合并')) return { type: 'merge', color: 'pink' };
    return { type: 'other', color: 'gray' };
  };

  const activeActions = actions.filter((_: any, i: number) => !deletedIdx.has(i));

  if (collapsed) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="w-full bg-green-50 border border-green-200 rounded-lg px-3 py-2 text-left
                   hover:bg-green-100 transition-colors"
      >
        <span className="text-xs text-green-700">
          ✅ 已更新 · {activeActions.length} 项变更
          {deletedIdx.size > 0 && <span className="text-red-500 ml-1">（已撤销 {deletedIdx.size} 项）</span>}
        </span>
      </button>
    );
  }

  return (
    <div className="bg-green-50 border border-green-200 rounded-lg p-3 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="text-green-600 font-medium text-sm">✅ 已更新族谱</span>
        {!reviewing && actions.length > 0 && (
          <button
            onClick={() => setReviewing(true)}
            className="text-xs text-green-600 hover:text-green-800 underline"
          >
            查看详情
          </button>
        )}
        {reviewing && (
          <button
            onClick={() => setReviewing(false)}
            className="text-xs text-gray-400 hover:text-gray-600 underline"
          >
            收起
          </button>
        )}
      </div>

      {message.content.replyMessage && (
        <div className="mb-3 bg-white/50 p-2.5 rounded-md border-l-4 border-green-400">
          <p className="text-sm text-gray-800 leading-relaxed">
            {message.content.replyMessage}
          </p>
        </div>
      )}

      {reviewing && (
        <div className="space-y-1 mt-2 pt-2 border-t border-green-100">
        {actions.map((action: string, i: number) => {
          if (deletedIdx.has(i)) return null;
          const info = parseAction(action);
          return (
            <div key={i} className="text-xs text-green-700 flex items-start gap-1 group">
              <span className="text-green-400 mt-0.5 flex-shrink-0">·</span>
              <span className="flex-1">{action}</span>
              {reviewing && (info.type === 'relationship' || info.type === 'create_person' || info.type === 'event') && onActionDelete && (
                <button
                  onClick={() => {
                    setDeletedIdx(prev => new Set([...prev, i]));
                    onActionDelete(action, info.type);
                  }}
                  className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600
                             flex-shrink-0 transition-opacity px-1"
                  title="撤销此操作"
                >
                  ✕
                </button>
              )}
            </div>
          );
        })}
        {activeActions.length === 0 && (
          <p className="text-xs text-green-600">所有信息已处理完毕</p>
        )}
      </div>
    )}
    </div>
  );
};

// 需要确认 — 支持 5 种歧义场景，每种都有 [取消] 和 [手动输入]
const QuestionCard: React.FC<{ message: FeedMessage }> = ({ message }) => {
  const [answered, setAnswered] = useState(false);
  const [nameInput, setNameInput] = useState('');
  // entity_confirm 的编辑状态（必须在顶层声明，不能放在 if 分支里）
  const entity = message.content.entity;
  const [editName, setEditName] = useState(entity?.name || '');
  const [editGender, setEditGender] = useState(entity?.gender || 'unknown');
  const [editBirth, setEditBirth] = useState(entity?.birth_year || '');
  const { questionId, message: questionText, questionType, candidates, conflictInfo, directionOptions } = message.content;
  const onAnswer = message.onAnswer;

  // 防御：如果 onAnswer 被 App.tsx 清除（标记为已回答），自动标记本地状态
  useEffect(() => {
    if (!onAnswer && !answered) {
      setAnswered(true);
    }
  }, [onAnswer]);

  if (answered) {
    return (
      <div className="bg-gray-100 border border-gray-200 rounded-lg px-3 py-2">
        <span className="text-xs text-gray-500">✅ 已处理</span>
      </div>
    );
  }

  const handleAnswer = (value: string) => {
    if (onAnswer && questionId) {
      onAnswer(questionId, value);
      setAnswered(true);
    }
  };

  // 场景1: 人物匹配歧义
  if (questionType === 'person_match' || (!questionType && candidates && candidates.length > 0)) {
    const allowNew = message.content.allowNew;
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 shadow-sm">
        <p className="text-sm text-yellow-800 font-medium mb-2">⚠️ {questionText}</p>
        <div className="space-y-1.5">
          {candidates?.map((c) => (
            <div key={c.id} className="flex items-center gap-1.5">
              <button
                onClick={() => handleAnswer(c.id)}
                className="flex-1 text-left px-3 py-2 bg-white border border-yellow-300 rounded-lg
                           hover:bg-yellow-100 transition-colors text-sm flex items-center justify-between"
              >
                <span>👤 {c.name}</span>
                <span className="flex items-center gap-2">
                  {c.reason && <span className="text-xs text-gray-400">{c.reason}</span>}
                  {c.score >= 0.9 && <span className="text-xs text-green-600">精确匹配</span>}
                  {c.score >= 0.8 && c.score < 0.9 && <span className="text-xs text-blue-600">相似</span>}
                </span>
              </button>
              {allowNew && (
                <button
                  onClick={() => handleAnswer(`__merge__:${c.id}`)}
                  className="px-2 py-2 bg-blue-500 text-white rounded-lg text-xs
                             hover:bg-blue-600 transition-colors whitespace-nowrap"
                  title="合并此人（保留已有记录，关联新信息）"
                >
                  合并
                </button>
              )}
            </div>
          ))}
          <button
            onClick={() => handleAnswer('__new__')}
            className="w-full text-left px-3 py-2 bg-white border border-yellow-300 rounded-lg
                       hover:bg-yellow-100 transition-colors text-sm text-yellow-700"
          >
            ➕ {allowNew ? '确认是不同的人，创建新人物' : '是新人物'}
          </button>
        </div>
        {/* 手动输入 */}
        <div className="mt-2 pt-2 border-t border-yellow-200">
          <div className="flex gap-2">
            <input
              type="text"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && nameInput.trim()) handleAnswer(nameInput.trim()); }}
              placeholder="手动输入姓名..."
              className="flex-1 px-2 py-1 bg-white border border-yellow-300 rounded text-xs
                         focus:ring-1 focus:ring-yellow-400 focus:border-transparent"
            />
            <button
              onClick={() => nameInput.trim() && handleAnswer(nameInput.trim())}
              disabled={!nameInput.trim()}
              className="px-2 py-1 bg-yellow-600 text-white rounded text-xs
                         hover:bg-yellow-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              确定
            </button>
          </div>
          <button
            onClick={() => handleAnswer('__cancel__')}
            className="mt-1.5 text-xs text-gray-400 hover:text-gray-600 underline"
          >
            取消 — 跳过此条输入
          </button>
        </div>
      </div>
    );
  }

  // 场景2: 逻辑矛盾
  if (questionType === 'logic_conflict' && conflictInfo) {
    return (
      <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 shadow-sm">
        <p className="text-sm text-orange-800 font-medium mb-2">⚠️ {questionText}</p>
        <div className="bg-white rounded-lg border border-orange-200 p-2 mb-2 text-xs space-y-1">
          <div className="flex justify-between">
            <span className="text-gray-500">数据库记录</span>
            <span className="text-gray-800 font-medium">{conflictInfo.old_value}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">你刚才提到</span>
            <span className="text-orange-700 font-medium">{conflictInfo.new_value}</span>
          </div>
        </div>
        <div className="space-y-1.5">
          <button
            onClick={() => handleAnswer(conflictInfo.new_value)}
            className="w-full px-3 py-2 bg-orange-600 text-white rounded-lg text-sm
                       hover:bg-orange-700 transition"
          >
            以新信息为准
          </button>
          <button
            onClick={() => handleAnswer(conflictInfo.old_value)}
            className="w-full px-3 py-2 bg-white border border-orange-300 rounded-lg text-sm
                       text-orange-700 hover:bg-orange-100 transition"
          >
            保留原记录
          </button>
        </div>
        {/* 手动输入正确值 */}
        <div className="mt-2 pt-2 border-t border-orange-200">
          <div className="flex gap-2">
            <input
              type="text"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && nameInput.trim()) handleAnswer(nameInput.trim()); }}
              placeholder="手动输入正确值..."
              className="flex-1 px-2 py-1 bg-white border border-orange-300 rounded text-xs
                         focus:ring-1 focus:ring-orange-400 focus:border-transparent"
            />
            <button
              onClick={() => nameInput.trim() && handleAnswer(nameInput.trim())}
              disabled={!nameInput.trim()}
              className="px-2 py-1 bg-orange-600 text-white rounded text-xs
                         hover:bg-orange-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              确定
            </button>
          </div>
          <button
            onClick={() => handleAnswer('__cancel__')}
            className="mt-1.5 text-xs text-gray-400 hover:text-gray-600 underline"
          >
            取消 — 不处理此条信息
          </button>
        </div>
      </div>
    );
  }

  // 场景3: AI 置信度低
  if (questionType === 'ai_low_confidence') {
    return (
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 shadow-sm">
        <p className="text-sm text-purple-800 font-medium mb-2">⚠️ {questionText}</p>
        <div className="space-y-1.5">
          <button
            onClick={() => handleAnswer('__confirm__')}
            className="w-full px-3 py-2 bg-purple-600 text-white rounded-lg text-sm
                       hover:bg-purple-700 transition"
          >
            确认
          </button>
          <button
            onClick={() => handleAnswer('__skip__')}
            className="w-full px-3 py-2 bg-white border border-purple-300 rounded-lg text-sm
                       text-purple-700 hover:bg-purple-100 transition"
          >
            跳过
          </button>
        </div>
        {/* 手动编辑 */}
        <div className="mt-2 pt-2 border-t border-purple-200">
          <div className="flex gap-2">
            <input
              type="text"
              value={nameInput}
              onChange={(e) => setNameInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && nameInput.trim()) handleAnswer(nameInput.trim()); }}
              placeholder="手动编辑此信息..."
              className="flex-1 px-2 py-1 bg-white border border-purple-300 rounded text-xs
                         focus:ring-1 focus:ring-purple-400 focus:border-transparent"
            />
            <button
              onClick={() => nameInput.trim() && handleAnswer(nameInput.trim())}
              disabled={!nameInput.trim()}
              className="px-2 py-1 bg-purple-600 text-white rounded text-xs
                         hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              确定
            </button>
          </div>
          <button
            onClick={() => handleAnswer('__cancel__')}
            className="mt-1.5 text-xs text-gray-400 hover:text-gray-600 underline"
          >
            取消 — 不处理此条信息
          </button>
        </div>
      </div>
    );
  }

  // 场景4: 关系方向不明
  if (questionType === 'relationship_direction' && directionOptions) {
    return (
      <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-3 shadow-sm">
        <p className="text-sm text-cyan-800 font-medium mb-2">⚠️ {questionText}</p>
        <div className="space-y-1.5">
          {directionOptions.map((opt) => (
            <button
              key={opt.id}
              onClick={() => handleAnswer(opt.id)}
              className="w-full text-left px-3 py-2 bg-white border border-cyan-300 rounded-lg
                         hover:bg-cyan-100 transition-colors text-sm"
            >
              <div className="font-medium text-cyan-800">{opt.label}</div>
              {opt.desc && <div className="text-xs text-gray-500 mt-0.5">{opt.desc}</div>}
            </button>
          ))}
        </div>
        <div className="mt-2 pt-2 border-t border-cyan-200 flex gap-2">
          <button
            onClick={() => handleAnswer('__cancel_rel__')}
            className="text-xs text-gray-400 hover:text-gray-600 underline"
          >
            取消 — 不添加此关系
          </button>
        </div>
      </div>
    );
  }

  // 场景5: 新实体确认（用户必须确认才创建，防止 AI 误提取）
  if (questionType === 'entity_confirm' && message.content.entity) {
    return (
      <div className="bg-teal-50 border border-teal-200 rounded-lg p-3 shadow-sm">
        <p className="text-sm text-teal-800 font-medium mb-2">🆕 {questionText}</p>
        <div className="bg-white rounded-lg border border-teal-200 p-2.5 space-y-2 mb-2">
          <div>
            <label className="text-xs text-gray-500">姓名</label>
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="w-full px-2 py-1 border border-gray-200 rounded text-sm mt-0.5
                         focus:ring-1 focus:ring-teal-400 focus:border-transparent"
            />
          </div>
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="text-xs text-gray-500">性别</label>
              <select
                value={editGender}
                onChange={(e) => setEditGender(e.target.value)}
                className="w-full px-2 py-1 border border-gray-200 rounded text-sm mt-0.5"
              >
                <option value="male">男 ♂</option>
                <option value="female">女 ♀</option>
                <option value="unknown">未知</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="text-xs text-gray-500">出生年</label>
              <input
                type="text"
                value={editBirth}
                onChange={(e) => setEditBirth(e.target.value)}
                placeholder="如 1985"
                className="w-full px-2 py-1 border border-gray-200 rounded text-sm mt-0.5
                           focus:ring-1 focus:ring-teal-400 focus:border-transparent"
              />
            </div>
          </div>
          {entity.tags && entity.tags.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              {entity.tags.map((t: string, i: number) => (
                <span key={i} className="text-xs bg-teal-100 text-teal-700 px-1.5 py-0.5 rounded">{t}</span>
              ))}
            </div>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {
              setAnswered(true);
              const parts = [editName.trim() || entity.name, editGender, editBirth].join('|');
              handleAnswer(`__create__:${parts}`);
            }}
            disabled={!editName.trim()}
            className="flex-1 px-3 py-1.5 bg-teal-600 text-white rounded-lg text-sm
                       hover:bg-teal-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            ✅ 确认创建
          </button>
          <button
            onClick={() => { setAnswered(true); handleAnswer('__skip__'); }}
            className="px-3 py-1.5 bg-white border border-teal-300 rounded-lg text-sm
                       text-teal-700 hover:bg-teal-100"
          >
            占位
          </button>
          <button
            onClick={() => { setAnswered(true); handleAnswer('__cancel__'); }}
            className="px-3 py-1.5 text-gray-400 hover:text-gray-600 text-sm underline"
          >
            跳过
          </button>
        </div>
      </div>
    );
  }

  // Fallback: 通用文本输入（如「请输入真实姓名」）
  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 shadow-sm">
      <p className="text-sm text-yellow-800 font-medium mb-2">⚠️ {questionText}</p>
      <div className="space-y-2">
        <input
          type="text"
          value={nameInput}
          onChange={(e) => setNameInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && nameInput.trim()) handleAnswer(nameInput.trim());
          }}
          placeholder="输入..."
          className="w-full px-3 py-2 bg-white border border-yellow-300 rounded-lg text-sm
                     focus:ring-2 focus:ring-yellow-400 focus:border-transparent"
          autoFocus
        />
        <div className="flex gap-2">
          <button
            onClick={() => nameInput.trim() && handleAnswer(nameInput.trim())}
            disabled={!nameInput.trim()}
            className="flex-1 px-3 py-1.5 bg-yellow-600 text-white rounded-lg text-sm
                       hover:bg-yellow-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            ✅ 确认
          </button>
          <button
            onClick={() => handleAnswer('__skip__')}
            className="px-3 py-1.5 bg-white border border-yellow-300 rounded-lg text-sm
                       text-yellow-700 hover:bg-yellow-100"
          >
            跳过
          </button>
          <button
            onClick={() => handleAnswer('__cancel__')}
            className="px-3 py-1.5 text-gray-400 hover:text-gray-600 text-sm underline"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
};

// 错误
const ErrorCard: React.FC<{ message: FeedMessage }> = ({ message }) => (
  <div className="bg-red-50 border border-red-200 rounded-lg p-3 shadow-sm">
    <p className="text-sm text-red-700">❌ {message.content.error}</p>
    {message.onRetry && (
      <button
        onClick={message.onRetry}
        className="mt-2 text-xs text-red-600 hover:text-red-800 underline"
      >
        重试
      </button>
    )}
  </div>
);

// 追问建议
const SuggestionCard: React.FC<{ message: FeedMessage }> = ({ message }) => (
  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 shadow-sm">
    <p className="text-sm text-blue-700">💬 {message.content.suggestion}</p>
  </div>
);

export default MessageFeed;
