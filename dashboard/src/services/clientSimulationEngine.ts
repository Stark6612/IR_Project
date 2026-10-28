/**
 * In-Browser Standalone Simulation Engine (Fail-safe Client Fallback)
 * Mirrors the Python robotics logic with A*, kinematics, PID, and deterministic scenarios.
 */

import type {
  SimulationTelemetry,
  GridCell,
  TaskItem,
  SimulationEvent,
  HeadingDirection,
  RobotState,
  EntityType,
  KalmanChannelData,
} from '../types/telemetry';

interface Coord {
  x: number;
  y: number;
}

export class ClientSimulationEngine {
  width = 8;
  height = 6;
  scenarioName = 'mixed_field';
  cells: Map<string, GridCell> = new Map();
  roverCoord: Coord = { x: 0, y: 0 };
  roverHeading: HeadingDirection = 'E';
  roverState: RobotState = 'IDLE';
  battery = 100.0;
  proximityCm = 100.0;
  currentTarget: Coord | null = null;
  plannedPath: Coord[] = [];
  previousPath: Coord[] | null = null;
  blockedObstacle: Coord | null = null;
  pathIndex = 0;

  // Kinematics & PID
  pose = { x: 0.0, y: 0.0, theta: 0.0 };
  linearVelocity = 0.0;
  angularVelocity = 0.0;
  integralError = 0.0;
  prevError = 0.0;
  lastPid = { error_deg: 0, p_term: 0, i_term: 0, d_term: 0, omega_command: 0 };

  // Discrete 1D Kalman Filters for State Estimation
  noiseEnabled = true;
  moistureSigma = 3.5;
  proximitySigma = 2.0;
  moistureEst = 50.0;
  moistureVar = 10.0;
  proximityEst = 100.0;
  proximityVar = 15.0;
  lastMoistureKalman: KalmanChannelData | null = null;
  lastProximityKalman: KalmanChannelData | null = null;

  // Metrics
  visitedCells = new Set<string>();
  weedsCleared = 0;
  plantsInspected = 0;
  plantsWatered = 0;
  obstaclesEncountered = 0;
  replansCount = 0;
  totalSteps = 0;
  missionStartTime: number | null = null;
  missionEndTime: number | null = null;

  tasks: TaskItem[] = [];
  events: SimulationEvent[] = [];
  currentTask: TaskItem | null = null;

  constructor() {
    this.loadScenario('mixed_field');
  }

  key(x: number, y: number): string {
    return `${x},${y}`;
  }

  boxMullerGaussian(mean: number, sigma: number): number {
    let u1 = 0, u2 = 0;
    while (u1 === 0) u1 = Math.random();
    while (u2 === 0) u2 = Math.random();
    const z0 = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
    return mean + z0 * sigma;
  }

  updateKalmanChannel(
    currentEst: number,
    currentVar: number,
    q: number,
    r: number,
    measurement: number,
    groundTruth: number
  ): { nextEst: number; nextVar: number; data: KalmanChannelData } {
    // Prediction
    const pMinus = currentVar + q;
    // Kalman gain
    const denom = pMinus + r;
    const gain = denom > 0 ? pMinus / denom : 0.0;
    // Innovation
    const innovation = measurement - currentEst;
    // Update
    const nextEst = currentEst + gain * innovation;
    const nextVar = (1.0 - gain) * pMinus;

    return {
      nextEst,
      nextVar,
      data: {
        ground_truth: Number(groundTruth.toFixed(2)),
        measurement: Number(measurement.toFixed(2)),
        estimate: Number(nextEst.toFixed(2)),
        gain: Number(gain.toFixed(4)),
        variance: Number(nextVar.toFixed(4)),
        innovation: Number(innovation.toFixed(2)),
      },
    };
  }

  initEmptyGrid() {
    this.cells.clear();
    for (let y = 0; y < this.height; y++) {
      for (let x = 0; x < this.width; x++) {
        this.cells.set(this.key(x, y), { x, y, entity_type: 'empty' });
      }
    }
  }

