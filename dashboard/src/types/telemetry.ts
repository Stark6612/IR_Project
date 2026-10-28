/**
 * Telemetry and Simulation TypeScript Data Contracts
 */

export type EntityType = 'empty' | 'plant' | 'weed' | 'obstacle';

export type PlantHealth = 'healthy' | 'suspected_disease' | 'needs_inspection';

export type RobotState =
  | 'IDLE'
  | 'PLANNING'
  | 'MOVING'
  | 'AVOIDING_OBSTACLE'
  | 'EXECUTING_TASK'
  | 'PAUSED'
  | 'COMPLETED'
  | 'ERROR';

export type HeadingDirection = 'N' | 'E' | 'S' | 'W';

export type ActionType =
  | 'watering'
  | 'weed_clearing'
  | 'plant_inspection'
  | 'patrol'
  | 'obstacle_avoidance';

export interface Coordinate {
  x: number;
  y: number;
}

export interface PlantInfo {
  moisture: number;
  health: PlantHealth;
  confidence: number;
  inspected: boolean;
  watered: boolean;
}

export interface GridCell {
  x: number;
  y: number;
  entity_type: EntityType;
  cleared_weed?: boolean;
  plant_info?: PlantInfo;
}

export interface TaskItem {
  task_id: string;
  priority: number;
  action_type: ActionType;
  target: [number, number];
  description: string;
  completed: boolean;
  active: boolean;
}

export interface SimulationEvent {
  timestamp: number;
  event_type: string;
  target: [number, number] | null;
  action: string;
  outcome: string;
  details: Record<string, any>;
}

export interface KinematicsData {
  pose_meters: {
    x: number;
    y: number;
    theta_deg: number;
  };
  linear_velocity_mps: number;
  angular_velocity_radps: number;
  wheel_velocities: {
    v_left_mps: number;
    v_right_mps: number;
    omega_left_radps: number;
    omega_right_radps: number;
  };
  pid_steering: {
    error_deg: number;
    p_term: number;
    i_term: number;
    d_term: number;
    omega_command: number;
  };
}

export interface UAVDroneMetadata {
  source: string;
  model: string;
  altitude_m: number;
  gsd_cm_px: number;
  map50: number;
  dataset: string;
}

export interface YoloDetection {
  class: string;
  confidence: number;
  bbox: [number, number, number, number];
}

export interface CVInspectionData {
  detected: boolean;
  classification: string;
  health_status: string;
  confidence: number;
  vegetation_pixels?: number;
  vegetation_coverage?: number;
  mean_excess_green?: number;
  chlorosis_ratio?: number;
  chlorosis_threshold?: number;
  is_diseased?: boolean;
  contour_solidity?: number;
  aspect_ratio?: number;
  image_base64?: string;
  target_coordinate?: [number, number];
  uav_drone?: UAVDroneMetadata;
  yolo_detections?: YoloDetection[];
}

export interface KalmanChannelData {
  ground_truth: number;
  measurement: number;
  estimate: number;
  gain: number;
  variance: number;
  innovation: number;
}

export interface KalmanTelemetryData {
  moisture?: KalmanChannelData | null;
  proximity?: KalmanChannelData | null;
  noise_enabled?: boolean;
  moisture_sigma?: number;
  proximity_sigma?: number;
}

export interface SimulationTelemetry {
  rover: {
    coordinate: [number, number];
    heading: HeadingDirection;
    state: RobotState;
    battery: number;
    proximity_cm: number;
    current_target: [number, number] | null;
    planned_path: [number, number][];
    previous_path?: [number, number][] | null;
    blocked_obstacle?: [number, number] | null;
  };
  kinematics?: KinematicsData;
  cv_inspection?: CVInspectionData | null;
  kalman?: KalmanTelemetryData | null;
  metrics: {
    mission_duration_seconds: number;
    cells_visited_count: number;
    total_path_steps: number;
    weeds_cleared_count: number;
    plants_inspected_count: number;
    plants_watered_count: number;
    obstacles_encountered_count: number;
    replans_count: number;
  };
  tasks: TaskItem[];
  world: {
    width: number;
    height: number;
    scenario: string;
    rover_start: [number, number];
    cells: GridCell[];
  };
  events: SimulationEvent[];
}
