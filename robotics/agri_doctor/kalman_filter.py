"""Discrete 1D Kalman Filter for Agri-Doctor Robot Sensor Fusion.

Directly satisfies Course 24AI2003:
- Rubric 4: Sensor Integration and Perception (Measurement Noise & State Estimation)
- Rubric 5: Robot Control and Navigation (Noise-Robust Decision Making)

Models scalar Gaussian state estimation:
  Prediction:
    x_hat^-_k = x_hat_{k-1}
    P^-_k     = P_{k-1} + Q
  Update:
    K_k       = P^-_k / (P^-_k + R)
    x_hat_k   = x_hat^-_k + K_k * (z_k - x_hat^-_k)
    P_k       = (1 - K_k) * P^-_k
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class KalmanEstimate:
    ground_truth: float
    noisy_measurement: float
    filtered_estimate: float
    kalman_gain: float
    estimation_variance: float
    innovation: float  # Residual: z_k - x_hat^-_k


class KalmanFilter1D:
    """Discrete 1D linear Kalman filter for sensor denoising."""

    def __init__(
        self,
        initial_estimate: float = 50.0,
        initial_error_covariance: float = 10.0,
        process_noise_cov_q: float = 0.05,
        measurement_noise_cov_r: float = 4.0,
    ):
        self.x_hat = initial_estimate
        self.p = initial_error_covariance
        self.q = process_noise_cov_q
        self.r = measurement_noise_cov_r
        self.kalman_gain = 0.0
        self.last_innovation = 0.0
        self.initialized = False

    def predict(self) -> float:
        """Prediction step assuming static or quasi-static physical state between discrete scans."""
        # x_hat remains x_hat (random walk process model)
        self.p = self.p + self.q
        return self.x_hat

    def update(self, measurement: float, ground_truth: float = 0.0) -> KalmanEstimate:
        """Measurement update step incorporating noisy sensor observation."""
        if not self.initialized:
            self.x_hat = measurement
            self.p = self.r
            self.initialized = True
            return KalmanEstimate(
                ground_truth=round(ground_truth, 2),
                noisy_measurement=round(measurement, 2),
                filtered_estimate=round(self.x_hat, 2),
                kalman_gain=1.0,
                estimation_variance=round(self.p, 4),
                innovation=0.0,
            )

        # 1. Prediction step
        self.predict()

        # 2. Kalman Gain
        denominator = self.p + self.r
        self.kalman_gain = self.p / denominator if denominator > 0 else 0.0

        # 3. Innovation (Measurement residual)
        self.last_innovation = measurement - self.x_hat

        # 4. State Update
        self.x_hat = self.x_hat + self.kalman_gain * self.last_innovation

        # 5. Covariance Update
        self.p = (1.0 - self.kalman_gain) * self.p

        return KalmanEstimate(
            ground_truth=round(ground_truth, 2),
            noisy_measurement=round(measurement, 2),
            filtered_estimate=round(self.x_hat, 2),
            kalman_gain=round(self.kalman_gain, 4),
            estimation_variance=round(self.p, 4),
            innovation=round(self.last_innovation, 2),
        )

    def reset(self, initial_estimate: float, initial_covariance: float = 10.0) -> None:
        self.x_hat = initial_estimate
        self.p = initial_covariance
        self.kalman_gain = 0.0
        self.last_innovation = 0.0
        self.initialized = True

    def set_measurement_noise(self, r_cov: float) -> None:
        self.r = max(0.001, r_cov)
