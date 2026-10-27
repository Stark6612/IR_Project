import React from 'react';
import type { TaskItem } from '../types/telemetry';
import { ListOrdered, CheckCircle2, Droplets, Search, Sparkles } from 'lucide-react';

interface TaskQueueHUDProps {
  tasks: TaskItem[];
}

export const TaskQueueHUD: React.FC<TaskQueueHUDProps> = ({ tasks }) => {
  const getActionIcon = (action: string) => {
    switch (action) {
      case 'watering':
        return <Droplets size={14} color="#38bdf8" />;
      case 'plant_inspection':
        return <Search size={14} color="#f59e0b" />;
      case 'weed_clearing':
        return <Sparkles size={14} color="#c084fc" />;
      default:
        return <ListOrdered size={14} color="#9ca3af" />;
    }
  };

  const completedCount = tasks.filter((t) => t.completed).length;

  return (
    <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ListOrdered size={18} color="#34d399" />
          <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#f3f4f6' }}>
            Mission Priority Queue
          </h3>
        </div>
        <span className="mono-badge" style={{ background: 'rgba(52, 211, 153, 0.15)', color: '#34d399' }}>
          {completedCount}/{tasks.length} Done
        </span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', maxHeight: '240px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {tasks.length === 0 ? (
          <p style={{ fontSize: '0.75rem', color: '#6b7280' }}>No tasks scheduled.</p>
        ) : (
          tasks.map((task) => (
            <div
              key={task.task_id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 10px',
                borderRadius: '6px',
                background: task.active
                  ? 'rgba(16, 185, 129, 0.15)'
                  : task.completed
                  ? 'rgba(0, 0, 0, 0.2)'
                  : 'rgba(255, 255, 255, 0.03)',
                border: task.active
                  ? '1px solid #10b981'
                  : '1px solid rgba(255, 255, 255, 0.05)',
                opacity: task.completed ? 0.5 : 1,
                transition: 'all 0.2s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {getActionIcon(task.action_type)}
                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: task.completed ? '#9ca3af' : '#f3f4f6' }}>
                    {task.description}
                  </div>
                  <div style={{ fontSize: '0.68rem', fontFamily: 'var(--font-mono)', color: '#6b7280' }}>
                    Target: ({task.target[0]}, {task.target[1]}) • Priority: P{task.priority}
                  </div>
                </div>
              </div>

              <div>
                {task.completed ? (
                  <CheckCircle2 size={16} color="#10b981" />
                ) : task.active ? (
                  <span
                    className="mono-badge"
                    style={{ background: 'rgba(16, 185, 129, 0.3)', color: '#34d399', fontSize: '0.65rem' }}
                  >
                    ACTIVE
                  </span>
                ) : (
                  <span
                    className="mono-badge"
                    style={{ background: 'rgba(255, 255, 255, 0.08)', color: '#9ca3af', fontSize: '0.65rem' }}
                  >
                    QUEUED
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
