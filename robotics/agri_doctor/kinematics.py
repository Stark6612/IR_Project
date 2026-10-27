"""Differential Drive Kinematics and PID Heading Controller for Agri-Doctor Robot.

Directly satisfies Course 24AI2003 Rubrics:
- Rubric 2: Kinematics and Motion Planning
- Rubric 5: Robot Control and Navigation (PID Control)
"""

from __future__ import annotations
import math
import time
from dataclasses import dataclass
from typing import Tuple, Dict, Any


@dataclass
class RobotPose2D:
    x: float  # meters
    y: float  # meters
    theta: float  # radians (0 = East, pi/2 = North, pi = West, -pi/2 = South)


@dataclass
class WheelVelocities:
    v_left: float  # m/s
    v_right: float  # m/s
    omega_left: float  # rad/s
    omega_right: float  # rad/s


class DifferentialDriveKinematics:
    """Models forward and inverse kinematics of a 2-wheel differential drive mobile robot."""

    def __init__(self, track_width_m: float = 0.25, wheel_radius_m: float = 0.05):
        self.L = track_width_m  # Distance between wheels (baseline)
        self.r = wheel_radius_m  # Wheel radius

    def forward_kinematics(self, v_left: float, v_right: float) -> Tuple[float, float]:
        """
        Calculates linear velocity (v) and angular velocity (omega) from wheel speeds.
        v = (v_r + v_l) / 2
        omega = (v_r - v_l) / L
        """
        v = (v_right + v_left) / 2.0
        omega = (v_right - v_left) / self.L
        return v, omega

    def inverse_kinematics(self, v: float, omega: float) -> WheelVelocities:
        """
        Calculates required individual wheel linear and angular velocities from (v, omega).
        v_l = v - (omega * L) / 2
        v_r = v + (omega * L) / 2
        """
        v_l = v - (omega * self.L) / 2.0
        v_r = v + (omega * self.L) / 2.0
        w_l = v_l / self.r
        w_r = v_r / self.r
        return WheelVelocities(
            v_left=round(v_l, 4),
            v_right=round(v_r, 4),
            omega_left=round(w_l, 4),
            omega_right=round(w_r, 4),
        )

    def integrate_odometry(
        self, pose: RobotPose2D, v: float, omega: float, dt: float
    ) -> RobotPose2D:
        """
        Integrates differential drive motion over time interval dt.
        dot_x = v * cos(theta)
        dot_y = v * sin(theta)
        dot_theta = omega
        """
        new_theta = pose.theta + omega * dt
        # Normalize theta to [-pi, pi]
        new_theta = math.atan2(math.sin(new_theta), math.cos(new_theta))

        new_x = pose.x + v * math.cos(pose.theta) * dt
        new_y = pose.y + v * math.sin(pose.theta) * dt

        return RobotPose2D(x=new_x, y=new_y, theta=new_theta)


class PIDHeadingController:
    """
    Closed-loop PID controller for robot heading alignment to waypoint trajectories.
    u(t) = Kp * e(t) + Ki * integral(e(t) dt) + Kd * de(t)/dt
    """

    def __init__(
        self,
        kp: float = 1.8,
        ki: float = 0.05,
        kd: float = 0.25,
        max_omega: float = 2.0,
        integral_limit: float = 1.0,
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_omega = max_omega
        self.integral_limit = integral_limit

        self.integral_error = 0.0
        self.prev_error = 0.0
        self.last_time = time.time()

    def reset(self) -> None:
        self.integral_error = 0.0
        self.prev_error = 0.0
        self.last_time = time.time()

    def compute(self, current_theta: float, target_theta: float, dt: float = 0.1) -> Dict[str, Any]:
        """
        Computes angular velocity steering command (omega) to minimize heading error.
        Error is wrapped to [-pi, pi] range.
        """
        # Angular error wrapped to [-pi, pi]
        error = math.atan2(
            math.sin(target_theta - current_theta),
            math.cos(target_theta - current_theta),
        )

        # Numerical integration with anti-windup clamping
        self.integral_error += error * dt
        self.integral_error = max(
            -self.integral_limit, min(self.integral_limit, self.integral_error)
        )

        # Derivative term
        derivative = (error - self.prev_error) / dt if dt > 0 else 0.0
        self.prev_error = error

        # PID control law
        omega = (self.kp * error) + (self.ki * self.integral_error) + (self.kd * derivative)

        # Clamp output angular velocity
        omega_clamped = max(-self.max_omega, min(self.max_omega, omega))

        return {
            "error_rad": round(error, 4),
            "error_deg": round(math.degrees(error), 2),
            "p_term": round(self.kp * error, 4),
            "i_term": round(self.ki * self.integral_error, 4),
            "d_term": round(self.kd * derivative, 4),
            "omega_command": round(omega_clamped, 4),
        }
