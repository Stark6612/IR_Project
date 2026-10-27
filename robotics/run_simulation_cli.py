"""Agri-Doctor Robot - Standalone Terminal CLI Runner.

Demonstrates simulation execution, A* navigation, and virtual tasks in pure terminal format.
"""

import sys
import time
from agri_doctor.world import FieldWorld
from agri_doctor.robot_controller import RobotController
from agri_doctor.models import RobotState, EntityType


def print_field(controller: RobotController):
    world = controller.world
    rover_coord = controller.rover.coordinate
    planned_set = set(controller.rover.planned_path)

    print("\n" + "=" * 40)
    print(f"Scenario: {world.scenario_name.upper()} | Rover State: {controller.rover.state.value}")
    print(f"Rover Position: {rover_coord} (Facing: {controller.rover.heading.value}) | Battery: {controller.rover.battery:.1f}%")
    if controller.current_task:
        print(f"Active Task: {controller.current_task.action_type.value.upper()} at {controller.current_task.target}")
    print("=" * 40)

    # Use clean ASCII symbols for universal Windows console compatibility
    for y in range(world.height - 1, -1, -1):
        row_str = f"y={y} | "
        for x in range(world.width):
            from agri_doctor.models import Coordinate
            c = Coordinate(x, y)
            cell = world.get_cell(c)

            if c == rover_coord:
                char = "[R]"
            elif cell.entity_type == EntityType.OBSTACLE:
                char = "[#]"
            elif cell.entity_type == EntityType.WEED:
                char = "[W]"
            elif cell.entity_type == EntityType.PLANT:
                if cell.plant_info and cell.plant_info.moisture < 30:
                    char = "[D]"  # Dry plant
                elif cell.plant_info and cell.plant_info.inspected:
                    char = "[I]"  # Inspected plant
                else:
                    char = "[P]"  # Healthy plant
            elif c in planned_set:
                char = " · "
            else:
                char = " . "
            row_str += f"{char:^5}"
        print(row_str)

    print("     " + " ".join([f"x={x:^3}" for x in range(world.width)]))
    print("Legend: [R] Rover | [P] Crop | [D] Dry Crop | [W] Weed | [#] Obstacle | · Path")


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else "mixed_field"
    print(f"\n>> Starting Agri-Doctor Simulation in '{scenario}' scenario...")

    world = FieldWorld(width=6, height=4)
    world.load_scenario(scenario)

    controller = RobotController(world)
    controller.start_mission()

    step_count = 0
    print_field(controller)

    while controller.rover.state != RobotState.COMPLETED and step_count < 100:
        controller.step()
        step_count += 1
        print_field(controller)
        time.sleep(0.15)

    telemetry = controller.get_telemetry()
    print("\n" + "#" * 40)
    print(">> MISSION COMPLETED SUCCESSFULLY!")
    print(f"Total Steps Taken: {telemetry['metrics']['total_path_steps']}")
    print(f"Cells Visited: {telemetry['metrics']['cells_visited_count']}")
    print(f"Dry Plants Watered: {telemetry['metrics']['plants_watered_count']}")
    print(f"Weeds Cleared: {telemetry['metrics']['weeds_cleared_count']}")
    print(f"Plants Inspected: {telemetry['metrics']['plants_inspected_count']}")
    print("#" * 40 + "\n")


if __name__ == "__main__":
    main()
