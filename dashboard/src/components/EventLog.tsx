import React from 'react';
import type { SimulationEvent } from '../types/telemetry';
import { Terminal, Clock } from 'lucide-react';

interface EventLogProps {
  events: SimulationEvent[];
}

export const EventLog: React.FC<EventLogProps> = ({ events }) => {
  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    return d.toTimeString().split(' ')[0] + '.' + Math.floor(d.getMilliseconds() / 100);
  };

  const getOutcomeStyle = (outcome: string) => {
    if (outcome === 'SUCCESS' || outcome === 'RESUMED') {
      return { bg: 'rgba(16, 185, 129, 0.2)', text: '#34d399' };
    }
    if (outcome === 'OBSTACLE_AVOIDANCE' || outcome === 'PAUSED' || outcome === 'FAILED') {
      return { bg: 'rgba(245, 158, 11, 0.2)', text: '#f59e0b' };
    }
    if (outcome === 'STOPPED' || outcome === 'UNREACHABLE') {
      return { bg: 'rgba(239, 68, 68, 0.2)', text: '#ef4444' };
    }
    return { bg: 'rgba(255, 255, 255, 0.1)', text: '#9ca3af' };
  };

  return (
    <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={18} color="#34d399" />
          <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#f3f4f6' }}>
            Mission Audit Event Log
          </h3>
        </div>
        <span className="mono-badge" style={{ background: 'rgba(255, 255, 255, 0.08)', color: '#9ca3af' }}>
          Live Log Stream
        </span>
      </div>

      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          maxHeight: '240px',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.73rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
        }}
      >
        {events.length === 0 ? (
          <p style={{ color: '#6b7280' }}>Waiting for simulation events...</p>
        ) : (
          events.map((evt, idx) => {
            const outcomeStyle = getOutcomeStyle(evt.outcome);
            return (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  padding: '6px 8px',
                  borderRadius: '4px',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid rgba(255, 255, 255, 0.04)',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                  <Clock size={11} color="#6b7280" style={{ marginTop: '2px', flexShrink: 0 }} />
                  <span style={{ color: '#6b7280', flexShrink: 0 }}>{formatTime(evt.timestamp)}</span>
                  <span style={{ color: '#e2e8f0' }}>
                    {evt.details?.message || evt.action}
                    {evt.target && <span style={{ color: '#67e8f9' }}> at ({evt.target[0]}, {evt.target[1]})</span>}
                  </span>
                </div>
                <span
                  style={{
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    background: outcomeStyle.bg,
                    color: outcomeStyle.text,
                    flexShrink: 0,
                  }}
                >
                  {evt.outcome}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
