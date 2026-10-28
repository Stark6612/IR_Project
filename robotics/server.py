"""FastAPI + WebSocket Live Telemetry Server for Agri-Doctor Robot.

Connects the Python Robotics Controller, Kinematics, PID, and OpenCV Perception
directly to the React/TypeScript web dashboard.
"""

from __future__ import annotations
import asyncio
import base64
import json
import cv2
from typing import Set, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agri_doctor.world import FieldWorld
from agri_doctor.robot_controller import RobotController
from agri_doctor.models import Coordinate, EntityType, RobotState, PlantHealth
from agri_doctor.cv_perception import CropComputerVisionPipeline

app = FastAPI(title="Agri-Doctor Robot Telemetry Server", version="1.0.0")

# Enable CORS for Vite dev server and production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global simulation instance
world = FieldWorld(width=8, height=6)
world.load_scenario("mixed_field")
controller = RobotController(world)
cv_pipeline = CropComputerVisionPipeline()

# Server state
simulation_running = False
simulation_speed = 1.0  # multiplier: 1.0 = ~350ms per step
active_connections: Set[WebSocket] = set()


class ScenarioRequest(BaseModel):
    scenario: str = "mixed_field"


class ObstacleRequest(BaseModel):
    x: int
    y: int


class SpeedRequest(BaseModel):
    speed: float = 1.0


class NoiseRequest(BaseModel):
    moisture_sigma: float = 3.5
    proximity_sigma: float = 2.0
    enabled: bool = True


class InspectRequest(BaseModel):
    x: int
    y: int


async def broadcast_state():
    """Broadcasts current telemetry snapshot to all connected WebSocket clients."""
    if not active_connections:
        return
    data = controller.get_telemetry()
    message = json.dumps(data)
    dead_connections = set()
    for ws in list(active_connections):
        try:
            await ws.send_text(message)
        except Exception:
            dead_connections.add(ws)
    active_connections.difference_update(dead_connections)


async def simulation_loop():
    """Background simulation tick runner."""
    global simulation_running
    while True:
        if simulation_running and controller.rover.state not in (
            RobotState.IDLE,
            RobotState.PAUSED,
            RobotState.COMPLETED,
            RobotState.ERROR,
        ):
            controller.step()
            await broadcast_state()

            # Base interval: 0.35s / speed
            delay = max(0.05, 0.35 / max(0.1, simulation_speed))
            await asyncio.sleep(delay)
        else:
            await asyncio.sleep(0.1)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulation_loop())


@app.get("/api/state")
def get_state() -> Dict[str, Any]:
    return controller.get_telemetry()


@app.post("/api/start")
async def start_mission():
    global simulation_running
    controller.start_mission()
    simulation_running = True
    await broadcast_state()
    return {"status": "started", "state": controller.rover.state.value}


@app.post("/api/pause")
async def pause_mission():
    global simulation_running
    controller.pause_mission()
    simulation_running = False
    await broadcast_state()
    return {"status": "paused", "state": controller.rover.state.value}


@app.post("/api/resume")
async def resume_mission():
    global simulation_running
    controller.resume_mission()
    simulation_running = True
    await broadcast_state()
    return {"status": "resumed", "state": controller.rover.state.value}


@app.post("/api/stop")
async def stop_mission():
    global simulation_running
    controller.stop_mission()
    simulation_running = False
    await broadcast_state()
    return {"status": "stopped", "state": controller.rover.state.value}


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "agri-doctor-backend"}


@app.get("/api/telemetry")
def get_current_telemetry():
    return controller.get_telemetry()


@app.post("/api/reset")
async def reset_mission(req: ScenarioRequest):
    global simulation_running
    controller.reset(req.scenario)
    simulation_running = False
    await broadcast_state()
    return {"status": "reset", "scenario": req.scenario}


@app.post("/api/step")
async def single_step():
    global simulation_running
    simulation_running = False  # Pause continuous loop on manual step
    state = controller.step()
    await broadcast_state()
    return state


@app.post("/api/speed")
def set_speed(req: SpeedRequest):
    global simulation_speed
    simulation_speed = max(0.1, min(10.0, req.speed))
    return {"speed": simulation_speed}