  loadScenario(name: string) {
    this.scenarioName = name;
    this.initEmptyGrid();
    this.roverCoord = { x: 0, y: 0 };
    this.roverHeading = 'E';
    this.roverState = 'IDLE';
    this.battery = 100.0;
    this.proximityCm = 100.0;
    this.currentTarget = null;
    this.plannedPath = [];
    this.previousPath = null;
    this.blockedObstacle = null;
    this.pathIndex = 0;
    this.visitedCells = new Set([this.key(0, 0)]);
    this.weedsCleared = 0;
    this.plantsInspected = 0;
    this.plantsWatered = 0;
    this.obstaclesEncountered = 0;
    this.replansCount = 0;
    this.totalSteps = 0;
    this.missionStartTime = null;
    this.missionEndTime = null;
    this.events = [];
    this.currentTask = null;
    this.pose = { x: 0.0, y: 0.0, theta: 0.0 };
    this.linearVelocity = 0.0;
    this.angularVelocity = 0.0;
    this.integralError = 0.0;
    this.prevError = 0.0;

    if (name === 'mixed_field') {
      this.setCell(1, 1, 'plant', { moisture: 65, health: 'healthy', confidence: 0.95, inspected: false, watered: false });
      this.setCell(1, 4, 'plant', { moisture: 70, health: 'healthy', confidence: 0.97, inspected: false, watered: false });
      this.setCell(3, 1, 'plant', { moisture: 68, health: 'healthy', confidence: 0.94, inspected: false, watered: false });
      this.setCell(3, 4, 'plant', { moisture: 62, health: 'healthy', confidence: 0.92, inspected: false, watered: false });
      this.setCell(5, 1, 'plant', { moisture: 72, health: 'healthy', confidence: 0.96, inspected: false, watered: false });
      this.setCell(5, 4, 'plant', { moisture: 60, health: 'healthy', confidence: 0.93, inspected: false, watered: false });
      this.setCell(7, 2, 'plant', { moisture: 55, health: 'healthy', confidence: 0.91, inspected: false, watered: false });
      this.setCell(7, 5, 'plant', { moisture: 58, health: 'healthy', confidence: 0.92, inspected: false, watered: false });

      this.setCell(2, 2, 'plant', { moisture: 18, health: 'healthy', confidence: 0.95, inspected: false, watered: false });
      this.setCell(4, 2, 'plant', { moisture: 22, health: 'healthy', confidence: 0.94, inspected: false, watered: false });
      this.setCell(6, 4, 'plant', { moisture: 15, health: 'healthy', confidence: 0.98, inspected: false, watered: false });

      this.setCell(3, 3, 'plant', { moisture: 58, health: 'suspected_disease', confidence: 0.88, inspected: false, watered: false });
      this.setCell(5, 2, 'plant', { moisture: 52, health: 'suspected_disease', confidence: 0.91, inspected: false, watered: false });

      this.setCell(2, 4, 'weed');
      this.setCell(4, 4, 'weed');
      this.setCell(6, 2, 'weed');
      this.setCell(7, 1, 'weed');

      this.setCell(2, 1, 'obstacle');
      this.setCell(4, 3, 'obstacle');
      this.setCell(6, 3, 'obstacle');
    } else if (name === 'obstacle_challenge') {
      this.setCell(3, 0, 'obstacle');
      this.setCell(3, 1, 'obstacle');
      this.setCell(3, 2, 'obstacle');
      this.setCell(3, 3, 'obstacle');

      this.setCell(5, 1, 'plant', { moisture: 18, health: 'healthy', confidence: 0.95, inspected: false, watered: false });
      this.setCell(7, 2, 'plant', { moisture: 20, health: 'healthy', confidence: 0.96, inspected: false, watered: false });
      this.setCell(6, 3, 'weed');
      this.setCell(7, 5, 'weed');
      this.setCell(5, 4, 'plant', { moisture: 62, health: 'needs_inspection', confidence: 0.92, inspected: false, watered: false });
    } else if (name === 'dry_field') {
      this.setCell(1, 2, 'plant', { moisture: 15, health: 'healthy', confidence: 0.96, inspected: false, watered: false });
      this.setCell(3, 1, 'plant', { moisture: 12, health: 'healthy', confidence: 0.94, inspected: false, watered: false });
      this.setCell(4, 4, 'plant', { moisture: 20, health: 'healthy', confidence: 0.95, inspected: false, watered: false });
      this.setCell(5, 2, 'plant', { moisture: 16, health: 'healthy', confidence: 0.97, inspected: false, watered: false });
      this.setCell(6, 4, 'plant', { moisture: 19, health: 'healthy', confidence: 0.94, inspected: false, watered: false });
      this.setCell(2, 5, 'plant', { moisture: 25, health: 'healthy', confidence: 0.93, inspected: false, watered: false });
      this.setCell(7, 3, 'plant', { moisture: 75, health: 'healthy', confidence: 0.99, inspected: false, watered: false });

      this.setCell(2, 2, 'obstacle');
      this.setCell(5, 3, 'obstacle');
    }

    this.scanTasks();
    this.logEvent('system', [0, 0], 'reset', 'SUCCESS', { scenario: name });
  }

