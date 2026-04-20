import React, { useState } from 'react';

interface StoryEditorProps {
  story?: string;
  personName: string;
  onSave: (story: string) => void;
}

const StoryEditor: React.FC<StoryEditorProps> = ({ story, personName, onSave }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(story || '');

  const handleSave = () => {
    onSave(draft);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setDraft(story || '');
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <div className="space-y-3">
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={`记录${personName}的生平故事...&#10;&#10;例如：年轻时读书很好，后来去了县城工作...`}
          className="w-full h-40 p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-primary-500 text-sm leading-relaxed"
          autoFocus
        />
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            className="flex-1 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 text-sm"
          >
            💾 保存
          </button>
          <button
            onClick={handleCancel}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm"
          >
            取消
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {story ? (
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">{story}</p>
        </div>
      ) : (
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-500 italic">暂无生平故事</p>
        </div>
      )}
      <button
        onClick={() => setIsEditing(true)}
        className="w-full py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm transition-colors"
      >
        ✏️ {story ? '编辑故事' : '添加故事'}
      </button>
    </div>
  );
};

export default StoryEditor;
