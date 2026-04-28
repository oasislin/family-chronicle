import React, { useState, useEffect } from 'react';
import { Person, Event, Relationship } from '../types';
import { personApi, relationshipApi } from '../services/api';
import PersonPicker from './PersonPicker';
import EventForm from './EventForm';
import StoryEditor from './StoryEditor';

// 解析传记中的 {{person:ID}} 占位符为当前名字
const resolveStoryRefs = (story: string | undefined, allPeople: Person[]): string => {
  if (!story) return '';
  const peopleMap = new Map(allPeople.map(p => [p.id, p.name]));
  return story.replace(/\{\{person:([^}]+)\}\}/g, (_, id) => {
    return peopleMap.get(id) || `[未知:${id}]`;
  });
};

interface PersonDetailProps {
  familyId: string;
  person: Person | null;
  allPeople: Person[];
  onClose: () => void;
  onDelete?: (personId: string) => void;
  onDataChanged?: () => void;
}

type TabType = 'info' | 'timeline' | 'relations' | 'story' | 'add';

const RELATIONSHIP_LABELS: Record<string, string> = {
  parent_child: '亲子关系',
  spouse: '配偶',
  sibling: '兄弟姐妹',
  step_parent_child: '继父母/子女',
  grandparent_grandchild: '祖孙关系',
  aunt_uncle_niece_nephew: '叔侄关系',
  cousin: '表亲',
  adopted_parent_child: '过继关系',
  godparent_godchild: '干亲关系',
  in_law: '姻亲',
  other: '其他',
};

// 根据两人性别返回具体的兄弟姐妹称谓
const getSiblingLabel = (gender1: string, gender2: string): string => {
  if (gender1 === 'male' && gender2 === 'male') return '兄弟';
  if (gender1 === 'female' && gender2 === 'female') return '姐妹';
  if (gender1 === 'male' && gender2 === 'female') return '兄妹';
  if (gender1 === 'female' && gender2 === 'male') return '姐弟';
  return '兄弟姐妹';
};

const EVENT_LABELS: Record<string, string> = {
  birth: '出生',
  death: '去世',
  marriage: '结婚',
  divorce: '离婚',
  adoption: '过继',
  illness: '生病',
  relocation: '搬家',
  education: '教育',
  career: '职业',
  recognition: '认干亲',
  other: '其他',
};

