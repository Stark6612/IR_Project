"""Task execution and virtual action implementation."""

from __future__ import annotations
import time
from typing import List, Dict, Any, Optional
from .models import (
    Coordinate,
    Cell,
    EntityType,
    PlantHealth,
    ActionType,
    SimulationEvent,
)
from .world import FieldWorld


class TaskExecutor:
    """Executes virtual actions (watering, weed clearing, plant inspection) on the simulation world."""

    WATERING_TARGET_MOISTURE = 60  # PRD FR-08: increase dry plant moisture to 60%

    def __init__(self, world: FieldWorld):
        self.world = world
        self.event_log: List[SimulationEvent] = []

    def log_event(
        self,
        event_type: str,
        target: Optional[Coordinate],
        action: str,
        outcome: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> SimulationEvent:
        event = SimulationEvent(
            timestamp=time.time(),
            event_type=event_type,
            target=target,
            action=action,
            outcome=outcome,
            details=details or {},
        )
        self.event_log.append(event)
        return event

    def execute_watering(self, target: Coordinate) -> bool:
        """Watering virtual action: raises plant moisture to 60%."""
        cell = self.world.get_cell(target)
        if not cell or not cell.plant_info:
            self.log_event(
                event_type="action_failed",
                target=target,
                action="watering",
                outcome="FAILED",
                details={"reason": "No plant at target coordinate"},
            )
            return False

        old_moisture = cell.plant_info.moisture
        cell.plant_info.moisture = self.WATERING_TARGET_MOISTURE
        cell.plant_info.watered = True

        self.log_event(
            event_type="action_executed",
            target=target,
            action="watering",
            outcome="SUCCESS",
            details={
                "previous_moisture": old_moisture,
                "new_moisture": self.WATERING_TARGET_MOISTURE,
                "message": f"Watered plant at {target}: moisture raised from {old_moisture}% to {self.WATERING_TARGET_MOISTURE}%",
            },
        )
        return True

    def execute_weed_clearing(self, target: Coordinate) -> bool:
        """Weed clearing virtual action: clears the weed from active state."""
        cell = self.world.get_cell(target)
        if not cell or cell.entity_type != EntityType.WEED:
            self.log_event(
                event_type="action_failed",
                target=target,
                action="weed_clearing",
                outcome="FAILED",
                details={"reason": "No weed at target coordinate"},
            )
            return False

        cell.cleared_weed = True
        cell.entity_type = EntityType.EMPTY  # Cleared to empty soil

        self.log_event(
            event_type="action_executed",
            target=target,
            action="weed_clearing",
            outcome="SUCCESS",
            details={
                "message": f"Successfully cleared invasive weed at {target}",
            },
        )
        return True

    def execute_plant_inspection(self, target: Coordinate) -> bool:
        """Plant inspection virtual action: logs health assessment and marks inspected."""
        cell = self.world.get_cell(target)
        if not cell or not cell.plant_info:
            self.log_event(
                event_type="action_failed",
                target=target,
                action="plant_inspection",
                outcome="FAILED",
                details={"reason": "No plant at target coordinate"},
            )
            return False

        cell.plant_info.inspected = True
        health = cell.plant_info.health.value
        confidence = cell.plant_info.confidence

        self.log_event(
            event_type="action_executed",
            target=target,
            action="plant_inspection",
            outcome="SUCCESS",
            details={
                "health_status": health,
                "confidence": confidence,
                "message": f"Inspected plant at {target}: status '{health}' (confidence {confidence*100:.1f}%)",
            },
        )
        return True

    def execute_task(self, action_type: ActionType, target: Coordinate) -> bool:
        """Dispatches action execution based on ActionType."""
        if action_type == ActionType.WATERING:
            return self.execute_watering(target)
        elif action_type == ActionType.WEED_CLEARING:
            return self.execute_weed_clearing(target)
        elif action_type == ActionType.PLANT_INSPECTION:
            return self.execute_plant_inspection(target)
        elif action_type == ActionType.PATROL:
            self.log_event(
                event_type="action_executed",
                target=target,
                action="patrol",
                outcome="SUCCESS",
                details={"message": f"Patrolled waypoint {target}"},
            )
            return True
        return False
