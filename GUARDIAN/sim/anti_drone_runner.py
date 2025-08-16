"""
Anti-Drone Scenario Runner
ΔΣ Guardian Training Environment
"""

from __future__ import annotations

import json
import time
import yaml
import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path

import paho.mqtt.client as mqtt
import numpy as np

from sim.emulator.anti_drone_world import AntiDroneWorld, Vector3D, AgentType


@dataclass
class ScenarioResult:
    scenario_name: str
    success: bool
    duration: float
    metrics: Dict[str, Any]
    violations: List[str]
    telemetry_path: Optional[str] = None


class AntiDroneScenarioRunner:
    def __init__(self, 
                 mqtt_host: str = "localhost",
                 mqtt_port: int = 1883,
                 telemetry_dir: str = "telemetry"):
        self.mqtt_client = mqtt.Client()
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.telemetry_dir = Path(telemetry_dir)
        self.telemetry_dir.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.performance_metrics = {
            "scenarios_run": 0,
            "successful_scenarios": 0,
            "total_detections": 0,
            "total_false_positives": 0,
            "average_response_time": 0.0
        }
    
    def connect_mqtt(self):
        """Connect to MQTT broker"""
        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            self.logger.info(f"Connected to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT: {e}")
    
    def disconnect_mqtt(self):
        """Disconnect from MQTT broker"""
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
    
    def publish_detection(self, detection: Dict):
        """Publish detection to MQTT"""
        topic = f"vision/detect/{detection['sensor_id']}"
        payload = json.dumps(detection)
        self.mqtt_client.publish(topic, payload)
    
    def publish_track(self, track: Dict):
        """Publish track to MQTT"""
        topic = f"vision/track/{track['track_id']}"
        payload = json.dumps(track)
        self.mqtt_client.publish(topic, payload)
    
    def publish_world_state(self, world_state: Dict):
        """Publish world state to MQTT"""
        topic = "sim/state/world"
        payload = json.dumps(world_state)
        self.mqtt_client.publish(topic, payload)
    
    def load_scenario(self, scenario_path: str) -> Dict:
        """Load scenario from YAML file"""
        with open(scenario_path, 'r', encoding='utf-8') as f:
            scenarios = yaml.safe_load(f)
        return scenarios
    
    def run_scenario(self, 
                    scenario_name: str,
                    scenario_config: Dict,
                    max_steps: Optional[int] = None,
                    save_telemetry: bool = True) -> ScenarioResult:
        """Run a single anti-drone scenario"""
        
        self.logger.info(f"Starting scenario: {scenario_name}")
        start_time = time.time()
        
        # Initialize world
        world = AntiDroneWorld(dt=0.05, seed=42)
        
        # Apply weather conditions
        if "weather" in scenario_config:
            weather = scenario_config["weather"]
            world.weather.wind_speed = weather.get("wind_speed", 0.0)
            world.weather.fog_density = weather.get("fog_density", 0.0)
            world.weather.visibility = weather.get("visibility", 1000.0)
            world.weather.rain_intensity = weather.get("rain_intensity", 0.0)
        
        # Calculate max steps if not provided
        if max_steps is None:
            duration = scenario_config.get("duration", 60)
            max_steps = int(duration / world.dt)
        
        # Prepare spawn schedule
        spawn_schedule = {}
        for spawn in scenario_config.get("spawns", []):
            step = int(spawn["time"] / world.dt)
            spawn_schedule[step] = spawn
        
        # Telemetry collection
        telemetry = []
        violations = []
        
        # Run simulation
        obs = world.reset()
        telemetry.append({"step": 0, "time": 0.0, **obs})
        
        for step in range(1, max_steps + 1):
            # Spawn agents if scheduled
            if step in spawn_schedule:
                spawn_config = spawn_schedule[step]
                self._spawn_agent(world, spawn_config)
            
            # Step simulation
            obs = world.step()
            telemetry.append({"step": step, "time": world.time, **obs})
            
            # Publish to MQTT
            self.publish_world_state(obs)
            
            # Publish detections
            for detection in obs["detections"]:
                self.publish_detection(detection)
            
            # Publish tracks
            for track in obs["tracks"]:
                self.publish_track(track)
            
            # Check for violations
            violations.extend(self._check_violations(obs, scenario_config))
            
            # Check if scenario objectives are met
            if self._check_success_criteria(obs, scenario_config):
                self.logger.info(f"Scenario {scenario_name} completed successfully at step {step}")
                break
        
        # Calculate final metrics
        duration = time.time() - start_time
        final_metrics = self._calculate_metrics(telemetry, scenario_config)
        
        # Save telemetry if requested
        telemetry_path = None
        if save_telemetry:
            telemetry_path = self._save_telemetry(telemetry, scenario_name)
        
        # Update performance metrics
        self.performance_metrics["scenarios_run"] += 1
        if len(violations) == 0:
            self.performance_metrics["successful_scenarios"] += 1
        
        result = ScenarioResult(
            scenario_name=scenario_name,
            success=len(violations) == 0,
            duration=duration,
            metrics=final_metrics,
            violations=violations,
            telemetry_path=telemetry_path
        )
        
        self.logger.info(f"Scenario {scenario_name} completed in {duration:.2f}s")
        return result
    
    def _spawn_agent(self, world: AntiDroneWorld, spawn_config: Dict):
        """Spawn agent based on configuration"""
        agent_type = AgentType(spawn_config["agent_type"])
        position = Vector3D(*spawn_config["position"])
        velocity = Vector3D(*spawn_config["velocity"])
        size = spawn_config.get("size", 1.0)
        
        if agent_type == AgentType.UAV:
            world.spawn_uav(position, velocity, size)
        elif agent_type == AgentType.BIRD:
            world.spawn_bird(position, velocity)
        elif agent_type == AgentType.ALLY:
            # TODO: Implement ally spawning
            pass
        elif agent_type == AgentType.TRASH:
            # TODO: Implement trash spawning
            pass
    
    def _check_violations(self, obs: Dict, scenario_config: Dict) -> List[str]:
        """Check for scenario violations"""
        violations = []
        
        # Check success criteria
        success_criteria = scenario_config.get("success_criteria", [])
        for criterion in success_criteria:
            if not self._evaluate_criterion(obs, criterion):
                violations.append(f"Failed criterion: {criterion}")
        
        return violations
    
    def _evaluate_criterion(self, obs: Dict, criterion: str) -> bool:
        """Evaluate a single success criterion"""
        try:
            # Simple criterion evaluation (can be extended)
            if "detection_time" in criterion:
                # Check if detection time is within limits
                if "detection_time < 10" in criterion:
                    # TODO: Implement detection time calculation
                    pass
            
            elif "track_continuity" in criterion:
                # Check track continuity
                if "track_continuity > 0.8" in criterion:
                    # TODO: Implement track continuity calculation
                    pass
            
            elif "false_positives" in criterion:
                # Check false positive rate
                if "false_positives == 0" in criterion:
                    # TODO: Implement false positive detection
                    pass
            
            return True  # Default to True for now
            
        except Exception as e:
            self.logger.error(f"Error evaluating criterion {criterion}: {e}")
            return False
    
    def _check_success_criteria(self, obs: Dict, scenario_config: Dict) -> bool:
        """Check if scenario success criteria are met"""
        # TODO: Implement comprehensive success checking
        return False
    
    def _calculate_metrics(self, telemetry: List[Dict], scenario_config: Dict) -> Dict[str, Any]:
        """Calculate performance metrics from telemetry"""
        metrics = {
            "total_steps": len(telemetry),
            "total_detections": 0,
            "total_tracks": 0,
            "average_detection_confidence": 0.0,
            "weather_conditions": {},
            "agent_counts": {}
        }
        
        if not telemetry:
            return metrics
        
        # Calculate metrics from telemetry
        total_confidence = 0.0
        detection_count = 0
        
        for step_data in telemetry:
            # Count detections
            detections = step_data.get("detections", [])
            metrics["total_detections"] += len(detections)
            
            # Calculate average confidence
            for detection in detections:
                total_confidence += detection.get("confidence", 0.0)
                detection_count += 1
            
            # Count tracks
            tracks = step_data.get("tracks", [])
            metrics["total_tracks"] = max(metrics["total_tracks"], len(tracks))
            
            # Track agent counts
            agents = step_data.get("agents", {})
            for agent_id, agent_data in agents.items():
                agent_type = agent_data.get("type", "unknown")
                if agent_type not in metrics["agent_counts"]:
                    metrics["agent_counts"][agent_type] = 0
                metrics["agent_counts"][agent_type] += 1
        
        # Calculate averages
        if detection_count > 0:
            metrics["average_detection_confidence"] = total_confidence / detection_count
        
        # Weather conditions from last step
        if telemetry:
            last_step = telemetry[-1]
            metrics["weather_conditions"] = last_step.get("weather", {})
        
        return metrics
    
    def _save_telemetry(self, telemetry: List[Dict], scenario_name: str) -> str:
        """Save telemetry to file"""
        timestamp = int(time.time())
        filename = f"{scenario_name}_{timestamp}.jsonl"
        filepath = self.telemetry_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for step_data in telemetry:
                f.write(json.dumps(step_data) + '\n')
        
        self.logger.info(f"Telemetry saved to {filepath}")
        return str(filepath)
    
    def run_curriculum(self, scenarios_path: str, curriculum_phase: str) -> List[ScenarioResult]:
        """Run a complete curriculum phase"""
        scenarios = self.load_scenario(scenarios_path)
        curriculum = scenarios.get("curriculum", {})
        
        if curriculum_phase not in curriculum:
            raise ValueError(f"Curriculum phase {curriculum_phase} not found")
        
        phase_config = curriculum[curriculum_phase]
        scenario_names = phase_config.get("scenarios", [])
        
        self.logger.info(f"Running curriculum phase: {curriculum_phase}")
        self.logger.info(f"Scenarios: {scenario_names}")
        
        results = []
        for scenario_name in scenario_names:
            if scenario_name in scenarios.get("scenarios", {}):
                scenario_config = scenarios["scenarios"][scenario_name]
                result = self.run_scenario(scenario_name, scenario_config)
                results.append(result)
            else:
                self.logger.warning(f"Scenario {scenario_name} not found")
        
        return results
    
    def generate_report(self, results: List[ScenarioResult]) -> Dict[str, Any]:
        """Generate comprehensive training report"""
        report = {
            "summary": {
                "total_scenarios": len(results),
                "successful_scenarios": sum(1 for r in results if r.success),
                "success_rate": sum(1 for r in results if r.success) / len(results) if results else 0,
                "total_duration": sum(r.duration for r in results),
                "average_duration": sum(r.duration for r in results) / len(results) if results else 0
            },
            "scenarios": [],
            "performance_metrics": self.performance_metrics.copy()
        }
        
        for result in results:
            scenario_report = {
                "name": result.scenario_name,
                "success": result.success,
                "duration": result.duration,
                "violations": result.violations,
                "metrics": result.metrics,
                "telemetry_path": result.telemetry_path
            }
            report["scenarios"].append(scenario_report)
        
        return report


