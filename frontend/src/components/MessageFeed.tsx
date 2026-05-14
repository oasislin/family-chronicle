import React, { useState, useEffect } from 'react';
import { Person, AIExtractionResult, ExtractionCommitRequest, InteractionTask } from '../types';
import ExtractionConfirmCard from './ExtractionConfirmCard';

export interface FeedMessage {
  id: string;
  type: 'parsing' | 'success' | 'question' | 'error' | 'suggestion' | 'extraction' | 'task';
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
    // ambiguities
    isAmbiguity?: boolean;
    ambiguitySuggestion?: {
      person_a: string;
      person_b: string;
      type: string;
      attributes: Record<string, any>;
    };
    // debug info for extraction
    debugInfo?: {
      prompt_used: { system: string; user: string };
      raw_response: string;
    };
    // task
    task?: InteractionTask;
  };
  onAnswer?: (questionId: string, answer: string) => void;
  onTaskAction?: (taskId: string, action: string, payload: any) => void;
  onConfirmExtraction?: (commitData: ExtractionCommitRequest) => void;
  onCancelExtraction?: () => void;
  onRetry?: () => void;
  allPeople?: Person[];
}

interface MessageFeedProps {
  messages: FeedMessage[];
  familyId?: string;
}

const MessageFeed: React.FC<MessageFeedProps> = ({ messages, familyId }) => {
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
          <MessageCard key={msg.id} message={msg} familyId={familyId} />
        ))}
      </div>
    </div>
  );
};

const MessageCard: React.FC<{ message: FeedMessage; familyId?: string }> = ({ message, familyId }) => {
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
      return <ExtractionWrapper message={message} familyId={familyId} />;
    case 'task':
      return <InteractionTaskCard message={message} />;
    default:
      return null;
  }
};

/**
 * 任务式交互组件：依据 InteractionTask 协议动态渲染 UI
 */
const InteractionTaskCard: React.FC<{ message: FeedMessage }> = ({ message }) => {
  const [answered, setAnswered] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const { task } = message.content;
  const onTaskAction = message.onTaskAction;

  if (!task) return null;

  if (answered) {
    return (
      <div className="bg-gray-100 border border-gray-200 rounded-lg px-3 py-2">
        <span className="text-xs text-gray-500">✅ 已处理</span>
      </div>
    );
  }

  const handleAction = (action: string, payload: any) => {
    if (onTaskAction) {
      onTaskAction(task.id, action, payload);
      setAnswered(true);
    }
  };

  // 根据分类选择基础色调
  const getCategoryStyles = () => {
    switch (task.category) {
      case 'ambiguity': return 'bg-indigo-50 border-indigo-200 text-indigo-800';
      case 'conflict': return 'bg-orange-50 border-orange-200 text-orange-800';
      case 'clarification': return 'bg-teal-50 border-teal-200 text-teal-800';
      case 'suggestion': return 'bg-blue-50 border-blue-200 text-blue-800';
      default: return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  const getButtonStyles = () => {
    switch (task.category) {
      case 'ambiguity': return 'bg-indigo-600 hover:bg-indigo-700 text-white';
      case 'conflict': return 'bg-orange-600 hover:bg-orange-700 text-white';
      case 'clarification': return 'bg-teal-600 hover:bg-teal-700 text-white';
      case 'suggestion': return 'bg-blue-600 hover:bg-blue-700 text-white';
      default: return 'bg-gray-600 hover:bg-gray-700 text-white';
    }
  };

  const styles = getCategoryStyles();
  const btnStyles = getButtonStyles();

  return (
    <div className={`${styles.split(' ')[0]} ${styles.split(' ')[1]} border rounded-lg p-3 shadow-sm`}>
      <p className={`text-sm font-medium mb-2 flex items-center gap-1.5`}>
        {task.category === 'ambiguity' && '🤔'}
        {task.category === 'conflict' && '⚠️'}
        {task.category === 'clarification' && '❓'}
        {task.category === 'suggestion' && '💡'}
        {task.message}
      </p>

      {/* 单选 / 二元确认 */}
      {(task.type === 'single_choice' || task.type === 'yes_no') && (
        <div className="space-y-1.5">
          {task.options.map((opt, idx) => (
            <button
              key={idx}
              onClick={() => handleAction(opt.action, opt.payload)}
              className={`w-full flex justify-between items-center px-3 py-2 bg-white border border-opacity-50 rounded-lg 
                         hover:bg-opacity-80 transition text-sm text-left group
                         ${task.category === 'ambiguity' ? 'border-indigo-300 hover:bg-indigo-50' : 'border-gray-300'}`}
            >
              <span className="font-medium">{opt.label}</span>
              <span className="text-[10px] opacity-0 group-hover:opacity-60 transition-opacity">
                点击执行
              </span>
            </button>
          ))}
        </div>
      )}

      {/* 文本输入 */}
      {task.type === 'input_text' && (
        <div className="space-y-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && inputValue.trim()) {
                handleAction(task.options[0]?.action || 'SUBMIT_TEXT', { text: inputValue.trim() });
              }
            }}
            placeholder="请输入..."
            className="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm
                       focus:ring-2 focus:ring-opacity-50 focus:border-transparent outline-none"
            autoFocus
          />
          <div className="flex gap-2">
            {task.options.map((opt, idx) => (
              <button
                key={idx}
                onClick={() => handleAction(opt.action, idx === 0 ? { text: inputValue.trim() } : opt.payload)}
                disabled={idx === 0 && !inputValue.trim()}
                className={`flex-1 px-3 py-1.5 rounded-lg text-sm transition-colors shadow-sm
                           ${idx === 0 ? btnStyles : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'}
                           disabled:bg-gray-300 disabled:text-gray-500 disabled:cursor-not-allowed`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 多选 (暂时简单实现为按钮列表) */}
      {task.type === 'multi_choice' && (
        <div className="flex flex-wrap gap-2">
          {task.options.map((opt, idx) => (
            <button
              key={idx}
              onClick={() => handleAction(opt.action, opt.payload)}
              className="px-3 py-1.5 bg-white border border-gray-300 rounded-full text-xs
                         hover:bg-gray-50 transition-colors shadow-sm"
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// 交互式提取确认包装组件
const ExtractionWrapper: React.FC<{ message: FeedMessage; familyId?: string }> = ({ message, familyId }) => {
  const [confirmed, setConfirmed] = useState(false);
  const { extractionData } = message.content;
  const allPeople = message.allPeople || [];

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
      familyId={familyId || ''}
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
  const { questionId, message: questionText, isAmbiguity, ambiguitySuggestion: _unused_ambiguitySuggestion } = message.content;
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

  // 场景X: 语义确认 / 歧义推导 (已废弃，迁往 InteractionTaskCard)
  if (isAmbiguity) {
    return (
      <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3 shadow-sm">
        <p className="text-sm text-indigo-800 font-medium mb-2">🤔 发现潜在关联 (Legacy)</p>
        <p className="text-xs text-gray-700 mb-3 leading-relaxed">{questionText}</p>
        <div className="flex gap-2">
          <button onClick={() => handleAnswer('yes')} className="flex-1 px-3 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium">✅ 是的</button>
          <button onClick={() => handleAnswer('no')} className="flex-1 px-3 py-2 bg-white border border-indigo-300 rounded-lg text-sm text-indigo-700">❌ 不是</button>
        </div>
      </div>
    );
  }

  // 场景 1-5 已统一由 InteractionTask 处理。此处保留极简逻辑作为过渡或通用提问。

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
