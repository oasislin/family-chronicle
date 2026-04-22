import React, { useState, useRef, useEffect } from 'react';
import { Person } from '../types';

interface PersonPickerProps {
  people: Person[];
  selectedId?: string;
  onSelect: (person: Person) => void;
  placeholder?: string;
  excludeIds?: string[];
}

const PersonPicker: React.FC<PersonPickerProps> = ({
  people,
  selectedId,
  onSelect,
  placeholder = '搜索选择人物...',
  excludeIds = [],
}) => {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const filtered = people.filter(
    (p) =>
      !p.is_placeholder &&
      !excludeIds.includes(p.id) &&
      (query ? p.name.includes(query) || p.tags.some((t) => t.includes(query)) : true)
  );

  const selected = people.find((p) => p.id === selectedId);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={wrapperRef} className="relative">
      <input
        type="text"
        value={isOpen ? query : selected?.name || ''}
        onChange={(e) => {
          setQuery(e.target.value);
          setIsOpen(true);
        }}
        onFocus={() => {
          setIsOpen(true);
          setQuery('');
        }}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
      />
      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
          {filtered.length > 0 ? (
            filtered.map((person) => (
              <button
                key={person.id}
                onClick={() => {
                  onSelect(person);
                  setIsOpen(false);
                  setQuery('');
                }}
                className="w-full px-3 py-2 text-left hover:bg-gray-50 flex items-center gap-2 text-sm border-b border-gray-100 last:border-0"
              >
                <span>
                  {person.gender === 'male' ? '👨' : person.gender === 'female' ? '👩' : '👤'}
                </span>
                <span>{person.name}</span>
                {person.birth_date && (
                  <span className="text-xs text-gray-400">{person.birth_date}</span>
                )}
              </button>
            ))
          ) : (
            <div className="px-3 py-2 text-sm text-gray-500">无匹配人物</div>
          )}
        </div>
      )}
    </div>
  );
};

export default PersonPicker;
