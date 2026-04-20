import React, { useState } from 'react';
import { Event, Person } from '../types';
import PersonPicker from './PersonPicker';

const EVENT_TYPES = [
  { value: 'birth', label: '出生', icon: '👶' },
  { value: 'death', label: '去世', icon: '🕊️' },
  { value: 'marriage', label: '结婚', icon: '💒' },
  { value: 'divorce', label: '离婚', icon: '💔' },
  { value: 'adoption', label: '过继', icon: '📜' },
  { value: 'illness', label: '生病', icon: '🏥' },
  { value: 'relocation', label: '搬家', icon: '🏠' },
  { value: 'education', label: '教育', icon: '🎓' },
  { value: 'career', label: '职业', icon: '💼' },
  { value: 'recognition', label: '认干亲', icon: '🤝' },
  { value: 'other', label: '其他', icon: '📌' },
];

interface EventFormProps {
  people: Person[];
  onSave: (event: Partial<Event>) => void;
  onCancel: () => void;
  initialData?: Partial<Event>;
}

const EventForm: React.FC<EventFormProps> = ({ people, onSave, onCancel, initialData }) => {
  const [type, setType] = useState(initialData?.type || 'other');
  const [description, setDescription] = useState(initialData?.description || '');
  const [date, setDate] = useState(initialData?.date || '');
  const [location, setLocation] = useState(initialData?.location || '');
  const [participants, setParticipants] = useState<Array<{ person_id: string; role: string }>>(
    initialData?.participants || []
  );

  const handleAddParticipant = (person: Person) => {
    if (!participants.find((p) => p.person_id === person.id)) {
      setParticipants([...participants, { person_id: person.id, role: '' }]);
    }
  };

  const handleRemoveParticipant = (personId: string) => {
    setParticipants(participants.filter((p) => p.person_id !== personId));
  };

  const handleUpdateRole = (personId: string, role: string) => {
    setParticipants(
      participants.map((p) => (p.person_id === personId ? { ...p, role } : p))
    );
  };

  const handleSubmit = () => {
    if (!description.trim()) return;
    onSave({
      type,
      description,
      date: date || undefined,
      location: location || undefined,
      participants,
      date_accuracy: date ? (date.length === 4 ? 'year' : 'exact') : 'unknown',
    });
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
      <h4 className="font-medium text-gray-800">
        {initialData ? '编辑事件' : '添加事件'}
      </h4>

      {/* 事件类型 */}
      <div>
        <label className="text-sm text-gray-600 mb-1 block">事件类型</label>
        <div className="flex flex-wrap gap-2">
          {EVENT_TYPES.map((t) => (
            <button
              key={t.value}
              onClick={() => setType(t.value)}
              className={`px-2 py-1 text-xs rounded-full transition-colors ${
                type === t.value
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
              }`}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* 描述 */}
      <div>
        <label className="text-sm text-gray-600 mb-1 block">描述 *</label>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="例：王建国与李梅结婚"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
        />
      </div>

      {/* 日期 & 地点 */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-sm text-gray-600 mb-1 block">日期</label>
          <input
            type="text"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            placeholder="1995 或 1995-09-15"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <div>
          <label className="text-sm text-gray-600 mb-1 block">地点</label>
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="王家村"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      {/* 参与者 */}
      <div>
        <label className="text-sm text-gray-600 mb-1 block">参与者</label>
        <div className="space-y-2">
          {participants.map((p) => {
            const person = people.find((pl) => pl.id === p.person_id);
            return (
              <div key={p.person_id} className="flex items-center gap-2">
                <span className="text-sm text-gray-800 w-20">{person?.name || '未知'}</span>
                <input
                  type="text"
                  value={p.role}
                  onChange={(e) => handleUpdateRole(p.person_id, e.target.value)}
                  placeholder="角色（如：新郎）"
                  className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
                />
                <button
                  onClick={() => handleRemoveParticipant(p.person_id)}
                  className="text-red-500 hover:text-red-700 text-sm"
                >
                  ✕
                </button>
              </div>
            );
          })}
          <PersonPicker
            people={people}
            onSelect={handleAddParticipant}
            placeholder="添加参与者..."
            excludeIds={participants.map((p) => p.person_id)}
          />
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-2 pt-2">
        <button
          onClick={handleSubmit}
          disabled={!description.trim()}
          className="flex-1 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 text-sm"
        >
          💾 保存事件
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
        >
          取消
        </button>
      </div>
    </div>
  );
};

export default EventForm;
