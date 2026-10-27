import React, { useEffect, useState } from 'react';
import type { SimulationTelemetry, CVInspectionData } from './types/telemetry';
import { telemetryService, type EngineMode } from './services/telemetryService';
import { Header } from './components/Header';
import { FieldCanvas } from './components/FieldCanvas';
import { MissionControls } from './components/MissionControls';
import { KinematicsHUD } from './components/KinematicsHUD';
import { SensorsAndCVCard } from './components/SensorsAndCVCard';
import { TaskQueueHUD } from './components/TaskQueueHUD';
import { EventLog } from './components/EventLog';
import { MetricsSummary } from './components/MetricsSummary';
import { KalmanFilterHUD } from './components/KalmanFilterHUD';

export const App: React.FC = () => {
  const [telemetry, setTelemetry] = useState<SimulationTelemetry>(() =>
    telemetryService.getCurrentTelemetry()
  );
  const [mode, setMode] = useState<EngineMode>(telemetryService.getMode());
  const [backendOnline, setBackendOnline] = useState<boolean>(telemetryService.isBackendOnline());
  const [speed, setSpeed] = useState<number>(1.0);
  const [activeCV, setActiveCV] = useState<CVInspectionData | null>(null);

  useEffect(() => {
    // Subscribe to telemetry updates
    const unsubTelemetry = telemetryService.subscribe((data) => {
      setTelemetry(data);
      if (data.cv_inspection) {
        setActiveCV(data.cv_inspection);
      }
    });

    // Subscribe to mode / connection status
    const unsubMode = telemetryService.subscribeMode((newMode, online) => {
      setMode(newMode);
      setBackendOnline(online);
    });

    return () => {
      unsubTelemetry();
      unsubMode();
    };
  }, []);

  const handleScenarioChange = (scenario: string) => {
    telemetryService.resetMission(scenario);
  };

  const handleSpeedChange = (newSpeed: number) => {
    setSpeed(newSpeed);
    telemetryService.setSpeed(newSpeed);
  };

  const handleCellClick = (x: number, y: number) => {
    telemetryService.toggleObstacle(x, y);
  };

  const handleCellInspect = async (x: number, y: number) => {
    const cvResult = await telemetryService.inspectCellCV(x, y);
    if (cvResult) {
      setActiveCV(cvResult);
    }
  };

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(telemetry, null, 2));
    const a = document.createElement('a');
    a.href = dataStr;
    a.download = `agri_doctor_${telemetry.world.scenario}_telemetry.json`;
    a.click();
  };

  const handleExportCsv = () => {
    const header = 'timestamp,event_type,target_x,target_y,action,outcome,message\n';
    const rows = telemetry.events.map((e) => {
      const tx = e.target ? e.target[0] : '';
      const ty = e.target ? e.target[1] : '';
      const msg = (e.details?.message || '').replace(/,/g, ';');
      return `${e.timestamp},${e.event_type},${tx},${ty},${e.action},${e.outcome},"${msg}"`;
    });
    const csvContent = 'data:text/csv;charset=utf-8,' + encodeURIComponent(header + rows.join('\n'));
    const a = document.createElement('a');
    a.href = csvContent;
    a.download = `agri_doctor_${telemetry.world.scenario}_events.csv`;
    a.click();
  };

  // Extract moisture at rover coordinate if on plant
  const roverCell = telemetry.world.cells.find(
    (c) => c.x === telemetry.rover.coordinate[0] && c.y === telemetry.rover.coordinate[1]
  );
  const currentMoisture = roverCell?.plant_info?.moisture;

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '16px 20px' }}>
      {/* Header with dual-mode badge & export */}
      <Header
        mode={mode}
        backendOnline={backendOnline}
        state={telemetry.rover.state}
        scenario={telemetry.world.scenario}
        onScenarioChange={handleScenarioChange}
        onExportJson={handleExportJson}
        onExportCsv={handleExportCsv}
      />

      {/* Main Grid & Controls Section */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '16px', marginBottom: '16px' }}>
        
        {/* Left Column: 2D Field Canvas & Playback Controls */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <FieldCanvas
            width={telemetry.world.width}
            height={telemetry.world.height}
            cells={telemetry.world.cells}
            roverCoord={telemetry.rover.coordinate}
            roverHeading={telemetry.rover.heading}
            currentTarget={telemetry.rover.current_target}
            plannedPath={telemetry.rover.planned_path}
            previousPath={telemetry.rover.previous_path}
            blockedObstacle={telemetry.rover.blocked_obstacle}
            proximityTriggered={telemetry.rover.proximity_cm < 15.0}
            onCellClick={handleCellClick}
            onCellInspect={handleCellInspect}
          />

          <MissionControls
            state={telemetry.rover.state}
            speed={speed}
            onStart={() => telemetryService.startMission()}
            onPause={() => telemetryService.pauseMission()}
            onResume={() => telemetryService.resumeMission()}
            onStop={() => telemetryService.stopMission()}
            onReset={() => telemetryService.resetMission(telemetry.world.scenario)}
            onStep={() => telemetryService.stepMission()}
            onSpeedChange={handleSpeedChange}
          />
        </div>

        {/* Right Column: Kinematics HUD & Sensors/OpenCV Card */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <KinematicsHUD kinematics={telemetry.kinematics} />
          <SensorsAndCVCard
            moistureReading={currentMoisture}
            proximityCm={telemetry.rover.proximity_cm}
            battery={telemetry.rover.battery}
            cvData={activeCV}
          />
        </div>

      </div>

      {/* Discrete 1D Kalman Filter (State Estimation HUD) */}
      <div style={{ marginBottom: '16px' }}>
        <KalmanFilterHUD telemetry={telemetry} />
      </div>

      {/* Bottom Section: Task Queue, Live Event Log & Metrics Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
        <TaskQueueHUD tasks={telemetry.tasks} />
        <EventLog events={telemetry.events} />
      </div>

      {/* Full-width Metrics Summary Bar */}
      <MetricsSummary
        metrics={telemetry.metrics}
        totalCells={telemetry.world.width * telemetry.world.height}
      />
    </div>
  );
};

export default App;
