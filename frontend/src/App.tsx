import { useState, useEffect, useCallback, useRef } from 'react';
import FamilyGraphView from './components/FamilyGraph';
import InputBar from './components/InputBar';
import MessageFeed, { FeedMessage } from './components/MessageFeed';
import PersonDetail from './components/PersonDetail';
import MergeConfirmDialog from './components/MergeConfirmDialog';
import FloatingPersonCard from './components/FloatingPersonCard';
import { Person, FamilyGraph, AIParseResult } from './types';
import { familyApi, personApi, healthApi, aiApi, autoImportApi, mergeApi, intentApi, deriveApi, relationshipApi } from './services/api';

function App() {
  const [familyId, setFamilyId] = useState<string>('');
  const [familyData, setFamilyData] = useState<FamilyGraph>({ people: [], events: [], relationships: [] });
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null);
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [highlightedPerson, setHighlightedPerson] = useState<Person | null>(null);
  const [showPlaceholders, setShowPlaceholders] = useState(true);

  // 合并候选（"A是B" 模式检测）
  const [mergeCandidate, setMergeCandidate] = useState<{
    nameA: string;
    nameB: string;
    personA: Person;
    personB: Person;
  } | null>(null);

  // 消息流
  const [messages, setMessages] = useState<FeedMessage[]>([]);
  // 待处理数据（有提问时暂存）
  const [pendingData, setPendingData] = useState<any>(null);
  const pendingDataRef = useRef<any>(null);
  // 累积所有已回答的答案（防止重复生成同一问题）
  const accumulatedAnswersRef = useRef<Record<string, string>>({});

  useEffect(() => { initializeApp(); }, []);

  const initializeApp = async () => {
    try {
      await healthApi.check();
      setIsHealthy(true);

      // 1. 优先从 URL 获取 family_id
      const urlParams = new URLSearchParams(window.location.search);
      let fId = urlParams.get('family_id');

      // 2. 如果 URL 没有，再从列表里取第一个
      if (!fId) {
        const familiesResponse = await familyApi.list();
        if (familiesResponse.success && familiesResponse.data && familiesResponse.data.length > 0) {
          fId = familiesResponse.data[0].family_id;
        }
      }

      // 3. 如果还是没有，创建一个
      if (!fId) {
        const createResponse = await familyApi.create('我的家族');
        if (createResponse.success && createResponse.data) {
          fId = createResponse.data.family_id;
        }
      }

      if (fId) {
        setFamilyId(fId);
        await loadFamilyData(fId);
      }
    } catch (error) {
      console.error('Failed to initialize:', error);
      setIsHealthy(false);
    }
  };

  const loadFamilyData = async (fId: string) => {
    try {
      const exportResponse = await familyApi.export(fId);
      if (exportResponse.success && exportResponse.data) {
        setFamilyData(exportResponse.data);
        
        // --- 核心：自动扫描推导歧义并推送到消息流 ---
        if (exportResponse.data.ambiguities && exportResponse.data.ambiguities.length > 0) {
          const newQuestions = exportResponse.data.ambiguities.map((amb: any) => ({
            id: `amb_${amb.type}_${amb.nodes.join('_')}`,
            type: 'question' as const,
            timestamp: Date.now(),
            content: {
              questionId: `amb_${amb.nodes.join('_')}`,
              message: amb.message,
              questionType: 'DIRECT_RELATIONSHIP',
              suggestion: amb.suggestion,
              isAmbiguity: true
            },
            onAnswer: async (qId: string, answer: string) => {
              if (answer === 'yes') {
                const res = await aiApi.commit(fId, {
                  family_id: fId,
                  confirmed_entities: [],
                  confirmed_relationships: [],
                  confirmed_events: [],
                  resolutions: [{ ...amb.suggestion, action: 'ADD_EDGE' }]
                });
                if (res.success) {
                  addMessage({
                    id: `confirmed_${Date.now()}`,
                    type: 'success',
                    timestamp: Date.now(),
                    content: { actions: [amb.message + " - 已确认"] }
                  });
                  await loadFamilyData(fId);
                }
              } else if (answer === 'no') {
                // 提交拒绝方案
                const res = await aiApi.commit(fId, {
                  family_id: fId,
                  confirmed_entities: [],
                  confirmed_relationships: [],
                  confirmed_events: [],
                  resolutions: [{ ...amb.suggestion, action: 'REJECT_EDGE' }]
                });
                if (res.success) {
                  addMessage({
                    id: `rejected_${Date.now()}`,
                    type: 'info',
                    timestamp: Date.now(),
                    content: { actions: [amb.message + " - 已忽略"] }
                  });
                  await loadFamilyData(fId);
                }
              }
            }
          }));
          
          setMessages((prev) => {
            const existingIds = new Set(prev.map(m => m.id));
            const uniqueNew = newQuestions.filter(q => !existingIds.has(q.id));
            return [...prev, ...uniqueNew];
          });
        }
      }
    } catch (error) {
      console.error('Failed to load family data:', error);
    }
  };

  const addMessage = useCallback((msg: FeedMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  // 确认合并
  const handleConfirmMerge = async (keepId: string, removeId: string, customName?: string) => {
    if (!familyId || !mergeCandidate) return;
    setIsLoading(true);
    try {
      // 如果有自定义名称，先更新保留者姓名
      if (customName) {
        await personApi.update(familyId, keepId, { name: customName });
      }
      const result = await mergeApi.run(familyId, keepId, removeId);
      if (result.success) {
        addMessage({
          id: `merge_${Date.now()}`,
          type: 'success',
          timestamp: Date.now(),
          content: { actions: result.data?.actions || ['合并成功'] },
        });
        await loadFamilyData(familyId);
      } else {
        addMessage({
          id: `merge_err_${Date.now()}`,
          type: 'error',
          timestamp: Date.now(),
          content: { error: result.message || '合并失败' },
        });
      }
    } catch (error: any) {
      addMessage({
        id: `merge_err_${Date.now()}`,
        type: 'error',
        timestamp: Date.now(),
        content: { error: error.message || '合并失败' },
      });
    } finally {
      setMergeCandidate(null);
      setIsLoading(false);
    }
  };

  // 处理交互式抽取确认
  const handleConfirmExtraction = async (commitData: ExtractionCommitRequest, replyMessage?: string) => {
    if (!familyId) return;
    setIsLoading(true);
    try {
      // 调用真实后端 API
      const result = await aiApi.commit(familyId, commitData);
      
      if (result.success && result.data) {
        // 模拟成功反馈
        addMessage({
          id: `commit_success_${Date.now()}`,
          type: 'success',
          timestamp: Date.now(),
          content: { 
            actions: result.data.actions,
            replyMessage: replyMessage 
          },
        });
        
        // 刷新图谱
        const exportRes = await familyApi.export(familyId);
        if (exportRes.success) {
          setFamilyData(exportRes.data);
        }
      } else {
        throw new Error(result.message || '入库失败');
      }
    } catch (error: any) {
      addMessage({
        id: `commit_err_${Date.now()}`,
        type: 'error',
        timestamp: Date.now(),
        content: { error: error.message || '提交确认信息失败' },
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelExtraction = () => {
    addMessage({
      id: `cancel_ext_${Date.now()}`,
      type: 'suggestion',
      timestamp: Date.now(),
      content: { suggestion: '已取消提取。' },
    });
  };

  // 核心：处理用户输入 → 先检测合并意图 → 再走正常AI解析
  const handleSend = async (text: string) => {
    if (!familyId) return;
    setIsLoading(true);
    // 新的一轮输入，重置累积答案
    accumulatedAnswersRef.current = {};

    const parsingMsgId = `parsing_${Date.now()}`;
    addMessage({
      id: parsingMsgId,
      type: 'parsing',
      timestamp: Date.now(),
      content: { text },
    });

    try {
      // 1. 先用AI判断是否是合并意图
      const intentRes = await intentApi.detect(text, familyId);
      if (intentRes.success && intentRes.data?.is_merge && intentRes.data.name_a && intentRes.data.name_b) {
        const nameA = intentRes.data.name_a;
        const nameB = intentRes.data.name_b;

        // 在数据库中匹配两人
        const foundA = familyData.people.filter(p => p.name === nameA || p.name.startsWith(nameA + ' '));
        const foundB = familyData.people.filter(p => p.name === nameB || p.name.startsWith(nameB + ' '));

        if (foundA.length >= 1 && foundB.length >= 1 && foundA[0].id !== foundB[0].id) {
          setMessages((prev) => prev.filter((m) => m.id !== parsingMsgId));
          setIsLoading(false);
          setMergeCandidate({ nameA, nameB, personA: foundA[0], personB: foundB[0] });
          return; // 弹出合并确认，不走AI解析
        }
      }

      // 2. 交互式提取逻辑 (Phase 3)
      const extractResponse = await aiApi.extract(text, familyId);
      
      if (extractResponse.success && extractResponse.data) {
        // 移除 parsing 消息
        setMessages((prev) => prev.filter((m) => m.id !== parsingMsgId));

        const parsedData = extractResponse.data.parsed_data;
        if (!parsedData) {
            throw new Error("AI 返回数据格式错误：缺少解析结果");
        }

        addMessage({
          id: `extraction_${Date.now()}`,
          type: 'extraction',
          timestamp: Date.now(),
          content: { 
            extractionData: parsedData,
            debugInfo: {
              prompt_used: extractResponse.data.prompt_used || { system: 'N/A', user: 'N/A' },
              raw_response: extractResponse.data.raw_response || 'N/A'
            },
            allPeople: familyData.people
          },
          onConfirmExtraction: (data) => handleConfirmExtraction(data, parsedData.reply_message),
          onCancelExtraction: handleCancelExtraction
        });
        return;
      } else {
        throw new Error(extractResponse.message || 'AI解析失败');
      }
    } catch (error: any) {
      setMessages((prev) => prev.filter((m) => m.id !== parsingMsgId));
      addMessage({
        id: `error_${Date.now()}`,
        type: 'error',
        timestamp: Date.now(),
        content: { error: error.message || '解析失败' },
        onRetry: () => handleSend(text),
      });
    } finally {
      setIsLoading(false);
    }
  };

  // 执行自动导入（可带用户回答）
  const runAutoImport = async (parsedData: any, answers?: Record<string, string>) => {
    try {
      const result = await autoImportApi.run(familyId, parsedData, answers);
      if (!result.success || !result.data) {
        throw new Error(result.message || '导入失败');
      }

      const { auto_saved, actions, questions, pending_data } = result.data;

      if (auto_saved) {
        // 全部自动入库
        addMessage({
          id: `success_${Date.now()}`,
          type: 'success',
          timestamp: Date.now(),
          content: {
            actions,
            onActionDelete: handleActionDelete,
          },
        });
        await loadFamilyData(familyId);
      } else {
        // 需要用户确认
        if (actions.length > 0) {
          addMessage({
            id: `partial_${Date.now()}`,
            type: 'success',
            timestamp: Date.now(),
            content: { actions },
          });
          // 即使有后续问题，如果已经有了实质动作（如新建了人），也刷新一下界面
          await loadFamilyData(familyId);
        }

        setPendingData(pending_data || parsedData);
        pendingDataRef.current = pending_data || parsedData;

        // 为每个问题创建提问消息（跳过已有相同 ID 的，防止重复 key）
        setMessages((prev) => {
          const existingIds = new Set(prev.map(m => m.id));
          const newQuestions = questions
            .filter((q: any) => !existingIds.has(`q_${q.id}`))
            .map((q: any) => ({
              id: `q_${q.id}`,
              type: 'question' as const,
              timestamp: Date.now(),
              content: {
                questionId: q.id,
                message: q.message,
                questionType: q.type,
                candidates: q.candidates,
                conflictInfo: q.conflict_info,
                directionOptions: q.direction_options,
                entity: q.entity,
                allowNew: q.allow_new || false,
              },
              onAnswer: handleAnswer,
            }));
          return [...prev, ...newQuestions];
        });
      }
    } catch (error: any) {
      addMessage({
        id: `error_${Date.now()}`,
        type: 'error',
        timestamp: Date.now(),
        content: { error: error.message || '自动导入失败' },
      });
    }
  };

  // 处理用户对提问的回答
  const handleAnswer = async (questionId: string, answer: string) => {
    const currentPendingData = pendingDataRef.current;

    // 先标记问题已回答（无论后续是否成功）
    setMessages((prev) =>
      prev.map((m) => {
        if (m.content.questionId === questionId && m.type === 'question') {
          return { ...m, type: 'question' as const, content: { ...m.content, onAnswer: undefined } };
        }
        return m;
      })
    );

    if (!currentPendingData) {
      console.error('handleAnswer: pendingData is null!');
      addMessage({
        id: `err_${Date.now()}`,
        type: 'error',
        timestamp: Date.now(),
        content: { error: '操作超时，请重新输入' },
      });
      return;
    }

    // 取消操作 — 不重新执行导入，直接跳过
    if (answer === '__cancel__' || answer === '__cancel_rel__') {
      addMessage({
        id: `cancel_${Date.now()}`,
        type: 'suggestion',
        timestamp: Date.now(),
        content: { suggestion: '已跳过此问题。你可以继续输入新的家族叙事。' },
      });
      return;
    }

    // 累积当前答案，发送所有已回答的答案
    accumulatedAnswersRef.current[questionId] = answer;
    const allAnswers = { ...accumulatedAnswersRef.current };
    await runAutoImport(currentPendingData, allAnswers);
  };

  // 处理消息流中"审查"时的逐条删除
  const handleActionDelete = async (action: string, actionType: string) => {
    if (!familyId) return;
    try {
      if (actionType === 'create_person') {
        // "新增人物: 张三" → 找到该人物并删除
        const match = action.match(/新增人物[^：:]*[：:]\s*(.+)/);
        if (match) {
          const name = match[1].trim();
          const person = familyData.people.find(p => p.name === name);
          if (person) {
            await personApi.delete(familyId, person.id);
            addMessage({
              id: `undo_${Date.now()}`,
              type: 'suggestion',
              timestamp: Date.now(),
              content: { suggestion: `已删除人物「${name}」。关系推导已自动更新。` },
            });
            // 重推导
            try { await deriveApi.run(familyId); } catch {}
            await loadFamilyData(familyId);
          }
        }
      } else if (actionType === 'relationship') {
        // "新增关系: A ↔ B (type)" 或 "推导关系: A ↔ B (type)"
        const match = action.match(/(?:新增关系|推导关系)[^：:]*[：:]\s*(.+?)\s*↔\s*(.+?)\s*\((.+?)\)/);
        if (match) {
          const [, nameA, nameB, relType] = match;
          const pA = familyData.people.find(p => p.name === nameA.trim());
          const pB = familyData.people.find(p => p.name === nameB.trim());
          if (pA && pB) {
            const rel = familyData.relationships.find(r =>
              ((r.person1_id === pA.id && r.person2_id === pB.id) ||
               (r.person1_id === pB.id && r.person2_id === pA.id)) &&
              r.type === relType.trim()
            );
            if (rel) {
              await relationshipApi.delete(familyId, rel.id);
              addMessage({
                id: `undo_${Date.now()}`,
                type: 'suggestion',
                timestamp: Date.now(),
                content: { suggestion: `已删除关系「${nameA.trim()} ↔ ${nameB.trim()} (${relType.trim()})」。` },
              });
              await loadFamilyData(familyId);
            }
          }
        }
      } else if (actionType === 'event') {
        // "新增事件: 描述" — 暂不处理事件删除
        addMessage({
          id: `info_${Date.now()}`,
          type: 'suggestion',
          timestamp: Date.now(),
          content: { suggestion: '事件删除功能即将上线，目前请在人物详情面板中操作。' },
        });
      }
    } catch (err: any) {
      addMessage({
        id: `err_${Date.now()}`,
        type: 'error',
        timestamp: Date.now(),
        content: { error: `撤销失败: ${err.message || '未知错误'}` },
      });
    }
  };

  const handleDeletePerson = async (personId: string) => {
    if (!familyId) return;
    try {
      await personApi.delete(familyId, personId);
      await loadFamilyData(familyId);
      setSelectedPerson(null);
    } catch (error) {
      console.error('Failed to delete person:', error);
    }
  };

  // 搜索过滤 + 占位过滤
  let displayPeople = showPlaceholders 
    ? familyData.people 
    : familyData.people.filter(p => !p.is_placeholder);
  const filteredPeople = searchQuery
    ? displayPeople.filter(
        (p) =>
          p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          p.tags.some((t) => t.includes(searchQuery))
      )
    : displayPeople;

  if (isHealthy === false) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-lg max-w-md text-center">
          <div className="text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-bold text-gray-800 mb-2">后端服务未启动</h2>
          <p className="text-gray-600 mb-4">请先启动后端API服务：</p>
          <code className="block bg-gray-100 p-3 rounded text-sm text-left">
            cd backend<br />python main.py
          </code>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* 顶部导航栏 */}
      <header className="bg-white shadow-sm border-b border-gray-200 flex-shrink-0 z-30">
        <div className="px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📖</span>
            <h1 className="text-xl font-bold text-gray-800">家族编年史</h1>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索成员..."
                className="pl-9 pr-4 py-1.5 border border-gray-300 rounded-lg text-sm
                           focus:ring-2 focus:ring-primary-500 focus:border-transparent w-48"
              />
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">🔍</span>
            </div>
            <button
              onClick={() => setShowPlaceholders(!showPlaceholders)}
              className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                showPlaceholders 
                  ? 'bg-amber-100 border-amber-400 text-amber-700' 
                  : 'bg-gray-50 border-gray-300 text-gray-500 hover:bg-gray-100'
              }`}
              title={showPlaceholders ? '隐藏占位节点' : '显示占位节点'}
            >
              👻 {showPlaceholders ? '隐藏占位' : '显示占位'}
            </button>
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 图谱主区域 */}
        <div className="flex-1 p-4 pb-0">
          <div className={`h-full bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden
                          ${selectedPerson ? 'rounded-b-none' : ''}`}>
            <FamilyGraphView
              people={filteredPeople}
              relationships={familyData.relationships}
              onPersonClick={setHighlightedPerson}
              onPersonDoubleClick={setSelectedPerson}
              selectedPersonId={highlightedPerson?.id || selectedPerson?.id}
            />
          </div>
        </div>

        {/* 消息流 */}
        <div className="w-72 flex-shrink-0">
          <MessageFeed messages={messages} />
        </div>
      </div>

      {/* 底部输入条 */}
      <InputBar onSend={handleSend} isLoading={isLoading} />

      {/* 合并确认弹窗 */}
      {mergeCandidate && (
        <MergeConfirmDialog
          personA={mergeCandidate.personA}
          personB={mergeCandidate.personB}
          familyId={familyId}
          onConfirm={handleConfirmMerge}
          onCancel={() => setMergeCandidate(null)}
        />
      )}

      {/* 人物详情面板（双击打开） */}
      {selectedPerson && (
        <>
          <div className="fixed inset-0 bg-black bg-opacity-10 z-40" onClick={() => { setSelectedPerson(null); setHighlightedPerson(null); }} />
          <PersonDetail
            familyId={familyId}
            person={selectedPerson}
            allPeople={familyData.people}
            onClose={() => { setSelectedPerson(null); setHighlightedPerson(null); }}
            onDelete={handleDeletePerson}
            onDataChanged={() => loadFamilyData(familyId)}
          />
        </>
      )}

      {/* 浮动人物卡片（单击显示） */}
      {highlightedPerson && !selectedPerson && (
        <FloatingPersonCard
          person={highlightedPerson}
          relationshipCount={familyData.relationships.filter(
            r => r.person1_id === highlightedPerson.id || r.person2_id === highlightedPerson.id
          ).length}
          onOpenDetail={() => setSelectedPerson(highlightedPerson)}
          onClose={() => setHighlightedPerson(null)}
        />
      )}
    </div>
  );
}

export default App;
