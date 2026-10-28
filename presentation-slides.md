# Agri-Doctor Robot: Project Presentation Slides

---

## Slide 1: Title Slide

# Agri-Doctor Robot
### Vision-Guided Autonomous Crop Health Monitoring & Micro-Treatment Platform

- **Course:** 24AI2003 – Intelligent Robotics
- **Institution:** Karunya Institute of Technology and Sciences
- **Team Members:**
  - K Kelvyn G Melcheizedek (URK24CS5073)
  - Naresh C (URK24CS5061)
  - Sandesh J (URK24CS5062)
- **Deployment Budget:** ₹0 (100% Windows Native, Local Execution, Zero Cloud APIs)

---

## Slide 2: Problem Statement & Motivation

### Challenges in Modern Agriculture:
- **Severe Labor Shortages:** Manual scouting across vast crop fields is labor-intensive, slow, and error-prone.
- **Chemical Overuse & Runoff:** Indiscriminate broad-spectrum pesticide spraying degrades soil and contaminates groundwater.
- **Drought & Water Stress:** Delayed detection of localized dehydration leads to irreversible crop yield loss.
- **Late Disease Detection:** Leaf chlorosis and invasive weed colonization spread exponentially before visual human detection.

### Project Objective:
- Build an autonomous ground robot capable of **real-time field traversal, non-invasive plant diagnostics, precision micro-interventions**, and dynamic obstacle avoidance.

---

## Slide 3: Proposed Solution

### Autonomous Robotic Field Doctor:
- **Discrete 6×4 Agricultural Field Environment:** Standardized grid containing healthy crops, dehydrated plants, diseased leaves, invasive weeds, and rock obstacles.
- **Targeted Micro-Interventions:**
  - Precision root-zone watering (activating only when moisture $<30\%$).
  - Physical weed clearing without broadcast herbicide spraying.
  - Non-contact multi-spectral computer vision inspection.
- **Dual-Engine Architecture:**
  - High-performance **Python / FastAPI + ROS 2** WebSocket streaming backend.
  - Zero-install standalone **TypeScript in-browser simulation engine** for instant offline demonstration.

---

## Slide 4: System Architecture & Workflow

### End-to-End System Pipeline:

1. **Perception Layer:**
   - Simulated ultrasonic distance sensor ($<15\text{ cm}$ collision alarm)
   - Soil moisture probe + Gaussian noise generator $\mathcal{N}(0, \sigma^2)$
   - High-resolution camera feed for crop patch analysis
2. **State Estimation:**
   - Discrete 1D Kalman Filter filtering stochastic sensor noise
3. **Decision & Motion Planning:**
   - Priority Task Scheduler (Safety > Hydration > Disease > Weed > Patrol)
   - A* Heuristic Motion Planner (Manhattan distance metric)
4. **Actuation & Control:**
   - 2-wheel differential drive kinematics + closed-loop PID heading controller
5. **Interactive Telemetry Dashboard:**
   - React 19 + TypeScript + SVG visualization with live telemetry export

---

## Slide 5: Motion Planning & Dynamic Collision Avoidance

### A* Manhattan Heuristic Search:
- **Heuristic Function:** $h(n) = |x_n - x_{goal}| + |y_n - y_{goal}|$
- **Orthogonal 4-Directional Grid Movement:** East, North, West, South.
- **Provable Optimality:** Guaranteed shortest collision-free path to agricultural targets.

### Real-Time Dynamic Replanning:
- **Reactive Ultrasonic Trigger:** Proximity reading $<15\text{ cm}$ immediately activates `AVOIDING_OBSTACLE` state.
- **Instant Detour (<0.05 ms):** Dynamically updates blocked cells and recalculates a detour without resetting the mission.
- **Dual-Trajectory Visualization:** Simultaneous display of original blocked route (red dashed) vs. active collision-free detour (green flowing).

---

## Slide 6: Computer Vision Diagnostic Pipeline

### Local OpenCV Leaf Analysis (Zero Cloud Dependency):
- **Excess Green Index ($\text{ExG}$):**
  $$\text{ExG} = 2G - R - B$$
  Distinguishes dense weed vegetation from healthy crops under variable illumination.