  setCell(x: number, y: number, type: EntityType, plantInfo?: any) {
    this.cells.set(this.key(x, y), { x, y, entity_type: type, plant_info: plantInfo });
  }

  logEvent(type: string, target: [number, number] | null, action: string, outcome: string, details: Record<string, any> = {}) {
    this.events.unshift({
      timestamp: Date.now() / 1000,
      event_type: type,
      target,
      action,
      outcome,
      details,
    });
    if (this.events.length > 50) this.events.pop();
  }

  scanTasks() {
    this.tasks = [];
    let id = 1;
    this.cells.forEach(cell => {
      if (cell.entity_type === 'plant' && cell.plant_info) {
        if (cell.plant_info.moisture < 30 && !cell.plant_info.watered) {
          this.tasks.push({
            task_id: `WATER_${id++}`,
            priority: 2,
            action_type: 'watering',
            target: [cell.x, cell.y],
            description: `Water dry plant (moisture ${cell.plant_info.moisture}%)`,
            completed: false,
            active: false,
          });
        }
        if ((cell.plant_info.health === 'suspected_disease' || cell.plant_info.health === 'needs_inspection') && !cell.plant_info.inspected) {
          this.tasks.push({
            task_id: `INSPECT_${id++}`,
            priority: 3,
            action_type: 'plant_inspection',
            target: [cell.x, cell.y],
            description: `Inspect plant for ${cell.plant_info.health}`,
            completed: false,
            active: false,
          });
        }
      } else if (cell.entity_type === 'weed' && !cell.cleared_weed) {
        this.tasks.push({
          task_id: `WEED_${id++}`,
          priority: 4,
          action_type: 'weed_clearing',
          target: [cell.x, cell.y],
          description: 'Clear invasive weed',
          completed: false,
          active: false,
        });
      }
    });
  }

