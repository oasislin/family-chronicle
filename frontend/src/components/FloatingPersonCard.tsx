import React from 'react';
import { Person } from '../types';

interface FloatingPersonCardProps {
  person: Person;
  relationshipCount: number;
  onOpenDetail: () => void;
  onClose: () => void;
}

const GENDER_STYLES: Record<string, { accent: string; bg: string; border: string; prefix: string }> = {
  male: { accent: '#3b82f6', bg: 'rgba(219,234,254,0.92)', border: '#93c5fd', prefix: '♂' },
  female: { accent: '#ec4899', bg: 'rgba(252,231,243,0.92)', border: '#f9a8d4', prefix: '♀' },
  unknown: { accent: '#9ca3af', bg: 'rgba(243,244,246,0.92)', border: '#d1d5db', prefix: '' },
};

const FloatingPersonCard: React.FC<FloatingPersonCardProps> = ({
  person,
  relationshipCount,
  onOpenDetail,
  onClose,
}) => {
  const style = GENDER_STYLES[person.gender] || GENDER_STYLES.unknown;
  const isDeceased = !!person.death_date;
  const hasConfirmTag = person.tags?.includes('待确认');

  const lifeStr = [person.birth_date, person.death_date]
    .filter(Boolean)
    .join(' → ') || null;

  return (
    <div
      className="fixed bottom-24 left-1/2 -translate-x-1/2 z-30 animate-slide-up"
      style={{
        animation: 'slideUp 0.2s ease-out',
      }}
    >
      <style>{`
        @keyframes slideUp {
          from { opacity: 0; transform: translate(-50%, 12px); }
          to { opacity: 1; transform: translate(-50%, 0); }
        }
      `}</style>

      <div
        className="relative flex items-center gap-3 px-4 py-2.5 rounded-2xl shadow-lg"
        style={{
          background: style.bg,
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          border: `1.5px solid ${style.border}`,
          boxShadow: `0 4px 24px ${style.accent}20, 0 1px 6px rgba(0,0,0,0.08)`,
          minWidth: 240,
          maxWidth: 360,
        }}
      >
        {/* 关闭按钮 */}
        <button
          onClick={onClose}
          className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-white shadow text-gray-400 hover:text-gray-600 text-xs flex items-center justify-center"
        >
          ✕
        </button>

        {/* 头像 */}
        <div
          className="w-10 h-10 rounded-full overflow-hidden flex-shrink-0"
          style={{
            border: `2px solid ${style.accent}`,
            boxShadow: `0 2px 8px ${style.accent}30`,
          }}
        >
          <img
            src={`https://api.dicebear.com/9.x/avataaars/svg?seed=${person.id}&backgroundColor=${person.gender === 'male' ? 'b6e3f4' : person.gender === 'female' ? 'ffd5dc' : 'd1d4f9'}`}
            alt={person.name}
            className="w-full h-full"
            style={{ objectFit: 'cover', objectPosition: 'center 15%' }}
            onError={(e) => {
              const el = e.target as HTMLImageElement;
              el.parentElement!.innerHTML = `<div class="w-full h-full flex items-center justify-center text-sm font-bold" style="color:${style.accent}">${person.name[0]}</div>`;
            }}
          />
        </div>

        {/* 信息 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-semibold text-gray-800 truncate">
              {isDeceased ? '✝ ' : ''}{style.prefix} {person.name}
            </span>
            {hasConfirmTag && (
              <span className="text-[9px] px-1.5 py-0.5 bg-amber-100 text-amber-600 rounded-full flex-shrink-0">
                待确认
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            {lifeStr && (
              <span className="text-[11px] text-gray-500">{lifeStr}</span>
            )}
            <span className="text-[11px] text-gray-400">
              {relationshipCount} 条关系
            </span>
          </div>
        </div>

        {/* 查看详情按钮 */}
        <button
          onClick={onOpenDetail}
          className="flex-shrink-0 px-3 py-1.5 rounded-xl text-[11px] font-medium text-white transition-all hover:shadow-md active:scale-95"
          style={{
            background: `linear-gradient(135deg, ${style.accent}, ${style.accent}cc)`,
          }}
        >
          详情 →
        </button>
      </div>
    </div>
  );
};

export default FloatingPersonCard;
