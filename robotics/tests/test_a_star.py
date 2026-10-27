"""Unit tests for A* Path Planner."""

import pytest
from agri_doctor.models import Coordinate
from agri_doctor.a_star import AStarPlanner


def test_start_equals_goal():
    planner = AStarPlanner(width=6, height=4)
    start = Coordinate(1, 1)
    goal = Coordinate(1, 1)
    result = planner.plan(start, goal)

    assert result.success is True
    assert result.cost == 0
    assert result.path == [Coordinate(1, 1)]


def test_straight_line_shortest_path():
    planner = AStarPlanner(width=6, height=4)
    start = Coordinate(0, 0)
    goal = Coordinate(3, 0)
    result = planner.plan(start, goal)

    assert result.success is True
    assert result.cost == 3
    assert len(result.path) == 4
    assert result.path[0] == start
    assert result.path[-1] == goal


def test_manhattan_corner_path():
    planner = AStarPlanner(width=6, height=4)
    start = Coordinate(0, 0)
    goal = Coordinate(2, 2)
    result = planner.plan(start, goal)

    assert result.success is True
    assert result.cost == 4
    assert len(result.path) == 5
    assert result.path[0] == start
    assert result.path[-1] == goal


def test_obstacle_avoidance():
    planner = AStarPlanner(width=6, height=4)
    start = Coordinate(0, 1)
    goal = Coordinate(2, 1)

    # Place obstacle directly in between at (1, 1)
    blocked = {Coordinate(1, 1)}
    result = planner.plan(start, goal, blocked)

    assert result.success is True
    assert Coordinate(1, 1) not in result.path
    # Manhattan distance was 2, detour must take at least 4 steps
    assert result.cost >= 4
    assert result.path[0] == start
    assert result.path[-1] == goal


def test_unreachable_target():
    planner = AStarPlanner(width=6, height=4)
    start = Coordinate(0, 0)
    goal = Coordinate(5, 3)

    # Surround goal completely by obstacles: (4, 3) and (5, 2)
    blocked = {Coordinate(4, 3), Coordinate(5, 2)}
    result = planner.plan(start, goal, blocked)

    assert result.success is False
    assert result.path == []
    assert result.cost == -1


def test_out_of_bounds_and_blocked_endpoints():
    planner = AStarPlanner(width=6, height=4)

    # Start out of bounds
    res1 = planner.plan(Coordinate(-1, 0), Coordinate(2, 2))
    assert res1.success is False

    # Goal out of bounds
    res2 = planner.plan(Coordinate(0, 0), Coordinate(6, 4))
    assert res2.success is False

    # Goal is inside obstacle
    res3 = planner.plan(Coordinate(0, 0), Coordinate(1, 1), blocked={Coordinate(1, 1)})
    assert res3.success is False