  // A* Search Algorithm
  planAStar(start: Coord, goal: Coord): Coord[] {
    if (start.x === goal.x && start.y === goal.y) return [start];

    const blocked = new Set<string>();
    this.cells.forEach(c => {
      if (c.entity_type === 'obstacle') blocked.add(this.key(c.x, c.y));
    });

    const openSet: Coord[] = [start];
    const cameFrom = new Map<string, Coord>();
    const gScore = new Map<string, number>();
    gScore.set(this.key(start.x, start.y), 0);

    const fScore = new Map<string, number>();
    fScore.set(this.key(start.x, start.y), Math.abs(start.x - goal.x) + Math.abs(start.y - goal.y));

    while (openSet.length > 0) {
      openSet.sort((a, b) => (fScore.get(this.key(a.x, a.y)) ?? 9999) - (fScore.get(this.key(b.x, b.y)) ?? 9999));
      const current = openSet.shift()!;

      if (current.x === goal.x && current.y === goal.y) {
        const path: Coord[] = [current];
        let currKey = this.key(current.x, current.y);
        while (cameFrom.has(currKey)) {
          const prev = cameFrom.get(currKey)!;
          path.unshift(prev);
          currKey = this.key(prev.x, prev.y);
        }
        return path;
      }

      const deltas = [{ dx: 0, dy: 1 }, { dx: 1, dy: 0 }, { dx: 0, dy: -1 }, { dx: -1, dy: 0 }];
      for (const d of deltas) {
        const nx = current.x + d.dx;
        const ny = current.y + d.dy;
        if (nx < 0 || nx >= this.width || ny < 0 || ny >= this.height) continue;
        const nKey = this.key(nx, ny);
        if (blocked.has(nKey) && !(nx === goal.x && ny === goal.y)) continue;

        const tentG = (gScore.get(this.key(current.x, current.y)) ?? 9999) + 1;
        if (tentG < (gScore.get(nKey) ?? 9999)) {
          cameFrom.set(nKey, current);
          gScore.set(nKey, tentG);
          const f = tentG + Math.abs(nx - goal.x) + Math.abs(ny - goal.y);
          fScore.set(nKey, f);
          if (!openSet.some(c => c.x === nx && c.y === ny)) {
            openSet.push({ x: nx, y: ny });
          }
        }
      }
    }
    return [];
  }

  // Heading PID Controller
  computePid(currentTheta: number, targetTheta: number): any {
    let error = Math.atan2(Math.sin(targetTheta - currentTheta), Math.cos(targetTheta - currentTheta));
    this.integralError = Math.max(-1.0, Math.min(1.0, this.integralError + error * 0.2));
    const derivative = (error - this.prevError) / 0.2;
    this.prevError = error;

    const kp = 1.8;
    const ki = 0.05;
    const kd = 0.25;
    let omega = kp * error + ki * this.integralError + kd * derivative;
    omega = Math.max(-2.0, Math.min(2.0, omega));

    this.lastPid = {
      error_deg: Number((error * (180 / Math.PI)).toFixed(1)),
      p_term: Number((kp * error).toFixed(3)),
      i_term: Number((ki * this.integralError).toFixed(3)),
      d_term: Number((kd * derivative).toFixed(3)),
      omega_command: Number(omega.toFixed(3)),
    };
    return omega;
  }

