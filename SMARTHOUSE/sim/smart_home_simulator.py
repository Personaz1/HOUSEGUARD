"""
Smart Home Simulator
ΔΣ Virtual House with Full Device Emulation
"""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

import aiomqtt
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
from PIL import Image, ImageDraw, ImageFont
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartHomeSimulator:
    """Full smart home simulator with device emulation"""
    
    def __init__(self, mqtt_host: str = "localhost", mqtt_port: int = 1883):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.devices = {}
        self.device_states = {}
        self.simulation_time = datetime.now()
        self.occupancy = {
            "living": False,
            "kitchen": False,
            "bedroom": False,
            "bathroom": False,
            "entrance": False
        }
        self.weather = {
            "temperature": 20.0,
            "humidity": 50.0,
            "pressure": 1013.25,
            "wind_speed": 5.0,
            "precipitation": 0.0
        }
        self.security_mode = "disarmed"  # disarmed, armed_home, armed_away
        self.app = FastAPI(title="Smart Home Simulator")
        self.setup_routes()
        
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "timestamp": self.simulation_time.isoformat()}
        
        @self.app.get("/time")
        async def get_time():
            return {"time": self.simulation_time.isoformat()}
        
        @self.app.get("/devices")
        async def get_devices():
            return {"devices": self.device_states}
        
        @self.app.get("/device/{device_id}")
        async def get_device(device_id: str):
            if device_id not in self.device_states:
                raise HTTPException(status_code=404, detail="Device not found")
            return {"device": self.device_states[device_id]}
        
        @self.app.post("/device/{device_id}/set")
        async def set_device(device_id: str, state: Dict):
            if device_id not in self.devices:
                raise HTTPException(status_code=404, detail="Device not found")
            
            # Update device state
            self.device_states[device_id].update(state)
            
            # Publish to MQTT
            await self.publish_device_state(device_id, self.device_states[device_id])
            
            return {"status": "success", "device": self.device_states[device_id]}
        
        @self.app.get("/camera/{camera_id}/frame")
        async def get_camera_frame(camera_id: str):
            """Generate camera frame"""
            frame = self.generate_camera_frame(camera_id)
            return StreamingResponse(io.BytesIO(frame), media_type="image/jpeg")
        
        @self.app.get("/occupancy")
        async def get_occupancy():
            return {"occupancy": self.occupancy}
        
        @self.app.post("/occupancy/{room}")
        async def set_occupancy(room: str, occupied: bool):
            if room not in self.occupancy:
                raise HTTPException(status_code=404, detail="Room not found")
            
            self.occupancy[room] = occupied
            await self.update_motion_sensors()
            return {"status": "success", "room": room, "occupied": occupied}
        
        @self.app.get("/weather")
        async def get_weather():
            return {"weather": self.weather}
        
        @self.app.post("/weather")
        async def set_weather(weather_data: Dict):
            self.weather.update(weather_data)
            await self.update_environmental_sensors()
            return {"status": "success", "weather": self.weather}
        
        @self.app.get("/security/mode")
        async def get_security_mode():
            return {"mode": self.security_mode}
        
        @self.app.post("/security/mode")
        async def set_security_mode(mode: str):
            if mode not in ["disarmed", "armed_home", "armed_away"]:
                raise HTTPException(status_code=400, detail="Invalid security mode")
            
            self.security_mode = mode
            await self.publish_security_state()
            return {"status": "success", "mode": self.security_mode}
    
    async def start(self):
        """Start the simulator"""
        # Load device configurations
        await self.load_devices()
        
        # Initialize device states
        await self.initialize_device_states()
        
        # Start MQTT client
        await self.start_mqtt()
        
        # Start simulation loops
        asyncio.create_task(self.simulation_loop())
        asyncio.create_task(self.sensor_loop())
        asyncio.create_task(self.camera_loop())
        
        logger.info("Smart Home Simulator started")
    
    async def load_devices(self):
        """Load device configurations"""
        try:
            with open("configs/devices.json", "r") as f:
                devices = json.load(f)
            
            for device in devices:
                self.devices[device["id"]] = device
                
        except FileNotFoundError:
            logger.error("devices.json not found, using default devices")
            self.devices = self.get_default_devices()
    
    def get_default_devices(self) -> Dict:
        """Get default device configurations"""
        return {
            "light_living_main": {
                "id": "light_living_main",
                "type": "light",
                "room": "living",
                "protocol": "mqtt",
                "capabilities": ["on_off", "brightness", "color_temp"],
                "topics": {
                    "set": "home/device/light_living_main/set",
                    "state": "home/device/light_living_main/state"
                }
            },
            "camera_front_door": {
                "id": "camera_front_door",
                "type": "camera",
                "room": "entrance",
                "protocol": "mqtt",
                "capabilities": ["motion_detection", "person_detection", "snapshot", "stream"],
                "topics": {
                    "events": "vision/events/camera_front_door",
                    "snapshot": "vision/snapshot/camera_front_door"
                }
            }
        }
    
    async def initialize_device_states(self):
        """Initialize device states"""
        for device_id, device in self.devices.items():
            self.device_states[device_id] = self.get_default_device_state(device)
    
    def get_default_device_state(self, device: Dict) -> Dict:
        """Get default state for device type"""
        device_type = device["type"]
        
        if device_type == "light":
            return {
                "state": "OFF",
                "brightness": 0,
                "color_temp": 2700,
                "last_update": self.simulation_time.isoformat()
            }
        elif device_type == "lock":
            return {
                "state": "LOCKED",
                "last_update": self.simulation_time.isoformat()
            }
        elif device_type == "camera":
            return {
                "motion_detected": False,
                "person_detected": False,
                "last_motion": None,
                "last_update": self.simulation_time.isoformat()
            }
        elif device_type == "motion_sensor":
            return {
                "motion": False,
                "occupancy": False,
                "last_motion": None,
                "last_update": self.simulation_time.isoformat()
            }
        elif device_type == "thermostat":
            return {
                "current_temperature": 20.0,
                "target_temperature": 22.0,
                "mode": "heat",
                "last_update": self.simulation_time.isoformat()
            }
        elif device_type == "siren":
            return {
                "state": "OFF",
                "volume": 50,
                "pattern": "continuous",
                "last_update": self.simulation_time.isoformat()
            }
        else:
            return {
                "state": "OFF",
                "last_update": self.simulation_time.isoformat()
            }
    
    async def start_mqtt(self):
        """Start MQTT client"""
        try:
            self.mqtt_client = aiomqtt.Client(
                hostname=self.mqtt_host,
                port=self.mqtt_port
            )
            await self.mqtt_client.connect()
            logger.info(f"Connected to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
    
    async def publish_device_state(self, device_id: str, state: Dict):
        """Publish device state to MQTT"""
        try:
            device = self.devices[device_id]
            
            # Check if device has state topic
            if "state" not in device["topics"]:
                logger.debug(f"Device {device_id} has no state topic, skipping")
                return
                
            topic = device["topics"]["state"]
            payload = {
                "device_id": device_id,
                "state": state,
                "timestamp": self.simulation_time.isoformat()
            }
            
            await self.mqtt_client.publish(topic, json.dumps(payload))
            logger.debug(f"Published state for {device_id}: {state}")
            
        except Exception as e:
            logger.error(f"Failed to publish state for {device_id}: {e}")
    
    async def publish_security_state(self):
        """Publish security system state"""
        try:
            payload = {
                "mode": self.security_mode,
                "timestamp": self.simulation_time.isoformat()
            }
            
            await self.mqtt_client.publish("home/security/state", json.dumps(payload))
            logger.info(f"Published security state: {self.security_mode}")
            
        except Exception as e:
            logger.error(f"Failed to publish security state: {e}")
    
    async def simulation_loop(self):
        """Main simulation loop"""
        while True:
            try:
                # Update simulation time
                self.simulation_time += timedelta(seconds=1)
                
                # Update device states based on time and conditions
                await self.update_device_states()
                
                # Publish periodic updates
                await self.publish_periodic_updates()
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
                await asyncio.sleep(5)
    
    async def sensor_loop(self):
        """Sensor simulation loop"""
        while True:
            try:
                # Simulate sensor readings
                await self.simulate_sensor_readings()
                
                # Update environmental sensors
                await self.update_environmental_sensors()
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in sensor loop: {e}")
                await asyncio.sleep(10)
    
    async def camera_loop(self):
        """Camera simulation loop"""
        while True:
            try:
                # Simulate camera events
                await self.simulate_camera_events()
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in camera loop: {e}")
                await asyncio.sleep(5)
    
    async def update_device_states(self):
        """Update device states based on simulation conditions"""
        for device_id, device in self.devices.items():
            device_type = device["type"]
            
            if device_type == "thermostat":
                # Simulate temperature changes
                current_temp = self.device_states[device_id]["current_temperature"]
                target_temp = self.device_states[device_id]["target_temperature"]
                
                if current_temp < target_temp:
                    self.device_states[device_id]["current_temperature"] += 0.1
                elif current_temp > target_temp:
                    self.device_states[device_id]["current_temperature"] -= 0.1
                
                self.device_states[device_id]["last_update"] = self.simulation_time.isoformat()
            
            elif device_type == "motion_sensor":
                # Update based on occupancy
                room = device["room"]
                if room in self.occupancy:
                    self.device_states[device_id]["motion"] = self.occupancy[room]
                    self.device_states[device_id]["occupancy"] = self.occupancy[room]
                    
                    if self.occupancy[room]:
                        self.device_states[device_id]["last_motion"] = self.simulation_time.isoformat()
                
                self.device_states[device_id]["last_update"] = self.simulation_time.isoformat()
    
    async def simulate_sensor_readings(self):
        """Simulate sensor readings"""
        # Simulate random sensor events
        for device_id, device in self.devices.items():
            if device["type"] in ["motion_sensor", "door_sensor", "window_sensor"]:
                # Random events (low probability)
                if random.random() < 0.01:  # 1% chance per 5 seconds
                    await self.trigger_sensor_event(device_id)
    
    async def trigger_sensor_event(self, device_id: str):
        """Trigger a sensor event"""
        device = self.devices[device_id]
        device_type = device["type"]
        
        if device_type == "motion_sensor":
            # Toggle motion
            current_state = self.device_states[device_id]["motion"]
            self.device_states[device_id]["motion"] = not current_state
            self.device_states[device_id]["occupancy"] = not current_state
            
            if not current_state:
                self.device_states[device_id]["last_motion"] = self.simulation_time.isoformat()
            
            # Update occupancy for the room
            room = device["room"]
            if room in self.occupancy:
                self.occupancy[room] = not current_state
        
        elif device_type == "door_sensor":
            # Toggle door state
            current_state = self.device_states[device_id]["state"]
            new_state = "OPEN" if current_state == "CLOSED" else "CLOSED"
            self.device_states[device_id]["state"] = new_state
        
        elif device_type == "window_sensor":
            # Toggle window state
            current_state = self.device_states[device_id]["state"]
            new_state = "OPEN" if current_state == "CLOSED" else "CLOSED"
            self.device_states[device_id]["state"] = new_state
        
        # Publish state update
        await self.publish_device_state(device_id, self.device_states[device_id])
    
    async def update_environmental_sensors(self):
        """Update environmental sensors based on weather"""
        for device_id, device in self.devices.items():
            if device["type"] == "humidity_sensor":
                self.device_states[device_id]["humidity"] = self.weather["humidity"]
                self.device_states[device_id]["temperature"] = self.weather["temperature"]
                self.device_states[device_id]["last_update"] = self.simulation_time.isoformat()
                
                await self.publish_device_state(device_id, self.device_states[device_id])
            
            elif device["type"] == "air_quality_sensor":
                # Simulate air quality based on occupancy and weather
                base_pm25 = 10.0
                if any(self.occupancy.values()):
                    base_pm25 += 5.0
                if self.weather["precipitation"] > 0:
                    base_pm25 -= 2.0
                
                self.device_states[device_id]["pm25"] = max(5.0, base_pm25 + random.uniform(-2, 2))
                self.device_states[device_id]["pm10"] = self.device_states[device_id]["pm25"] * 1.5
                self.device_states[device_id]["voc"] = random.uniform(100, 300)
                self.device_states[device_id]["co2"] = 400 + (50 if any(self.occupancy.values()) else 0)
                self.device_states[device_id]["last_update"] = self.simulation_time.isoformat()
                
                await self.publish_device_state(device_id, self.device_states[device_id])
    
    async def simulate_camera_events(self):
        """Simulate camera events"""
        for device_id, device in self.devices.items():
            if device["type"] == "camera":
                # Check for motion based on occupancy
                room = device["room"]
                motion_detected = self.occupancy.get(room, False)
                
                if motion_detected != self.device_states[device_id]["motion_detected"]:
                    self.device_states[device_id]["motion_detected"] = motion_detected
                    self.device_states[device_id]["person_detected"] = motion_detected
                    
                    if motion_detected:
                        self.device_states[device_id]["last_motion"] = self.simulation_time.isoformat()
                        
                        # Publish camera event
                        await self.publish_camera_event(device_id, "motion")
                        
                        if motion_detected:
                            await self.publish_camera_event(device_id, "person_detected")
    
    async def publish_camera_event(self, camera_id: str, event_type: str):
        """Publish camera event to MQTT"""
        try:
            device = self.devices[camera_id]
            topic = device["topics"]["events"]
            
            payload = {
                "camera_id": camera_id,
                "event_type": event_type,
                "timestamp": self.simulation_time.isoformat(),
                "confidence": random.uniform(0.7, 0.95)
            }
            
            await self.mqtt_client.publish(topic, json.dumps(payload))
            logger.info(f"Published camera event: {camera_id} - {event_type}")
            
        except Exception as e:
            logger.error(f"Failed to publish camera event: {e}")
    
    async def update_motion_sensors(self):
        """Update motion sensors based on occupancy"""
        for device_id, device in self.devices.items():
            if device["type"] == "motion_sensor":
                room = device["room"]
                if room in self.occupancy:
                    occupied = self.occupancy[room]
                    
                    if occupied != self.device_states[device_id]["motion"]:
                        self.device_states[device_id]["motion"] = occupied
                        self.device_states[device_id]["occupancy"] = occupied
                        
                        if occupied:
                            self.device_states[device_id]["last_motion"] = self.simulation_time.isoformat()
                        
                        await self.publish_device_state(device_id, self.device_states[device_id])
    
    async def publish_periodic_updates(self):
        """Publish periodic device updates"""
        # Publish updates every 30 seconds
        if self.simulation_time.second % 30 == 0:
            for device_id in self.devices:
                await self.publish_device_state(device_id, self.device_states[device_id])
    
    def generate_camera_frame(self, camera_id: str) -> bytes:
        """Generate a camera frame as JPEG"""
        # Create a simple image with camera info
        width, height = 640, 480
        image = Image.new('RGB', (width, height), color='black')
        draw = ImageDraw.Draw(image)
        
        # Add camera info
        device = self.devices.get(camera_id, {})
        room = device.get("room", "unknown")
        motion = self.device_states.get(camera_id, {}).get("motion_detected", False)
        
        # Draw some basic content
        draw.rectangle([50, 50, width-50, height-50], outline='white', width=2)
        draw.text((width//2, 100), f"Camera: {camera_id}", fill='white', anchor='mm')
        draw.text((width//2, 150), f"Room: {room}", fill='white', anchor='mm')
        draw.text((width//2, 200), f"Motion: {'YES' if motion else 'NO'}", fill='green' if motion else 'red', anchor='mm')
        draw.text((width//2, 250), f"Time: {self.simulation_time.strftime('%H:%M:%S')}", fill='white', anchor='mm')
        
        # Convert to JPEG
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=80)
        return buffer.getvalue()
    
    async def stop(self):
        """Stop the simulator"""
        if hasattr(self, 'mqtt_client'):
            await self.mqtt_client.disconnect()
        logger.info("Smart Home Simulator stopped")

async def main():
    """Main function"""
    simulator = SmartHomeSimulator()
    await simulator.start()
    
    # Start FastAPI server
    config = uvicorn.Config(simulator.app, host="0.0.0.0", port=8200)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
