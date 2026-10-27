import React from 'react';
import { telemetryService, type EngineMode } from '../services/telemetryService';
import type { RobotState } from '../types/telemetry';
import {
  Tractor,
  Download,
  FileSpreadsheet,
  Activity,
  Layers,
  Server,
  Cpu,
} from 'lucide-react';

interface HeaderProps {
  mode: EngineMode;
  backendOnline: boolean;
  state: RobotState;
  scenario: string;
  onScenarioChange: (scenario: string) => void;
  onExportJson: () => void;
  onExportCsv: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  mode,
  backendOnline,
  state,
  scenario,
  onScenarioChange,
  onExportJson,
  onExportCsv,
}) => {
  const stateColorMap: Record<RobotState, { bg: string; text: string; border: string }> = {
    IDLE: { bg: 'rgba(107, 114, 128, 0.2)', text: '#9ca3af', border: '#4b5563' },
    PLANNING: { bg: 'rgba(99, 102, 241, 0.2)', text: '#a5b4fc', border: '#6366f1' },
    MOVING: { bg: 'rgba(16, 185, 129, 0.2)', text: '#34d399', border: '#10b981' },
    AVOIDING_OBSTACLE: { bg: 'rgba(239, 68, 68, 0.2)', text: '#fca5a5', border: '#ef4444' },
    EXECUTING_TASK: { bg: 'rgba(245, 158, 11, 0.2)', text: '#fcd34d', border: '#f59e0b' },
    PAUSED: { bg: 'rgba(217, 119, 6, 0.2)', text: '#fbbf24', border: '#d97706' },
    COMPLETED: { bg: 'rgba(52, 211, 153, 0.25)', text: '#6ee7b7', border: '#059669' },
    ERROR: { bg: 'rgba(220, 38, 38, 0.3)', text: '#f87171', border: '#dc2626' },
  };

  const stateStyle = stateColorMap[state] || stateColorMap.IDLE;

  return (
    <header className="glass-panel" style={{ padding: '14px 24px', marginBottom: '18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        
        {/* Logo and Project Branding */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #10b981 0%, #064e3b 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px rgba(16, 185, 129, 0.4)',
            }}
          >
            <Tractor size={24} color="#ffffff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#ffffff' }}>
                AGRI-DOCTOR ROBOT
              </h1>
              <span
                className="mono-badge"
                style={{
                  background: 'rgba(52, 211, 153, 0.15)',
                  color: '#34d399',
                  border: '1px solid rgba(52, 211, 153, 0.3)',
                }}
              >
                v1.0 Windows Native
              </span>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#9ca3af', margin: 0 }}>
              Autonomous 2D Crop Simulation • A* Motion Planning • Kinematics &amp; PID • OpenCV Vision
            </p>
          </div>
        </div>

        {/* Center / Scenario Selector and Mission State */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Scenario Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Layers size={16} color="#9ca3af" />
            <select
              value={scenario}
              onChange={(e) => onScenarioChange(e.target.value)}
              style={{
                background: 'rgba(18, 28, 22, 0.9)',
                color: '#f3f4f6',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '6px 12px',
                fontSize: '0.85rem',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value="mixed_field">Scenario 1: Mixed Field</option>
              <option value="obstacle_challenge">Scenario 2: Obstacle Challenge</option>
              <option value="dry_field">Scenario 3: Dry Field</option>
            </select>
          </div>

          {/* Mission State Indicator */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 12px',
              borderRadius: '20px',
              background: stateStyle.bg,
              border: `1px solid ${stateStyle.border}`,
            }}
          >
            <Activity size={14} color={stateStyle.text} />
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: stateStyle.text, letterSpacing: '0.04em' }}>
              {state}
            </span>
          </div>

          {/* Engine Mode Toggle (Dual-Engine Indicator) */}
          <button
            onClick={() => {
              const nextMode = mode === 'python_server' ? 'standalone_client' : 'python_server';
              telemetryService.setMode(nextMode);
            }}
            title="Click to toggle between Python Server and Standalone In-Browser engine"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '5px 12px',
              borderRadius: '20px',
              background: mode === 'python_server' && backendOnline ? 'rgba(16, 185, 129, 0.15)' : 'rgba(6, 182, 212, 0.15)',
              border: `1px solid ${mode === 'python_server' && backendOnline ? '#10b981' : '#06b6d4'}`,
              color: mode === 'python_server' && backendOnline ? '#34d399' : '#67e8f9',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            {mode === 'python_server' && backendOnline ? (
              <>
                <Server size={13} />
                <span>PYTHON / ROS 2 SERVER</span>
              </>
            ) : (
              <>
                <Cpu size={13} />
                <span>STANDALONE CLIENT ENGINE</span>
              </>
            )}
          </button>
        </div>

        {/* Right / Export Audit Data Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={onExportJson}
            title="Export mission run log and telemetry as JSON"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              color: '#d1d5db',
              borderRadius: '6px',
              padding: '6px 10px',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <Download size={13} />
            <span>JSON</span>
          </button>
          <button
            onClick={onExportCsv}
            title="Export mission event logs as CSV"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              background: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              color: '#34d399',
              borderRadius: '6px',
              padding: '6px 10px',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            <FileSpreadsheet size={13} />
            <span>CSV</span>
          </button>
        </div>

      </div>
    </header>
  );
};