const PersonDetail: React.FC<PersonDetailProps> = ({
  familyId,
  person,
  allPeople,
  onClose,
  onDelete,
  onDataChanged,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('info');
  const [details, setDetails] = useState<{
    person: Person;
    relationships: Relationship[];
    events: Event[];
  } | null>(null);
  const [loading, setLoading] = useState(false);

  // 编辑状态
  const [editData, setEditData] = useState<Partial<Person>>({});
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  // 编辑历史
  const [editHistory, setEditHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // 添加关系状态
  const [newRelType, setNewRelType] = useState('parent_child');
  const [newRelTarget, setNewRelTarget] = useState<Person | null>(null);
  const [newRelSubtype, setNewRelSubtype] = useState('');
  const [showEventForm, setShowEventForm] = useState(false);

  useEffect(() => {
    if (person) {
      loadDetails();
      setIsEditing(false);
      setActiveTab('info');
      setEditHistory([]);
    }
  }, [person]);

  // 当切换到时间线 tab 时加载历史
  useEffect(() => {
    if (activeTab === 'timeline' && person && familyId) {
      loadEditHistory();
    }
  }, [activeTab, person?.id]);

  const loadEditHistory = async () => {
    if (!person || !familyId) return;
    setLoadingHistory(true);
    try {
      const { historyApi } = await import('../services/api');
      const res = await historyApi.get(familyId, person.id);
      if (res.success && res.data) {
        setEditHistory(res.data.reverse()); // 最新的在前
      }
    } catch (err) {
      console.error('Failed to load edit history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const loadDetails = async () => {
    if (!person || !familyId) return;
    setLoading(true);
    try {
      const res = await personApi.get(familyId, person.id);
      if (res.success && res.data) {
        setDetails(res.data);
        setEditData(res.data.person);
      }
    } catch (err) {
      console.error('Failed to load details:', err);
    } finally {
      setLoading(false);
    }
  };

  const getPersonName = (id: string) => allPeople.find((p) => p.id === id)?.name || '未知';
  const getPersonGender = (id: string) => allPeople.find((p) => p.id === id)?.gender || 'unknown';

  const handleSavePerson = async () => {
    if (!person || !familyId) return;
    setSaving(true);
    try {
      await personApi.update(familyId, person.id, editData);
      setIsEditing(false);
      loadDetails();
      onDataChanged?.();
    } catch (err) {
      console.error('Failed to save:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRelationship = async (relId: string) => {
    if (!familyId) return;
    if (!confirm('确定删除此关系？')) return;
    try {
      await relationshipApi.delete(familyId, relId);
      loadDetails();
      onDataChanged?.();
    } catch (err) {
      console.error('Failed to delete relationship:', err);
    }
  };

  const handleAddRelationship = async () => {
    if (!person || !familyId || !newRelTarget) return;
    try {
      const relData: any = {
        type: newRelType,
        subtype: newRelSubtype || undefined,
      };
      // 根据关系类型确定方向
      if (newRelType === 'parent_child') {
        relData.person1_id = person.id;
        relData.person2_id = newRelTarget.id;
        relData.subtype = 'father';
      } else if (newRelType === 'spouse') {
        relData.person1_id = person.id;
        relData.person2_id = newRelTarget.id;
      } else {
        relData.person1_id = person.id;
        relData.person2_id = newRelTarget.id;
      }

      await relationshipApi.create(familyId, relData);
      setNewRelTarget(null);
      setNewRelSubtype('');
      loadDetails();
      onDataChanged?.();
    } catch (err) {
      console.error('Failed to add relationship:', err);
    }
  };

  const handleStorySave = async (story: string) => {
    if (!person || !familyId) return;
    try {
      await personApi.update(familyId, person.id, { story });
      loadDetails();
      onDataChanged?.();
    } catch (err) {
      console.error('Failed to save story:', err);
    }
  };

  const handleRegenerateBiography = async () => {
    if (!person || !familyId) return;
    try {
      const { biographyApi } = await import('../services/api');
      const res = await biographyApi.generate(familyId, person.id);
      if (res.success) {
        loadDetails();
        onDataChanged?.();
      }
    } catch (err) {
      console.error('Failed to regenerate biography:', err);
    }
  };

  const handleAddEvent = async (eventData: Partial<Event>) => {
    if (!familyId) return;
    try {
      const { eventApi } = await import('../services/api');
      await eventApi.create(familyId, eventData);
      setShowEventForm(false);
      loadDetails();
      onDataChanged?.();
    } catch (err) {
      console.error('Failed to create event:', err);
    }
  };

  if (!person) return null;

  const genderIcon = person.gender === 'male' ? '👨' : person.gender === 'female' ? '👩' : '👤';

  const tabs: { key: TabType; label: string; icon: string }[] = [
    { key: 'info', label: '基本信息', icon: '📋' },
    { key: 'timeline', label: '时间线', icon: '📅' },
    { key: 'relations', label: '关系网络', icon: '👥' },
    { key: 'story', label: '生平故事', icon: '📖' },
    { key: 'add', label: '添加', icon: '➕' },
  ];

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white shadow-2xl z-50 flex flex-col rounded-t-xl"
         style={{ height: '45vh' }}>
      {/* 头部 */}
      <div className="px-6 py-3 border-b border-gray-200 flex items-center justify-between bg-gray-50 rounded-t-xl">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{genderIcon}</span>
          <div>
            <h2 className="font-bold text-lg text-gray-800">{person.name}</h2>
            <p className="text-sm text-gray-500">
              {person.birth_date || '?'}{person.death_date ? ` - ${person.death_date}` : ''}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!isEditing && activeTab === 'info' && (
            <button onClick={() => setIsEditing(true)}
              className="px-3 py-1 text-sm bg-primary-100 text-primary-700 rounded-lg hover:bg-primary-200">
              ✏️ 编辑
            </button>
          )}
          {onDelete && (
            <button
              onClick={() => {
                if (confirm(`确定要删除「${person.name}」吗？此操作不可撤销，会同时删除所有关联的关系。`)) {
                  onDelete(person.id);
                  onClose();
                }
              }}
              className="px-3 py-1 text-sm bg-red-50 text-red-600 rounded-lg hover:bg-red-100">
              🗑️ 删除
            </button>
          )}
          <button onClick={onClose} className="p-2 hover:bg-gray-200 rounded-lg">
            <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Tab 栏 */}
      <div className="flex border-b border-gray-200 px-6">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => { setActiveTab(tab.key); setIsEditing(false); }}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <svg className="animate-spin h-8 w-8 text-primary-500" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
          </div>
        ) : (
          <>
            {/* === 基本信息 Tab === */}
            {activeTab === 'info' && (
              <div className="max-w-lg space-y-4">
                {isEditing ? (
                  <>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm text-gray-600">姓名</label>
                        <input type="text" value={editData.name || ''} onChange={(e) => setEditData({...editData, name: e.target.value})}
                          className="w-full px-3 py-2 border rounded-lg text-sm mt-1"/>
                      </div>
                      <div>
                        <label className="text-sm text-gray-600">性别</label>
                        <select value={editData.gender || 'unknown'} onChange={(e) => setEditData({...editData, gender: e.target.value as any})}
                          className="w-full px-3 py-2 border rounded-lg text-sm mt-1">
                          <option value="male">男</option>
                          <option value="female">女</option>
                          <option value="unknown">未知</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-sm text-gray-600">出生日期</label>
                        <input type="text" value={editData.birth_date || ''} onChange={(e) => setEditData({...editData, birth_date: e.target.value})}
                          placeholder="1980 或 1980-12-08" className="w-full px-3 py-2 border rounded-lg text-sm mt-1"/>
                      </div>
                      <div>
                        <label className="text-sm text-gray-600">去世日期</label>
                        <input type="text" value={editData.death_date || ''} onChange={(e) => setEditData({...editData, death_date: e.target.value})}
                          className="w-full px-3 py-2 border rounded-lg text-sm mt-1"/>
                      </div>
                      <div>
                        <label className="text-sm text-gray-600">出生地</label>
                        <input type="text" value={editData.birth_place || ''} onChange={(e) => setEditData({...editData, birth_place: e.target.value})}
                          className="w-full px-3 py-2 border rounded-lg text-sm mt-1"/>
                      </div>
                      <div>
                        <label className="text-sm text-gray-600">现居地</label>
                        <input type="text" value={editData.current_residence || ''} onChange={(e) => setEditData({...editData, current_residence: e.target.value})}
                          className="w-full px-3 py-2 border rounded-lg text-sm mt-1"/>
                      </div>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">备注</label>
                      <textarea value={editData.notes || ''} onChange={(e) => setEditData({...editData, notes: e.target.value})}
                        className="w-full px-3 py-2 border rounded-lg text-sm mt-1 h-20 resize-none"/>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={handleSavePerson} disabled={saving}
                        className="flex-1 py-2 bg-primary-600 text-white rounded-lg text-sm disabled:bg-gray-300">
                        {saving ? '保存中...' : '💾 保存修改'}
                      </button>
                      <button onClick={() => { setIsEditing(false); setEditData(details?.person || {}); }}
                        className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm">取消</button>
                    </div>
                  </>
                ) : (
                  <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                    <InfoRow label="姓名" value={person.name} />
                    <InfoRow label="性别" value={person.gender === 'male' ? '男' : person.gender === 'female' ? '女' : '未知'} />
                    <InfoRow label="出生日期" value={person.birth_date || '未知'} />
                    {person.death_date && <InfoRow label="去世日期" value={person.death_date} />}
                    {person.birth_place && <InfoRow label="出生地" value={person.birth_place} />}
                    {person.current_residence && <InfoRow label="现居地" value={person.current_residence} />}
                    {person.notes && <InfoRow label="备注" value={person.notes} />}
                    {person.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {person.tags.map((t, i) => (
                          <span key={i} className="text-xs bg-primary-100 text-primary-700 px-2 py-0.5 rounded-full">{t}</span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* === 时间线 Tab === */}
            {activeTab === 'timeline' && (
              <div className="max-w-lg space-y-6">
                {/* 事件时间线 */}
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-3">📅 人生事件</h4>
                  {details && details.events.length > 0 ? (
                    <div className="relative">
                      <div className="absolute left-3 top-0 bottom-0 w-0.5 bg-gray-200"/>
                      <div className="space-y-4">
                        {details.events.sort((a, b) => (a.date || '').localeCompare(b.date || '')).map((event, i) => (
                          <div key={i} className="relative pl-8">
                            <div className="absolute left-1.5 top-1 w-3 h-3 bg-primary-500 rounded-full border-2 border-white"/>
                            <div className="bg-gray-50 rounded-lg p-3">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs px-2 py-0.5 bg-primary-100 text-primary-700 rounded">
                                  {EVENT_LABELS[event.type] || event.type}
                                </span>
                                <span className="text-xs text-gray-500">{event.date || '日期未知'}</span>
                              </div>
                              <p className="text-sm text-gray-800">{event.description}</p>
                              {event.location && <p className="text-xs text-gray-500 mt-1">📍 {event.location}</p>}
                              {event.participants.length > 0 && (
                                <p className="text-xs text-gray-500 mt-1">
                                  {event.participants.map(p => `${getPersonName(p.person_id)}(${p.role})`).join('、')}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 text-center py-4">暂无事件记录</p>
                  )}
                </div>

                {/* 编辑历史 */}
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-3">📝 编辑历史</h4>
                  {loadingHistory ? (
                    <div className="flex justify-center py-4">
                      <svg className="animate-spin h-5 w-5 text-gray-400" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                      </svg>
                    </div>
                  ) : editHistory.length > 0 ? (
                    <div className="space-y-2">
                      {editHistory.map((h, i) => (
                        <div key={i} className="bg-gray-50 rounded-lg p-3 text-xs">
                          <div className="flex items-center justify-between mb-1">
                            <span className={`px-1.5 py-0.5 rounded font-medium ${
                              h.action === 'create_person' ? 'bg-green-100 text-green-700' :
                              h.action === 'update_person' ? 'bg-blue-100 text-blue-700' :
                              h.action === 'merge' ? 'bg-purple-100 text-purple-700' :
                              h.action === 'delete_person' ? 'bg-red-100 text-red-700' :
                              'bg-gray-100 text-gray-600'
                            }`}>
                              {h.action === 'create_person' ? '新增' :
                               h.action === 'update_person' ? '更新' :
                               h.action === 'merge' ? '合并' :
                               h.action === 'delete_person' ? '删除' :
                               h.action === 'auto_import' ? '导入' : h.action}
                            </span>
                            <span className="text-gray-400">
                              {new Date(h.timestamp).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                          <p className="text-gray-600">{h.summary}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-400 text-center py-4">暂无编辑记录</p>
                  )}
                </div>
              </div>
            )}

            {/* === 关系网络 Tab === */}
            {activeTab === 'relations' && (
              <div className="max-w-lg space-y-2">
                {details && details.relationships.filter(rel => {
                  const otherId = rel.person1_id === person.id ? rel.person2_id : rel.person1_id;
                  const otherPerson = allPeople.find(p => p.id === otherId);
                  return !otherPerson?.is_placeholder;
                }).length > 0 ? (
                  details.relationships.filter(rel => {
                    const otherId = rel.person1_id === person.id ? rel.person2_id : rel.person1_id;
                    const otherPerson = allPeople.find(p => p.id === otherId);
                    return !otherPerson?.is_placeholder;
                  }).map((rel, i) => {
                    const isSource = rel.person1_id === person.id;
                    const otherId = isSource ? rel.person2_id : rel.person1_id;
                    const otherName = getPersonName(otherId);
                    const otherGender = getPersonGender(otherId);
                    const icon = otherGender === 'male' ? '👨' : otherGender === 'female' ? '👩' : '👤';

                    return (
                      <div key={i} className="bg-gray-50 rounded-lg p-3 flex items-center justify-between"
                           style={rel.type === 'step_parent_child' ? { border: '1.5px dashed #d1d5db', background: 'rgba(249,250,251,0.6)' } : {}}>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            rel.type === 'step_parent_child'
                              ? 'bg-gray-100 text-gray-500 border border-dashed border-gray-300'
                              : rel.type === 'sibling'
                              ? 'bg-green-100 text-green-700'
                              : rel.type === 'parent_child'
                              ? 'bg-blue-100 text-blue-700'
                              : rel.type === 'spouse'
                              ? 'bg-pink-100 text-pink-700'
                              : 'bg-blue-100 text-blue-700'
                          }`}>
                            {rel.type === 'sibling'
                              ? getSiblingLabel(person.gender, otherGender)
                              : RELATIONSHIP_LABELS[rel.type] || rel.type}
                          </span>
                          <span>{icon}</span>
                          <span className="text-sm font-medium">{otherName}</span>
                        </div>
                        <button onClick={() => handleDeleteRelationship(rel.id)}
                          className="text-xs text-red-500 hover:text-red-700 px-2 py-1 hover:bg-red-50 rounded">
                          🗑️
                        </button>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-sm text-gray-500 text-center py-8">暂无关系记录</p>
                )}
              </div>
            )}

            {/* === 生平故事 Tab === */}
            {activeTab === 'story' && (
              <div className="max-w-lg space-y-3">
                <button
                  onClick={handleRegenerateBiography}
                  className="w-full py-2 bg-blue-50 text-blue-700 rounded-lg text-sm hover:bg-blue-100 font-medium">
                  🔄 根据关系和事件自动生成传记
                </button>
                {/* 自动生成的传记（可读版本） */}
                {details?.person.story && (
                  <div className="bg-gray-50 rounded-lg p-3 border border-gray-200">
                    <p className="text-xs text-gray-400 mb-2">📖 自动生成传记</p>
                    {resolveStoryRefs(details.person.story, allPeople).split('\n').filter(l => l.trim()).map((line, i) => (
                      <p key={i} className="text-sm text-gray-700 leading-relaxed">
                        {line}
                      </p>
                    ))}
                  </div>
                )}
                <StoryEditor
                  story={details?.person.story}
                  personName={person.name}
                  onSave={handleStorySave}
                />
              </div>
            )}

            {/* === 添加 Tab === */}
            {activeTab === 'add' && (
              <div className="max-w-lg space-y-6">
                {/* 添加关系 */}
                <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                  <h4 className="font-medium text-gray-800">🔗 添加关系</h4>
                  <div>
                    <label className="text-sm text-gray-600">关系类型</label>
                    <select value={newRelType} onChange={(e) => setNewRelType(e.target.value)}
                      className="w-full px-3 py-2 border rounded-lg text-sm mt-1">
                      {Object.entries(RELATIONSHIP_LABELS).map(([k, v]) => (
                        <option key={k} value={k}>{v}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">对象人物</label>
                    <div className="mt-1">
                      <PersonPicker
                        people={allPeople}
                        selectedId={newRelTarget?.id}
                        onSelect={setNewRelTarget}
                        placeholder="搜索选择..."
                        excludeIds={[person.id]}
                      />
                    </div>
                  </div>
                  <button onClick={handleAddRelationship} disabled={!newRelTarget}
                    className="w-full py-2 bg-blue-600 text-white rounded-lg text-sm disabled:bg-gray-300 hover:bg-blue-700">
                    🔗 确认添加关系
                  </button>
                </div>

                {/* 添加事件 */}
                <div>
                  {showEventForm ? (
                    <EventForm
                      people={allPeople}
                      onSave={handleAddEvent}
                      onCancel={() => setShowEventForm(false)}
                    />
                  ) : (
                    <button onClick={() => setShowEventForm(true)}
                      className="w-full py-3 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 text-sm font-medium">
                      📅 添加事件
                    </button>
                  )}
                </div>


              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

const InfoRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="flex justify-between text-sm">
    <span className="text-gray-500">{label}</span>
    <span className="text-gray-800">{value}</span>
  </div>
);

export default PersonDetail;
