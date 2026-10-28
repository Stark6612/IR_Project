/**
 * Telemetry Service: Dual-Engine Connection Manager
 * Seamlessly interfaces between the live Python FastAPI/WebSocket backend
 * and the in-browser ClientSimulationEngine fallback.
 */

import type { SimulationTelemetry, CVInspectionData } from '../types/telemetry';
import { ClientSimulationEngine } from './clientSimulationEngine';

export type EngineMode = 'python_server' | 'standalone_client';

export class TelemetryService {
  private mode: EngineMode = 'standalone_client';
  private ws: WebSocket | null = null;
  private clientEngine: ClientSimulationEngine;
  private clientTimer: number | null = null;
  private speed = 1.0;
  private listeners: ((data: SimulationTelemetry) => void)[] = [];
  private modeListeners: ((mode: EngineMode, connected: boolean) => void)[] = [];
  private isServerOnline = false;

  constructor() {
    this.clientEngine = new ClientSimulationEngine();
    this.attemptServerConnection();
  }

  public getMode(): EngineMode {
    return this.mode;
  }

  public isBackendOnline(): boolean {
    return this.isServerOnline;
  }

  public subscribe(callback: (data: SimulationTelemetry) => void): () => void {
    this.listeners.push(callback);
    // Emit initial telemetry immediately
    callback(this.getCurrentTelemetry());
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback);
    };
  }

  public subscribeMode(callback: (mode: EngineMode, connected: boolean) => void): () => void {
    this.modeListeners.push(callback);
    callback(this.mode, this.isServerOnline);
    return () => {
      this.modeListeners = this.modeListeners.filter(cb => cb !== callback);
    };
  }

  private notify(data: SimulationTelemetry) {
    this.listeners.forEach(cb => cb(data));
  }

  private notifyMode() {
    this.modeListeners.forEach(cb => cb(this.mode, this.isServerOnline));
  }

  public setMode(newMode: EngineMode) {
    this.mode = newMode;
    if (this.mode === 'standalone_client') {
      this.notify(this.clientEngine.getTelemetry());
    } else {
      this.attemptServerConnection();
    }
    this.notifyMode();
  }

  private async attemptServerConnection() {
    try {
      const res = await fetch('http://localhost:8000/api/state', { method: 'GET' });
      if (res.ok) {
        this.isServerOnline = true;
        this.mode = 'python_server';
        this.connectWebSocket();
      } else {
        this.fallbackToClient();
      }
    } catch {
      this.fallbackToClient();
    }
    this.notifyMode();
  }

  private fallbackToClient() {
    this.isServerOnline = false;
    this.mode = 'standalone_client';
    this.notify(this.clientEngine.getTelemetry());
  }

  private connectWebSocket() {
    if (this.ws) {
      try { this.ws.close(); } catch {}
    }

    try {
      this.ws = new WebSocket('ws://localhost:8000/ws');
      this.ws.onopen = () => {
        this.isServerOnline = true;
        this.mode = 'python_server';
        this.notifyMode();
      };

      this.ws.onmessage = (event) => {
        if (this.mode === 'python_server') {
          try {
            const data: SimulationTelemetry = JSON.parse(event.data);
            this.notify(data);
          } catch {}
        }
      };

      this.ws.onclose = () => {
        this.isServerOnline = false;
        this.notifyMode();
      };

      this.ws.onerror = () => {
        this.isServerOnline = false;
        this.fallbackToClient();
      };
    } catch {
      this.fallbackToClient();
    }
  }

  public getCurrentTelemetry(): SimulationTelemetry {
    return this.clientEngine.getTelemetry();
  }

  // Action dispatches
  public async startMission() {
    if (this.mode === 'python_server' && this.isServerOnline) {
      try {
        await fetch('http://localhost:8000/api/start', { method: 'POST' });
        return;
      } catch {}
    }

    // Client engine
    this.clientEngine.roverState = 'PLANNING';
    if (!this.clientEngine.missionStartTime) {
      this.clientEngine.missionStartTime = Date.now() / 1000;
    }
    this.clientEngine.logEvent('mission_state', [this.clientEngine.roverCoord.x, this.clientEngine.roverCoord.y], 'start_mission', 'SUCCESS', {
      tasks_count: this.clientEngine.tasks.length,
    });
    this.startClientLoop();
    this.notify(this.clientEngine.getTelemetry());
  }

  public async pauseMission() {
    if (this.mode === 'python_server' && this.isServerOnline) {
      try {
        await fetch('http://localhost:8000/api/pause', { method: 'POST' });
        return;
      } catch {}
    }

    this.stopClientLoop();
    this.clientEngine.roverState = 'PAUSED';
    this.clientEngine.logEvent('mission_state', [this.clientEngine.roverCoord.x, this.clientEngine.roverCoord.y], 'pause', 'PAUSED');
    this.notify(this.clientEngine.getTelemetry());
  }

  public async resumeMission() {
    if (this.mode === 'python_server' && this.isServerOnline) {
      try {
        await fetch('http://localhost:8000/api/resume', { method: 'POST' });
        return;
      } catch {}
    }

    if (this.clientEngine.roverState === 'PAUSED') {
      this.clientEngine.roverState = this.clientEngine.plannedPath.length > 0 ? 'MOVING' : 'PLANNING';
      this.clientEngine.logEvent('mission_state', [this.clientEngine.roverCoord.x, this.clientEngine.roverCoord.y], 'resume', 'RESUMED');
      this.startClientLoop();
      this.notify(this.clientEngine.getTelemetry());
    }
  }

  public async stopMission() {
    if (this.mode === 'python_server' && this.isServerOnline) {
      try {
        await fetch('http://localhost:8000/api/stop', { method: 'POST' });
        return;
      } catch {}
    }

    this.stopClientLoop();
    this.clientEngine.roverState = 'IDLE';
    this.clientEngine.missionEndTime = Date.now() / 1000;
    this.clientEngine.logEvent('mission_state', [this.clientEngine.roverCoord.x, this.clientEngine.roverCoord.y], 'stop', 'STOPPED');
    this.notify(this.clientEngine.getTelemetry());
  }

  public async resetMission(scenario: string) {
    if (this.mode === 'python_server' && this.isServerOnline) {
      try {
        await fetch('http://localhost:8000/api/reset', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario }),
        });
        return;
      } catch {}
    }

    this.stopClientLoop();
    this.clientEngine.loadScenario(scenario);
    this.notify(this.clientEngine.getTelemetry());
  }

  public async stepMission() {
    if (this.mode === 'python_server' && this.isServerOnline) {
      try {
        const res = await fetch('http://localhost:8000/api/step', { method: 'POST' });
        const data = await res.json();
        this.notify(data);
        return;
      } catch {}
    }

    this.stopClientLoop();
    const data = this.clientEngine.step();
    this.notify(data);
  }

  public async toggleObstacle(x: number, y: number) {
    if (this.mode === 'python_server' && this.isServerOnline) {
      try {
        await fetch('http://localhost:8000/api/obstacle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ x, y }),
        });
        return;
      } catch {}
    }

    this.clientEngine.toggleObstacle(x, y);
    this.notify(this.clientEngine.getTelemetry());
  }

  public async setSpeed(multiplier: number) {
    this.speed = multiplier;
    if (this.mode === 'python_server' && this.isServerOnline) {
      try {
        await fetch('http://localhost:8000/api/speed', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ speed: multiplier }),
        });
      } catch {}
    } else {
      if (this.clientTimer) {
        this.startClientLoop(); // Restart with updated speed
      }
    }
  }

  public async inspectCellCV(x: number, y: number): Promise<CVInspectionData | null> {
    if (this.mode === 'python_server' && this.isServerOnline) {
      try {
        const res = await fetch('http://localhost:8000/api/cv_inspect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ x, y }),
        });
        if (res.ok) {
          return await res.json();
        }
      } catch {}
    }

    // Client fallback CV representation
    const k = `${x},${y}`;
    const cell = this.clientEngine.cells.get(k);
    if (!cell) return null;

    const uavMetadata = {
      source: 'UAV Aerial Drone Orthophoto',
      model: 'YOLOv8n',
      altitude_m: 25.4,
      gsd_cm_px: 0.82,
      map50: 0.824,
      dataset: 'LibreYOLO/weed-crop-aerial',
    };

    if (cell.entity_type === 'weed') {
      return {
        detected: true,
        classification: 'weed',
        health_status: 'invasive_weed',
        confidence: 0.95,
        vegetation_coverage: 0.28,
        mean_excess_green: 172.4,
        chlorosis_ratio: 0.0,
        chlorosis_threshold: 0.15,
        is_diseased: false,
        contour_solidity: 0.88,
        target_coordinate: [x, y],
        uav_drone: uavMetadata,
      };
    } else if (cell.entity_type === 'plant') {
      const isDis = cell.plant_info?.health === 'suspected_disease';
      return {
        detected: true,
        classification: 'crop',
        health_status: cell.plant_info?.health ?? 'healthy',
        confidence: cell.plant_info?.confidence ?? 0.96,
        vegetation_coverage: 0.145,
        mean_excess_green: 135.2,
        chlorosis_ratio: isDis ? 0.24 : 0.0,
        chlorosis_threshold: 0.15,
        is_diseased: isDis,
        contour_solidity: 0.76,
        target_coordinate: [x, y],
        uav_drone: uavMetadata,
      };
    }
    return {
      detected: false,
      classification: 'empty_soil_or_obstacle',
      health_status: 'none',
      confidence: 0.98,
      vegetation_coverage: 0.0,
      target_coordinate: [x, y],
      uav_drone: uavMetadata,
    };
  }

  private startClientLoop() {
    this.stopClientLoop();
    const interval = Math.max(50, Math.floor(350 / Math.max(0.1, this.speed)));
    this.clientTimer = window.setInterval(() => {
      if (
        this.clientEngine.roverState === 'PLANNING' ||
        this.clientEngine.roverState === 'MOVING' ||
        this.clientEngine.roverState === 'AVOIDING_OBSTACLE' ||
        this.clientEngine.roverState === 'EXECUTING_TASK'
      ) {
        const data = this.clientEngine.step();
        this.notify(data);
      } else {
        this.stopClientLoop();
      }
    }, interval);
  }

  private stopClientLoop() {
    if (this.clientTimer !== null) {
      clearInterval(this.clientTimer);
      this.clientTimer = null;
    }
  }
}

export const telemetryService = new TelemetryService();
