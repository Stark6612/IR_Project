"""ROS 2 Perception Node for Agri-Doctor Robot.

Subscribes to:
- /agri/world_state
- /agri/sensor/moisture
- /agri/sensor/obstacle_distance

Publishes:
- /agri/perception/detections: High-level agronomic and obstacle detections
  (e.g., Weed detected via ExG, Chlorosis detected via HSV hue, Drought detected via Capacitive sensor)
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any, Dict, List, Optional

from robotics.agri_doctor.cv_perception import CropComputerVisionPipeline
from robotics.agri_doctor.models import Coordinate, PlantHealth
from robotics.agri_doctor.perception_simulator import PerceptionSimulator
from robotics.agri_doctor.world import FieldWorld
from robotics.ros_nodes.ros_compat import BaseAgriNode, HAS_RCLPY

logger = logging.getLogger("AgriDoctor.PerceptionNode")


class PerceptionNode(BaseAgriNode):
    """ROS 2 Node that processes raw sensor streams and OpenCV vision data into actionable plant insights."""

    def __init__(self):
        super().__init__("perception_node")
        self.world = FieldWorld(6, 4)
        self.world.load_scenario("mixed_field")
        self.perception_sim = PerceptionSimulator(self.world)
        self.cv_pipeline = CropComputerVisionPipeline()

        # Cache of incoming states
        self.latest_world_grid: Optional[List[List[Dict[str, Any]]]] = None
        self.latest_moisture: Optional[Dict[str, Any]] = None
        self.latest_obstacle: Optional[Dict[str, Any]] = None

        # Subscriptions
        self.sub_world = self.create_subscription(
            msg_type="std_msgs/msg/String",
            topic="/agri/world_state",
            callback=self._handle_world_state,
            qos_profile=10,
        )
        self.sub_moisture = self.create_subscription(
            msg_type="std_msgs/msg/String",
            topic="/agri/sensor/moisture",
            callback=self._handle_moisture,
            qos_profile=10,
        )
        self.sub_obstacle = self.create_subscription(
            msg_type="std_msgs/msg/String",
            topic="/agri/sensor/obstacle_distance",
            callback=self._handle_obstacle,
            qos_profile=10,
        )

        # Publisher for agronomic detections
        self.pub_detections = self.create_publisher(
            msg_type="std_msgs/msg/String",
            topic="/agri/perception/detections",
            qos_profile=10,
        )

        # Processing loop timer (2 Hz)
        self.process_timer = self.create_timer(0.5, self._process_detections)
        self.get_logger().info("PerceptionNode initialized and listening for sensor telemetry")

    def _handle_world_state(self, msg: Any) -> None:
        try:
            data = json.loads(msg.data)
            self.latest_world_grid = data.get("grid")
        except Exception as e:
            self.get_logger().error(f"Failed to parse world state message: {e}")

    def _handle_moisture(self, msg: Any) -> None:
        try:
            self.latest_moisture = json.loads(msg.data)
        except Exception as e:
            self.get_logger().error(f"Failed to parse moisture message: {e}")

    def _handle_obstacle(self, msg: Any) -> None:
        try:
            self.latest_obstacle = json.loads(msg.data)
        except Exception as e:
            self.get_logger().error(f"Failed to parse obstacle message: {e}")

    def _process_detections(self) -> None:
        """Runs agronomic rules and synthetic OpenCV evaluation on current field items."""
        detections: List[Dict[str, Any]] = []

        # 1. Evaluate moisture alerts
        if self.latest_moisture and self.latest_moisture.get("is_dry"):
            detections.append({
                "type": "DROUGHT_STRESS",
                "sensor": "capacitive_moisture",
                "value": self.latest_moisture.get("moisture_percent"),
                "priority": "HIGH",
                "recommended_action": "WATER_CROP",
            })

        # 2. Evaluate obstacle proximity
        if self.latest_obstacle and self.latest_obstacle.get("is_collision_risk"):
            detections.append({
                "type": "COLLISION_RISK",
                "sensor": "ultrasonic",
                "distance_cm": self.latest_obstacle.get("min_distance_cm"),
                "priority": "SAFETY_P1",
                "recommended_action": "EMERGENCY_HALT",
            })

        # 3. Scan cached grid for weed and chlorosis targets using CV pipeline
        if self.latest_world_grid:
            for row in self.latest_world_grid:
                for cell in row:
                    coord = Coordinate(cell["x"], cell["y"])
                    entity = cell.get("entity")
                    health = cell.get("health")

                    if entity == "WEED":
                        # Run OpenCV weed classification
                        img = self.cv_pipeline.generate_synthetic_leaf(is_weed=True)
                        cv_res = self.cv_pipeline.classify_leaf(img)
                        detections.append({
                            "type": "WEED_DETECTED",
                            "coordinate": {"x": coord.x, "y": coord.y},
                            "cv_exg_mean": cv_res.exg_mean,
                            "is_weed": cv_res.is_weed,
                            "recommended_action": "MECHANICAL_WEEDING",
                        })
                    elif entity == "PLANT" and health == "CHLOROTIC":
                        img = self.cv_pipeline.generate_synthetic_leaf(is_chlorotic=True)
                        cv_res = self.cv_pipeline.classify_leaf(img)
                        detections.append({
                            "type": "CHLOROSIS_DETECTED",
                            "coordinate": {"x": coord.x, "y": coord.y},
                            "chlorosis_ratio": cv_res.chlorosis_ratio,
                            "diagnosis": "Nitrogen / Iron Deficiency",
                            "recommended_action": "INSPECT_AND_LOG",
                        })

        # Publish synthesized detections
        detection_msg = self.create_string_message({
            "timestamp": time.time(),
            "count": len(detections),
            "detections": detections,
        })
        self.pub_detections.publish(detection_msg)


def main(args: Optional[list] = None) -> None:
    node = PerceptionNode()
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
        print("[Standalone Mode] Running PerceptionNode for 2 evaluation cycles...")
        node._process_detections()
        time.sleep(0.05)
        node._process_detections()
        node.destroy_node()
        print("[Standalone Mode] PerceptionNode execution test passed.")


if __name__ == "__main__":
    main()
