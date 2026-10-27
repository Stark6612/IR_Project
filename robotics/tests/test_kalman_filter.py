"""Unit Tests for 1D Kalman Filter and Noisy Perception."""

import pytest
from robotics.agri_doctor.kalman_filter import KalmanFilter1D
from robotics.agri_doctor.models import Coordinate, Heading, EntityType, PlantInfo, PlantHealth
from robotics.agri_doctor.world import FieldWorld
from robotics.agri_doctor.perception_simulator import PerceptionSimulator


def test_kalman_filter_initialization():
    kf = KalmanFilter1D(initial_estimate=40.0, initial_error_covariance=5.0)
    assert kf.x_hat == 40.0
    assert kf.p == 5.0
    assert kf.kalman_gain == 0.0


def test_kalman_filter_convergence_on_constant_state():
    """Verify that a noisy measurement stream converges towards ground truth with decreasing variance."""
    true_val = 25.0
    kf = KalmanFilter1D(
        initial_estimate=50.0,  # Biased initial prior
        initial_error_covariance=20.0,
        process_noise_cov_q=0.01,
        measurement_noise_cov_r=4.0,
    )

    # Feed 20 measurements centered around 25.0 with alternating +/- 1.5 noise
    for i in range(20):
        noise = 1.5 if i % 2 == 0 else -1.5
        kf.update(true_val + noise, ground_truth=true_val)

    # Estimate should be close to 25.0
    assert abs(kf.x_hat - true_val) < 1.0
    # Estimation variance should have dropped significantly below initial 20.0
    assert kf.p < 2.0


def test_kalman_filter_transient_spike_rejection():
    """Verify that Kalman filter dampens a single rogue measurement outlier."""
    kf = KalmanFilter1D(
        initial_estimate=60.0,
        initial_error_covariance=1.0,
        process_noise_cov_q=0.02,
        measurement_noise_cov_r=9.0,
    )

    # Steady state
    for _ in range(5):
        kf.update(60.0, ground_truth=60.0)

    # Rogue outlier measurement: 95.0
    estimate = kf.update(95.0, ground_truth=60.0)

    # The filtered estimate must not jump to 95; it should be dampened by Kalman gain (gain ~ 0.1)
    assert estimate.filtered_estimate < 70.0
    assert estimate.innovation == pytest.approx(35.0, abs=1.0)


def test_perception_simulator_gaussian_noise_and_filtering():
    world = FieldWorld(6, 4)
    world.load_scenario("mixed_field")
    perception = PerceptionSimulator(world)

    # Test reading moisture at (1, 0) where ground truth moisture is 65
    res = perception.read_soil_moisture(Coordinate(1, 0))
    assert res["moisture"] == 65.0
    assert "moisture_noisy" in res
    assert "moisture_filtered" in res
    assert "kalman" in res
    assert res["kalman"]["ground_truth"] == 65.0
    assert abs(res["moisture_filtered"] - 65.0) < 15.0  # Initial convergence bounds


def test_perception_simulator_proximity_kalman():
    world = FieldWorld(6, 4)
    world.load_scenario("obstacle_challenge")
    perception = PerceptionSimulator(world)

    # Obstacle wall at x=2, rover at (0, 0) facing East -> target is (1, 0) which is clear (dist 100cm)
    prox = perception.read_proximity(Coordinate(0, 0), Heading.EAST)
    assert prox["distance_cm"] == 100.0
    assert "kalman" in prox
    assert prox["kalman"]["ground_truth"] == 100.0
