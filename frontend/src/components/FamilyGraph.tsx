import React, { useMemo, useCallback, useState, useRef, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  NodeTypes,
  Position,
  Handle,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Person, Relationship } from '../types';

// 覆盖 React Flow 节点容器默认样式（去掉外框）
const reactFlowStyleOverride = `
  .react-flow__node-person {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    border-radius: 0 !important;
  }
`;

// DiceBear 头像 URL（免费，无需 API Key，SVG 格式）
// avataaars = 纯面部头像
const avatarUrl = (seed: string, gender: string) => {
  const bg = gender === 'male' ? 'b6e3f4' : gender === 'female' ? 'ffd5dc' : 'd1d4f9';
  return `https://api.dicebear.com/9.x/avataaars/svg?seed=${seed}&backgroundColor=${bg}`;
};

// 性别对应的颜色
const GENDER_COLORS: Record<string, { accent: string; handle: string; gradient: string; glow: string; labelBg: string }> = {
  male: {
    accent: '#3b82f6',
    handle: '#60a5fa',
    gradient: 'from-blue-50/80 to-sky-50/60',
    glow: 'rgba(59,130,246,0.15)',
    labelBg: 'rgba(219,234,254,0.5)',   // blue-100 半透明
  },
  female: {
    accent: '#ec4899',
    handle: '#f472b6',
    gradient: 'from-pink-50/80 to-rose-50/60',
    glow: 'rgba(236,72,153,0.15)',
    labelBg: 'rgba(252,231,243,0.5)',   // pink-100 半透明
  },
  unknown: {
    accent: '#9ca3af',
    handle: '#d1d5db',
    gradient: 'from-gray-50/80 to-slate-50/60',
    glow: 'rgba(156,163,175,0.12)',
    labelBg: 'rgba(243,244,246,0.5)',
  },
};

