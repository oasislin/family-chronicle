import React, { useState, useEffect } from 'react';
import { Person } from '../types';

interface PersonSummary {
  person: Person;
  relationship_count: number;
  event_count: number;
  relationships: Array<{ id: string; type: string; other_person_id: string; other_person_name: string }>;
}

interface MergeConfirmDialogProps {
  personA: Person;
  personB: Person;
  familyId: string;
  onConfirm: (keepId: string, removeId: string, customName?: string) => void;
  onCancel: () => void;
}

type ViewMode = 'simple' | 'advanced';

const REL_TYPE_LABELS: Record<string, string> = {
  parent_child: '亲子',
  spouse: '配偶',
  sibling: '兄弟',
  grandparent_grandchild: '祖孙',
  other: '其他',
};

const MergeConfirmDialog: React.FC<MergeConfirmDialogProps> = ({
  personA,
  personB,
  familyId,
  onConfirm,
  onCancel,
}) => {
  const [mode, setMode] = useState<ViewMode>('simple');
  const [preview, setPreview] = useState<{
    primary: PersonSummary;
    secondary: PersonSummary;
    overlap_relationships: string[];
  } | null>(null);
  const [loading, setLoading] = useState(true);

  // 简单模式：默认保留名字更长/更完整的人
  const [keepId, setKeepId] = useState<string>(personA.id);
  const removeId = keepId === personA.id ? personB.id : personA.id;

  // 高级模式：自定义名称
  const [customName, setCustomName] = useState('');
  const [useCustomName, setUseCustomName] = useState(false);

  // 加载预览数据
  useEffect(() => {
    let cancelled = false;
    const loadPreview = async () => {
      try {
        const { mergePreviewApi } = await import('../services/api');
        const res = await mergePreviewApi.run(familyId, personA.id, personB.id);
        if (!cancelled && res.success && res.data) {
          setPreview({
            primary: res.data.primary,
            secondary: res.data.secondary,
            overlap_relationships: res.data.overlap_relationships,
          });
        }
      } catch (e) {
        console.warn('Merge preview failed:', e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadPreview();
    return () => { cancelled = true; };
  }, [familyId, personA.id, personB.id]);

  const handleConfirm = () => {
    const finalName = useCustomName && customName.trim() ? customName.trim() : undefined;
    onConfirm(keepId, removeId, finalName);
  };

  const keepPerson = keepId === personA.id ? personA : personB;
  const dropPerson = keepId === personA.id ? personB : personA;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 pt-5 pb-3 border-b border-gray-100">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">🔀</span>
            <h3 className="text-lg font-bold text-gray-800">合并确认</h3>
          </div>
          <p className="text-sm text-gray-500">
            检测到「{personA.name}」和「{personB.name}」可能是同一人
          </p>
        </div>

        {/* Person Cards */}
        <div className="px-6 py-4">
          <div className="flex gap-3">
            {/* Person A */}
            <PersonCard
              person={personA}
              isKeep={keepId === personA.id}
              onClick={() => setKeepId(personA.id)}
              summary={preview?.primary}
              loading={loading}
            />

            <div className="flex items-center text-xl text-gray-300 self-center">⇄</div>

            {/* Person B */}
            <PersonCard
              person={personB}
              isKeep={keepId === personB.id}
              onClick={() => setKeepId(personB.id)}
              summary={preview?.secondary}
              loading={loading}
            />
          </div>

          {/* Merge result preview */}
          <div className="mt-4 bg-gray-50 rounded-xl p-3">
            <div className="text-xs text-gray-500 mb-2">合并结果预览</div>
            <div className="space-y-1.5 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-gray-400">保留</span>
                <span className="font-medium text-gray-800">{keepPerson.name}</span>
                {useCustomName && customName.trim() && (
                  <>
                    <span className="text-gray-400">→</span>
                    <span className="font-medium text-blue-600">{customName.trim()}</span>
                  </>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400">吸收</span>
                <span className="text-red-500 line-through">{dropPerson.name}</span>
                <span className="text-xs text-gray-400">
                  ({preview ? preview.secondary.relationship_count : '?'}条关系)
                </span>
              </div>
              {preview && preview.overlap_relationships.length > 0 && (
                <div className="flex items-start gap-2">
                  <span className="text-yellow-500">⚠</span>
                  <span className="text-xs text-yellow-700">
                    {preview.overlap_relationships.length} 条重叠关系将自动去重
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Advanced toggle */}
        {mode === 'simple' ? (
          <div className="px-6 pb-2">
            <button
              onClick={() => setMode('advanced')}
              className="text-xs text-gray-400 hover:text-gray-600 underline transition"
            >
              手动编辑 → 自定义名称 / 方向
            </button>
          </div>
        ) : (
          <div className="px-6 pb-4 border-t border-gray-100 pt-3">
            <div className="text-xs font-medium text-gray-600 mb-2">高级选项</div>

            {/* 自定义名称 */}
            <div className="mb-3">
              <label className="flex items-center gap-2 mb-1.5">
                <input
                  type="checkbox"
                  checked={useCustomName}
                  onChange={(e) => setUseCustomName(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <span className="text-sm text-gray-700">合并后使用自定义名称</span>
              </label>
              {useCustomName && (
                <input
                  type="text"
                  value={customName}
                  onChange={(e) => setCustomName(e.target.value)}
                  placeholder={keepPerson.name}
                  className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm
                             focus:ring-2 focus:ring-blue-400 focus:border-transparent"
                  autoFocus
                />
              )}
            </div>

            {/* 关系列表预览 */}
            {preview && (
              <div className="mb-3">
                <div className="text-xs text-gray-500 mb-1">将迁移的关系：</div>
                <div className="max-h-24 overflow-y-auto space-y-0.5">
                  {preview.secondary.relationships.map((r, i) => (
                    <div key={i} className="text-xs text-gray-600 flex justify-between">
                      <span>{r.other_person_name}</span>
                      <span className="text-gray-400">{REL_TYPE_LABELS[r.type] || r.type}</span>
                    </div>
                  ))}
                  {preview.secondary.relationships.length === 0 && (
                    <span className="text-xs text-gray-400">无关系</span>
                  )}
                </div>
              </div>
            )}

            <button
              onClick={() => setMode('simple')}
              className="text-xs text-gray-400 hover:text-gray-600 underline transition"
            >
              ← 返回简单模式
            </button>
          </div>
        )}

        {/* Actions */}
        <div className="px-6 py-4 border-t border-gray-100 flex gap-3">
          <button
            onClick={handleConfirm}
            disabled={loading}
            className="flex-1 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium
                       hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition"
          >
            {loading ? '加载中...' : '确认合并'}
          </button>
          <button
            onClick={onCancel}
            className="px-5 py-2.5 text-gray-500 hover:text-gray-700 text-sm rounded-xl
                       border border-gray-200 hover:bg-gray-50 transition"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
};

// 单个人物卡片
const PersonCard: React.FC<{
  person: Person;
  isKeep: boolean;
  onClick: () => void;
  summary?: PersonSummary;
  loading: boolean;
}> = ({ person, isKeep, onClick, summary, loading }) => {
  const genderBg =
    person.gender === 'male' ? 'bg-blue-500'
    : person.gender === 'female' ? 'bg-pink-500'
    : 'bg-gray-400';

  return (
    <div
      onClick={onClick}
      className={`flex-1 rounded-xl p-3 cursor-pointer transition border-2
        ${isKeep
          ? 'border-blue-400 bg-blue-50 shadow-sm'
          : 'border-gray-200 bg-white hover:border-gray-300'
        }`}
    >
      <div className="text-center">
        {/* Avatar */}
        <div className={`w-10 h-10 rounded-full mx-auto mb-2 flex items-center justify-center
                         text-white text-sm font-bold ${genderBg}`}>
          {person.name[0]}
        </div>

        {/* Name */}
        <div className="font-bold text-gray-800 text-sm">{person.name}</div>

        {/* Birth date */}
        <div className="text-xs text-gray-500 mt-0.5">
          {person.birth_date || '生日未知'}
        </div>

        {/* Stats */}
        {!loading && summary && (
          <div className="flex justify-center gap-3 mt-2">
            <span className="text-xs text-gray-400">
              关系 {summary.relationship_count}
            </span>
            <span className="text-xs text-gray-400">
              事件 {summary.event_count}
            </span>
          </div>
        )}

        {/* Keep indicator */}
        <div className={`text-xs font-medium mt-2 ${isKeep ? 'text-blue-600' : 'text-gray-400'}`}>
          {isKeep ? '← 保留这个' : '点击选择保留'}
        </div>
      </div>
    </div>
  );
};

export default MergeConfirmDialog;
