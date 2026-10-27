# Agri-Doctor Robot: Vision-Guided Autonomous Crop Health Monitoring & Micro-Treatment Platform

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61dafb.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178c6.svg)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.0-646cff.svg)](https://vitejs.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.12-5C3EE8.svg)](https://opencv.org/)
[![Tests](https://img.shields.io/badge/pytest-30%20passed-success.svg)](https://pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Course:** 24AI2003 – Intelligent Robotics  
**Institution:** Karunya Institute of Technology and Sciences  
**Authors:** K Kelvyn G Melcheizedek (URK24CS5073), Naresh C (URK24CS5061), Sandesh J (URK24CS5062)  
**Budget:** ₹0 (100% Windows Native, Local Execution, Zero Cloud APIs)

---

## 1. Project Overview

The **Agri-Doctor Robot** is an autonomous agricultural robotics system designed to address labor shortages, drought stress, and chemical overuse through targeted micro-interventions.

Operating across a discrete 6×4 crop field grid, the virtual robot integrates:
1. **Kinematics & Control:** 2-wheel differential drive kinematics ($L=0.25\text{ m}, r=0.05\text{ m}$) with an anti-windup closed-loop **PID Heading Controller** ($K_p=1.8, K_i=0.05, K_d=0.25$).
2. **Path Planning:** Provably optimal **A\* Heuristic Search** utilizing the Manhattan distance heuristic, with real-time dynamic obstacle avoidance and replanning ($<0.05\text{ ms}$ latency).
3. **Computer Vision:** Local **OpenCV** pipeline performing HSV foliage segmentation, Excess Green Index ($\text{ExG} = 2G - R - B$) weed discrimination, and quantitative chlorosis disease analysis ($>15\%$ yellow ratio).
4. **State Estimation:** Discrete **1D Kalman Filter (Linear Quadratic Estimator)** filtering stochastic Gaussian noise $\mathcal{N}(0, \sigma^2)$ over soil moisture and ultrasonic proximity sensors.
5. **Priority Scheduling:** Autonomous finite state machine (`IDLE` $\to$ `PLANNING` $\to$ `MOVING` $\to$ `AVOIDING_OBSTACLE` $\to$ `EXECUTING_TASK`) resolving competing agricultural goals (Safety > Hydration > Disease Inspection > Weed Eradication > Patrol).
6. **Dual-Engine Architecture:** High-throughput Python FastAPI WebSocket streaming backend + Standalone In-Browser TypeScript fail-safe engine.

---

## 2. System Architecture

```text
                               ┌──────────────────────────────────────────────┐
                               │       React 19 + TypeScript + Vite UI        │
                               │  - 2D Canvas SVG Grid with Animated Rover    │
                               │  - Real-time Kinematics & PID Steering HUD   │
                               │  - Discrete 1D Kalman Filter Waveform HUD    │
                               │  - OpenCV Diagnostic Thumbnail Viewer        │
                               │  - Scenario Selector, Controls & CSV Export  │
                               └──────────────────────┬───────────────────────┘
                                                      │
                                      HTTP / WebSocket / Local Bridge
                                                      │
                     ┌────────────────────────────────┴──────────────────────────────┐
                     ▼                                                               ▼
      ┌───────────────────────────────┐                             ┌───────────────────────────────┐
      │   Python / FastAPI Backend    │                             │      ROS 2 Modular Nodes      │
      │  - A* Manhattan Path Planner  │                             │  - world_simulator_node       │
      │  - Differential Drive & PID   │  ◄── [Identical Domain] ──► │  - perception_node            │
      │  - 1D Kalman Filter (LQE)     │      [Logic & Contracts]    │  - planner_node               │
      │  - OpenCV CV Pipeline (ExG)   │                             │  - controller_node            │
      └───────────────────────────────┘                             └───────────────────────────────┘
```

---

## 3. Directory Layout

```text
IR Project/
├── dashboard/                 # React 19 + TypeScript + Vite web dashboard
│   ├── src/
│   │   ├── components/        # FieldCanvas, KinematicsHUD, KalmanFilterHUD, SensorsAndCVCard, etc.
│   │   ├── services/          # clientSimulationEngine.ts (fail-safe fallback), telemetryService.ts
│   │   └── types/             # TypeScript data contracts & telemetry schemas
├── robotics/                  # Core Python robotics algorithms & ROS 2 nodes
│   ├── agri_doctor/
│   │   ├── a_star.py          # A* Manhattan distance heuristic motion planner
│   │   ├── cv_perception.py   # OpenCV HSV, ExG, and chlorosis image processing
│   │   ├── kalman_filter.py   # Discrete 1D Kalman filter state estimator
│   │   ├── kinematics.py      # Differential drive kinematics & closed-loop PID controller
│   │   ├── mission_planner.py # Priority task queue engine
│   │   ├── models.py          # Dataclasses, states, and coordinates
│   │   ├── perception_simulator.py # Simulated sensors with Gaussian noise
│   │   ├── robot_controller.py# Autonomous rover state machine
│   │   ├── task_executor.py   # Virtual watering, weeding, and inspection actions
│   │   └── world.py           # 6x4 discrete field model & 3 deterministic scenarios
│   ├── ros_nodes/             # Modular ROS 2 node wrappers (rclpy + standalone fallback)
│   ├── tests/                 # 30 passing unit and integration tests
│   ├── run_simulation_cli.py  # Standalone CLI ASCII runner
│   └── server.py              # FastAPI WebSocket telemetry streaming server
├── scripts/                   # Automated PowerShell launchers & test runners
├── pytest.ini                 # Pytest root configuration
├── .gitignore                 # Git ignore rules
└── README.md                  # Project documentation
```

---

## 4. Quick Start

### 1. One-Click Launch (Recommended on Windows)
```powershell
.\scripts\run-all.ps1
```
* Launches the Python FastAPI backend on `http://127.0.0.1:8000`
* Launches the Vite React dashboard on `http://localhost:5173`

### 2. Manual Startup
**Backend:**
```bash
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --app-dir robotics
```

**Frontend:**
```bash
cd dashboard
npm install
npm run dev
```

### 3. Running Test Suite
```bash
python -m pytest
```
*Executes all 30 unit and integration tests across pathfinding, kinematics, PID stability, OpenCV computer vision, and the Kalman Filter.*

---

## 5. Course Rubrics Alignment (Course 24AI2003)

| Rubric # | Assessment Area | Implementation in Repository | Marks |
| :---: | :--- | :--- | :---: |
| **Rubric 1** | Robot Design & Architecture | Differential drive chassis ($40\times 30\text{ cm}, L=0.25\text{ m}, r=0.05\text{ m}$); modular decoupled software design. | 5 |
| **Rubric 2** | Kinematics & Motion Planning | Forward/inverse kinematics; $A^*$ Manhattan heuristic orthogonal path planning. | 5 |
| **Rubric 3** | AI / ML Implementation | Authentic OpenCV pipeline: HSV canopy isolation, $\text{ExG} = 2G - R - B$ weed discrimination, $>15\%$ chlorosis disease ratio. | 5 |
| **Rubric 4** | Sensor Integration & Perception | Discrete 1D Kalman Filter (LQE) filtering Gaussian noise $\mathcal{N}(0, \sigma^2)$ over soil moisture & ultrasonic proximity. | 5 |
| **Rubric 5** | Robot Control & Navigation | Closed-loop PID Heading Controller ($K_p=1.8, K_i=0.05, K_d=0.25$) with anti-windup clamping and shortest-turn $[-\pi, \pi]$ wrap. | 5 |
| **Rubric 6** | Innovation & Critical Thinking | Real-time dynamic obstacle injection & live rerouting; priority task scheduler; dual-engine fallback. | 4 |
| **Rubric 7** | Performance Analysis | 100% path optimality ratio; sub-millisecond A* latency; CSV and JSON mission audit export. | 4 |
| **Rubric 8** | Presentation & Viva Voce | 3-minute timed presentation script and examiner Q&A (`docs/demo-script.md`). | 4 |
| **Rubric 9** | Completeness of the Report | Comprehensive 14-page report template with source code snippets and output screenshots. | 3 |
| **Total** | | | **40** |

---

## 6. License
This project is released under the MIT License for educational and academic research purposes.