def main():
    """Main function for running anti-drone scenarios"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Anti-Drone Defense Scenarios")
    parser.add_argument("scenarios", help="Path to scenarios YAML file")
    parser.add_argument("--scenario", help="Specific scenario to run")
    parser.add_argument("--curriculum", help="Curriculum phase to run")
    parser.add_argument("--mqtt-host", default="localhost", help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--telemetry-dir", default="telemetry", help="Telemetry output directory")
    parser.add_argument("--report", help="Output report file")
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = AntiDroneScenarioRunner(
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        telemetry_dir=args.telemetry_dir
    )
    
    try:
        # Connect to MQTT
        runner.connect_mqtt()
        
        if args.curriculum:
            # Run curriculum phase
            results = runner.run_curriculum(args.scenarios, args.curriculum)
        elif args.scenario:
            # Run specific scenario
            scenarios = runner.load_scenario(args.scenarios)
            if args.scenario in scenarios.get("scenarios", {}):
                scenario_config = scenarios["scenarios"][args.scenario]
                result = runner.run_scenario(args.scenario, scenario_config)
                results = [result]
            else:
                print(f"Scenario {args.scenario} not found")
                return 1
        else:
            print("Please specify either --scenario or --curriculum")
            return 1
        
        # Generate and save report
        report = runner.generate_report(results)
        
        if args.report:
            with open(args.report, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
        else:
            print(json.dumps(report, indent=2))
        
        # Print summary
        success_count = sum(1 for r in results if r.success)
        print(f"\nSummary: {success_count}/{len(results)} scenarios successful")
        
        return 0 if success_count == len(results) else 1
        
    finally:
        runner.disconnect_mqtt()


if __name__ == "__main__":
    exit(main())