// 人物节点 — DiceBear 头像 + 性别差异化毛玻璃效果
const PersonNode: React.FC<{ data: Person & { selected?: boolean } }> = ({ data }) => {
  const colors = GENDER_COLORS[data.gender] || GENDER_COLORS.unknown;
  const isDeceased = !!data.death_date;
  const hasConfirmTag = data.tags.includes('待确认');
  const isFemale = data.gender === 'female';
  const isMale = data.gender === 'male';
  const isPlaceholder = data.is_placeholder;

  return (
    <div className="flex flex-col items-center" style={{ 
      width: 96, background: 'transparent', border: 'none', padding: 0,
      opacity: isPlaceholder ? 0.5 : 1,
      filter: isPlaceholder ? 'saturate(0.3)' : 'none',
    }}>
      <Handle type="target" position={Position.Top} id="top"
        className="!w-2.5 !h-2.5 !border-2 !-top-1.5" style={{ background: colors.handle, borderColor: colors.accent }} />

      {/* 头像 — 大圆形，占位节点用虚线边框 */}
      <div
        className={`
          relative w-[68px] h-[68px] rounded-full overflow-hidden cursor-pointer
          transition-all duration-200
          ${data.selected
            ? 'ring-3 ring-yellow-400 shadow-xl scale-110'
            : 'hover:shadow-lg hover:scale-105'}
          ${isDeceased ? 'grayscale opacity-40' : ''}
        `}
        style={{
          border: `${isPlaceholder ? '3px dashed' : isMale ? '3px solid' : isFemale ? '3px dashed' : '2.5px solid'} ${data.selected ? '#facc15' : isPlaceholder ? '#9ca3af' : colors.accent}`,
          boxShadow: data.selected
            ? `0 0 0 2px ${colors.accent}40, 0 4px 16px rgba(0,0,0,0.12)`
            : `0 2px 12px ${colors.glow}, 0 0 0 1px ${colors.accent}15`,
          background: isPlaceholder ? '#f3f4f6' : 'transparent',
        }}
      >
        {isPlaceholder ? (
          <div className="w-full h-full flex items-center justify-center text-2xl">👻</div>
        ) : (
          <img
            src={avatarUrl(data.id, data.gender)}
            alt={data.name}
            className="w-full h-full"
            style={{ objectFit: 'cover', objectPosition: 'center 15%' }}
            loading="lazy"
            onError={(e) => {
              const el = e.target as HTMLImageElement;
              el.parentElement!.innerHTML = `<div class="w-full h-full flex items-center justify-center text-xl font-bold" style="color:${colors.accent}">${data.name[0]}</div>`;
            }}
          />
        )}
      </div>

      {/* 名字 + 信息 — 占位节点显示特殊样式 */}
      <div
        className="relative -mt-1 px-2.5 py-1 rounded-xl text-center min-w-[72px]"
        style={{
          background: isPlaceholder ? 'rgba(243,244,246,0.9)' : colors.labelBg,
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          border: `1px ${isPlaceholder ? 'dashed' : 'solid'} ${isPlaceholder ? '#9ca3af40' : colors.accent}25`,
          boxShadow: `0 1px 8px ${colors.glow}`,
        }}
      >
        <div className={`text-[11px] font-semibold leading-tight truncate ${
          isPlaceholder ? 'text-gray-400 italic' : isDeceased ? 'text-gray-400 line-through' : 'text-gray-700'
        }`}>
          {isPlaceholder ? '👻 ' : isDeceased ? '✝ ' : ''}{isMale ? '♂ ' : isFemale ? '♀ ' : ''}{data.name}
        </div>
        {isPlaceholder && data.placeholder_reason && (
          <div className="text-[8px] text-gray-400 leading-tight mt-0.5 truncate" title={data.placeholder_reason}>
            占位
          </div>
        )}
        {data.birth_date && !isPlaceholder && (
          <div className="text-[9px] text-gray-400 leading-tight mt-0.5">{data.birth_date}</div>
        )}
        {hasConfirmTag && !isPlaceholder && (
          <div className="text-[8px] text-amber-500 font-medium leading-tight mt-0.5">待确认</div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} id="bottom"
        className="!w-2.5 !h-2.5 !border-2 !-bottom-1.5" style={{ background: colors.handle, borderColor: colors.accent }} />
    </div>
  );
};

const nodeTypes: NodeTypes = { person: PersonNode };

// 关系类型样式
const EDGE_STYLES: Record<string, { color: string; label: string; dashed?: boolean }> = {
  parent_child: { color: '#0ea5e9', label: '亲子' },
  spouse: { color: '#ec4899', label: '配偶', dashed: true },
  sibling: { color: '#10b981', label: '兄弟姐妹' },
  step_parent_child: { color: '#94a3b8', label: '继亲', dashed: true },
  grandparent_grandchild: { color: '#8b5cf6', label: '祖孙' },
  cousin: { color: '#14b8a6', label: '表亲' },
  aunt_uncle_niece_nephew: { color: '#06b6d4', label: '叔侄' },
  adopted_parent_child: { color: '#f59e0b', label: '过继' },
  godparent_godchild: { color: '#6366f1', label: '干亲' },
  in_law: { color: '#64748b', label: '姻亲' },
  other: { color: '#94a3b8', label: '其他' },
};

// 箭头标记 — 用于长辈→晚辈的方向指示
const ArrowMarker = () => (
  <svg style={{ position: 'absolute', top: 0, width: 0, height: 0 }}>
    <defs>
      <marker id="arrow-parent" viewBox="0 0 12 12" refX="10" refY="6"
        markerWidth="8" markerHeight="8" orient="auto-start-reverse">
        <path d="M 0 0 L 12 6 L 0 12 z" fill="#0ea5e9" />
      </marker>
      <marker id="arrow-step" viewBox="0 0 12 12" refX="10" refY="6"
        markerWidth="8" markerHeight="8" orient="auto-start-reverse">
        <path d="M 0 0 L 12 6 L 0 12 z" fill="#94a3b8" />
      </marker>
      <marker id="arrow-grandparent" viewBox="0 0 12 12" refX="10" refY="6"
        markerWidth="8" markerHeight="8" orient="auto-start-reverse">
        <path d="M 0 0 L 12 6 L 0 12 z" fill="#8b5cf6" />
      </marker>
    </defs>
  </svg>
);

interface FamilyGraphProps {
  people: Person[];
  relationships: Relationship[];
  onPersonClick?: (person: Person | null) => void;
  onPersonDoubleClick?: (person: Person) => void;
  selectedPersonId?: string;
}

const FamilyGraphView: React.FC<FamilyGraphProps> = ({
  people,
  relationships,
  onPersonClick,
  onPersonDoubleClick,
  selectedPersonId,
}) => {
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [showInferred, setShowInferred] = useState<boolean>(true);
  const [displayDepth, setDisplayDepth] = useState<number>(1); // 默认显示 1 层
  const [isFocusMode, setIsFocusMode] = useState<boolean>(false); // 默认全量显示，开启后聚焦选中人

  // 持久化节点位置 — 不随数据更新而重置
  const positionsRef = useRef<Record<string, { x: number; y: number }>>({});
  const [layoutKey, setLayoutKey] = useState(0); // 手动重置时递增

  // 为新节点分配位置（网格），已有节点保持原位
  const ensurePositions = useCallback(() => {
    const positions = positionsRef.current;
    const existingIds = new Set(Object.keys(positions));
    const newPeople = people.filter(p => !existingIds.has(p.id));

    if (newPeople.length === 0 && layoutKey === 0) return; // 没有新节点，不需要更新

    // 如果是手动重置（layoutKey > 0），全部重新计算
    if (layoutKey > 0 || Object.keys(positions).length === 0) {
      const cols = Math.ceil(Math.sqrt(people.length || 1));
      const newPositions: Record<string, { x: number; y: number }> = {};
      people.forEach((person, index) => {
        const row = Math.floor(index / cols);
        const col = index % cols;
        newPositions[person.id] = { x: col * 120 + 60, y: row * 140 + 40 };
      });
      positionsRef.current = newPositions;
    } else {
      // 只为新节点分配位置：放在现有节点的下方
      const existingPositions = Object.values(positions);
      const maxY = existingPositions.length > 0 ? Math.max(...existingPositions.map(p => p.y)) : 0;
      const cols = Math.ceil(Math.sqrt(people.length || 1));
      newPeople.forEach((person, index) => {
        const row = Math.floor(index / cols);
        const col = index % cols;
        positions[person.id] = { x: col * 120 + 60, y: maxY + 140 + row * 140 };
      });
    }
  }, [people, layoutKey]);

  ensurePositions();

  // 关系类型筛选
  const relTypes = useMemo(() => {
    const types = new Set(relationships.map((r) => r.type));
    return ['all', ...Array.from(types)];
  }, [relationships]);

  // 计算距离选中人的距离 (BFS)
  const distances = useMemo(() => {
    if (!selectedPersonId || !isFocusMode) return null;
    const dists: Record<string, number> = { [selectedPersonId]: 0 };
    const queue = [selectedPersonId];
    
    while (queue.length > 0) {
      const currId = queue.shift()!;
      const d = dists[currId];
      if (d >= displayDepth) continue;

      // 查找所有邻居（不分显式推导）
      relationships.forEach(rel => {
        let neighborId: string | null = null;
        if (rel.person1_id === currId) neighborId = rel.person2_id;
        else if (rel.person2_id === currId) neighborId = rel.person1_id;

        if (neighborId && dists[neighborId] === undefined) {
          dists[neighborId] = d + 1;
          queue.push(neighborId);
        }
      });
    }
    return dists;
  }, [selectedPersonId, relationships, displayDepth, isFocusMode]);

  const filteredPeople = useMemo(() => {
    if (!isFocusMode || !distances) return people;
    return people.filter(p => distances[p.id] !== undefined);
  }, [people, distances, isFocusMode]);

  const filteredRelationships = useMemo(() => {
    let result = relationships;
    if (!showInferred) {
      result = result.filter(r => !r.is_inferred);
    }
    if (activeFilter !== 'all') {
      result = result.filter((r) => r.type === activeFilter);
    }
    if (isFocusMode && distances) {
      result = result.filter(r => distances[r.person1_id] !== undefined && distances[r.person2_id] !== undefined);
    }
    return result;
  }, [relationships, activeFilter, showInferred, isFocusMode, distances]);

  // 节点 — 使用持久化位置
  const buildNodes = useCallback((): Node[] => {
    const positions = positionsRef.current;
    return filteredPeople.map((person) => ({
      id: person.id,
      type: 'person',
      position: positions[person.id] || { x: 0, y: 0 },
      data: { ...person, selected: person.id === selectedPersonId },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
    }));
  }, [filteredPeople, selectedPersonId]);

  // 边 — 根据选中人物高亮连接的关系
  const initialEdges: Edge[] = useMemo(() => {
    // 找出与选中人物关联的关系ID
    const connectedRelIds = new Set<string>();
    if (selectedPersonId) {
      filteredRelationships.forEach((rel) => {
        if (rel.person1_id === selectedPersonId || rel.person2_id === selectedPersonId) {
          connectedRelIds.add(rel.id);
        }
      });
    }
    const hasSelection = selectedPersonId && connectedRelIds.size > 0;

    return filteredRelationships.map((rel) => {
      const style = EDGE_STYLES[rel.type] || EDGE_STYLES.other;
      const isConnected = connectedRelIds.has(rel.id);

      // 选中人物时：关联边高亮，其他边变暗
      // 未选中时：推导边（is_inferred）变暗
      const strokeWidth = hasSelection ? (isConnected ? 3 : 1) : (rel.is_inferred ? 1 : 1.5);
      const opacity = hasSelection 
        ? (isConnected ? 1 : 0.05) 
        : (rel.is_inferred ? 0.3 : 0.7);
      const animated: boolean = rel.type === 'spouse' || (!!hasSelection && isConnected);

      // 箭头标记 — 长辈→晚辈方向
      const markerEnd = rel.type === 'parent_child'
        ? 'url(#arrow-parent)'
        : rel.type === 'step_parent_child'
        ? 'url(#arrow-step)'
        : rel.type === 'grandparent_grandchild'
        ? 'url(#arrow-grandparent)'
        : undefined;

      return {
        id: rel.id,
        source: rel.person1_id,
        target: rel.person2_id,
        sourceHandle: 'bottom',
        targetHandle: 'top',
        label: style.label,
        type: 'smoothstep',
        markerEnd,
        style: {
          stroke: style.color,
          strokeWidth,
          strokeDasharray: style.dashed ? '4,4' : undefined,
          opacity,
        },
        animated,
        labelStyle: {
          fill: style.color,
          fontSize: 9,
          fontWeight: isConnected && hasSelection ? 700 : 400,
          opacity: hasSelection 
            ? (isConnected ? 1 : 0.15) 
            : (rel.is_inferred ? 0.4 : 1),
        },
        labelBgStyle: { fill: '#fafafa', fillOpacity: hasSelection ? (isConnected ? 0.95 : 0.3) : 0.85 },
        labelBgPadding: [4, 2] as [number, number],
        labelBgBorderRadius: 3,
      };
    });
  }, [filteredRelationships, selectedPersonId]);

  const [nodes, setNodes, onNodesChange] = useNodesState(buildNodes());
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // 数据变化时：只更新节点数据（保留位置），边正常重建
  useEffect(() => {
    const currentNodes = buildNodes();
    setNodes((prevNodes) => {
      // 保留用户拖动后的位置
      const posMap = new Map(prevNodes.map(n => [n.id, n.position]));
      return currentNodes.map(n => ({
        ...n,
        position: posMap.get(n.id) || n.position,
      }));
    });
    setEdges(initialEdges);

    // 清理已删除人物的位置
    const currentIds = new Set(people.map(p => p.id));
    Object.keys(positionsRef.current).forEach(id => {
      if (!currentIds.has(id)) delete positionsRef.current[id];
    });
  }, [filteredPeople, initialEdges, setNodes, setEdges, people]);

  const resetLayout = useCallback(() => {
    setLayoutKey(k => k + 1);
  }, []);

  // layoutKey 变化时重新布局
  useEffect(() => {
    if (layoutKey > 0) {
      ensurePositions();
      setNodes(buildNodes());
    }
  }, [layoutKey]);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const person = people.find((p) => p.id === node.id);
      if (person && onPersonClick) {
        onPersonClick(person);
        // 如果开启了聚焦模式，点击新节点时可能需要更新视图
        // 但这里我们主要依赖 App.tsx 传回来的 selectedPersonId
      }
    },
    [people, onPersonClick]
  );

  // 点击空白区域取消选择
  const onPaneClick = useCallback(() => {
    if (onPersonClick) onPersonClick(null);
  }, [onPersonClick]);

  // 双击节点 → 打开详情面板
  const onNodeDoubleClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const person = people.find((p) => p.id === node.id);
      if (person && onPersonDoubleClick) onPersonDoubleClick(person);
    },
    [people, onPersonDoubleClick]
  );

  const handleFitView = () => {
    // ReactFlow fitView via instance — simplified
    setNodes((nds) => nds.map((n) => ({ ...n })));
  };

  if (people.length === 0) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-50 rounded-lg">
        <div className="text-center text-gray-400">
          <div className="text-3xl mb-2">🕸️</div>
          <p className="text-sm">暂无图谱数据</p>
          <p className="text-xs mt-1">输入家族故事开始构建</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col">
      <style>{reactFlowStyleOverride}</style>
      {/* 工具栏 — 紧凑 */}
      <div className="px-3 py-1.5 border-b border-gray-200 bg-gray-50 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <button onClick={handleFitView}
            className="px-1.5 py-0.5 text-[10px] bg-white border border-gray-200 rounded hover:bg-gray-50">
            居中
          </button>
          <button onClick={resetLayout}
            className="px-1.5 py-0.5 text-[10px] bg-white border border-gray-200 rounded hover:bg-gray-50">
            重置布局
          </button>
          {/* 关系筛选 */}
          <select
            value={activeFilter}
            onChange={(e) => setActiveFilter(e.target.value)}
            className="text-[10px] px-1.5 py-0.5 bg-white border border-gray-200 rounded"
          >
            <option value="all">全部关系</option>
            {relTypes.filter((t) => t !== 'all').map((t) => (
              <option key={t} value={t}>{EDGE_STYLES[t]?.label || t}</option>
            ))}
          </select>
          {/* 显示推导关系开关 */}
          <label className="flex items-center gap-1 cursor-pointer">
            <input 
              type="checkbox" 
              checked={showInferred} 
              onChange={(e) => setShowInferred(e.target.checked)}
              className="w-3 h-3 rounded"
            />
            <span className="text-[10px] text-gray-600">显示推导关系</span>
          </label>
          <span className="text-gray-300 text-[10px]">|</span>
          {/* 聚焦模式 */}
          <label className="flex items-center gap-1 cursor-pointer">
            <input 
              type="checkbox" 
              checked={isFocusMode} 
              onChange={(e) => setIsFocusMode(e.target.checked)}
              className="w-3 h-3 rounded"
            />
            <span className="text-[10px] text-gray-600 font-medium">聚焦模式</span>
          </label>
          {isFocusMode && (
            <div className="flex items-center gap-1.5 ml-1">
              <span className="text-[10px] text-gray-400">层级:</span>
              <button onClick={() => setDisplayDepth(Math.max(1, displayDepth - 1))}
                className="w-4 h-4 flex items-center justify-center bg-white border border-gray-200 rounded text-[10px]">-</button>
              <span className="text-[10px] font-bold min-w-[8px] text-center">{displayDepth}</span>
              <button onClick={() => setDisplayDepth(Math.min(5, displayDepth + 1))}
                className="w-4 h-4 flex items-center justify-center bg-white border border-gray-200 rounded text-[10px]">+</button>
            </div>
          )}
        </div>
        <span className="text-[10px] text-gray-400">
          {filteredPeople.length}人/{filteredRelationships.length}条
        </span>
      </div>

      {/* 图谱 */}
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          onNodeDoubleClick={onNodeDoubleClick}
          onPaneClick={onPaneClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2, maxZoom: 1.2 }}
          defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
          attributionPosition="bottom-left"
        >
          <ArrowMarker />
          <Controls />
          <MiniMap
            nodeStrokeColor={() => '#0ea5e9'}
            nodeColor={() => '#fff'}
            maskColor="rgba(240, 240, 240, 0.6)"
          />
          <Background color="#aaa" gap={16} />
        </ReactFlow>
      </div>

      {/* 图例 — 紧凑风格 */}
      <div className="px-3 py-1 border-t border-gray-200 bg-gray-50 flex flex-wrap items-center gap-x-3 gap-y-0.5 flex-shrink-0">
        {/* 性别图例 */}
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full border border-blue-400 bg-blue-50" />
          <span className="text-[10px] text-gray-500">男</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-full border border-pink-400 bg-pink-50" />
          <span className="text-[10px] text-gray-500">女</span>
        </div>
        <span className="text-gray-300 text-[10px]">|</span>
        {/* 关系图例 */}
        {Object.entries(EDGE_STYLES).map(([key, style]) => (
          <div key={key} className="flex items-center gap-1">
            <div
              className="w-4 h-[1px]"
              style={{
                backgroundColor: style.color,
                borderTop: style.dashed ? `1px dashed ${style.color}` : `1px solid ${style.color}`,
              }}
            />
            <span className="text-[10px] text-gray-500">{style.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default FamilyGraphView;