  step(): SimulationTelemetry {
    if (this.roverState !== 'IDLE' && this.roverState !== 'PAUSED' && this.roverState !== 'COMPLETED') {
      this.battery = Math.max(0, this.battery - 0.05);
    }

    if (this.roverState === 'PLANNING') {
      const pending = this.tasks.filter(t => !t.completed);
      if (pending.length === 0) {
        this.roverState = 'COMPLETED';
        this.missionEndTime = Date.now() / 1000;
        this.logEvent('mission_state', [this.roverCoord.x, this.roverCoord.y], 'complete_mission', 'SUCCESS', {
          summary: 'All prioritized agricultural tasks fulfilled.',
        });
        return this.getTelemetry();
      }

      pending.sort((a, b) => {
        if (a.priority !== b.priority) return a.priority - b.priority;
        const distA = Math.abs(a.target[0] - this.roverCoord.x) + Math.abs(a.target[1] - this.roverCoord.y);
        const distB = Math.abs(b.target[0] - this.roverCoord.x) + Math.abs(b.target[1] - this.roverCoord.y);
        return distA - distB;
      });

      this.currentTask = pending[0];
      this.currentTask.active = true;
      this.currentTarget = { x: this.currentTask.target[0], y: this.currentTask.target[1] };

      const path = this.planAStar(this.roverCoord, this.currentTarget);
      if (path.length > 0) {
        this.plannedPath = path;
        this.pathIndex = 0;
        this.roverState = 'MOVING';
      } else {
        this.logEvent('navigation_error', [this.currentTarget.x, this.currentTarget.y], 'plan_path', 'UNREACHABLE', {
          reason: 'Path blocked or unreachable. Skipping task.',
        });
        this.currentTask.completed = true;
        this.currentTask.active = false;
        this.currentTask = null;
        this.roverState = 'PLANNING';
      }
    } else if (this.roverState === 'MOVING') {
      if (this.plannedPath.length === 0) {
        this.roverState = 'PLANNING';
        return this.getTelemetry();
      }

      if (this.roverCoord.x === this.currentTarget?.x && this.roverCoord.y === this.currentTarget?.y) {
        this.roverState = 'EXECUTING_TASK';
        return this.getTelemetry();
      }

      if (this.pathIndex + 1 < this.plannedPath.length) {
        const next = this.plannedPath[this.pathIndex + 1];

        // Determine heading
        if (next.x > this.roverCoord.x) this.roverHeading = 'E';
        else if (next.x < this.roverCoord.x) this.roverHeading = 'W';
        else if (next.y > this.roverCoord.y) this.roverHeading = 'N';
        else if (next.y < this.roverCoord.y) this.roverHeading = 'S';

        // Proximity sensor check with Gaussian noise & discrete Kalman filter
        const nextCell = this.cells.get(this.key(next.x, next.y));
        const groundTruthDist = (nextCell && nextCell.entity_type === 'obstacle') ? 10.0 : 100.0;
        const noisyDist = this.noiseEnabled && this.proximitySigma > 0
          ? Math.max(2.0, Math.min(200.0, this.boxMullerGaussian(groundTruthDist, this.proximitySigma)))
          : groundTruthDist;
        const proxRes = this.updateKalmanChannel(
          this.proximityEst,
          this.proximityVar,
          0.15,
          Math.max(0.01, this.proximitySigma ** 2),
          noisyDist,
          groundTruthDist
        );
        this.proximityEst = proxRes.nextEst;
        this.proximityVar = proxRes.nextVar;
        this.lastProximityKalman = proxRes.data;
        this.proximityCm = proxRes.data.estimate;

        // Current cell soil moisture with Kalman filtering
        const curCell = this.cells.get(this.key(this.roverCoord.x, this.roverCoord.y));
        const groundTruthMoist = curCell?.plant_info ? curCell.plant_info.moisture : 50.0;
        const noisyMoist = this.noiseEnabled && this.moistureSigma > 0
          ? Math.max(0.0, Math.min(100.0, this.boxMullerGaussian(groundTruthMoist, this.moistureSigma)))
          : groundTruthMoist;
        const moistRes = this.updateKalmanChannel(
          this.moistureEst,
          this.moistureVar,
          0.08,
          Math.max(0.01, this.moistureSigma ** 2),
          noisyMoist,
          groundTruthMoist
        );
        this.moistureEst = moistRes.nextEst;
        this.moistureVar = moistRes.nextVar;
        this.lastMoistureKalman = moistRes.data;

        if (this.proximityCm < 15.0) {
          this.obstaclesEncountered++;
          this.replansCount++;
          this.roverState = 'AVOIDING_OBSTACLE';
          this.previousPath = [...this.plannedPath];
          this.blockedObstacle = { x: next.x, y: next.y };
          this.logEvent('sensor_trigger', [next.x, next.y], 'proximity_detect', 'OBSTACLE_AVOIDANCE', {
            proximity_cm: this.proximityCm,
            message: `Obstacle encountered ahead at (${next.x}, ${next.y})!`,
          });
          return this.getTelemetry();
        }

        // Kinematics & PID calculation
        const radMap: Record<HeadingDirection, number> = {
          E: 0.0,
          N: Math.PI / 2,
          W: Math.PI,
          S: -Math.PI / 2,
        };
        const targetTheta = radMap[this.roverHeading];
        this.angularVelocity = this.computePid(this.pose.theta, targetTheta);
        this.linearVelocity = 0.3;
        this.pose.theta += this.angularVelocity * 0.2;
        this.pose.x += this.linearVelocity * Math.cos(this.pose.theta) * 0.2;
        this.pose.y += this.linearVelocity * Math.sin(this.pose.theta) * 0.2;

        this.roverCoord = next;
        this.pathIndex++;
        this.visitedCells.add(this.key(next.x, next.y));
        this.totalSteps++;

        if (this.roverCoord.x === this.currentTarget?.x && this.roverCoord.y === this.currentTarget?.y) {
          this.roverState = 'EXECUTING_TASK';
        }
      }
    } else if (this.roverState === 'AVOIDING_OBSTACLE') {
      if (this.currentTarget) {
        const replan = this.planAStar(this.roverCoord, this.currentTarget);
        if (replan.length > 0) {
          if (!this.previousPath) {
            this.previousPath = [...this.plannedPath];
          }
          this.plannedPath = replan;
          this.pathIndex = 0;
          this.roverState = 'MOVING';
          this.logEvent('navigation', [this.currentTarget.x, this.currentTarget.y], 'replan_path', 'SUCCESS', {
            new_path_length: replan.length,
          });
        } else {
          if (this.currentTask) {
            this.currentTask.completed = true;
            this.currentTask.active = false;
            this.currentTask = null;
          }
          this.roverState = 'PLANNING';
        }
      }
    } else if (this.roverState === 'EXECUTING_TASK') {
      if (this.currentTask) {
        const target = this.currentTask.target;
        const cell = this.cells.get(this.key(target[0], target[1]));
        if (cell) {
          if (this.currentTask.action_type === 'watering' && cell.plant_info) {
            const oldM = cell.plant_info.moisture;
            cell.plant_info.moisture = 60;
            cell.plant_info.watered = true;
            this.plantsWatered++;
            this.logEvent('action_executed', target, 'watering', 'SUCCESS', {
              message: `Watered plant at (${target[0]}, ${target[1]}): moisture raised from ${oldM}% to 60%`,
            });
          } else if (this.currentTask.action_type === 'weed_clearing') {
            cell.cleared_weed = true;
            cell.entity_type = 'empty';
            this.weedsCleared++;
            this.logEvent('action_executed', target, 'weed_clearing', 'SUCCESS', {
              message: `Cleared invasive weed at (${target[0]}, ${target[1]})`,
            });
          } else if (this.currentTask.action_type === 'plant_inspection' && cell.plant_info) {
            cell.plant_info.inspected = true;
            this.plantsInspected++;
            this.logEvent('action_executed', target, 'plant_inspection', 'SUCCESS', {
              message: `Inspected crop at (${target[0]}, ${target[1]}): status '${cell.plant_info.health}' (confidence ${(cell.plant_info.confidence * 100).toFixed(1)}%)`,
            });
          }
          this.currentTask.completed = true;
          this.currentTask.active = false;
        }
        this.currentTask = null;
        this.plannedPath = [];
        this.currentTarget = null;
        this.roverState = 'PLANNING';
      }
    }

    return this.getTelemetry();
  }

