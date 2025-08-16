"""
Guardian Integration for Anti-Drone Simulation
ΔΣ Seamless Sim2Real Bridge
"""

from __future__ import annotations

import json
import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import paho.mqtt.client as mqtt
import requests
from requests.exceptions import RequestException

from sim.emulator.anti_drone_world import AntiDroneWorld, Vector3D, AgentType
from sim.anti_drone_runner import AntiDroneScenarioRunner


@dataclass
class GuardianConfig:
    """Configuration for Guardian services"""
    core_url: str = "http://localhost:8005"
    vision_url: str = "http://localhost:8002"
    security_url: str = "http://localhost:8003"
    comfort_url: str = "http://localhost:8004"
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    api_timeout: int = 5


class GuardianIntegration:
    """Integration layer between simulation and Guardian services"""
    
    def __init__(self, config: GuardianConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # MQTT client for real-time communication
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        
        # State tracking
        self.guardian_state = {
            "core_status": "unknown",
            "vision_status": "unknown",
            "security_status": "unknown",
            "comfort_status": "unknown",
            "last_decision": None,
            "pending_requests": [],
            "active_tracks": []
        }
        
        # Performance metrics
        self.metrics = {
            "decisions_made": 0,
            "response_times": [],
            "successful_integrations": 0,
            "failed_integrations": 0
        }
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            # Subscribe to Guardian topics
            topics = [
                "guardian/decision/#",
                "guardian/event/#",
                "guardian/explain/#",
                "intent/security/#",
                "intent/user/#"
            ]
            for topic in topics:
                client.subscribe(topic)
        else:
            self.logger.error(f"Failed to connect to MQTT: {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            payload = json.loads(msg.payload.decode())
            self._process_guardian_message(msg.topic, payload)
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON in MQTT message: {msg.payload}")
    
    def _process_guardian_message(self, topic: str, payload: Dict):
        """Process messages from Guardian services"""
        if topic.startswith("guardian/decision/"):
            self.guardian_state["last_decision"] = payload
            self.metrics["decisions_made"] += 1
            self.logger.info(f"Received decision: {payload}")
        
        elif topic.startswith("guardian/event/"):
            self.logger.info(f"Guardian event: {payload}")
        
        elif topic.startswith("intent/security/"):
            self.logger.info(f"Security intent: {payload}")
        
        elif topic.startswith("intent/user/"):
            self.logger.info(f"User intent: {payload}")
    
    def connect(self):
        """Connect to Guardian services"""
        try:
            # Connect to MQTT
            self.mqtt_client.connect(self.config.mqtt_host, self.config.mqtt_port, 60)
            self.mqtt_client.loop_start()
            
            # Check service health
            self._check_services_health()
            
            self.logger.info("Successfully connected to Guardian services")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Guardian services: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Guardian services"""
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
    
    def _check_services_health(self):
        """Check health of all Guardian services"""
        services = {
            "core": self.config.core_url,
            "vision": self.config.vision_url,
            "security": self.config.security_url,
            "comfort": self.config.comfort_url
        }
        
        for service_name, url in services.items():
            try:
                response = requests.get(f"{url}/health", timeout=self.config.api_timeout)
                if response.status_code == 200:
                    self.guardian_state[f"{service_name}_status"] = "healthy"
                    self.logger.info(f"{service_name} service is healthy")
                else:
                    self.guardian_state[f"{service_name}_status"] = "unhealthy"
                    self.logger.warning(f"{service_name} service returned {response.status_code}")
            except RequestException as e:
                self.guardian_state[f"{service_name}_status"] = "unreachable"
                self.logger.error(f"{service_name} service is unreachable: {e}")
    
    def send_detection_to_vision(self, detection: Dict) -> bool:
        """Send detection to Vision service"""
        try:
            # Format detection for Vision service
            vision_detection = {
                "camera_id": detection["sensor_id"],
                "timestamp": detection["timestamp"],
                "detections": [{
                    "class": detection["agent_type"],
                    "confidence": detection["confidence"],
                    "bbox": [0, 0, 100, 100],  # Placeholder bbox
                    "position": detection["position"]
                }]
            }
            
            # Send via MQTT (Vision service listens to these topics)
            topic = f"vision/detection/{detection['sensor_id']}"
            payload = json.dumps(vision_detection)
            self.mqtt_client.publish(topic, payload)
            
            self.logger.debug(f"Sent detection to Vision: {vision_detection}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send detection to Vision: {e}")
            return False
    
    def send_event_to_core(self, event: Dict) -> bool:
        """Send event to Core service for decision making"""
        try:
            # Format event for Core service
            core_event = {
                "event": {
                    "type": event["type"],
                    "camera_id": event.get("camera_id", "sim_camera"),
                    "time": time.strftime("%H:%M"),
                    "mode": "away",  # Default mode
                    "data": event.get("data", {})
                }
            }
            
            # Send to Core /decide endpoint
            response = requests.post(
                f"{self.config.core_url}/decide",
                json=core_event,
                timeout=self.config.api_timeout
            )
            
            if response.status_code == 200:
                decision = response.json()
                self.logger.info(f"Core decision: {decision}")
                self.metrics["successful_integrations"] += 1
                return True
            else:
                self.logger.error(f"Core service returned {response.status_code}")
                self.metrics["failed_integrations"] += 1
                return False
                
        except RequestException as e:
            self.logger.error(f"Failed to send event to Core: {e}")
            self.metrics["failed_integrations"] += 1
            return False
    
    def send_approval_to_safety(self, request_id: str, approved: bool) -> bool:
        """Send approval/denial to Safety service"""
        try:
            endpoint = "approve" if approved else "deny"
            payload = {"request_id": request_id}
            
            response = requests.post(
                f"{self.config.core_url}/{endpoint}",
                json=payload,
                timeout=self.config.api_timeout
            )
            
            if response.status_code == 200:
                self.logger.info(f"Safety {endpoint}: {request_id}")
                return True
            else:
                self.logger.error(f"Safety service returned {response.status_code}")
                return False
                
        except RequestException as e:
            self.logger.error(f"Failed to send approval to Safety: {e}")
            return False
    
    def get_guardian_status(self) -> Dict:
        """Get current Guardian system status"""
        return {
            "services": self.guardian_state,
            "metrics": self.metrics.copy(),
            "timestamp": time.time()
        }


class IntegratedAntiDroneRunner(AntiDroneScenarioRunner):
    """Anti-drone runner with Guardian integration"""
    
    def __init__(self, 
                 guardian_config: GuardianConfig,
                 mqtt_host: str = "localhost",
                 mqtt_port: int = 1883,
                 telemetry_dir: str = "telemetry"):
        super().__init__(mqtt_host, mqtt_port, telemetry_dir)
        
        self.guardian = GuardianIntegration(guardian_config)
        self.integration_enabled = False
    
    def enable_guardian_integration(self):
        """Enable integration with Guardian services"""
        if self.guardian.connect():
            self.integration_enabled = True
            self.logger.info("Guardian integration enabled")
        else:
            self.logger.warning("Failed to enable Guardian integration")
    
    def disable_guardian_integration(self):
        """Disable integration with Guardian services"""
        self.guardian.disconnect()
        self.integration_enabled = False
        self.logger.info("Guardian integration disabled")
    
    def run_scenario(self, 
                    scenario_name: str,
                    scenario_config: Dict,
                    max_steps: Optional[int] = None,
                    save_telemetry: bool = True) -> ScenarioResult:
        """Run scenario with Guardian integration"""
        
        if self.integration_enabled:
            self.logger.info("Running scenario with Guardian integration")
        
        # Run base scenario
        result = super().run_scenario(scenario_name, scenario_config, max_steps, save_telemetry)
        
        # Add Guardian integration metrics
        if self.integration_enabled:
            guardian_status = self.guardian.get_guardian_status()
            result.metrics["guardian_integration"] = guardian_status
        
        return result
    
    def publish_detection(self, detection: Dict):
        """Publish detection with Guardian integration"""
        # Publish to MQTT (base functionality)
        super().publish_detection(detection)
        
        # Send to Guardian Vision service if integration enabled
        if self.integration_enabled:
            self.guardian.send_detection_to_vision(detection)
    
    def publish_track(self, track: Dict):
        """Publish track with Guardian integration"""
        # Publish to MQTT (base functionality)
        super().publish_track(track)
        
        # Send to Guardian Core service if integration enabled
        if self.integration_enabled:
            event = {
                "type": "track_updated",
                "camera_id": "sim_camera",
                "data": track
            }
            self.guardian.send_event_to_core(event)


def create_simulation_environment(config: GuardianConfig) -> IntegratedAntiDroneRunner:
    """Create integrated simulation environment"""
    runner = IntegratedAntiDroneRunner(config)
    
    # Enable Guardian integration
    runner.enable_guardian_integration()
    
    return runner


def run_integrated_training(scenarios_path: str, 
                          curriculum_phase: str,
                          guardian_config: GuardianConfig) -> Dict:
    """Run integrated training with Guardian services"""
    
    # Create integrated runner
    runner = create_simulation_environment(guardian_config)
    
    try:
        # Run curriculum
        results = runner.run_curriculum(scenarios_path, curriculum_phase)
        
        # Generate report
        report = runner.generate_report(results)
        
        # Add Guardian integration status
        guardian_status = runner.guardian.get_guardian_status()
        report["guardian_integration"] = guardian_status
        
        return report
        
    finally:
        runner.disable_guardian_integration()


def main():
    """Main function for integrated training"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Integrated Anti-Drone Training")
    parser.add_argument("scenarios", help="Path to scenarios YAML file")
    parser.add_argument("--curriculum", required=True, help="Curriculum phase to run")
    parser.add_argument("--core-url", default="http://localhost:8005", help="Core service URL")
    parser.add_argument("--vision-url", default="http://localhost:8002", help="Vision service URL")
    parser.add_argument("--security-url", default="http://localhost:8003", help="Security service URL")
    parser.add_argument("--comfort-url", default="http://localhost:8004", help="Comfort service URL")
    parser.add_argument("--mqtt-host", default="localhost", help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--report", help="Output report file")
    
    args = parser.parse_args()
    
    # Create Guardian configuration
    config = GuardianConfig(
        core_url=args.core_url,
        vision_url=args.vision_url,
        security_url=args.security_url,
        comfort_url=args.comfort_url,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port
    )
    
    # Run integrated training
    report = run_integrated_training(args.scenarios, args.curriculum, config)
    
    # Save or print report
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
    else:
        print(json.dumps(report, indent=2))
    
    # Print summary
    summary = report["summary"]
    guardian_status = report.get("guardian_integration", {})
    
    print(f"\n=== Training Summary ===")
    print(f"Scenarios: {summary['successful_scenarios']}/{summary['total_scenarios']} successful")
    print(f"Success Rate: {summary['success_rate']:.2%}")
    print(f"Total Duration: {summary['total_duration']:.2f}s")
    
    print(f"\n=== Guardian Integration ===")
    services = guardian_status.get("services", {})
    for service, status in services.items():
        if service.endswith("_status"):
            print(f"{service.replace('_status', '')}: {status}")
    
    metrics = guardian_status.get("metrics", {})
    print(f"Decisions Made: {metrics.get('decisions_made', 0)}")
    print(f"Successful Integrations: {metrics.get('successful_integrations', 0)}")
    print(f"Failed Integrations: {metrics.get('failed_integrations', 0)}")
    
    return 0 if summary['successful_scenarios'] == summary['total_scenarios'] else 1


if __name__ == "__main__":
    exit(main())



