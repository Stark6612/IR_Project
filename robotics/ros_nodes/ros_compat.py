"""ROS 2 Compatibility Layer for Agri-Doctor Robot.

Provides transparent abstraction between real ROS 2 (rclpy) and
a zero-dependency Windows standalone mock execution environment.
Allows all nodes to run on standard Python 3 on Windows 11 without ROS 2 installed,
while preserving authentic ROS 2 Node/Topic/Service semantics for academic defense.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("AgriDoctor.ROSCompat")

try:
    import rclpy
    from rclpy.node import Node as RealNode
    from std_msgs.msg import String as RealStringMsg
    HAS_RCLPY = True
except ImportError:
    HAS_RCLPY = False
    RealNode = object  # type: ignore
    RealStringMsg = None  # type: ignore


class MockStringMsg:
    """Mock std_msgs/msg/String message."""

    def __init__(self, data: str = ""):
        self.data = data

    def __repr__(self) -> str:
        return f"std_msgs.msg.String(data={self.data[:60]}...)" if len(self.data) > 60 else f"std_msgs.msg.String(data={self.data})"


class MockPublisher:
    """Mock ROS 2 Publisher logging published messages and triggering mock callbacks."""

    def __init__(self, topic_name: str, msg_type: Any, qos: int = 10):
        self.topic_name = topic_name
        self.msg_type = msg_type
        self.qos = qos
        self.publish_count = 0
        self.subscribers: List[Callable[[Any], None]] = []

    def publish(self, msg: Any) -> None:
        self.publish_count += 1
        # Notify local simulated subscribers
        for callback in self.subscribers:
            try:
                callback(msg)
            except Exception as e:
                logger.error(f"Error in subscriber callback for {self.topic_name}: {e}")


class MockSubscription:
    """Mock ROS 2 Subscription."""

    def __init__(self, topic_name: str, msg_type: Any, callback: Callable[[Any], None]):
        self.topic_name = topic_name
        self.msg_type = msg_type
        self.callback = callback


class MockTimer:
    """Mock ROS 2 Timer."""

    def __init__(self, period_sec: float, callback: Callable[[], None]):
        self.period_sec = period_sec
        self.callback = callback
        self.is_active = True

    def cancel(self) -> None:
        self.is_active = False


class BaseAgriNode:
    """Universal Node wrapper supporting both rclpy.Node and standalone MockNode."""

    def __init__(self, node_name: str):
        self.node_name = node_name
        self._is_ros_native = HAS_RCLPY
        self._mock_publishers: Dict[str, MockPublisher] = {}
        self._mock_timers: List[MockTimer] = []

        if HAS_RCLPY:
            if not rclpy.ok():
                rclpy.init(args=sys.argv)
            self._ros_node = RealNode(node_name)
            self._logger = self._ros_node.get_logger()
        else:
            self._ros_node = None
            logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
            self._logger = logging.getLogger(f"ROS2.{node_name}")
            self._logger.info(f"Initialized standalone ROS 2 mock node '{node_name}' (Windows Native fallback)")

    def get_logger(self) -> Any:
        return self._logger

    def create_publisher(self, msg_type: Any, topic: str, qos_profile: int = 10) -> Any:
        if self._is_ros_native and self._ros_node:
            return self._ros_node.create_publisher(msg_type, topic, qos_profile)
        pub = MockPublisher(topic, msg_type, qos_profile)
        self._mock_publishers[topic] = pub
        return pub

    def create_subscription(self, msg_type: Any, topic: str, callback: Callable[[Any], None], qos_profile: int = 10) -> Any:
        if self._is_ros_native and self._ros_node:
            return self._ros_node.create_subscription(msg_type, topic, callback, qos_profile)
        return MockSubscription(topic, msg_type, callback)

    def create_timer(self, period_sec: float, callback: Callable[[], None]) -> Any:
        if self._is_ros_native and self._ros_node:
            return self._ros_node.create_timer(period_sec, callback)
        timer = MockTimer(period_sec, callback)
        self._mock_timers.append(timer)
        return timer

    def destroy_node(self) -> None:
        if self._is_ros_native and self._ros_node:
            self._ros_node.destroy_node()
        for t in self._mock_timers:
            t.cancel()

    @staticmethod
    def create_string_message(payload: Any) -> Any:
        """Create JSON-serialized String message."""
        raw = json.dumps(payload, default=str)
        if HAS_RCLPY and RealStringMsg:
            msg = RealStringMsg()
            msg.data = raw
            return msg
        return MockStringMsg(raw)
