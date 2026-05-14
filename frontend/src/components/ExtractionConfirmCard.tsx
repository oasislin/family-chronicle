import React, { useState, useEffect } from 'react';
import { AIExtractionResult, Person, AIExtractionEntity, AIExtractionRelationship, AIExtractionEvent, ExtractionCommitRequest } from '../types';

interface ExtractionConfirmCardProps {
  data: AIExtractionResult;
  allPeople: Person[];
  familyId: string;
  onConfirm: (commitData: ExtractionCommitRequest) => void;
  onCancel: () => void;
  debugInfo?: {
    prompt_used: { system: string; user: string };
    raw_response: string;
  };
}

const ExtractionConfirmCard: React.FC<ExtractionConfirmCardProps> = ({
  data,
  allPeople,
  onConfirm,
  onCancel,
  familyId,
  debugInfo,
}) => {
  const [entities, setEntities] = useState<AIExtractionEntity[]>(data?.entities || []);
  const [relationships, setRelationships] = useState<AIExtractionRelationship[]>(data?.relationships || []);
  const [events, setEvents] = useState<AIExtractionEvent[]>(data?.events || []);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showDebug, setShowDebug] = useState(false);
  const [resolutions, setResolutions] = useState<Record<string, string>>({});
  const [currentData, setCurrentData] = useState<AIExtractionResult>(data);
  const [isValidating, setIsValidating] = useState(false);
  const [taskInputs, setTaskInputs] = useState<Record<string, string>>({});

  // Sync state if data changes
  useEffect(() => {
    if (data) {
      setEntities(data.entities || []);
      setRelationships(data.relationships || []);
      setEvents(data.events || []);
      setCurrentData(data);
    }
  }, [data]);

  const handleEntityChange = (index: number, field: keyof AIExtractionEntity, value: any) => {
    const newEntities = [...entities];
    newEntities[index] = { ...newEntities[index], [field]: value };
    
    if (field === 'matched_db_id') {
      if (value) {
        newEntities[index].is_new = false;
        const person = allPeople.find(p => p.id === value);
        if (person) {
          newEntities[index].gender = person.gender === 'male' ? 'M' : (person.gender === 'female' ? 'F' : 'UNKNOWN');
        }
      } else {
        newEntities[index].is_new = true;
      }
    }
    
    setEntities(newEntities);
  };

  const handleRelChange = (index: number, value: string) => {
    const newRels = [...relationships];
    newRels[index] = { ...newRels[index], natural_language_desc: value };
    setRelationships(newRels);
  };

  const handleEventChange = (index: number, field: keyof AIExtractionEvent, value: any) => {
    const newEvents = [...events];
    newEvents[index] = { ...newEvents[index], [field]: value };
    setEvents(newEvents);
  };

  const handleResolutionChange = (key: string, value: string) => {
    const updated = { ...resolutions, [key]: value };
    setResolutions(updated);
    // 触发扩散校验
    triggerValidation(updated);
  };

  const triggerValidation = async (updatedResolutions: Record<string, string>) => {
    setIsValidating(true);
    try {
      const response = await fetch('/api/chat/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          family_id: familyId,
          confirmed_entities: entities.map(e => ({
            temp_id: e.temp_id,
            name: e.name,
            gender: e.gender,
            action: e.is_new ? 'CREATE' : 'LINK_EXISTING',
            matched_db_id: e.matched_db_id || undefined,
          })),
          confirmed_relationships: relationships,
          confirmed_events: events,
          resolutions: updatedResolutions,
        })
      });
      const result = await response.json();
      if (result.success) {
        setCurrentData(prev => ({
          ...prev,
          tasks: result.data.tasks,
          reply_message: result.data.reply_message || prev.reply_message
        }));
      }
    } catch (e) {
      console.error("Validation failed", e);
    } finally {
      setIsValidating(false);
    }
  };

  const handleTaskAction = (task: any, option: any) => {
    const { action, payload, target_id } = option;
    const taskId = task.id;

    if (action === 'RESOLVE_AMBIGUITY') {
      handleResolutionChange(taskId, target_id);
    } else if (action === 'CREATE_PLACEHOLDER') {
      // 携带 payload 以便后端知道要创建什么的占位符
      const resVal = `ACTION:CREATE_PLACEHOLDER:${JSON.stringify(payload || {})}`;
      handleResolutionChange(taskId, resVal);
    } else if (action === 'RESOLVE_GRANDPARENT') {
      resolveGrandparent(taskId, payload.name, payload.target_name || "王芳", payload.base_type, payload.variant);
    } else if (action === 'LINK_EXISTING') {
      const entIdx = entities.findIndex(e => e.temp_id === payload.temp_id);
      if (entIdx !== -1) {
        handleEntityChange(entIdx, 'matched_db_id', payload.matched_db_id);
        handleResolutionChange(taskId, payload.matched_db_id);
      }
    } else if (action === 'REJECT_EDGE' || action === 'IGNORE' || action === 'SWAP_DIRECTION' || action === 'MODIFY_GENDER') {
      const resVal = `ACTION:${action}:${JSON.stringify(payload || {})}`;
      handleResolutionChange(taskId, resVal);
    } else if (action.startsWith('SUBMIT_')) {
      const text = taskInputs[taskId] || "";
      handleResolutionChange(taskId, `ACTION:SUBMIT_TEXT:${JSON.stringify({ text })}`);
    }
  };

  const resolveGrandparent = (
    taskId: string, 
    sourceName: string, 
    targetName: string, 
    baseType: 'grandfather' | 'grandmother',
    variant: 'PATERNAL' | 'MATERNAL'
  ) => {
    let relIdx = relationships.findIndex(r => {
      const sName = getDisplayName(r.source_ref);
      const tName = getDisplayName(r.target_ref);
      return (sName.includes(sourceName) || tName.includes(sourceName)) && 
             (sName.includes(targetName) || tName.includes(targetName));
    });

    const kinshipType = `${baseType}_${variant.toLowerCase()}` as any;

    if (relIdx !== -1) {
      const newRels = [...relationships];
      newRels[relIdx] = { ...newRels[relIdx], kinship_type: kinshipType };
      setRelationships(newRels);
      handleResolutionChange(taskId, variant);
    } else {
      const sourceEnt = entities.find(e => e.name.includes(sourceName));
      const targetEnt = entities.find(e => e.name.includes(targetName)) || 
                        allPeople.find(p => p.name.includes(targetName));

      if (sourceEnt && targetEnt) {
        const newRel: AIExtractionRelationship = {
          source_ref: sourceEnt.temp_id,
          target_ref: (targetEnt as any).temp_id || (targetEnt as any).id,
          kinship_type: kinshipType,
          natural_language_desc: `${sourceName}是${targetName}的${baseType === 'grandfather' ? (variant === 'PATERNAL' ? '祖父' : '外祖父') : (variant === 'PATERNAL' ? '祖母' : '外祖母')}`
        };
        setRelationships([...relationships, newRel]);
        handleResolutionChange(taskId, variant);
      }
    }
  };

  const getDisplayName = (ref: string) => {
    const entity = entities.find(e => e.temp_id === ref);
    if (entity) return entity.name;
    const person = allPeople.find(p => p.id === ref);
    if (person) return person.name;
    return ref;
  };

  const handleCommit = () => {
    setIsSubmitting(true);
    const commitData: ExtractionCommitRequest = {
      family_id: familyId,
      confirmed_entities: entities.map(e => ({
        temp_id: e.temp_id,
        name: e.name,
        gender: e.gender,
        action: e.is_new ? 'CREATE' : 'LINK_EXISTING',
        matched_db_id: e.matched_db_id || undefined,
      })),
      confirmed_relationships: relationships,
      confirmed_events: events,
      resolutions: resolutions,
    };
    onConfirm(commitData);
  };

  return (
    <div className="bg-white rounded-xl border border-blue-200 shadow-lg overflow-hidden flex flex-col max-h-[500px]">
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3 flex items-center justify-between">
        <h3 className="text-white font-medium flex items-center gap-2">
          <span>🧩</span> 确认提取结果
        </h3>
        <button 
          onClick={onCancel}
          className="text-white/70 hover:text-white transition-colors"
        >
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {currentData.reply_message && (
          <div className={`border-l-4 p-3 rounded-r-lg transition-colors ${isValidating ? "bg-gray-50 border-gray-300" : "bg-blue-50 border-blue-400"}`}>
            <p className="text-sm text-blue-800 flex items-center gap-2">
              {isValidating && <span className="animate-pulse">🔄</span>}
              {currentData.reply_message}
            </p>
          </div>
        )}

        {currentData.tasks && currentData.tasks.length > 0 && (
          <div className={`border rounded-lg p-3 space-y-3 transition-all ${isValidating ? "bg-gray-50 border-gray-200 opacity-60" : "bg-amber-50 border-amber-200"}`}>
            <h4 className="text-xs font-bold text-amber-700 flex items-center gap-1">
              <span>🧠</span> 待确认的智能推导与补全任务 ({currentData.tasks.length}):
            </h4>
            <div className="space-y-4">
              {currentData.tasks.map((task) => {
                const currentRes = resolutions[task.id];
                const isResolved = !!currentRes;
                
                const isConflict = task.category === 'conflict';
                
                return (
                  <div key={task.id} className={`space-y-2 pb-3 border-b last:border-0 ${
                    isConflict ? "bg-red-50/50 p-2 rounded -mx-2 border-red-100" : "border-amber-100"
                  }`}>
                    <div className="flex items-start gap-1.5">
                      {isConflict ? (
                        <span className="text-red-500 mt-0.5">⚠️</span>
                      ) : (
                        <span className="text-amber-500 mt-0.5">💡</span>
                      )}
                      <p className={`text-[11px] font-medium leading-relaxed ${
                        isConflict ? "text-red-900" : "text-amber-900"
                      }`}>
                        {task.message}
                      </p>
                    </div>
                    
                    {task.type === 'input_text' && !isResolved && (
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={taskInputs[task.id] || ''}
                          onChange={(e) => setTaskInputs({...taskInputs, [task.id]: e.target.value})}
                          placeholder="请输入修正信息..."
                          className="flex-1 px-2 py-1 bg-white border border-amber-200 rounded text-[10px] outline-none focus:ring-1 focus:ring-amber-400"
                        />
                      </div>
                    )}

                    <div className="flex flex-wrap gap-2">
                      {task.options.map((opt, i) => {
                        const isSelected = currentRes === opt.target_id || 
                                          (opt.action === 'RESOLVE_GRANDPARENT' && currentRes === opt.payload.variant) ||
                                          (opt.action === 'CREATE_PLACEHOLDER' && typeof currentRes === 'string' && currentRes.startsWith('ACTION:CREATE_PLACEHOLDER')) ||
                                          currentRes === opt.action;
                        
                        const isCorrection = opt.action === 'SWAP_DIRECTION' || opt.action === 'MODIFY_GENDER' || opt.action === 'REJECT_EDGE';

                        return (
                          <button
                            key={i}
                            disabled={isResolved && !isSelected}
                            onClick={() => handleTaskAction(task, opt)}
                            className={`px-3 py-1.5 rounded text-[10px] font-medium transition-all ${
                              isSelected ? "bg-green-100 text-green-700 border border-green-300 shadow-sm" : 
                              (isResolved ? "bg-gray-100 text-gray-400 opacity-50 cursor-not-allowed" : 
                               (isCorrection ? "bg-red-50 border border-red-200 text-red-700 hover:bg-red-100 shadow-sm" : 
                                "bg-white border border-amber-300 text-amber-700 hover:bg-amber-50 shadow-sm")
                              )
                            }`}
                          >
                            {isSelected ? `✓ ${opt.label.replace('确认为', '已设为')}` : opt.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="text-[10px] text-amber-600 border-t border-amber-100 pt-2">
              提示：基于协议驱动的交互任务，确认后将自动触发推导算法扩散校验。
            </p>
          </div>
        )}

        <div>
          <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-1">
            <span>👤</span> 人物实体 ({entities.length})
          </h4>
          <div className="space-y-3">
            {entities.map((entity, idx) => (
              <div key={entity.temp_id} className="p-3 rounded-lg border border-gray-100 bg-gray-50/50 space-y-2">
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={entity.name}
                    onChange={(e) => handleEntityChange(idx, 'name', e.target.value)}
                    className="flex-1 px-2 py-1 bg-white border border-gray-200 rounded text-sm font-medium focus:ring-1 focus:ring-blue-400 focus:border-transparent outline-none"
                    placeholder="姓名"
                  />
                  <select
                    value={entity.gender}
                    onChange={(e) => handleEntityChange(idx, 'gender', e.target.value)}
                    className="px-2 py-1 bg-white border border-gray-200 rounded text-sm outline-none"
                  >
                    <option value="M">男 ♂</option>
                    <option value="F">女 ♀</option>
                    <option value="UNKNOWN">未知</option>
                  </select>
                </div>
                
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-gray-400 whitespace-nowrap">关联到:</span>
                  <select
                    value={entity.matched_db_id || ''}
                    onChange={(e) => handleEntityChange(idx, 'matched_db_id', e.target.value || null)}
                    className={`flex-1 px-2 py-1 bg-white border rounded text-xs outline-none transition-colors ${
                      entity.matched_db_id ? 'border-green-300 text-green-700' : 'border-gray-200 text-gray-500'
                    }`}
                  >
                    <option value="">-- 新建人物 --</option>
                    {allPeople
                      .filter(p => !entities.some((e, i) => i !== idx && e.matched_db_id === p.id))
                      .sort((a, b) => a.name.localeCompare(b.name))
                      .map(p => (
                        <option key={p.id} value={p.id}>{p.name} {p.is_placeholder ? '(占位)' : ''}</option>
                      ))
                    }
                  </select>
                </div>
                
                {entity.reason && (
                  <p className="text-[10px] text-amber-600 bg-amber-50 px-2 py-1 rounded">
                    💡 {entity.reason}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>

        {relationships.length > 0 && (
          <div>
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-1">
              <span>🔗</span> 关系描述 ({relationships.length})
            </h4>
            <div className="space-y-3">
              {relationships.map((rel, idx) => (
                <div key={idx} className="p-3 rounded-lg border border-gray-100 bg-gray-50/50">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xs font-medium text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full">
                      {getDisplayName(rel.source_ref)}
                    </span>
                    <span className="text-gray-400 text-[10px]">→</span>
                    <span className="text-xs font-medium text-indigo-700 bg-indigo-100 px-2 py-0.5 rounded-full">
                      {getDisplayName(rel.target_ref)}
                    </span>
                  </div>
                  <input
                    type="text"
                    value={rel.natural_language_desc}
                    onChange={(e) => handleRelChange(idx, e.target.value)}
                    className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs focus:ring-1 focus:ring-blue-400 outline-none"
                    placeholder="描述他们的关系，例如：A是B的父亲"
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {events.length > 0 && (
          <div>
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-1">
              <span>📅</span> 家族事件 ({events.length})
            </h4>
            <div className="space-y-3">
              {events.map((ev, idx) => (
                <div key={idx} className="p-3 rounded-lg border border-gray-100 bg-gray-50/50 space-y-2">
                  <input
                    type="text"
                    value={ev.description}
                    onChange={(e) => handleEventChange(idx, 'description', e.target.value)}
                    className="w-full px-2 py-1 bg-white border border-gray-200 rounded text-xs font-medium focus:ring-1 focus:ring-blue-400 outline-none"
                    placeholder="事件描述"
                  />
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={ev.date || ''}
                      onChange={(e) => handleEventChange(idx, 'date', e.target.value)}
                      className="flex-1 px-2 py-1 bg-white border border-gray-200 rounded text-[10px] outline-none"
                      placeholder="时间 (如: 1950)"
                    />
                    <input
                      type="text"
                      value={ev.location || ''}
                      onChange={(e) => handleEventChange(idx, 'location', e.target.value)}
                      className="flex-1 px-2 py-1 bg-white border border-gray-200 rounded text-[10px] outline-none"
                      placeholder="地点"
                    />
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {ev.involved_refs.map(ref => (
                      <span key={ref} className="text-[9px] bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded">
                        {getDisplayName(ref)}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="p-4 bg-gray-50 border-t border-gray-200 flex gap-3">
        <button
          onClick={handleCommit}
          disabled={isSubmitting}
          className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg text-sm shadow-md shadow-blue-200 transition-all active:scale-95 disabled:opacity-50 disabled:active:scale-100"
        >
          {isSubmitting ? '正在提交...' : '确认并存入族谱'}
        </button>
        <button
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-4 py-2 bg-white border border-gray-300 text-gray-600 font-medium rounded-lg text-sm hover:bg-gray-50 transition-all"
        >
          取消
        </button>
      </div>

      {debugInfo && (
        <div className="border-t border-gray-100">
          <button 
            onClick={() => setShowDebug(!showDebug)}
            className="w-full px-4 py-1.5 bg-gray-50 text-[10px] text-gray-400 text-left hover:bg-gray-100 transition-colors flex justify-between items-center"
          >
            <span>🛠️ 开发者调试信息 (Prompt & Raw Response)</span>
            <span>{showDebug ? '▲ 收起' : '▼ 展开'}</span>
          </button>
          
          {showDebug && (
            <div className="p-3 bg-gray-900 text-gray-300 text-[10px] font-mono overflow-auto max-h-[300px] space-y-3">
              {debugInfo?.prompt_used && (
                <>
                  <div>
                    <div className="text-blue-400 mb-1 border-b border-gray-700 pb-0.5">--- SYSTEM PROMPT ---</div>
                    <pre className="whitespace-pre-wrap">{debugInfo.prompt_used.system || 'N/A'}</pre>
                  </div>
                  <div>
                    <div className="text-green-400 mb-1 border-b border-gray-700 pb-0.5">--- USER PROMPT ---</div>
                    <pre className="whitespace-pre-wrap">{debugInfo.prompt_used.user || 'N/A'}</pre>
                  </div>
                </>
              )}
              <div>
                <div className="text-amber-400 mb-1 border-b border-gray-700 pb-0.5">--- RAW JSON RESPONSE ---</div>
                <pre className="whitespace-pre-wrap">{debugInfo?.raw_response || 'N/A'}</pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ExtractionConfirmCard;
