"""Comprehensive integration and unit tests for Agri-Doctor simulation engine."""

import pytest
from agri_doctor.models import (
    Coordinate,
    RobotState,
    EntityType,
    PlantHealth,
    ActionType,
)
from agri_doctor.world import FieldWorld
from agri_doctor.perception_simulator import PerceptionSimulator
from agri_doctor.task_executor import TaskExecutor
from agri_doctor.mission_planner import MissionPlanner
from agri_doctor.robot_controller import RobotController


def test_scenario_loading():
    world = FieldWorld(width=6, height=4)

    # Test Mixed Field
    world.load_scenario("mixed_field")
    assert world.scenario_name == "mixed_field"
    assert len(world.get_blocked_coordinates()) == 2
    # Check dry plant at (2, 1)
    cell = world.get_cell(Coordinate(2, 1))
    assert cell is not None and cell.plant_info is not None
    assert cell.plant_info.moisture == 22

    # Test Obstacle Challenge
    world.load_scenario("obstacle_challenge")
    assert world.scenario_name == "obstacle_challenge"
    blocked = world.get_blocked_coordinates()
    assert Coordinate(2, 0) in blocked
    assert Coordinate(2, 1) in blocked
    assert Coordinate(2, 2) in blocked
    assert Coordinate(2, 3) not in blocked  # Opening

    # Test Dry Field
    world.load_scenario("dry_field")
    assert world.scenario_name == "dry_field"


def test_moisture_sensing_and_watering():
    world = FieldWorld(width=6, height=4)
    world.load_scenario("mixed_field")

    perception = PerceptionSimulator(world)
    executor = TaskExecutor(world)

    dry_plant_coord = Coordinate(2, 1)
    reading = perception.read_soil_moisture(dry_plant_coord)
    assert reading["is_dry"] is True
    assert reading["moisture"] == 22
    assert reading["is_simulated"] is True

    # Water the dry plant
    success = executor.execute_watering(dry_plant_coord)
    assert success is True

    # Verify moisture increased to 60%
    after_reading = perception.read_soil_moisture(dry_plant_coord)
    assert after_reading["moisture"] == 60
    assert after_reading["is_dry"] is False


def test_weed_clearing():
    world = FieldWorld(width=6, height=4)
    world.load_scenario("mixed_field")

    executor = TaskExecutor(world)
    weed_coord = Coordinate(2, 3)

    cell = world.get_cell(weed_coord)
    assert cell.entity_type == EntityType.WEED

    success = executor.execute_weed_clearing(weed_coord)
    assert success is True
    assert cell.cleared_weed is True
    assert cell.entity_type == EntityType.EMPTY


def test_plant_inspection():
    world = FieldWorld(width=6, height=4)
    world.load_scenario("mixed_field")

    executor = TaskExecutor(world)
    diseased_coord = Coordinate(4, 2)

    cell = world.get_cell(diseased_coord)
    assert cell.plant_info.health == PlantHealth.SUSPECTED_DISEASE
    assert cell.plant_info.inspected is False

    success = executor.execute_plant_inspection(diseased_coord)
    assert success is True
    assert cell.plant_info.inspected is True


def test_task_priority_order():
    world = FieldWorld(width=6, height=4)
    world.load_scenario("mixed_field")

    planner = MissionPlanner(world)
    tasks = planner.scan_and_generate_tasks()

    # Priorities: 2 (Watering), 3 (Inspection), 4 (Weed)
    next_task = planner.get_next_task(Coordinate(0, 0))
    assert next_task is not None
    # Highest priority in mixed_field is watering dry plant (Priority 2)
    assert next_task.action_type == ActionType.WATERING
    assert next_task.target == Coordinate(2, 1)


def test_full_mission_execution_mixed_field():
    world = FieldWorld(width=6, height=4)
    world.load_scenario("mixed_field")

    controller = RobotController(world)
    controller.start_mission()

    assert controller.rover.state == RobotState.PLANNING

    # Step simulation until mission is completed (max 200 ticks to avoid infinite loop)
    ticks = 0
    max_ticks = 200
    while controller.rover.state != RobotState.COMPLETED and ticks < max_ticks:
        controller.step()
        ticks += 1

    assert controller.rover.state == RobotState.COMPLETED
    assert controller.plants_watered_count >= 1
    assert controller.weeds_cleared_count >= 2
    assert controller.plants_inspected_count >= 1
    assert len(controller.visited_cells) > 1

    telemetry = controller.get_telemetry()
    assert telemetry["metrics"]["total_path_steps"] > 0
    assert len(telemetry["events"]) > 0


def test_full_mission_execution_obstacle_challenge():
    world = FieldWorld(width=6, height=4)
    world.load_scenario("obstacle_challenge")

    controller = RobotController(world)
    controller.start_mission()

    ticks = 0
    while controller.rover.state != RobotState.COMPLETED and ticks < 200:
        controller.step()
        ticks += 1

    assert controller.rover.state == RobotState.COMPLETED
    assert controller.plants_watered_count >= 1
    assert controller.plants_inspected_count >= 1


def test_full_mission_execution_dry_field():
    world = FieldWorld(width=6, height=4)
    world.load_scenario("dry_field")

    controller = RobotController(world)
    controller.start_mission()

    ticks = 0
    while controller.rover.state != RobotState.COMPLETED and ticks < 200:
        controller.step()
        ticks += 1

    assert controller.rover.state == RobotState.COMPLETED
    assert controller.plants_watered_count == 4  # All 4 dry plants watered
