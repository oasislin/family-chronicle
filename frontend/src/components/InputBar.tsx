import React, { useState, useRef } from 'react';

interface InputBarProps {
  onSend: (text: string) => void;
  isLoading: boolean;
}

const InputBar: React.FC<InputBarProps> = ({ onSend, isLoading }) => {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    if (!text.trim() || isLoading) return;
    onSend(text.trim());
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    // 自动调整高度
    const el = e.target;
    el.style.height = '44px';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  };

  return (
    <div className="bg-white border-t border-gray-200 px-4 py-3">
      <div className="flex items-end gap-2 max-w-4xl mx-auto">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="输入家族叙事，例如：王建国是家里的老二，1980年出生，后来娶了李梅..."
          disabled={isLoading}
          rows={1}
          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-xl resize-none
                     focus:ring-2 focus:ring-primary-500 focus:border-transparent
                     text-sm leading-relaxed disabled:bg-gray-50"
          style={{ height: '44px', maxHeight: '120px' }}
        />
        <button
          onClick={handleSend}
          disabled={!text.trim() || isLoading}
          className="px-5 py-2.5 bg-primary-600 text-white rounded-xl hover:bg-primary-700
                     disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors
                     flex items-center gap-1.5 text-sm font-medium flex-shrink-0"
          style={{ height: '44px' }}
        >
          {isLoading ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              解析中
            </>
          ) : (
            <>✨ 发送</>
          )}
        </button>
      </div>
      <p className="text-xs text-gray-400 text-center mt-1.5">
        ⌘+Enter 发送 · 支持自然语言描述家族信息
      </p>
    </div>
  );
};

export default InputBar;
