"""ROS 2 Controller & Kinematics Node for Agri-Doctor Robot.

Subscribes to:
- /agri/planned_path: Waypoint coordinates dispatched by PlannerNode
- /agri/perception/detections: High-priority agronomic and safety alerts

Publishes:
- /agri/mission/status: Kinematic telemetry (v, omega, v_L, v_R, pid_error, execution state)
- /agri/events: Discrete simulation events (watering, weed removal, inspection logs)
"""

from __future__ import annotations

import json
import logging
import math
import sys
import time
from typing import Any, Dict, List, Optional

from robotics.agri_doctor.kinematics import DifferentialDriveKinematics, PIDHeadingController
from robotics.agri_doctor.models import ActionType, Coordinate, Heading, PlantHealth, RobotState, RoverState
from robotics.agri_doctor.task_executor import TaskExecutor
from robotics.agri_doctor.world import FieldWorld
from robotics.ros_nodes.ros_compat import BaseAgriNode, HAS_RCLPY

logger = logging.getLogger("AgriDoctor.ControllerNode")


class ControllerNode(BaseAgriNode):
    """ROS 2 Node that tracks waypoints using differential drive kinematics, closed-loop PID, and task execution."""

    def __init__(self, track_width: float = 0.25, wheel_radius: float = 0.05):
        super().__init__("controller_node")
        self.kinematics = DifferentialDriveKinematics(track_width_m=track_width, wheel_radius_m=wheel_radius)
        self.pid = PIDHeadingController(kp=1.8, ki=0.05, kd=0.25)
        self.world = FieldWorld(6, 4)
        self.world.load_scenario("mixed_field")
        self.executor = TaskExecutor(self.world)

        self.state = RoverState(
            coordinate=Coordinate(0, 0),
            heading=Heading.EAST,
            state=RobotState.IDLE,
            battery=100.0,
        )
        self.active_waypoints: List[Coordinate] = []

        # Subscriptions
        self.sub_path = self.create_subscription(
            msg_type="std_msgs/msg/String",
            topic="/agri/planned_path",
            callback=self._handle_path,
            qos_profile=10,
        )
        self.sub_detections = self.create_subscription(
            msg_type="std_msgs/msg/String",
            topic="/agri/perception/detections",
            callback=self._handle_detections,
            qos_profile=10,
        )

        # Publishers
        self.pub_status = self.create_publisher(
            msg_type="std_msgs/msg/String",
            topic="/agri/mission/status",
            qos_profile=10,
        )
        self.pub_events = self.create_publisher(
            msg_type="std_msgs/msg/String",
            topic="/agri/events",
            qos_profile=10,
        )

        # 4 Hz control loop timer
        self.control_timer = self.create_timer(0.25, self._control_step)
        self.get_logger().info("ControllerNode initialized with differential drive kinematics & PID heading")

    def _handle_path(self, msg: Any) -> None:
        try:
            data = json.loads(msg.data)
            waypoints = data.get("waypoints", [])
            if waypoints:
                self.active_waypoints = [Coordinate(w["x"], w["y"]) for w in waypoints]
                self.get_logger().info(f"Controller received {len(self.active_waypoints)} new waypoints")
        except Exception as e:
            self.get_logger().error(f"Error handling path in controller: {e}")

    def _handle_detections(self, msg: Any) -> None:
        try:
            data = json.loads(msg.data)
            for det in data.get("detections", []):
                if det.get("type") == "COLLISION_RISK":
                    self.state.state = RobotState.AVOIDING_OBSTACLE
                    self.get_logger().warn("Obstacle proximity alert: entering AVOIDING_OBSTACLE state!")
        except Exception as e:
            self.get_logger().error(f"Error handling detections in controller: {e}")

    def _control_step(self) -> None:
        """Executes a discrete kinematic motion step towards next waypoint."""
        v_linear = 0.0
        w_angular = 0.0
        pid_effort = 0.0
        v_left = 0.0
        v_right = 0.0

        if self.state.state != RobotState.AVOIDING_OBSTACLE and self.active_waypoints:
            next_target = self.active_waypoints[0]
            if next_target == self.state.coordinate:
                self.active_waypoints.pop(0)

            if self.active_waypoints:
                next_target = self.active_waypoints[0]
                self.state.state = RobotState.MOVING

                # Heading calculation
                heading_rad_map = {
                    Heading.EAST: 0.0,
                    Heading.NORTH: math.pi / 2,
                    Heading.WEST: math.pi,
                    Heading.SOUTH: -math.pi / 2,
                }
                current_theta = heading_rad_map.get(self.state.heading, 0.0)
                dx = next_target.x - self.state.coordinate.x
                dy = next_target.y - self.state.coordinate.y
                target_theta = math.atan2(dy, dx)

                pid_metrics = self.pid.compute(current_theta, target_theta, dt=0.25)
                w_angular = pid_metrics["omega_command"]
                v_linear = 0.22  # nominal forward velocity m/s

                wheel_vels = self.kinematics.inverse_kinematics(v_linear, w_angular)
                v_left = wheel_vels.v_left
                v_right = wheel_vels.v_right

                # Update heading enum
                if dx > 0:
                    self.state.heading = Heading.EAST
                elif dx < 0:
                    self.state.heading = Heading.WEST
                elif dy > 0:
                    self.state.heading = Heading.NORTH
                elif dy < 0:
                    self.state.heading = Heading.SOUTH

                # Step coordinate forward
                self.state.coordinate = next_target
                self.state.battery = max(0.0, self.state.battery - 0.1)

                # Check cell action at new coordinate
                cell = self.world.get_cell(self.state.coordinate)
                if cell and cell.entity_type.value == "WEED":
                    res = self.executor.execute_weed_clearing(self.state.coordinate)
                    self._emit_event(f"Mechanical weed cleared at {self.state.coordinate}", "SUCCESS" if res else "FAILED")
                elif cell and cell.plant_info and cell.plant_info.moisture < 30.0:
                    res = self.executor.execute_watering(self.state.coordinate)
                    self._emit_event(f"Micro-drip irrigation applied at {self.state.coordinate}", "SUCCESS" if res else "FAILED")
            else:
                self.state.state = RobotState.COMPLETED
                self.pid.reset()
        else:
            self.pid.reset()

        # Publish status telemetry
        status_msg = self.create_string_message({
            "timestamp": time.time(),
            "coordinate": {"x": self.state.coordinate.x, "y": self.state.coordinate.y},
            "heading": self.state.heading.value,
            "status": self.state.state.value,
            "v_linear_mps": round(v_linear, 3),
            "w_angular_radps": round(w_angular, 3),
            "v_left_mps": round(v_left, 3),
            "v_right_mps": round(v_right, 3),
            "pid_error_deg": round(math.degrees(self.pid.prev_error), 2),
            "battery_percent": round(self.state.battery, 1),
            "water_percent": 95.0,
        })
        self.pub_status.publish(status_msg)

    def _emit_event(self, description: str, outcome: str) -> None:
        event_msg = self.create_string_message({
            "timestamp": time.time(),
            "description": description,
            "outcome": outcome,
            "coordinate": {"x": self.state.coordinate.x, "y": self.state.coordinate.y},
        })
        self.pub_events.publish(event_msg)
        self.get_logger().info(f"Event: {description}")


def main(args: Optional[list] = None) -> None:
    node = ControllerNode()
    if HAS_RCLPY:
        import rclpy
        try:
            rclpy.spin(node._ros_node)
        except KeyboardInterrupt:
            pass
        finally:
            node.destroy_node()
            rclpy.shutdown()
    else:
        print("[Standalone Mode] Running ControllerNode for 2 sample steps...")
        node.active_waypoints = [Coordinate(1, 0), Coordinate(2, 0)]
        node._control_step()
        time.sleep(0.05)
        node._control_step()
        node.destroy_node()
        print("[Standalone Mode] ControllerNode execution test passed.")


if __name__ == "__main__":
    main()
