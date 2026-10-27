import React from 'react';
import type { RobotState } from '../types/telemetry';
import {
  Play,
  Pause,
  RotateCcw,
  Square,
  StepForward,
  Gauge,
} from 'lucide-react';

interface MissionControlsProps {
  state: RobotState;
  speed: number;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onReset: () => void;
  onStep: () => void;
  onSpeedChange: (speed: number) => void;
}

export const MissionControls: React.FC<MissionControlsProps> = ({
  state,
  speed,
  onStart,
  onPause,
  onResume,
  onStop,
  onReset,
  onStep,
  onSpeedChange,
}) => {
  const isRunning = state === 'MOVING' || state === 'PLANNING' || state === 'EXECUTING_TASK' || state === 'AVOIDING_OBSTACLE';
  const isPaused = state === 'PAUSED';

  return (
    <div className="glass-panel" style={{ padding: '14px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        
        {/* Playback Button Group */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {!isRunning && !isPaused ? (
            <button
              onClick={onStart}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                padding: '8px 16px',
                fontSize: '0.85rem',
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 0 16px rgba(16, 185, 129, 0.4)',
              }}
            >
              <Play size={15} fill="#ffffff" />
              <span>START MISSION</span>
            </button>
          ) : isPaused ? (
            <button
              onClick={onResume}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                padding: '8px 16px',
                fontSize: '0.85rem',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              <Play size={15} fill="#ffffff" />
              <span>RESUME</span>
            </button>
          ) : (
            <button
              onClick={onPause}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: 'rgba(245, 158, 11, 0.2)',
                color: '#fcd34d',
                border: '1px solid #f59e0b',
                borderRadius: '8px',
                padding: '8px 16px',
                fontSize: '0.85rem',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              <Pause size={15} />
              <span>PAUSE</span>
            </button>
          )}

          <button
            onClick={onStop}
            disabled={state === 'IDLE' || state === 'COMPLETED'}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(239, 68, 68, 0.15)',
              color: '#fca5a5',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              borderRadius: '8px',
              padding: '8px 14px',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: state === 'IDLE' || state === 'COMPLETED' ? 'not-allowed' : 'pointer',
              opacity: state === 'IDLE' || state === 'COMPLETED' ? 0.4 : 1,
            }}
          >
            <Square size={14} />
            <span>STOP</span>
          </button>

          <button
            onClick={onReset}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(255, 255, 255, 0.06)',
              color: '#e2e8f0',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: '8px',
              padding: '8px 14px',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={14} />
            <span>RESET</span>
          </button>

          {/* Single Step Tick (Crucial for Viva Defense Demonstration!) */}
          <button
            onClick={onStep}
            title="Single-step simulation tick for demonstrating state transitions"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(99, 102, 241, 0.15)',
              color: '#a5b4fc',
              border: '1px solid rgba(99, 102, 241, 0.4)',
              borderRadius: '8px',
              padding: '8px 14px',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <StepForward size={15} />
            <span>STEP TICK</span>
          </button>
        </div>

        {/* Simulation Speed Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Gauge size={16} color="#9ca3af" />
          <span style={{ fontSize: '0.78rem', color: '#9ca3af', fontWeight: 600 }}>Speed:</span>
          {[0.5, 1.0, 2.0, 5.0].map((s) => (
            <button
              key={s}
              onClick={() => onSpeedChange(s)}
              style={{
                padding: '4px 8px',
                borderRadius: '6px',
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                background: speed === s ? '#10b981' : 'rgba(255, 255, 255, 0.06)',
                color: speed === s ? '#ffffff' : '#9ca3af',
                border: speed === s ? '1px solid #34d399' : '1px solid rgba(255, 255, 255, 0.1)',
                cursor: 'pointer',
              }}
            >
              {s}x
            </button>
          ))}
        </div>

      </div>
    </div>
  );
};
