"""ROS 2 World Simulator Node for Agri-Doctor Robot.

Publishes:
- /agri/world_state: Complete 6x4 field grid state (entities, moisture levels, plants)
- /agri/sensor/moisture: Capacitive soil moisture readings at current robot coordinate
- /agri/sensor/obstacle_distance: Ultrasonic proximity sensor range (cm)
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Optional

from robotics.agri_doctor.models import Coordinate, EntityType
from robotics.agri_doctor.world import FieldWorld
from robotics.ros_nodes.ros_compat import BaseAgriNode, HAS_RCLPY

logger = logging.getLogger("AgriDoctor.WorldSimulatorNode")


class WorldSimulatorNode(BaseAgriNode):
    """ROS 2 Node that manages the agricultural world grid and simulates environmental sensors."""

    def __init__(self, scenario_name: str = "mixed_field", publish_rate_hz: float = 2.0):
        super().__init__("world_simulator_node")
        self.world = FieldWorld(6, 4)
        self.world.load_scenario(scenario_name)
        self.publish_rate_hz = publish_rate_hz

        # Publishers
        self.pub_world_state = self.create_publisher(
            msg_type="std_msgs/msg/String",
            topic="/agri/world_state",
            qos_profile=10,
        )
        self.pub_moisture = self.create_publisher(
            msg_type="std_msgs/msg/String",
            topic="/agri/sensor/moisture",
            qos_profile=10,
        )
        self.pub_obstacle_dist = self.create_publisher(
            msg_type="std_msgs/msg/String",
            topic="/agri/sensor/obstacle_distance",
            qos_profile=10,
        )

        # Periodic publication timer
        self.timer = self.create_timer(1.0 / self.publish_rate_hz, self._timer_callback)
        self.get_logger().info(
            f"WorldSimulatorNode started with scenario='{scenario_name}' at {self.publish_rate_hz}Hz"
        )

    def _timer_callback(self) -> None:
        """Publishes synchronized field state and sensor values."""
        # 1. World State
        grid_data = []
        for y in range(self.world.height):
            row_cells = []
            for x in range(self.world.width):
                coord = Coordinate(x, y)
                cell = self.world.get_cell(coord)
                if cell:
                    row_cells.append({
                        "x": x,
                        "y": y,
                        "entity": cell.entity_type.value,
                        "moisture": round(cell.plant_info.moisture, 1) if cell.plant_info else 50.0,
                        "health": cell.plant_info.health.value if cell.plant_info else None,
                    })
            grid_data.append(row_cells)

        world_msg = self.create_string_message({
            "timestamp": time.time(),
            "width": self.world.width,
            "height": self.world.height,
            "grid": grid_data,
        })
        self.pub_world_state.publish(world_msg)

        # 2. Moisture at rover anchor (0, 0)
        cell = self.world.get_cell(Coordinate(0, 0))
        moisture_val = cell.plant_info.moisture if cell and cell.plant_info else 50.0
        moisture_msg = self.create_string_message({
            "timestamp": time.time(),
            "coordinate": {"x": 0, "y": 0},
            "sensor": "capacitive_soil_moisture_v1.2",
            "moisture_percent": moisture_val,
            "is_dry": moisture_val < 30.0,
        })
        self.pub_moisture.publish(moisture_msg)

        # 3. Obstacle proximity distance
        obstacle_msg = self.create_string_message({
            "timestamp": time.time(),
            "sensor": "ultrasonic_hcsr04",
            "min_distance_cm": 42.5,
            "threshold_cm": 15.0,
            "is_collision_risk": False,
        })
        self.pub_obstacle_dist.publish(obstacle_msg)


def main(args: Optional[list] = None) -> None:
    node = WorldSimulatorNode()
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
        print("[Standalone Mode] Running WorldSimulatorNode for 2 sample cycles...")
        for _ in range(2):
            node._timer_callback()
            time.sleep(0.05)
        node.destroy_node()
        print("[Standalone Mode] WorldSimulatorNode execution test passed.")


if __name__ == "__main__":
    main()
