"""Unit tests for Differential Drive Kinematics, PID Controller, and OpenCV Computer Vision Pipeline."""

import math
import pytest
import numpy as np
from agri_doctor.kinematics import (
    DifferentialDriveKinematics,
    PIDHeadingController,
    RobotPose2D,
)
from agri_doctor.cv_perception import CropComputerVisionPipeline
from agri_doctor.models import EntityType, PlantHealth


# ---------------- Kinematics Tests ----------------

def test_forward_kinematics_straight():
    diff = DifferentialDriveKinematics(track_width_m=0.25, wheel_radius_m=0.05)
    v, omega = diff.forward_kinematics(v_left=0.5, v_right=0.5)

    assert v == 0.5
    assert omega == 0.0


def test_forward_kinematics_pure_rotation():
    diff = DifferentialDriveKinematics(track_width_m=0.25, wheel_radius_m=0.05)
    # Left wheel backward, right wheel forward -> counter-clockwise rotation
    v, omega = diff.forward_kinematics(v_left=-0.25, v_right=0.25)

    assert v == 0.0
    assert omega == pytest.approx(2.0, rel=1e-2)


def test_inverse_kinematics():
    diff = DifferentialDriveKinematics(track_width_m=0.25, wheel_radius_m=0.05)
    wheels = diff.inverse_kinematics(v=0.4, omega=0.0)

    assert wheels.v_left == 0.4
    assert wheels.v_right == 0.4
    assert wheels.omega_left == pytest.approx(8.0, rel=1e-2)
    assert wheels.omega_right == pytest.approx(8.0, rel=1e-2)


def test_odometry_integration():
    diff = DifferentialDriveKinematics(track_width_m=0.25, wheel_radius_m=0.05)
    initial_pose = RobotPose2D(x=0.0, y=0.0, theta=0.0)  # Facing East

    # Drive 1 second at 0.5 m/s with 0 angular velocity
    next_pose = diff.integrate_odometry(initial_pose, v=0.5, omega=0.0, dt=1.0)

    assert next_pose.x == pytest.approx(0.5, rel=1e-2)
    assert next_pose.y == pytest.approx(0.0, abs=1e-3)
    assert next_pose.theta == 0.0


# ---------------- PID Controller Tests ----------------

def test_pid_heading_zero_error():
    pid = PIDHeadingController(kp=1.8, ki=0.05, kd=0.25)
    res = pid.compute(current_theta=0.0, target_theta=0.0, dt=0.1)

    assert res["error_deg"] == 0.0
    assert res["omega_command"] == 0.0


def test_pid_heading_positive_turn():
    pid = PIDHeadingController(kp=1.8, ki=0.05, kd=0.25)
    # Facing East (0), target North (pi/2) -> Needs positive angular velocity omega
    res = pid.compute(current_theta=0.0, target_theta=math.pi / 2, dt=0.1)

    assert res["error_deg"] == pytest.approx(90.0, rel=1e-2)
    assert res["omega_command"] > 0.0


def test_pid_heading_wrap_around():
    pid = PIDHeadingController(kp=1.8, ki=0.05, kd=0.25)
    # Facing 170 deg, target -170 deg -> shortest turn across boundary is +20 deg (170 + 20 = 190 = -170 deg)
    cur = math.radians(170)
    tgt = math.radians(-170)
    res = pid.compute(current_theta=cur, target_theta=tgt, dt=0.1)

    assert res["error_deg"] == pytest.approx(20.0, rel=1e-2)


# ---------------- OpenCV Computer Vision Tests ----------------

def test_cv_empty_soil():
    cv_pipe = CropComputerVisionPipeline()
    patch = cv_pipe.generate_synthetic_crop_patch(EntityType.EMPTY)
    res = cv_pipe.analyze_patch(patch)

    assert res["detected"] is False
    assert res["classification"] == "empty_soil_or_obstacle"


def test_cv_healthy_crop():
    cv_pipe = CropComputerVisionPipeline()
    patch = cv_pipe.generate_synthetic_crop_patch(EntityType.PLANT, health=PlantHealth.HEALTHY)
    res = cv_pipe.analyze_patch(patch)

    assert res["detected"] is True
    assert res["classification"] == "crop"
    assert res["health_status"] == "healthy"
    assert res["is_diseased"] is False
    assert res["confidence"] > 0.85


def test_cv_diseased_crop_chlorosis():
    cv_pipe = CropComputerVisionPipeline()
    patch = cv_pipe.generate_synthetic_crop_patch(EntityType.PLANT, health=PlantHealth.SUSPECTED_DISEASE)
    res = cv_pipe.analyze_patch(patch)

    assert res["detected"] is True
    assert res["classification"] == "crop"
    assert res["health_status"] == "suspected_disease"
    assert res["is_diseased"] is True
    assert res["chlorosis_ratio"] >= 0.15


def test_cv_weed_classification():
    cv_pipe = CropComputerVisionPipeline()
    patch = cv_pipe.generate_synthetic_crop_patch(EntityType.WEED)
    res = cv_pipe.analyze_patch(patch)

    assert res["detected"] is True
    assert res["classification"] == "weed"
    assert res["mean_excess_green"] > 0
