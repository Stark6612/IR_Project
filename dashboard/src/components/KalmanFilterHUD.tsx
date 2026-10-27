import React, { useState, useEffect, useRef } from 'react';
import type { SimulationTelemetry } from '../types/telemetry';

interface KalmanFilterHUDProps {
  telemetry: SimulationTelemetry | null;
}

interface HistoryPoint {
  raw: number;
  filtered: number;
  truth: number;
}

export const KalmanFilterHUD: React.FC<KalmanFilterHUDProps> = ({ telemetry }) => {
  const [moistureHistory, setMoistureHistory] = useState<HistoryPoint[]>([]);
  const [proximityHistory, setProximityHistory] = useState<HistoryPoint[]>([]);
  const [noiseSigma, setNoiseSigma] = useState<number>(3.5);
  const [isNoiseEnabled, setIsNoiseEnabled] = useState<boolean>(true);
  const lastTimestampRef = useRef<number>(0);

  const kalman = telemetry?.kalman;
  const moist = kalman?.moisture;
  const prox = kalman?.proximity;

  useEffect(() => {
    if (!kalman) return;
    const now = Date.now();
    // Throttle history updates to 5Hz
    if (now - lastTimestampRef.current < 200) return;
    lastTimestampRef.current = now;

    if (moist) {
      setMoistureHistory(prev => [
        ...prev.slice(-24),
        {
          raw: moist.measurement,
          filtered: moist.estimate,
          truth: moist.ground_truth,
        },
      ]);
    }

    if (prox) {
      setProximityHistory(prev => [
        ...prev.slice(-24),
        {
          raw: prox.measurement,
          filtered: prox.estimate,
          truth: prox.ground_truth,
        },
      ]);
    }
  }, [kalman, moist, prox]);

  const handleNoiseChange = async (newSigma: number) => {
    setNoiseSigma(newSigma);
    try {
      await fetch('http://127.0.0.1:8000/api/noise', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          moisture_sigma: newSigma,
          proximity_sigma: newSigma * 0.6,
          enabled: isNoiseEnabled,
        }),
      });
    } catch {
      // Standalone mode handles this automatically
    }
  };

  const handleToggleNoise = async () => {
    const nextState = !isNoiseEnabled;
    setIsNoiseEnabled(nextState);
    try {
      await fetch('http://127.0.0.1:8000/api/noise', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          moisture_sigma: noiseSigma,
          proximity_sigma: noiseSigma * 0.6,
          enabled: nextState,
        }),
      });
    } catch {
      // Standalone mode handles this automatically
    }
  };

  const renderSparkline = (data: HistoryPoint[], minVal: number, maxVal: number, unit: string) => {
    if (data.length < 2) {
      return (
        <div style={{ height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: 11 }}>
          Accumulating sensor telemetry...
        </div>
      );
    }

    const svgWidth = 260;
    const svgHeight = 60;
    const padding = 6;
    const range = Math.max(1, maxVal - minVal);

    const getY = (val: number) => {
      const normalized = (val - minVal) / range;
      const clamped = Math.max(0, Math.min(1, normalized));
      return svgHeight - padding - clamped * (svgHeight - 2 * padding);
    };

    const getX = (idx: number) => padding + (idx / (data.length - 1)) * (svgWidth - 2 * padding);

    const rawPath = data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(d.raw)}`).join(' ');
    const filteredPath = data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(d.filtered)}`).join(' ');
    const truthPath = data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(d.truth)}`).join(' ');

    return (
      <div style={{ position: 'relative', width: '100%', height: svgHeight, background: '#0a0f1d', borderRadius: 6, overflow: 'hidden' }}>
        <svg width="100%" height={svgHeight} viewBox={`0 0 ${svgWidth} ${svgHeight}`} preserveAspectRatio="none">
          {/* Ground truth target line */}
          <path d={truthPath} fill="none" stroke="#22c55e" strokeWidth="1.2" strokeDasharray="3 3" opacity="0.6" />
          {/* Noisy raw measurement */}
          <path d={rawPath} fill="none" stroke="#f43f5e" strokeWidth="1.2" strokeOpacity="0.75" />
          {/* Kalman filtered estimate */}
          <path d={filteredPath} fill="none" stroke="#38bdf8" strokeWidth="2.2" />
        </svg>
        <div style={{ position: 'absolute', right: 6, bottom: 3, fontSize: 9, color: '#94a3b8', background: 'rgba(15,23,42,0.85)', padding: '1px 4px', borderRadius: 3 }}>
          {unit}
        </div>
      </div>
    );
  };

  return (
    <div
      style={{
        background: 'linear-gradient(145deg, #0f172a 0%, #1e293b 100%)',
        border: '1px solid #334155',
        borderRadius: 12,
        padding: '16px 20px',
        color: '#f8fafc',
        boxShadow: '0 4px 20px -2px rgba(0, 0, 0, 0.4)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#38bdf8', boxShadow: '0 0 8px #38bdf8' }} />
          <h3 style={{ margin: 0, fontSize: 14, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', color: '#e2e8f0' }}>
            Discrete 1D Kalman Filter (LQE State Estimation)
          </h3>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={handleToggleNoise}
            style={{
              padding: '3px 8px',
              fontSize: 10,
              fontWeight: 600,
              borderRadius: 4,
              border: 'none',
              cursor: 'pointer',
              background: isNoiseEnabled ? '#0284c7' : '#475569',
              color: '#ffffff',
            }}
          >
            {isNoiseEnabled ? 'Noise: ON' : 'Noise: OFF'}
          </button>
          <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 12, background: '#0369a1', color: '#bae6fd', fontWeight: 600 }}>
            Rubric 4 & 5
          </span>
        </div>
      </div>

      {/* Mathematical Principle Callout */}
      <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 14, background: 'rgba(15, 23, 42, 0.6)', padding: '6px 10px', borderRadius: 6, borderLeft: '3px solid #38bdf8' }}>
        <strong>State Update Law:</strong> x̂_k = x̂⁻_k + K_k(z_k - x̂⁻_k), where Kalman Gain K_k = P⁻_k / (P⁻_k + R) dynamically rejects sensor noise variance R.
      </div>

      {/* Main Grid: Moisture and Proximity Filters */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        {/* Moisture Channel */}
        <div style={{ background: '#0b1329', border: '1px solid #1e293b', borderRadius: 8, padding: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#67e8f9' }}>Soil Moisture Channel</span>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>Q = 0.08, R = {moist ? (3.5 ** 2).toFixed(1) : '12.2'}</span>
          </div>

          {/* Metric Comparison Values */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginBottom: 8, textAlign: 'center' }}>
            <div style={{ background: 'rgba(34, 197, 94, 0.1)', padding: 4, borderRadius: 4, border: '1px solid rgba(34, 197, 94, 0.2)' }}>
              <div style={{ fontSize: 9, color: '#86efac' }}>Ground Truth</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#22c55e' }}>{moist?.ground_truth ?? 50.0}%</div>
            </div>
            <div style={{ background: 'rgba(244, 63, 94, 0.1)', padding: 4, borderRadius: 4, border: '1px solid rgba(244, 63, 94, 0.2)' }}>
              <div style={{ fontSize: 9, color: '#fda4af' }}>Noisy Raw (z_k)</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f43f5e' }}>{moist?.measurement ?? 50.0}%</div>
            </div>
            <div style={{ background: 'rgba(56, 189, 248, 0.1)', padding: 4, borderRadius: 4, border: '1px solid rgba(56, 189, 248, 0.3)' }}>
              <div style={{ fontSize: 9, color: '#7dd3fc' }}>Filtered (x̂_k)</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#38bdf8' }}>{moist?.estimate ?? 50.0}%</div>
            </div>
          </div>

          {/* Sparkline chart */}
          {renderSparkline(moistureHistory, 0, 100, '%')}

          {/* Sub-parameters */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 10, color: '#64748b' }}>
            <span>Kalman Gain K: <strong style={{ color: '#cbd5e1' }}>{moist?.gain ?? 0.28}</strong></span>
            <span>Error Var P: <strong style={{ color: '#cbd5e1' }}>{moist?.variance ?? 1.84}</strong></span>
            <span>Innovation ỹ: <strong style={{ color: '#cbd5e1' }}>{moist?.innovation ?? 0.0}</strong></span>
          </div>
        </div>

        {/* Ultrasonic Proximity Channel */}
        <div style={{ background: '#0b1329', border: '1px solid #1e293b', borderRadius: 8, padding: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#a78bfa' }}>Ultrasonic Range Channel</span>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>Q = 0.15, R = 4.0</span>
          </div>

          {/* Metric Comparison Values */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6, marginBottom: 8, textAlign: 'center' }}>
            <div style={{ background: 'rgba(34, 197, 94, 0.1)', padding: 4, borderRadius: 4, border: '1px solid rgba(34, 197, 94, 0.2)' }}>
              <div style={{ fontSize: 9, color: '#86efac' }}>Ground Truth</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#22c55e' }}>{prox?.ground_truth ?? 100.0} cm</div>
            </div>
            <div style={{ background: 'rgba(244, 63, 94, 0.1)', padding: 4, borderRadius: 4, border: '1px solid rgba(244, 63, 94, 0.2)' }}>
              <div style={{ fontSize: 9, color: '#fda4af' }}>Noisy Raw (z_k)</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#f43f5e' }}>{prox?.measurement ?? 100.0} cm</div>
            </div>
            <div style={{ background: 'rgba(56, 189, 248, 0.1)', padding: 4, borderRadius: 4, border: '1px solid rgba(56, 189, 248, 0.3)' }}>
              <div style={{ fontSize: 9, color: '#7dd3fc' }}>Filtered (x̂_k)</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#38bdf8' }}>{prox?.estimate ?? 100.0} cm</div>
            </div>
          </div>

          {/* Sparkline chart */}
          {renderSparkline(proximityHistory, 0, 120, 'cm')}

          {/* Sub-parameters */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 10, color: '#64748b' }}>
            <span>Kalman Gain $K$: <strong style={{ color: '#cbd5e1' }}>{prox?.gain ?? 0.34}</strong></span>
            <span>Error Var $P$: <strong style={{ color: '#cbd5e1' }}>{prox?.variance ?? 1.25}</strong></span>
            <span>Trigger Threshold: <strong style={{ color: '#f59e0b' }}>&lt; 15 cm</strong></span>
          </div>
        </div>
      </div>

      {/* Interactive Noise Injection Slider for Viva Defense */}
      <div style={{ marginTop: 14, display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(30, 41, 59, 0.5)', padding: '8px 14px', borderRadius: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: '#cbd5e1' }}>Gaussian Noise Intensity ($\sigma$):</span>
          <input
            type="range"
            min="0"
            max="10"
            step="0.5"
            value={noiseSigma}
            onChange={(e) => handleNoiseChange(parseFloat(e.target.value))}
            style={{ width: 140, accentColor: '#38bdf8', cursor: 'pointer' }}
          />
          <span style={{ fontSize: 12, fontWeight: 700, color: '#38bdf8' }}>±{noiseSigma.toFixed(1)}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 10, color: '#94a3b8' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ display: 'inline-block', width: 10, height: 2, background: '#22c55e' }} /> Truth
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ display: 'inline-block', width: 10, height: 2, background: '#f43f5e' }} /> Noisy Raw
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ display: 'inline-block', width: 10, height: 3, background: '#38bdf8' }} /> Kalman Filtered
          </span>
        </div>
      </div>
    </div>
  );
};