  toggleObstacle(x: number, y: number): boolean {
    const k = this.key(x, y);
    const cell = this.cells.get(k);
    if (!cell) return false;
    if (cell.entity_type === 'obstacle') {
      cell.entity_type = 'empty';
      return true;
    } else if (cell.entity_type === 'empty' && !(x === this.roverCoord.x && y === this.roverCoord.y)) {
      cell.entity_type = 'obstacle';
      // If dynamic obstacle blocks current path, preserve old path and replan immediately
      const blocks = this.plannedPath.some(p => p.x === x && p.y === y);
      if (blocks) {
        this.previousPath = [...this.plannedPath];
        this.blockedObstacle = { x, y };
        if (this.currentTarget) {
          const replan = this.planAStar(this.roverCoord, this.currentTarget);
          if (replan.length > 0) {
            this.plannedPath = replan;
            this.pathIndex = 0;
            this.roverState = 'MOVING';
            this.replansCount++;
            this.obstaclesEncountered++;
            this.logEvent('navigation', [this.currentTarget.x, this.currentTarget.y], 'replan_path', 'SUCCESS', {
              new_path_length: replan.length,
              reason: 'dynamic_obstacle_placed',
            });
          }
        }
      }
      return true;
    }
    return false;
  }

  getTelemetry(): SimulationTelemetry {
    const L = 0.25;
    const r = 0.05;
    const v_l = this.linearVelocity - (this.angularVelocity * L) / 2.0;
    const v_r = this.linearVelocity + (this.angularVelocity * L) / 2.0;

    const cellList: GridCell[] = [];
    this.cells.forEach(c => cellList.push(c));

    let duration = 0.0;
    if (this.missionStartTime) {
      const end = this.missionEndTime ?? Date.now() / 1000;
      duration = Number((end - this.missionStartTime).toFixed(1));
    }

    return {
      rover: {
        coordinate: [this.roverCoord.x, this.roverCoord.y],
        heading: this.roverHeading,
        state: this.roverState,
        battery: Number(this.battery.toFixed(1)),
        proximity_cm: Number(this.proximityCm.toFixed(1)),
        current_target: this.currentTarget ? [this.currentTarget.x, this.currentTarget.y] : null,
        planned_path: this.plannedPath.map(p => [p.x, p.y]),
        previous_path: this.previousPath ? this.previousPath.map(p => [p.x, p.y]) : null,
        blocked_obstacle: this.blockedObstacle ? [this.blockedObstacle.x, this.blockedObstacle.y] : null,
      },
      kinematics: {
        pose_meters: {
          x: Number(this.pose.x.toFixed(3)),
          y: Number(this.pose.y.toFixed(3)),
          theta_deg: Number(((this.pose.theta * 180) / Math.PI).toFixed(1)),
        },
        linear_velocity_mps: Number(this.linearVelocity.toFixed(2)),
        angular_velocity_radps: Number(this.angularVelocity.toFixed(2)),
        wheel_velocities: {
          v_left_mps: Number(v_l.toFixed(3)),
          v_right_mps: Number(v_r.toFixed(3)),
          omega_left_radps: Number((v_l / r).toFixed(2)),
          omega_right_radps: Number((v_r / r).toFixed(2)),
        },
        pid_steering: this.lastPid,
      },
      cv_inspection: {
        detected: true,
        classification: 'crop',
        health_status: 'healthy',
        confidence: 0.96,
        vegetation_coverage: 0.148,
        mean_excess_green: 142.5,
        chlorosis_ratio: 0.0,
        chlorosis_threshold: 0.15,
        is_diseased: false,
        contour_solidity: 0.78,
      },
      kalman: {
        moisture: this.lastMoistureKalman,
        proximity: this.lastProximityKalman,
        noise_enabled: this.noiseEnabled,
        moisture_sigma: this.moistureSigma,
        proximity_sigma: this.proximitySigma,
      },
      metrics: {
        mission_duration_seconds: duration,
        cells_visited_count: this.visitedCells.size,
        total_path_steps: this.totalSteps,
        weeds_cleared_count: this.weedsCleared,
        plants_inspected_count: this.plantsInspected,
        plants_watered_count: this.plantsWatered,
        obstacles_encountered_count: this.obstaclesEncountered,
        replans_count: this.replansCount,
      },
      tasks: this.tasks,
      world: {
        width: this.width,
        height: this.height,
        scenario: this.scenarioName,
        rover_start: [0, 0],
        cells: cellList,
      },
      events: this.events.slice(0, 30),
    };
  }
}