- **HSV Color Foliage Segmentation:**
  - Isolates active leaf biomass within $H \in [25^\circ, 85^\circ]$.
- **Quantitative Chlorosis Assessment:**
  - Computes yellow necrosis pixel ratio within $H \in [15^\circ, 35^\circ]$.
  - Flags disease warning if yellow ratio exceeds threshold ($>15\%$).

---

## Slide 7: Robot Kinematics & Closed-Loop Steering

### 2-Wheel Differential Drive Kinematics:
- **Track Width:** $L = 0.25\text{ m}$, **Wheel Radius:** $r = 0.05\text{ m}$
- **Forward Kinematics:**
  $$v = \frac{r(v_R + v_L)}{2}, \quad \omega = \frac{r(v_R - v_L)}{L}$$

### Anti-Windup PID Heading Controller:
- **Error Function:** $e_\theta = \text{atan2}(\sin(\theta_{\text{target}} - \theta), \cos(\theta_{\text{target}} - \theta))$
- **Control Law:**
  $$\omega(t) = K_p e_\theta + K_i \int e_\theta \, dt + K_d \frac{de_\theta}{dt}$$
- **Tuned Gains:** $K_p = 1.8, \quad K_i = 0.05, \quad K_d = 0.25$
- Smooth 90° pivot turns with zero overshoot and rapid steady-state convergence.

---

## Slide 8: State Estimation via 1D Kalman Filter

### Tackling Real-World Sensor Noise:
- Physical sensors suffer from stochastic Gaussian noise: $z_k = x_k + v_k, \quad v_k \sim \mathcal{N}(0, \sigma^2)$
- Applied dual independent channels: **Soil Moisture** ($\sigma=3.5\%$) and **Proximity** ($\sigma=2.0\text{ cm}$).

### Recursive Linear Quadratic Estimator (LQE):
1. **Time Update (Predict):**
   $$\hat{x}_k^- = \hat{x}_{k-1}, \quad P_k^- = P_{k-1} + Q$$
2. **Measurement Update (Correct):**
   $$K_k = \frac{P_k^-}{P_k^- + R}, \quad \hat{x}_k = \hat{x}_k^- + K_k(z_k - \hat{x}_k^-), \quad P_k = (1 - K_k)P_k^-$$
- Smooths noisy raw spikes, preventing false watering actions and accidental obstacle panic stops.

---

## Slide 9: Experimental Results & Performance Metrics

### Validation Across 3 Benchmark Scenarios:
| Metric | Mixed Field | Obstacle Challenge | Dry Field |
| :--- | :---: | :---: | :---: |
| **Grid Dimensions** | 6 × 4 (24 cells) | 6 × 4 (24 cells) | 6 × 4 (24 cells) |
| **A\* Planning Latency** | $<0.05\text{ ms}$ | $<0.05\text{ ms}$ | $<0.05\text{ ms}$ |
| **Path Optimality** | 100% Optimal | 100% Optimal | 100% Optimal |
| **Weed Eradication Rate** | 100% (2/2) | 100% (1/1) | N/A |
| **Watering Accuracy** | 100% ($M < 30\%$) | 100% ($M < 30\%$) | 100% (4/4) |
| **Dynamic Obstacle Avoidance**| 100% Collision-Free | 100% Collision-Free | 100% Collision-Free |

### Test & Codebase Health:
- **30/30 Unit & Integration Tests Passing** (`pytest` in 0.53s).
- **Zero Linter or TypeScript Errors** in React 19 dashboard.

---

## Slide 10: Conclusion & Thank You

### Key Takeaways:
- **Fully Integrated Autonomous System:** Combines A* planning, differential drive PID steering, OpenCV multi-spectral analysis, and 1D Kalman filtering.
- **Targeted Precision Agriculture:** Replaces indiscriminate spraying and uniform irrigation with surgical, localized treatments.
- **Deterministic & Accessible:** Built entirely on Windows native tools with ₹0 cloud infrastructure cost.

---

# Thank You!

### Questions & Answers
**Open for Examiner & Faculty Evaluation**

- **GitHub Repository:** [github.com/Stark6612/IR_Project](https://github.com/Stark6612/IR_Project.git)
- **Live Demo Dashboard:** `http://localhost:3000/`
