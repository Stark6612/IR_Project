import React, { useState } from 'react';
import type { GridCell, HeadingDirection } from '../types/telemetry';
import { Droplets, AlertTriangle, Sparkles } from 'lucide-react';

interface FieldCanvasProps {
  width: number;
  height: number;
  cells: GridCell[];
  roverCoord: [number, number];
  roverHeading: HeadingDirection;
  currentTarget: [number, number] | null;
  plannedPath: [number, number][];
  previousPath?: [number, number][] | null;
  blockedObstacle?: [number, number] | null;
  proximityTriggered: boolean;
  onCellClick: (x: number, y: number) => void;
  onCellInspect: (x: number, y: number) => void;
}

export const FieldCanvas: React.FC<FieldCanvasProps> = ({
  width,
  height,
  cells,
  roverCoord,
  roverHeading,
  currentTarget,
  plannedPath,
  previousPath,
  blockedObstacle,
  proximityTriggered,
  onCellClick,
  onCellInspect,
}) => {
  const [hoveredCell, setHoveredCell] = useState<{ x: number; y: number } | null>(null);

  // Map coordinate (x, y) to cell
  const cellMap = new Map<string, GridCell>();
  cells.forEach((c) => cellMap.set(`${c.x},${c.y}`, c));

  // Heading rotation degrees: E = 0, S = 90, W = 180, N = 270
  const headingDegMap: Record<HeadingDirection, number> = {
    E: 0,
    S: 90,
    W: 180,
    N: 270,
  };

  const roverRotation = headingDegMap[roverHeading] ?? 0;

  // Generate SVG path for the planned route
  // Grid cell size in SVG coordinates
  const CELL_SIZE = 100;
  const PADDING = 20;

  const pathPoints = plannedPath.map(([px, py]) => {
    // In our coordinate system, y=0 is bottom, y=height-1 is top
    const svgX = PADDING + px * CELL_SIZE + CELL_SIZE / 2;
    const svgY = PADDING + (height - 1 - py) * CELL_SIZE + CELL_SIZE / 2;
    return `${svgX},${svgY}`;
  });

  const pathSvgD = pathPoints.length > 0 ? `M ${pathPoints.join(' L ')}` : '';

  // Generate SVG path for the superseded/old blocked route
  const previousPoints = (previousPath || []).map(([px, py]) => {
    const svgX = PADDING + px * CELL_SIZE + CELL_SIZE / 2;
    const svgY = PADDING + (height - 1 - py) * CELL_SIZE + CELL_SIZE / 2;
    return `${svgX},${svgY}`;
  });

  const previousSvgD = previousPoints.length > 0 ? `M ${previousPoints.join(' L ')}` : '';

  return (
    <div className="glass-panel" style={{ padding: '16px', position: 'relative' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#f3f4f6' }}>
            2D Field Grid Canvas
          </h2>
          <span className="mono-badge" style={{ background: 'rgba(255, 255, 255, 0.08)', color: '#9ca3af' }}>
            {width} × {height} ({width * height} cells)
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '0.75rem', color: '#9ca3af', flexWrap: 'wrap' }}>
          {previousSvgD && (
            <>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#f87171', fontWeight: 600 }}>
                <span style={{ width: '14px', height: '0px', borderTop: '2px dashed #ef4444', display: 'inline-block' }} />
                Old Path (Blocked)
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#34d399', fontWeight: 600 }}>
                <span style={{ width: '14px', height: '0px', borderTop: '2px solid #34d399', display: 'inline-block' }} />
                New Detour (A*)
              </span>
            </>
          )}
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', display: 'inline-block' }} />
            Crop
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b', display: 'inline-block' }} />
            Dry Crop (&lt;30%)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#a855f7', display: 'inline-block' }} />
            Weed
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#64748b', display: 'inline-block' }} />
            Obstacle (Click to place)
          </span>
        </div>
      </div>

      {/* Dynamic Detour Alert Banner */}
      {previousSvgD && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            borderRadius: '6px',
            padding: '6px 12px',
            marginBottom: '10px',
            fontSize: '0.76rem',
            color: '#fca5a5',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.95rem' }}>⚠️</span>
            <span>
              <strong>Dynamic Replanning Active:</strong> Old Path (Red dashed) bypassed via collision-free A* detour (Green flowing).
            </span>
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: '#f87171' }}>
            Replanned in &lt;0.05 ms
          </span>
        </div>
      )}

      {/* Grid Canvas Wrapper */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: '760px',
          margin: '0 auto',
          aspectRatio: `${width} / ${height}`,
          background: 'radial-gradient(ellipse at center, #112017 0%, #08110c 100%)',
          borderRadius: '10px',
          border: '1px solid rgba(52, 211, 153, 0.2)',
          boxShadow: 'inset 0 0 30px rgba(0, 0, 0, 0.7)',
          overflow: 'hidden',
        }}
      >
        {/* SVG Path Layer */}
        <svg
          viewBox={`0 0 ${width * CELL_SIZE + PADDING * 2} ${height * CELL_SIZE + PADDING * 2}`}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
            zIndex: 10,
          }}
        >
          {/* Old Superseded Route (Blocked Path in Dashed Red) */}
          {previousSvgD && (
            <path
              d={previousSvgD}
              fill="none"
              stroke="#ef4444"
              strokeWidth="3.5"
              strokeDasharray="8 6"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ filter: 'drop-shadow(0 0 6px rgba(239, 68, 68, 0.8))', opacity: 0.9 }}
            />
          )}

          {/* New Active Detour Route (Flowing Green) */}
          {pathSvgD && (
            <path
              d={pathSvgD}
              fill="none"
              stroke="#34d399"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="path-line-flowing"
              style={{ filter: 'drop-shadow(0 0 6px #10b981)' }}
            />
          )}

          {/* Blocked Obstacle Highlight Marker */}
          {blockedObstacle && (
            <g
              transform={`translate(${PADDING + blockedObstacle[0] * CELL_SIZE + CELL_SIZE / 2}, ${
                PADDING + (height - 1 - blockedObstacle[1]) * CELL_SIZE + CELL_SIZE / 2
              })`}
            >
              <circle r="18" fill="rgba(239, 68, 68, 0.25)" stroke="#ef4444" strokeWidth="2" strokeDasharray="3 3" />
              <line x1="-8" y1="-8" x2="8" y2="8" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />
              <line x1="8" y1="-8" x2="-8" y2="8" stroke="#ef4444" strokeWidth="3" strokeLinecap="round" />
            </g>
          )}
        </svg>

        {/* 6x4 Cells CSS Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${width}, 1fr)`,
            gridTemplateRows: `repeat(${height}, 1fr)`,
            width: '100%',
            height: '100%',
            padding: '8px',
            gap: '6px',
          }}
        >
          {/* Render rows from top (y = height - 1) down to 0 */}
          {Array.from({ length: height }, (_, rIdx) => {
            const y = height - 1 - rIdx;
            return Array.from({ length: width }, (_, x) => {
              const key = `${x},${y}`;
              const cell = cellMap.get(key) || { x, y, entity_type: 'empty' };
              const isRoverHere = roverCoord[0] === x && roverCoord[1] === y;
              const isTarget = currentTarget && currentTarget[0] === x && currentTarget[1] === y;
              const isPlanned = plannedPath.some(([px, py]) => px === x && py === y);

              return (
                <div
                  key={key}
                  onClick={() => onCellClick(x, y)}
                  onContextMenu={(e) => {
                    e.preventDefault();
                    onCellInspect(x, y);
                  }}
                  onMouseEnter={() => setHoveredCell({ x, y })}
                  onMouseLeave={() => setHoveredCell(null)}
                  style={{
                    position: 'relative',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    userSelect: 'none',
                    transition: 'all 0.15s ease',
                    background:
                      cell.entity_type === 'obstacle'
                        ? 'linear-gradient(135deg, #334155 0%, #1e293b 100%)'
                        : isTarget
                        ? 'rgba(16, 185, 129, 0.18)'
                        : 'rgba(18, 28, 22, 0.65)',
                    border: isTarget
                      ? '2px solid #10b981'
                      : isPlanned
                      ? '1px dashed rgba(52, 211, 153, 0.4)'
                      : cell.entity_type === 'obstacle'
                      ? '1px solid #64748b'
                      : '1px solid rgba(255, 255, 255, 0.05)',
                    boxShadow: isTarget
                      ? '0 0 16px rgba(16, 185, 129, 0.4)'
                      : 'inset 0 1px 3px rgba(0,0,0,0.4)',
                  }}
                >
                  {/* Coordinate Label */}
                  <span
                    style={{
                      position: 'absolute',
                      top: '3px',
                      left: '5px',
                      fontSize: '0.62rem',
                      fontFamily: 'var(--font-mono)',
                      color: 'rgba(255, 255, 255, 0.3)',
                    }}
                  >
                    {x},{y}
                  </span>

                  {/* Target Indicator Marker */}
                  {isTarget && !isRoverHere && (
                    <div
                      className="animate-target-pulse"
                      style={{
                        position: 'absolute',
                        inset: '2px',
                        border: '2px dashed #10b981',
                        borderRadius: '6px',
                        pointerEvents: 'none',
                      }}
                    />
                  )}

                  {/* Cell Content: Rover */}
                  {isRoverHere ? (
                    <div
                      className="rover-beacon"
                      style={{
                        position: 'relative',
                        width: '72%',
                        height: '72%',
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #10b981 0%, #047857 100%)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transform: `rotate(${roverRotation}deg)`,
                        transition: 'transform 0.25s ease',
                        boxShadow: '0 0 16px #10b981',
                        zIndex: 20,
                      }}
                    >
                      {/* Left & Right Differential Drive Wheels */}
                      <div
                        style={{
                          position: 'absolute',
                          top: '-4px',
                          left: '50%',
                          transform: 'translateX(-50%)',
                          width: '18px',
                          height: '5px',
                          background: '#0f172a',
                          borderRadius: '2px',
                          border: '1px solid #38bdf8',
                        }}
                      />
                      <div
                        style={{
                          position: 'absolute',
                          bottom: '-4px',
                          left: '50%',
                          transform: 'translateX(-50%)',
                          width: '18px',
                          height: '5px',
                          background: '#0f172a',
                          borderRadius: '2px',
                          border: '1px solid #38bdf8',
                        }}
                      />

                      {/* Directional Heading Nose / Arrow */}
                      <div
                        style={{
                          position: 'absolute',
                          right: '-6px',
                          top: '50%',
                          transform: 'translateY(-50%)',
                          width: 0,
                          height: 0,
                          borderTop: '6px solid transparent',
                          borderBottom: '6px solid transparent',
                          borderLeft: '10px solid #ffffff',
                          filter: 'drop-shadow(0 0 4px #ffffff)',
                        }}
                      />

                      {/* Rover Core Lens */}
                      <div
                        style={{
                          width: '14px',
                          height: '14px',
                          borderRadius: '50%',
                          background: '#ffffff',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <div
                          style={{
                            width: '6px',
                            height: '6px',
                            borderRadius: '50%',
                            background: '#047857',
                          }}
                        />
                      </div>

                      {/* Ultrasonic Sensor Beam Cone */}
                      <div
                        style={{
                          position: 'absolute',
                          right: '-36px',
                          top: '50%',
                          transform: 'translateY(-50%)',
                          width: '32px',
                          height: '24px',
                          background: proximityTriggered
                            ? 'radial-gradient(ellipse at left, rgba(239, 68, 68, 0.45) 0%, transparent 70%)'
                            : 'radial-gradient(ellipse at left, rgba(56, 189, 248, 0.35) 0%, transparent 70%)',
                          pointerEvents: 'none',
                        }}
                      />
                    </div>
                  ) : cell.entity_type === 'plant' ? (
                    // Plant Cell
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                      <div
                        style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '50%',
                          background:
                            cell.plant_info?.health === 'suspected_disease'
                              ? 'radial-gradient(circle, #facc15 30%, #15803d 80%)'
                              : cell.plant_info && cell.plant_info.moisture < 30
                              ? 'radial-gradient(circle, #f97316 40%, #166534 85%)'
                              : 'radial-gradient(circle, #4ade80 30%, #166534 80%)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          boxShadow: '0 2px 8px rgba(0,0,0,0.4)',
                        }}
                      >
                        <span style={{ fontSize: '1.1rem' }}>🌱</span>
                      </div>
                      {/* Moisture Badge */}
                      {cell.plant_info && (
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '2px',
                            fontSize: '0.65rem',
                            fontWeight: 700,
                            fontFamily: 'var(--font-mono)',
                            color: cell.plant_info.moisture < 30 ? '#f59e0b' : '#34d399',
                            background: 'rgba(0,0,0,0.6)',
                            padding: '1px 5px',
                            borderRadius: '4px',
                          }}
                        >
                          <Droplets size={9} />
                          <span>{cell.plant_info.moisture}%</span>
                        </div>
                      )}
                    </div>
                  ) : cell.entity_type === 'weed' ? (
                    // Invasive Weed Cell
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <div
                        style={{
                          width: '34px',
                          height: '34px',
                          borderRadius: '8px',
                          background: 'linear-gradient(135deg, #7e22ce 0%, #15803d 100%)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          boxShadow: '0 0 10px rgba(168, 85, 247, 0.4)',
                        }}
                      >
                        <span style={{ fontSize: '1.15rem' }}>🌿</span>
                      </div>
                      <span style={{ fontSize: '0.62rem', color: '#c084fc', fontWeight: 600 }}>Weed</span>
                    </div>
                  ) : cell.entity_type === 'obstacle' ? (
                    // Obstacle Rock Cell
                    <div
                      style={{
                        width: '38px',
                        height: '38px',
                        borderRadius: '6px',
                        background: 'linear-gradient(135deg, #475569 0%, #0f172a 100%)',
                        border: '1px solid #94a3b8',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: '0 4px 10px rgba(0,0,0,0.6)',
                      }}
                    >
                      <AlertTriangle size={18} color="#e2e8f0" />
                    </div>
                  ) : (
                    // Empty Soil Cell
                    <div
                      style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        background: 'rgba(255, 255, 255, 0.08)',
                      }}
                    />
                  )}
                </div>
              );
            });
          })}
        </div>
      </div>

      {/* Grid Canvas Bottom Info Bar */}
      <div
        style={{
          marginTop: '10px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '0.75rem',
          color: '#9ca3af',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Sparkles size={13} color="#34d399" />
          <span>
            <b>Interactive Mode:</b> Left-Click empty cell to drop obstacle • Right-Click any plant/weed to inspect with OpenCV
          </span>
        </div>
        {hoveredCell && (
          <div style={{ fontFamily: 'var(--font-mono)', color: '#34d399' }}>
            Cursor Cell: ({hoveredCell.x}, {hoveredCell.y})
          </div>
        )}
      </div>
    </div>
  );
};
