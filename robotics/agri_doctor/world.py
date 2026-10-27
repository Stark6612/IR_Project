"""Crop Field Grid and Deterministic Scenario Definitions."""

from __future__ import annotations
from typing import Dict, List, Optional, Set
from .models import (
    Coordinate,
    Cell,
    EntityType,
    PlantInfo,
    PlantHealth,
)


class FieldWorld:
    """Represents a 2D discrete crop-field grid."""

    def __init__(self, width: int = 6, height: int = 4):
        self.width = width
        self.height = height
        self.cells: Dict[Coordinate, Cell] = {}
        self.scenario_name: str = "custom"
        self.rover_start: Coordinate = Coordinate(0, 0)
        self._initialize_empty_grid()

    def _initialize_empty_grid(self) -> None:
        self.cells.clear()
        for y in range(self.height):
            for x in range(self.width):
                coord = Coordinate(x, y)
                self.cells[coord] = Cell(coordinate=coord, entity_type=EntityType.EMPTY)

    def is_within_bounds(self, coord: Coordinate) -> bool:
        return 0 <= coord.x < self.width and 0 <= coord.y < self.height

    def get_cell(self, coord: Coordinate) -> Optional[Cell]:
        return self.cells.get(coord)

    def set_cell(
        self,
        coord: Coordinate,
        entity_type: EntityType,
        plant_info: Optional[PlantInfo] = None,
    ) -> None:
        if not self.is_within_bounds(coord):
            raise ValueError(f"Coordinate {coord} out of field bounds ({self.width}x{self.height})")
        self.cells[coord] = Cell(
            coordinate=coord,
            entity_type=entity_type,
            plant_info=plant_info,
        )

    def get_blocked_coordinates(self) -> Set[Coordinate]:
        """Returns set of all coordinates occupied by obstacles."""
        return {
            coord
            for coord, cell in self.cells.items()
            if cell.entity_type == EntityType.OBSTACLE
        }

    def load_scenario(self, scenario_name: str) -> None:
        """
        Loads one of the 3 deterministic scenarios defined in PRD FR-02:
        1. 'mixed_field': plants, weeds, dry plants, and obstacles.
        2. 'obstacle_challenge': route requiring rover to navigate around an obstacle barrier.
        3. 'dry_field': several plants with low moisture needing prioritized watering.
        """
        self._initialize_empty_grid()
        self.scenario_name = scenario_name

        if scenario_name == "mixed_field":
            self.rover_start = Coordinate(0, 0)

            # Healthy plants
            self.set_cell(Coordinate(1, 0), EntityType.PLANT, PlantInfo(moisture=65, health=PlantHealth.HEALTHY))
            self.set_cell(Coordinate(3, 1), EntityType.PLANT, PlantInfo(moisture=70, health=PlantHealth.HEALTHY))
            self.set_cell(Coordinate(5, 3), EntityType.PLANT, PlantInfo(moisture=55, health=PlantHealth.HEALTHY))

            # Dry plant needing watering (<30%)
            self.set_cell(Coordinate(2, 1), EntityType.PLANT, PlantInfo(moisture=22, health=PlantHealth.HEALTHY))

            # Diseased/inspection needed plant
            self.set_cell(Coordinate(4, 2), EntityType.PLANT, PlantInfo(moisture=58, health=PlantHealth.SUSPECTED_DISEASE, confidence=0.88))

            # Weeds
            self.set_cell(Coordinate(2, 3), EntityType.WEED)
            self.set_cell(Coordinate(5, 1), EntityType.WEED)

            # Obstacles
            self.set_cell(Coordinate(1, 1), EntityType.OBSTACLE)
            self.set_cell(Coordinate(3, 2), EntityType.OBSTACLE)

        elif scenario_name == "obstacle_challenge":
            self.rover_start = Coordinate(0, 0)

            # Creates a vertical barrier at x=2 with an opening at y=3
            self.set_cell(Coordinate(2, 0), EntityType.OBSTACLE)
            self.set_cell(Coordinate(2, 1), EntityType.OBSTACLE)
            self.set_cell(Coordinate(2, 2), EntityType.OBSTACLE)
            # Opening at (2, 3)

            # High priority dry plant behind the barrier
            self.set_cell(Coordinate(4, 1), EntityType.PLANT, PlantInfo(moisture=18, health=PlantHealth.HEALTHY))
            # Weed to clear
            self.set_cell(Coordinate(5, 2), EntityType.WEED)
            # Inspection target
            self.set_cell(Coordinate(4, 3), EntityType.PLANT, PlantInfo(moisture=60, health=PlantHealth.NEEDS_INSPECTION, confidence=0.92))

        elif scenario_name == "dry_field":
            self.rover_start = Coordinate(0, 0)

            # Multiple dry plants requiring immediate watering
            self.set_cell(Coordinate(1, 1), EntityType.PLANT, PlantInfo(moisture=15, health=PlantHealth.HEALTHY))
            self.set_cell(Coordinate(3, 0), EntityType.PLANT, PlantInfo(moisture=20, health=PlantHealth.HEALTHY))
            self.set_cell(Coordinate(4, 2), EntityType.PLANT, PlantInfo(moisture=25, health=PlantHealth.HEALTHY))
            self.set_cell(Coordinate(2, 3), EntityType.PLANT, PlantInfo(moisture=12, health=PlantHealth.HEALTHY))

            # One healthy plant for comparison
            self.set_cell(Coordinate(5, 1), EntityType.PLANT, PlantInfo(moisture=75, health=PlantHealth.HEALTHY))

            # One obstacle
            self.set_cell(Coordinate(2, 1), EntityType.OBSTACLE)

        else:
            raise ValueError(f"Unknown scenario name: '{scenario_name}'. Valid: 'mixed_field', 'obstacle_challenge', 'dry_field'")

    def to_dict(self) -> Dict:
        """Serializes current world grid for UI dashboard consumption."""
        cells_data = []
        for coord, cell in self.cells.items():
            cell_dict = {
                "x": coord.x,
                "y": coord.y,
                "entity_type": cell.entity_type.value,
                "cleared_weed": cell.cleared_weed,
            }
            if cell.plant_info:
                cell_dict["plant_info"] = {
                    "moisture": cell.plant_info.moisture,
                    "health": cell.plant_info.health.value,
                    "confidence": cell.plant_info.confidence,
                    "inspected": cell.plant_info.inspected,
                    "watered": cell.plant_info.watered,
                }
            cells_data.append(cell_dict)

        return {
            "width": self.width,
            "height": self.height,
            "scenario": self.scenario_name,
            "rover_start": self.rover_start.to_tuple(),
            "cells": cells_data,
        }
