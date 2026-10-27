"""Robot controller state machine and simulation step engine."""

from __future__ import annotations
import time
from typing import Set, List, Optional, Dict, Any
from .models import (
    Coordinate,
    Heading,
    RobotState,
    ActionType,
    PlantHealth,
    RoverState,
    Task,
    SimulationEvent,
)
from .world import FieldWorld
from .a_star import AStarPlanner
from .perception_simulator import PerceptionSimulator
from .task_executor import TaskExecutor
from .mission_planner import MissionPlanner
from .kinematics import (
    DifferentialDriveKinematics,
    PIDHeadingController,
    RobotPose2D,
    WheelVelocities,
)
from .cv_perception import CropComputerVisionPipeline
import math


class RobotController:
    """Controls the Agri-Doctor Rover lifecycle, kinematics, navigation, and mission state transitions."""

    def __init__(self, world: FieldWorld):
        self.world = world
        self.planner = AStarPlanner(width=world.width, height=world.height)
        self.perception = PerceptionSimulator(world)
        self.executor = TaskExecutor(world)
        self.mission_planner = MissionPlanner(world)

        # Kinematics and Control Subsystems
        self.kinematics = DifferentialDriveKinematics(track_width_m=0.25, wheel_radius_m=0.05)
        self.pid_heading = PIDHeadingController(kp=1.8, ki=0.05, kd=0.25)
        self.cv_pipeline = CropComputerVisionPipeline()

        # Continuous Kinematic Pose: x (meters), y (meters), theta (radians)
        # 1 grid cell = 0.5 meters
        cell_size = 0.5
        self.rover_pose = RobotPose2D(
            x=world.rover_start.x * cell_size,
            y=world.rover_start.y * cell_size,
            theta=0.0,  # Facing East initially
        )
        self.linear_velocity = 0.0  # m/s
        self.angular_velocity = 0.0  # rad/s
        self.wheel_velocities = WheelVelocities(0.0, 0.0, 0.0, 0.0)
        self.last_pid_metrics: Dict[str, Any] = {
            "error_deg": 0.0,
            "p_term": 0.0,
            "i_term": 0.0,
            "d_term": 0.0,
            "omega_command": 0.0,
        }
        self.latest_cv_inspection: Optional[Dict[str, Any]] = None
        self.latest_proximity_data = self.perception.read_proximity(world.rover_start, Heading.EAST)
        self.latest_moisture_data = self.perception.read_soil_moisture(world.rover_start)

        # Rover physical state
        self.rover = RoverState(coordinate=world.rover_start)

        # Active mission state
        self.current_task: Optional[Task] = None
        self.path_index: int = 0

        # Metrics tracking
        self.visited_cells: Set[Coordinate] = {world.rover_start}
        self.weeds_cleared_count: int = 0
        self.plants_inspected_count: int = 0
        self.plants_watered_count: int = 0
        self.obstacles_encountered_count: int = 0
        self.replans_count: int = 0
        self.mission_start_time: Optional[float] = None
        self.mission_end_time: Optional[float] = None
        self.total_path_steps: int = 0

    def reset(self, scenario_name: Optional[str] = None) -> None:
        """Resets the world and rover back to initial scenario state."""
        if scenario_name:
            self.world.load_scenario(scenario_name)
        elif self.world.scenario_name != "custom":
            self.world.load_scenario(self.world.scenario_name)

        self.rover = RoverState(coordinate=self.world.rover_start)
        self.current_task = None
        self.path_index = 0
        self.visited_cells = {self.world.rover_start}
        self.weeds_cleared_count = 0
        self.plants_inspected_count = 0
        self.plants_watered_count = 0
        self.obstacles_encountered_count = 0
        self.replans_count = 0
        self.mission_start_time = None
        self.mission_end_time = None
        self.total_path_steps = 0
        self.executor.event_log.clear()
        self.mission_planner.scan_and_generate_tasks()
        self.latest_proximity_data = self.perception.read_proximity(self.rover.coordinate, self.rover.heading)
        self.latest_moisture_data = self.perception.read_soil_moisture(self.rover.coordinate)

        self.executor.log_event(
            event_type="system",
            target=self.rover.coordinate,
            action="reset",
            outcome="SUCCESS",
            details={"scenario": self.world.scenario_name},
        )

    def start_mission(self) -> None:
        """Starts mission execution."""
        if self.rover.state in (RobotState.IDLE, RobotState.COMPLETED, RobotState.ERROR):
            self.mission_planner.scan_and_generate_tasks()
            self.mission_start_time = time.time()
            self.mission_end_time = None
            self.rover.state = RobotState.PLANNING

            self.executor.log_event(
                event_type="mission_state",
                target=self.rover.coordinate,
                action="start_mission",
                outcome="SUCCESS",
                details={"tasks_count": len(self.mission_planner.tasks)},
            )

    def pause_mission(self) -> None:
        """Pauses the rover execution."""
        if self.rover.state not in (RobotState.IDLE, RobotState.COMPLETED, RobotState.PAUSED):
            self.rover.state = RobotState.PAUSED
            self.executor.log_event(
                event_type="mission_state",
                target=self.rover.coordinate,
                action="pause",
                outcome="PAUSED",
            )

    def resume_mission(self) -> None:
        """Resumes a paused mission."""
        if self.rover.state == RobotState.PAUSED:
            if self.current_task:
                self.rover.state = RobotState.MOVING if self.rover.planned_path else RobotState.PLANNING
            else:
                self.rover.state = RobotState.PLANNING

            self.executor.log_event(
                event_type="mission_state",
                target=self.rover.coordinate,
                action="resume",
                outcome="RESUMED",
            )

    def stop_mission(self) -> None:
        """Stops the mission immediately."""
        self.rover.state = RobotState.IDLE
        self.mission_end_time = time.time()
        self.executor.log_event(
            event_type="mission_state",
            target=self.rover.coordinate,
            action="stop",
            outcome="STOPPED",
        )

    def _determine_heading(self, current: Coordinate, next_pos: Coordinate) -> Heading:
        if next_pos.x > current.x:
            return Heading.EAST
        elif next_pos.x < current.x:
            return Heading.WEST
        elif next_pos.y > current.y:
            return Heading.NORTH
        elif next_pos.y < current.y:
            return Heading.SOUTH
        return self.rover.heading

    def step(self) -> Dict[str, Any]:
        """
        Executes one discrete simulation tick of the robot controller state machine.
        Returns the snapshot of telemetry and current state.
        """
        # Consume minimal battery estimate per tick (0.05% per step)
        if self.rover.state not in (RobotState.IDLE, RobotState.PAUSED, RobotState.COMPLETED):
            self.rover.battery = max(0.0, self.rover.battery - 0.05)

        # ---------------- State: PLANNING ----------------
        if self.rover.state == RobotState.PLANNING:
            next_task = self.mission_planner.get_next_task(self.rover.coordinate)
            if not next_task:
                # No more tasks available; mission is complete!
                self.rover.state = RobotState.COMPLETED
                self.mission_end_time = time.time()
                self.executor.log_event(
                    event_type="mission_state",
                    target=self.rover.coordinate,
                    action="complete_mission",
                    outcome="SUCCESS",
                    details={"summary": "All prioritized agricultural tasks fulfilled."},
                )
                return self.get_telemetry()

            self.current_task = next_task
            self.current_task.active = True
            self.rover.current_target = next_task.target

            # Plan A* path to target
            blocked_coords = self.world.get_blocked_coordinates()
            plan_res = self.planner.plan(
                start=self.rover.coordinate,
                goal=next_task.target,
                blocked=blocked_coords,
            )

            if plan_res.success and plan_res.path:
                self.rover.planned_path = plan_res.path
                self.path_index = 0
                self.rover.state = RobotState.MOVING
            else:
                # Goal unreachable
                self.executor.log_event(
                    event_type="navigation_error",
                    target=next_task.target,
                    action="plan_path",
                    outcome="UNREACHABLE",
                    details={"message": f"Target at {next_task.target} blocked or unreachable. Skipping task."},
                )
                self.current_task.completed = True
                self.current_task.active = False
                self.current_task = None
                self.rover.state = RobotState.PLANNING

        # ---------------- State: MOVING ----------------
        elif self.rover.state == RobotState.MOVING:
            if not self.rover.planned_path:
                self.rover.state = RobotState.PLANNING
                return self.get_telemetry()

            # If rover is already at the target cell
            if self.rover.coordinate == self.rover.current_target:
                self.rover.state = RobotState.EXECUTING_TASK
                return self.get_telemetry()

            # Advance to next waypoint
            if self.path_index + 1 < len(self.rover.planned_path):
                next_cell = self.rover.planned_path[self.path_index + 1]

                # Update heading towards next cell
                self.rover.heading = self._determine_heading(self.rover.coordinate, next_cell)

                # Check proximity sensor for unexpected obstacle in heading direction
                prox_data = self.perception.read_proximity(self.rover.coordinate, self.rover.heading)
                self.latest_proximity_data = prox_data
                self.rover.proximity_cm = prox_data["distance_filtered"]
                self.latest_moisture_data = self.perception.read_soil_moisture(self.rover.coordinate)

                if prox_data["obstacle_triggered"]:
                    # An obstacle is blocking the immediate path
                    self.obstacles_encountered_count += 1
                    self.replans_count += 1
                    self.rover.state = RobotState.AVOIDING_OBSTACLE
                    self.rover.previous_path = list(self.rover.planned_path)
                    self.rover.blocked_obstacle = next_cell
                    self.executor.log_event(
                        event_type="sensor_trigger",
                        target=next_cell,
                        action="proximity_detect",
                        outcome="OBSTACLE_AVOIDANCE",
                        details={"proximity_cm": prox_data["distance_cm"], "message": f"Obstacle encountered ahead at {next_cell}!"},
                    )
                    return self.get_telemetry()

                # Move rover
                self.rover.coordinate = next_cell
                self.path_index += 1
                self.visited_cells.add(next_cell)
                self.total_path_steps += 1

                # Kinematics & PID calculation for this motion step
                heading_rad_map = {
                    Heading.EAST: 0.0,
                    Heading.NORTH: math.pi / 2,
                    Heading.WEST: math.pi,
                    Heading.SOUTH: -math.pi / 2,
                }
                target_theta = heading_rad_map.get(self.rover.heading, 0.0)
                self.last_pid_metrics = self.pid_heading.compute(
                    current_theta=self.rover_pose.theta,
                    target_theta=target_theta,
                    dt=0.2,
                )
                self.angular_velocity = self.last_pid_metrics["omega_command"]
                self.linear_velocity = 0.3  # Nominal 0.3 m/s forward speed
                self.wheel_velocities = self.kinematics.inverse_kinematics(
                    v=self.linear_velocity,
                    omega=self.angular_velocity,
                )
                self.rover_pose = self.kinematics.integrate_odometry(
                    pose=self.rover_pose,
                    v=self.linear_velocity,
                    omega=self.angular_velocity,
                    dt=0.2,
                )

                # Check if arrived at target
                if self.rover.coordinate == self.rover.current_target:
                    self.rover.state = RobotState.EXECUTING_TASK

        # ---------------- State: AVOIDING_OBSTACLE ----------------
        elif self.rover.state == RobotState.AVOIDING_OBSTACLE:
            if not self.current_task:
                self.rover.state = RobotState.PLANNING
                return self.get_telemetry()

            # Replan with current blocked obstacles
            blocked_coords = self.world.get_blocked_coordinates()
            replan_res = self.planner.plan(
                start=self.rover.coordinate,
                goal=self.current_task.target,
                blocked=blocked_coords,
            )

            if replan_res.success and replan_res.path:
                if not self.rover.previous_path:
                    self.rover.previous_path = list(self.rover.planned_path)
                self.rover.planned_path = replan_res.path
                self.path_index = 0
                self.rover.state = RobotState.MOVING
                self.executor.log_event(
                    event_type="navigation",
                    target=self.current_task.target,
                    action="replan_path",
                    outcome="SUCCESS",
                    details={"new_path_length": len(replan_res.path)},
                )
            else:
                self.executor.log_event(
                    event_type="navigation_error",
                    target=self.current_task.target,
                    action="replan_path",
                    outcome="FAILED",
                    details={"reason": "Cannot navigate around obstacle to current target. Aborting task."},
                )
                self.current_task.completed = True
                self.current_task.active = False
                self.current_task = None
                self.rover.state = RobotState.PLANNING

        # ---------------- State: EXECUTING_TASK ----------------
        elif self.rover.state == RobotState.EXECUTING_TASK:
            if not self.current_task:
                self.rover.state = RobotState.PLANNING
                return self.get_telemetry()

            # Execute real-time OpenCV computer vision inspection on target patch
            target = self.current_task.target
            target_cell = self.world.get_cell(target)
            if target_cell:
                patch = self.cv_pipeline.generate_synthetic_crop_patch(
                    entity_type=target_cell.entity_type,
                    health=target_cell.plant_info.health if target_cell.plant_info else PlantHealth.HEALTHY,
                    moisture=target_cell.plant_info.moisture if target_cell.plant_info else 65,
                )
                self.latest_cv_inspection = self.cv_pipeline.analyze_patch(patch)

            # Perform action via TaskExecutor
            action = self.current_task.action_type
            success = self.executor.execute_task(action, target)

            if success:
                if action == ActionType.WATERING:
                    self.plants_watered_count += 1
                elif action == ActionType.WEED_CLEARING:
                    self.weeds_cleared_count += 1
                elif action == ActionType.PLANT_INSPECTION:
                    self.plants_inspected_count += 1

            self.mission_planner.mark_task_complete(self.current_task.task_id)
            self.current_task = None
            self.rover.planned_path = []
            self.rover.current_target = None

            # Transition back to PLANNING for next task
            self.rover.state = RobotState.PLANNING

        return self.get_telemetry()

    def get_telemetry(self) -> Dict[str, Any]:
        """Provides full telemetry snapshot for UI and metrics export."""
        now = time.time()
        duration = 0.0
        if self.mission_start_time:
            end = self.mission_end_time or now
            duration = round(end - self.mission_start_time, 2)

        return {
            "rover": {
                "coordinate": self.rover.coordinate.to_tuple(),
                "heading": self.rover.heading.value,
                "state": self.rover.state.value,
                "battery": round(self.rover.battery, 1),
                "proximity_cm": round(self.rover.proximity_cm, 1),
                "current_target": self.rover.current_target.to_tuple() if self.rover.current_target else None,
                "planned_path": [c.to_tuple() for c in self.rover.planned_path],
                "previous_path": [c.to_tuple() for c in self.rover.previous_path] if self.rover.previous_path else None,
                "blocked_obstacle": self.rover.blocked_obstacle.to_tuple() if self.rover.blocked_obstacle else None,
            },
            "kinematics": {
                "pose_meters": {
                    "x": round(self.rover_pose.x, 3),
                    "y": round(self.rover_pose.y, 3),
                    "theta_deg": round(math.degrees(self.rover_pose.theta), 1),
                },
                "linear_velocity_mps": round(self.linear_velocity, 2),
                "angular_velocity_radps": round(self.angular_velocity, 2),
                "wheel_velocities": {
                    "v_left_mps": self.wheel_velocities.v_left,
                    "v_right_mps": self.wheel_velocities.v_right,
                    "omega_left_radps": self.wheel_velocities.omega_left,
                    "omega_right_radps": self.wheel_velocities.omega_right,
                },
                "pid_steering": self.last_pid_metrics,
            },
            "cv_inspection": self.latest_cv_inspection,
            "kalman": {
                "moisture": self.latest_moisture_data.get("kalman") if self.latest_moisture_data else None,
                "proximity": self.latest_proximity_data.get("kalman") if self.latest_proximity_data else None,
                "noise_enabled": self.perception.noise_enabled,
                "moisture_sigma": self.perception.moisture_sigma,
                "proximity_sigma": self.perception.proximity_sigma,
            },
            "metrics": {
                "mission_duration_seconds": duration,
                "cells_visited_count": len(self.visited_cells),
                "total_path_steps": self.total_path_steps,
                "weeds_cleared_count": self.weeds_cleared_count,
                "plants_inspected_count": self.plants_inspected_count,
                "plants_watered_count": self.plants_watered_count,
                "obstacles_encountered_count": self.obstacles_encountered_count,
                "replans_count": self.replans_count,
            },
            "tasks": self.mission_planner.to_list(),
            "world": self.world.to_dict(),
            "events": [e.to_dict() for e in self.executor.event_log[-30:]],  # Last 30 events
        }
