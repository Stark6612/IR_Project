"""ROS 2 Planner Node for Agri-Doctor Robot.

Subscribes to:
- /agri/world_state: Field layout, plant coordinates, and obstacle boundaries
- /agri/perception/detections: High-priority targets requiring navigation

Publishes:
- /agri/planned_path: Sequence of orthogonal grid waypoints computed via A* search
- /agri/robot_state: Current planner tracking and goal dispatch telemetry
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any, Dict, List, Optional

from robotics.agri_doctor.a_star import AStarPlanner
from robotics.agri_doctor.models import Coordinate, EntityType, Heading, RobotState, RoverState
from robotics.agri_doctor.world import FieldWorld
from robotics.ros_nodes.ros_compat import BaseAgriNode, HAS_RCLPY

logger = logging.getLogger("AgriDoctor.PlannerNode")


class PlannerNode(BaseAgriNode):
    """ROS 2 Node that computes optimal obstacle-free paths across the 6x4 field using A*."""

    def __init__(self):
        super().__init__("planner_node")
        self.planner = AStarPlanner()
        self.world = FieldWorld(6, 4)
        self.world.load_scenario("mixed_field")
        self.current_pos = Coordinate(0, 0)
        self.target_pos = Coordinate(5, 3)

        # Subscriptions
        self.sub_world = self.create_subscription(
            msg_type="std_msgs/msg/String",
            topic="/agri/world_state",
            callback=self._handle_world_update,
            qos_profile=10,
        )
        self.sub_detections = self.create_subscription(
            msg_type="std_msgs/msg/String",
            topic="/agri/perception/detections",
            callback=self._handle_detections,
            qos_profile=10,
        )

        # Publishers
        self.pub_planned_path = self.create_publisher(
            msg_type="std_msgs/msg/String",
            topic="/agri/planned_path",
            qos_profile=10,
        )
        self.pub_robot_state = self.create_publisher(
            msg_type="std_msgs/msg/String",
            topic="/agri/robot_state",
            qos_profile=10,
        )

        # Timer to generate or refresh planned path
        self.plan_timer = self.create_timer(1.0, self._publish_plan)
        self.get_logger().info("PlannerNode initialized using A* heuristic Manhattan planner")

    def _handle_world_update(self, msg: Any) -> None:
        try:
            data = json.loads(msg.data)
            grid_data = data.get("grid", [])
            for row in grid_data:
                for cell in row:
                    coord = Coordinate(cell["x"], cell["y"])
                    if cell.get("entity") == "OBSTACLE":
                        self.world.set_cell(coord, EntityType.OBSTACLE)
        except Exception as e:
            self.get_logger().error(f"Error updating world in planner: {e}")

    def _handle_detections(self, msg: Any) -> None:
        try:
            data = json.loads(msg.data)
            detections = data.get("detections", [])
            for det in detections:
                if det.get("type") in ("WEED_DETECTED", "CHLOROSIS_DETECTED"):
                    coord_dict = det.get("coordinate")
                    if coord_dict:
                        self.target_pos = Coordinate(coord_dict["x"], coord_dict["y"])
                        break
        except Exception as e:
            self.get_logger().error(f"Error handling detections in planner: {e}")

    def _publish_plan(self) -> None:
        """Computes path from current position to target position and publishes it."""
        blocked_coords = self.world.get_blocked_coordinates()
        path_result = self.planner.plan(self.current_pos, self.target_pos, blocked_coords)
        path = path_result.path

        path_msg = self.create_string_message({
            "timestamp": time.time(),
            "start": {"x": self.current_pos.x, "y": self.current_pos.y},
            "goal": {"x": self.target_pos.x, "y": self.target_pos.y},
            "path_found": path_result.success,
            "waypoints": [{"x": c.x, "y": c.y} for c in path],
            "step_count": len(path),
        })
        self.pub_planned_path.publish(path_msg)

        # Publish robot state
        state_msg = self.create_string_message({
            "timestamp": time.time(),
            "coordinate": {"x": self.current_pos.x, "y": self.current_pos.y},
            "heading": "EAST",
            "state": RobotState.PLANNING.value if len(path) > 0 else RobotState.IDLE.value,
            "battery_percent": 98.5,
        })
        self.pub_robot_state.publish(state_msg)


def main(args: Optional[list] = None) -> None:
    node = PlannerNode()
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
        print("[Standalone Mode] Running PlannerNode for 2 planning iterations...")
        node._publish_plan()
        time.sleep(0.05)
        node._publish_plan()
        node.destroy_node()
        print("[Standalone Mode] PlannerNode execution test passed.")


if __name__ == "__main__":
    main()
