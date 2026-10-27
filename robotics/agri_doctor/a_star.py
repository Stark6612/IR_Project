"""A* Path Planning implementation with Manhattan heuristic for 4-directional grid movement."""

from __future__ import annotations
import heapq
import time
from typing import Set, List, Optional, Tuple, Dict
from .models import Coordinate


class PathResult:
    def __init__(
        self,
        path: List[Coordinate],
        cost: int,
        nodes_expanded: int,
        planning_time_ms: float,
        success: bool,
    ):
        self.path = path
        self.cost = cost
        self.nodes_expanded = nodes_expanded
        self.planning_time_ms = planning_time_ms
        self.success = success

    def __repr__(self) -> str:
        return f"PathResult(success={self.success}, cost={self.cost}, len={len(self.path)}, time={self.planning_time_ms:.3f}ms)"


class AStarPlanner:
    def __init__(self, width: int = 6, height: int = 4):
        self.width = width
        self.height = height

    def is_within_bounds(self, coord: Coordinate) -> bool:
        return 0 <= coord.x < self.width and 0 <= coord.y < self.height

    def get_neighbors(
        self, coord: Coordinate, blocked: Set[Coordinate]
    ) -> List[Coordinate]:
        """Returns 4-directional orthogonal neighbors (Up, Down, Left, Right)."""
        deltas = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # North, East, South, West
        neighbors = []
        for dx, dy in deltas:
            neighbor = Coordinate(coord.x + dx, coord.y + dy)
            if self.is_within_bounds(neighbor) and neighbor not in blocked:
                neighbors.append(neighbor)
        return neighbors

    def plan(
        self,
        start: Coordinate,
        goal: Coordinate,
        blocked: Optional[Set[Coordinate]] = None,
    ) -> PathResult:
        """
        Executes A* path planning from start to goal.
        - Heuristic: Manhattan distance
        - Movement: 4-directional orthogonal
        - Returns PathResult containing ordered list of Coordinates from start to goal.
        """
        start_time = time.perf_counter()
        blocked_set = blocked or set()

        # Edge Case 1: Start or Goal out of bounds
        if not self.is_within_bounds(start) or not self.is_within_bounds(goal):
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return PathResult([], -1, 0, elapsed_ms, False)

        # Edge Case 2: Start or Goal is blocked (unless start == goal which is checked next)
        if start in blocked_set or goal in blocked_set:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return PathResult([], -1, 0, elapsed_ms, False)

        # Edge Case 3: Start equals Goal
        if start == goal:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return PathResult([start], 0, 0, elapsed_ms, True)

        # Priority queue stores tuples: (f_score, tie_breaker, current_coord)
        tie_breaker = 0
        open_set: List[Tuple[int, int, Coordinate]] = []
        heapq.heappush(open_set, (start.manhattan_distance(goal), tie_breaker, start))

        came_from: Dict[Coordinate, Coordinate] = {}
        g_score: Dict[Coordinate, int] = {start: 0}
        f_score: Dict[Coordinate, int] = {start: start.manhattan_distance(goal)}

        open_set_hash: Set[Coordinate] = {start}
        nodes_expanded = 0

        while open_set:
            _, _, current = heapq.heappop(open_set)
            open_set_hash.discard(current)
            nodes_expanded += 1

            if current == goal:
                # Reconstruct path
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return PathResult(
                    path=path,
                    cost=g_score[goal],
                    nodes_expanded=nodes_expanded,
                    planning_time_ms=elapsed_ms,
                    success=True,
                )

            for neighbor in self.get_neighbors(current, blocked_set):
                tentative_g_score = g_score[current] + 1

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f = tentative_g_score + neighbor.manhattan_distance(goal)
                    f_score[neighbor] = f

                    if neighbor not in open_set_hash:
                        tie_breaker += 1
                        heapq.heappush(open_set, (f, tie_breaker, neighbor))
                        open_set_hash.add(neighbor)

        # Unreachable target
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return PathResult([], -1, nodes_expanded, elapsed_ms, False)
