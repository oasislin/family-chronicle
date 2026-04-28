import React, { useState, useEffect } from 'react';
import { AIExtractionResult, Person, AIExtractionEntity, AIExtractionRelationship, AIExtractionEvent, ExtractionCommitRequest } from '../types';

interface ExtractionConfirmCardProps {
  data: AIExtractionResult;
  allPeople: Person[];
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
  debugInfo,
}) => {
  const [entities, setEntities] = useState<AIExtractionEntity[]>(data?.entities || []);
  const [relationships, setRelationships] = useState<AIExtractionRelationship[]>(data?.relationships || []);
  const [events, setEvents] = useState<AIExtractionEvent[]>(data?.events || []);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showDebug, setShowDebug] = useState(false);

  // Sync state if data changes
  useEffect(() => {
    if (data) {
      setEntities(data.entities || []);
      setRelationships(data.relationships || []);
      setEvents(data.events || []);
    }
  }, [data]);

  const handleEntityChange = (index: number, field: keyof AIExtractionEntity, value: any) => {
    const newEntities = [...entities];
    newEntities[index] = { ...newEntities[index], [field]: value };
    
    // If we link to an existing person, mark as not new
    if (field === 'matched_db_id') {
      if (value) {
        newEntities[index].is_new = false;
        const person = allPeople.find(p => p.id === value);
        if (person) {
          // 不再强制覆盖姓名，保留提取到的更具体的姓名（如“林高德”而非“丈夫”）
          // newEntities[index].name = person.name; 
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

  const getDisplayName = (ref: string) => {
    // Check entities first
    const entity = entities.find(e => e.temp_id === ref);
    if (entity) return entity.name;
    
    // Then check database
    const person = allPeople.find(p => p.id === ref);
    if (person) return person.name;
    
    return ref;
  };

  const handleCommit = () => {
    setIsSubmitting(true);
    const commitData: ExtractionCommitRequest = {
      confirmed_entities: entities.map(e => ({
        temp_id: e.temp_id,
        name: e.name,
        gender: e.gender,
        action: e.is_new ? 'CREATE' : 'LINK_EXISTING',
        matched_db_id: e.matched_db_id || undefined,
      })),
      confirmed_relationships: relationships,
      confirmed_events: events,
    };
    onConfirm(commitData);
  };

  return (
    <div className="bg-white rounded-xl border border-blue-200 shadow-lg overflow-hidden flex flex-col max-h-[500px]">
      {/* Header */}
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
        {/* Reply Message */}
        {data.reply_message && (
          <div className="bg-blue-50 border-l-4 border-blue-400 p-3 rounded-r-lg">
            <p className="text-sm text-blue-800">{data.reply_message}</p>
          </div>
        )}

        {/* Clarification Questions */}
        {data.clarification_questions && data.clarification_questions.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
            <h4 className="text-xs font-bold text-amber-700 flex items-center gap-1">
              <span>🤔</span> 发现潜在矛盾或需要澄清：
            </h4>
            <ul className="list-disc list-inside space-y-1">
              {data.clarification_questions.map((q, i) => (
                <li key={i} className="text-xs text-amber-800 italic">“{q}”</li>
              ))}
            </ul>
            <p className="text-[10px] text-amber-600 mt-2">
              提示：你可以根据这些疑问，在下方手动调整匹配的人员或描述。
            </p>
          </div>
        )}

        {/* Entities Section */}
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

        {/* Relationships Section */}
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

        {/* Events Section */}
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

      {/* Footer */}
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

      {/* Debug Info Section */}
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
