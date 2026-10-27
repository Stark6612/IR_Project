"""Mission planning and priority queue management."""

from __future__ import annotations
from typing import List, Optional, Dict
from .models import (
    Coordinate,
    Cell,
    EntityType,
    PlantHealth,
    ActionType,
    Task,
)
from .world import FieldWorld


class MissionPlanner:
    """Discovers, prioritizes, and schedules field tasks based on PRD FR-07 rules."""

    # Configurable priority ranks (Lower number = Higher execution urgency)
    PRIORITY_OBSTACLE_SAFETY = 1
    PRIORITY_DRY_PLANT_WATERING = 2
    PRIORITY_PLANT_INSPECTION = 3
    PRIORITY_WEED_CLEARING = 4
    PRIORITY_PATROL = 5

    def __init__(self, world: FieldWorld):
        self.world = world
        self.tasks: List[Task] = []
        self._task_counter: int = 0

    def _next_task_id(self, prefix: str) -> str:
        self._task_counter += 1
        return f"{prefix}_{self._task_counter:03d}"

    def scan_and_generate_tasks(self, include_patrol: bool = False) -> List[Task]:
        """
        Scans the entire world grid and generates prioritized tasks:
        1. Dry plants (<30% moisture) needing watering.
        2. Diseased / flagged plants needing inspection.
        3. Invasive weeds needing clearing.
        4. (Optional) Unvisited empty waypoints for general patrol.
        """
        self.tasks.clear()

        for y in range(self.world.height):
            for x in range(self.world.width):
                coord = Coordinate(x, y)
                cell = self.world.get_cell(coord)
                if not cell:
                    continue

                # 1. Check for Dry Plants
                if cell.entity_type == EntityType.PLANT and cell.plant_info:
                    if cell.plant_info.moisture < 30 and not cell.plant_info.watered:
                        self.tasks.append(
                            Task(
                                task_id=self._next_task_id("WATER"),
                                priority=self.PRIORITY_DRY_PLANT_WATERING,
                                action_type=ActionType.WATERING,
                                target=coord,
                                description=f"Water dry plant (moisture {cell.plant_info.moisture}%)",
                            )
                        )

                # 2. Check for Diseased / Inspection-needed Plants
                if cell.entity_type == EntityType.PLANT and cell.plant_info:
                    if (
                        cell.plant_info.health in (PlantHealth.SUSPECTED_DISEASE, PlantHealth.NEEDS_INSPECTION)
                        and not cell.plant_info.inspected
                    ):
                        self.tasks.append(
                            Task(
                                task_id=self._next_task_id("INSPECT"),
                                priority=self.PRIORITY_PLANT_INSPECTION,
                                action_type=ActionType.PLANT_INSPECTION,
                                target=coord,
                                description=f"Inspect plant for {cell.plant_info.health.value}",
                            )
                        )

                # 3. Check for Invasive Weeds
                if cell.entity_type == EntityType.WEED and not cell.cleared_weed:
                    self.tasks.append(
                        Task(
                            task_id=self._next_task_id("WEED"),
                            priority=self.PRIORITY_WEED_CLEARING,
                            action_type=ActionType.WEED_CLEARING,
                            target=coord,
                            description="Clear invasive weed",
                        )
                    )

        # 4. Optional Patrol tasks
        if include_patrol and not self.tasks:
            # Add corner waypoints for patrol
            patrol_points = [
                Coordinate(0, 0),
                Coordinate(self.world.width - 1, 0),
                Coordinate(self.world.width - 1, self.world.height - 1),
                Coordinate(0, self.world.height - 1),
            ]
            for pt in patrol_points:
                self.tasks.append(
                    Task(
                        task_id=self._next_task_id("PATROL"),
                        priority=self.PRIORITY_PATROL,
                        action_type=ActionType.PATROL,
                        target=pt,
                        description="Patrol field perimeter",
                    )
                )

        return self.tasks

    def get_next_task(self, current_rover_coord: Coordinate) -> Optional[Task]:
        """
        Retrieves the next highest priority actionable task.
        Ties are broken by Manhattan distance to the rover's current location (nearest first).
        """
        pending_tasks = [t for t in self.tasks if not t.completed]
        if not pending_tasks:
            return None

        # Sort key: (priority ascending, distance to rover ascending)
        pending_tasks.sort(
            key=lambda t: (t.priority, t.target.manhattan_distance(current_rover_coord))
        )
        return pending_tasks[0]

    def mark_task_complete(self, task_id: str) -> None:
        for t in self.tasks:
            if t.task_id == task_id:
                t.completed = True
                t.active = False
                break

    def to_list(self) -> List[Dict]:
        return [
            {
                "task_id": t.task_id,
                "priority": t.priority,
                "action_type": t.action_type.value,
                "target": t.target.to_tuple(),
                "description": t.description,
                "completed": t.completed,
                "active": t.active,
            }
            for t in self.tasks
        ]
