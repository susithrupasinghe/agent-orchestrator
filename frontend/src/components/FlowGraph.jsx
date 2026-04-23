import React, { useCallback, useMemo } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'

const AGENT_ORDER = ['Orchestrator', 'FrontDesk', 'GitHub', 'Security', 'ClickUp']

const BASE_NODES = [
  { id: 'Orchestrator', data: { label: '🧠 Orchestrator' }, position: { x: 300, y: 20 } },
  { id: 'FrontDesk',    data: { label: '📋 Front Desk' },   position: { x: 80,  y: 160 } },
  { id: 'GitHub',       data: { label: '🐙 GitHub' },       position: { x: 280, y: 160 } },
  { id: 'Security',     data: { label: '🔒 Security' },     position: { x: 480, y: 160 } },
  { id: 'ClickUp',      data: { label: '🎫 ClickUp' },      position: { x: 300, y: 300 } },
]

const BASE_EDGES = [
  { id: 'o-fd', source: 'Orchestrator', target: 'FrontDesk', animated: false },
  { id: 'o-gh', source: 'Orchestrator', target: 'GitHub',    animated: false },
  { id: 'o-se', source: 'Orchestrator', target: 'Security',  animated: false },
  { id: 'o-cu', source: 'Orchestrator', target: 'ClickUp',   animated: false },
  { id: 'fd-o', source: 'FrontDesk', target: 'Orchestrator', animated: false, type: 'step' },
  { id: 'gh-o', source: 'GitHub',    target: 'Orchestrator', animated: false, type: 'step' },
  { id: 'se-o', source: 'Security',  target: 'Orchestrator', animated: false, type: 'step' },
  { id: 'cu-o', source: 'ClickUp',   target: 'Orchestrator', animated: false, type: 'step' },
]

function nodeStyle(agentName, activeAgent, doneAgents) {
  const isDone   = doneAgents.includes(agentName)
  const isActive = activeAgent === agentName

  if (isActive) return { background: '#f59e0b', color: '#1f2937', border: '2px solid #d97706', borderRadius: 8 }
  if (isDone)   return { background: '#10b981', color: '#fff',    border: '2px solid #059669', borderRadius: 8 }
  return { background: '#1e293b', color: '#94a3b8', border: '1px solid #334155', borderRadius: 8 }
}

export default function FlowGraph({ activeAgent, doneAgents = [] }) {
  const nodes = useMemo(
    () =>
      BASE_NODES.map((n) => ({
        ...n,
        style: nodeStyle(n.id, activeAgent, doneAgents),
      })),
    [activeAgent, doneAgents]
  )

  const edges = useMemo(
    () =>
      BASE_EDGES.map((e) => ({
        ...e,
        animated: activeAgent === e.source || activeAgent === e.target,
        style: { stroke: activeAgent === e.source ? '#f59e0b' : '#334155' },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#334155' },
      })),
    [activeAgent]
  )

  const [rfNodes, , onNodesChange] = useNodesState(nodes)
  const [rfEdges, , onEdgesChange] = useEdgesState(edges)

  return (
    <div className="flow-panel">
      <div className="flow-header">
        <h2>Agent Graph</h2>
        <div className="flow-legend">
          <span className="legend-item active">● Active</span>
          <span className="legend-item done">● Done</span>
          <span className="legend-item idle">● Idle</span>
        </div>
      </div>
      <div className="flow-canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          attributionPosition="bottom-right"
        >
          <Background color="#334155" gap={20} />
          <Controls />
          <MiniMap nodeColor={(n) => n.style?.background || '#1e293b'} style={{ background: '#0f172a' }} />
        </ReactFlow>
      </div>
    </div>
  )
}
