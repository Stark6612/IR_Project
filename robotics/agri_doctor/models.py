"""Data models and enumerations for the Agri-Doctor Robot simulation."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
import time


class EntityType(str, Enum):
    EMPTY = "empty"
    PLANT = "plant"
    WEED = "weed"
    OBSTACLE = "obstacle"


class PlantHealth(str, Enum):
    HEALTHY = "healthy"
    SUSPECTED_DISEASE = "suspected_disease"
    NEEDS_INSPECTION = "needs_inspection"


class RobotState(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    MOVING = "MOVING"
    AVOIDING_OBSTACLE = "AVOIDING_OBSTACLE"
    EXECUTING_TASK = "EXECUTING_TASK"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class Heading(str, Enum):
    NORTH = "N"
    EAST = "E"
    SOUTH = "S"
    WEST = "W"


class ActionType(str, Enum):
    WATERING = "watering"
    WEED_CLEARING = "weed_clearing"
    PLANT_INSPECTION = "plant_inspection"
    PATROL = "patrol"
    OBSTACLE_AVOIDANCE = "obstacle_avoidance"


@dataclass(frozen=True)
class Coordinate:
    x: int
    y: int

    def to_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)

    def manhattan_distance(self, other: Coordinate) -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)

    def __repr__(self) -> str:
        return f"({self.x}, {self.y})"


@dataclass
class PlantInfo:
    moisture: int  # 0 to 100 percentage
    health: PlantHealth = PlantHealth.HEALTHY
    confidence: float = 1.0  # Perception confidence 0.0 - 1.0
    inspected: bool = False
    watered: bool = False


@dataclass
class Cell:
    coordinate: Coordinate
    entity_type: EntityType = EntityType.EMPTY
    plant_info: Optional[PlantInfo] = None
    cleared_weed: bool = False


@dataclass
class Task:
    task_id: str
    priority: int  # Lower number = higher priority
    action_type: ActionType
    target: Coordinate
    description: str
    completed: bool = False
    active: bool = False


@dataclass
class RoverState:
    coordinate: Coordinate
    heading: Heading = Heading.EAST
    state: RobotState = RobotState.IDLE
    battery: float = 100.0  # Percentage estimate 0-100
    proximity_cm: float = 100.0  # Simulated distance in cm
    current_target: Optional[Coordinate] = None
    planned_path: List[Coordinate] = field(default_factory=list)


@dataclass
class SimulationEvent:
    timestamp: float
    event_type: str
    target: Optional[Coordinate]
    action: str
    outcome: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "target": self.target.to_tuple() if self.target else None,
            "action": self.action,
            "outcome": self.outcome,
            "details": self.details,
        }