@app.post("/api/noise")
async def update_noise_config(req: NoiseRequest):
    controller.perception.noise_enabled = req.enabled
    controller.perception.set_noise_level(req.moisture_sigma, req.proximity_sigma)
    await broadcast_state()
    return {
        "status": "updated",
        "enabled": req.enabled,
        "moisture_sigma": req.moisture_sigma,
        "proximity_sigma": req.proximity_sigma,
    }


@app.post("/api/obstacle")
async def toggle_obstacle(req: ObstacleRequest):
    coord = Coordinate(req.x, req.y)
    cell = controller.world.get_cell(coord)
    if not cell:
        return {"error": "Out of bounds"}

    if cell.entity_type == EntityType.OBSTACLE:
        cell.entity_type = EntityType.EMPTY
        action = "cleared"
    elif cell.entity_type == EntityType.EMPTY and coord != controller.rover.coordinate:
        cell.entity_type = EntityType.OBSTACLE
        action = "placed"
        # If the newly placed obstacle blocks the rover's current planned path, trigger dynamic replanning
        if coord in controller.rover.planned_path:
            controller.rover.previous_path = list(controller.rover.planned_path)
            controller.rover.blocked_obstacle = coord
            if controller.current_task:
                blocked_coords = controller.world.get_blocked_coordinates()
                replan_res = controller.planner.plan(
                    start=controller.rover.coordinate,
                    goal=controller.current_task.target,
                    blocked=blocked_coords,
                )
                if replan_res.success and replan_res.path:
                    controller.rover.planned_path = replan_res.path
                    controller.path_index = 0
                    controller.rover.state = RobotState.MOVING
                    controller.replans_count += 1
                    controller.obstacles_encountered_count += 1
                    controller.executor.log_event(
                        event_type="navigation",
                        target=controller.current_task.target,
                        action="replan_path",
                        outcome="SUCCESS",
                        details={"new_path_length": len(replan_res.path), "reason": "dynamic_obstacle_placed"},
                    )
    else:
        return {"error": "Cannot place obstacle on occupied cell"}

    # Broadcast updated state with both old and new paths
    await broadcast_state()
    return {"action": action, "coordinate": (req.x, req.y)}


@app.post("/api/cv_inspect")
def inspect_cell_cv(req: InspectRequest):
    """Executes live UAV aerial drone computer vision analysis on cell patch with YOLOv8."""
    coord = Coordinate(req.x, req.y)
    cell = controller.world.get_cell(coord)
    if not cell:
        return {"error": "Cell not found"}

    patch, detections = cv_pipeline.get_drone_aerial_patch(
        entity_type=cell.entity_type,
        health=cell.plant_info.health if cell.plant_info else PlantHealth.HEALTHY,
        moisture=cell.plant_info.moisture if cell.plant_info else 60,
        coord=(req.x, req.y),
    )
    analysis = cv_pipeline.analyze_patch(patch, entity_type=cell.entity_type)
    analysis["yolo_detections"] = detections

    # Encode annotated patch to base64 JPEG
    _, buffer = cv2.imencode(".jpg", patch)
    base64_img = base64.b64encode(buffer).decode("utf-8")
    analysis["image_base64"] = f"data:image/jpeg;base64,{base64_img}"
    analysis["target_coordinate"] = (req.x, req.y)

    return analysis


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        # Send initial state immediately
        await websocket.send_text(json.dumps(controller.get_telemetry()))
        while True:
            # Keep socket alive and receive any incoming commands
            msg_text = await websocket.receive_text()
            try:
                msg = json.loads(msg_text)
                cmd = msg.get("action")
                if cmd == "start":
                    await start_mission()
                elif cmd == "pause":
                    await pause_mission()
                elif cmd == "resume":
                    await resume_mission()
                elif cmd == "stop":
                    await stop_mission()
                elif cmd == "step":
                    await single_step()
                elif cmd == "reset":
                    await reset_mission(ScenarioRequest(scenario=msg.get("scenario", "mixed_field")))
            except Exception:
                pass
    except WebSocketDisconnect:
        active_connections.discard(websocket)
