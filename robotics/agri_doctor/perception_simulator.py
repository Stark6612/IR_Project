"""Simulated perception and sensor readings for the Agri-Doctor Robot.

Honesty Requirement:
All readings and detections in this module are simulated and generated based on
predefined scenario rules. They are advisory demonstration outputs and do not represent
physically measured values or validated biological diagnoses.
"""

from __future__ import annotations
import random
import time
from typing import Dict, Any, Optional
from .kalman_filter import KalmanFilter1D, KalmanEstimate
from .models import (
    Coordinate,
    Heading,
    Cell,
    EntityType,
    PlantHealth,
)
from .world import FieldWorld


class PerceptionSimulator:
    """Simulates onboard sensors: soil moisture probe, proximity lidar/sonar, and crop camera."""

    MOISTURE_DRY_THRESHOLD = 30  # Below 30% indicates plant needing watering
    OBSTACLE_PROXIMITY_THRESHOLD_CM = 15.0  # Under 15cm triggers obstacle avoidance/replan

    def __init__(self, world: FieldWorld):
        self.world = world
        self.noise_enabled: bool = True
        self.moisture_sigma: float = 3.5  # Gaussian noise std dev (percentage points)
        self.proximity_sigma: float = 2.0  # Gaussian noise std dev (cm)
        self.moisture_kf = KalmanFilter1D(
            initial_estimate=50.0,
            initial_error_covariance=10.0,
            process_noise_cov_q=0.08,
            measurement_noise_cov_r=self.moisture_sigma ** 2,
        )
        self.proximity_kf = KalmanFilter1D(
            initial_estimate=100.0,
            initial_error_covariance=15.0,
            process_noise_cov_q=0.15,
            measurement_noise_cov_r=self.proximity_sigma ** 2,
        )

    def set_noise_level(self, moisture_sigma: float, proximity_sigma: float) -> None:
        self.moisture_sigma = max(0.0, moisture_sigma)
        self.proximity_sigma = max(0.0, proximity_sigma)
        self.moisture_kf.set_measurement_noise(max(0.01, self.moisture_sigma ** 2))
        self.proximity_kf.set_measurement_noise(max(0.01, self.proximity_sigma ** 2))

    def read_soil_moisture(self, coord: Coordinate) -> Dict[str, Any]:
        """
        Simulates soil moisture probe reading at a specific coordinate.
        Generates Gaussian noise and filters it through a discrete Kalman Filter.
        """
        cell = self.world.get_cell(coord)
        if not cell or not cell.plant_info:
            return {
                "coordinate": coord.to_tuple(),
                "moisture": None,
                "is_dry": False,
                "is_simulated": True,
                "kalman": None,
            }

        ground_truth = float(cell.plant_info.moisture)
        noisy_val = ground_truth
        if self.noise_enabled and self.moisture_sigma > 0:
            noisy_val = max(0.0, min(100.0, ground_truth + random.gauss(0.0, self.moisture_sigma)))

        kf_res = self.moisture_kf.update(noisy_val, ground_truth=ground_truth)

        # Decision is made on the robust filtered estimate
        is_dry = kf_res.filtered_estimate < self.MOISTURE_DRY_THRESHOLD
        return {
            "coordinate": coord.to_tuple(),
            "moisture": ground_truth,
            "moisture_noisy": round(noisy_val, 2),
            "moisture_filtered": kf_res.filtered_estimate,
            "is_dry": is_dry,
            "threshold": self.MOISTURE_DRY_THRESHOLD,
            "is_simulated": True,
            "timestamp": time.time(),
            "kalman": {
                "ground_truth": kf_res.ground_truth,
                "measurement": kf_res.noisy_measurement,
                "estimate": kf_res.filtered_estimate,
                "gain": kf_res.kalman_gain,
                "variance": kf_res.estimation_variance,
                "innovation": kf_res.innovation,
            },
        }

    def read_proximity(self, rover_coord: Coordinate, heading: Heading) -> Dict[str, Any]:
        """
        Simulates directional proximity sensor in front of the rover.
        Generates noisy range measurements and filters via Kalman Filter to prevent false triggers.
        """
        heading_deltas = {
            Heading.NORTH: (0, 1),
            Heading.EAST: (1, 0),
            Heading.SOUTH: (0, -1),
            Heading.WEST: (-1, 0),
        }
        dx, dy = heading_deltas.get(heading, (0, 0))
        target_coord = Coordinate(rover_coord.x + dx, rover_coord.y + dy)

        distance_cm = 100.0
        if not self.world.is_within_bounds(target_coord):
            distance_cm = 10.0
        else:
            cell = self.world.get_cell(target_coord)
            if cell and cell.entity_type == EntityType.OBSTACLE:
                distance_cm = 10.0

        ground_truth = float(distance_cm)
        noisy_dist = ground_truth
        if self.noise_enabled and self.proximity_sigma > 0:
            noisy_dist = max(2.0, min(200.0, ground_truth + random.gauss(0.0, self.proximity_sigma)))

        kf_res = self.proximity_kf.update(noisy_dist, ground_truth=ground_truth)

        # Trigger decision based on filtered estimate to reject transient spikes
        obstacle_triggered = kf_res.filtered_estimate < self.OBSTACLE_PROXIMITY_THRESHOLD_CM

        return {
            "rover_coordinate": rover_coord.to_tuple(),
            "facing_direction": heading.value,
            "target_coordinate": target_coord.to_tuple() if self.world.is_within_bounds(target_coord) else None,
            "distance_cm": ground_truth,
            "distance_noisy": round(noisy_dist, 2),
            "distance_filtered": kf_res.filtered_estimate,
            "obstacle_triggered": obstacle_triggered,
            "threshold_cm": self.OBSTACLE_PROXIMITY_THRESHOLD_CM,
            "is_simulated": True,
            "timestamp": time.time(),
            "kalman": {
                "ground_truth": kf_res.ground_truth,
                "measurement": kf_res.noisy_measurement,
                "estimate": kf_res.filtered_estimate,
                "gain": kf_res.kalman_gain,
                "variance": kf_res.estimation_variance,
                "innovation": kf_res.innovation,
            },
        }

    def inspect_crop_health(self, coord: Coordinate) -> Dict[str, Any]:
        """
        Simulates camera perception for weed detection and plant-health classification.
        Boundary interface designed to be pluggable with real OpenCV/ML model in future.
        """
        cell = self.world.get_cell(coord)
        if not cell:
            return {"detected": False, "is_simulated": True}

        if cell.entity_type == EntityType.WEED and not cell.cleared_weed:
            return {
                "detected": True,
                "type": "weed",
                "label": "weed_infestation",
                "coordinate": coord.to_tuple(),
                "confidence": 0.95,
                "needs_action": True,
                "recommended_action": "weed_clearing",
                "is_simulated": True,
                "timestamp": time.time(),
            }

        if cell.entity_type == EntityType.PLANT and cell.plant_info:
            health = cell.plant_info.health
            confidence = cell.plant_info.confidence
            needs_action = health in (PlantHealth.SUSPECTED_DISEASE, PlantHealth.NEEDS_INSPECTION)
            return {
                "detected": True,
                "type": "plant",
                "health_label": health.value,
                "coordinate": coord.to_tuple(),
                "confidence": confidence,
                "inspected": cell.plant_info.inspected,
                "needs_action": needs_action and not cell.plant_info.inspected,
                "recommended_action": "plant_inspection",
                "is_simulated": True,
                "timestamp": time.time(),
            }

        return {"detected": False, "coordinate": coord.to_tuple(), "is_simulated": True}
