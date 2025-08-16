#!/usr/bin/env python3
"""
3D House World for Guardian Simulator
ΔΣ Integrated Smart Home with AI Training
"""

import asyncio
import json
import logging
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    """Smart home device types"""
    LIGHT = "light"
    CAMERA = "camera"
    SENSOR = "sensor"
    THERMOSTAT = "thermostat"
    LOCK = "lock"
    SIREN = "siren"
    FAN = "fan"
    BLIND = "blind"
    PLUG = "plug"
    VACUUM = "vacuum"

class RoomType(Enum):
    """House room types"""
    LIVING = "living"
    KITCHEN = "kitchen"
    BEDROOM = "bedroom"
    BATHROOM = "bathroom"
    GARAGE = "garage"
    OUTDOOR = "outdoor"

@dataclass
class Device:
    """Smart home device"""
    id: str
    type: DeviceType
    room: RoomType
    position: Tuple[float, float, float]
    state: Dict = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    mqtt_topic: str = ""
    
    def update_state(self, new_state: Dict):
        """Update device state"""
        self.state.update(new_state)
        logger.debug(f"Device {self.id} state updated: {new_state}")

@dataclass
class Room:
    """House room"""
    name: str
    type: RoomType
    position: Tuple[float, float, float]
    size: Tuple[float, float, float]
    occupancy: bool = False
    temperature: float = 22.0
    humidity: float = 45.0
    devices: List[str] = field(default_factory=list)

@dataclass
class House3DWorld:
    """3D House World for Guardian Simulator"""
    
    # World state
    time: float = 0.0
    weather: Dict = field(default_factory=lambda: {
        "temperature": 18.0,
        "humidity": 60.0,
        "pressure": 1013.25,
        "wind_speed": 5.0,
        "precipitation": 0.0,
        "condition": "partly_cloudy"
    })
    
    # Security
    security_mode: str = "disarmed"
    alarm_triggered: bool = False
    
    # House structure
    rooms: Dict[str, Room] = field(default_factory=dict)
    devices: Dict[str, Device] = field(default_factory=dict)
    
    # AI Training data
    training_data: List[Dict] = field(default_factory=list)
    scenarios: List[Dict] = field(default_factory=list)
    
    # MQTT integration
    mqtt_client = None
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    
    def __post_init__(self):
        """Initialize house structure"""
        self._create_house_layout()
        self._create_devices()
        self._setup_scenarios()
    
    def _create_house_layout(self):
        """Create house room layout"""
        self.rooms = {
            "living": Room("Living Room", RoomType.LIVING, (-4, 0, 0), (6, 4, 6)),
            "kitchen": Room("Kitchen", RoomType.KITCHEN, (4, 0, 0), (6, 4, 6)),
            "bedroom": Room("Bedroom", RoomType.BEDROOM, (-4, 0, 6), (6, 4, 6)),
            "bathroom": Room("Bathroom", RoomType.BATHROOM, (4, 0, 6), (6, 4, 6)),
            "garage": Room("Garage", RoomType.GARAGE, (12, 0, 0), (8, 4, 6)),
            "outdoor": Room("Outdoor", RoomType.OUTDOOR, (0, 0, -10), (20, 10, 20))
        }
    
    def _create_devices(self):
        """Create smart home devices"""
        # Lights
        self.devices["light_living_main"] = Device(
            "light_living_main", DeviceType.LIGHT, RoomType.LIVING,
            (-4, 3, 0), {"state": "OFF", "brightness": 0},
            ["on_off", "dimming"], "house/living/light/main"
        )
        
        self.devices["light_kitchen_main"] = Device(
            "light_kitchen_main", DeviceType.LIGHT, RoomType.KITCHEN,
            (4, 3, 0), {"state": "OFF", "brightness": 0},
            ["on_off", "dimming"], "house/kitchen/light/main"
        )
        
        self.devices["light_bedroom_main"] = Device(
            "light_bedroom_main", DeviceType.LIGHT, RoomType.BEDROOM,
            (-4, 3, 6), {"state": "OFF", "brightness": 0},
            ["on_off", "dimming"], "house/bedroom/light/main"
        )
        
        self.devices["light_outdoor_main"] = Device(
            "light_outdoor_main", DeviceType.LIGHT, RoomType.OUTDOOR,
            (0, 2, -5), {"state": "OFF", "brightness": 0},
            ["on_off", "motion_trigger"], "house/outdoor/light/main"
        )
        
        # Cameras
        self.devices["camera_front_door"] = Device(
            "camera_front_door", DeviceType.CAMERA, RoomType.OUTDOOR,
            (0, 2, 6.1), {"motion_detected": False, "person_detected": False},
            ["motion_detection", "person_detection", "recording"],
            "house/camera/front_door"
        )
        
        self.devices["camera_backyard"] = Device(
            "camera_backyard", DeviceType.CAMERA, RoomType.OUTDOOR,
            (0, 2, -6.1), {"motion_detected": False, "person_detected": False},
            ["motion_detection", "person_detection", "recording"],
            "house/camera/backyard"
        )
        
        self.devices["camera_garage"] = Device(
            "camera_garage", DeviceType.CAMERA, RoomType.GARAGE,
            (12, 2, 3.1), {"motion_detected": False, "person_detected": False},
            ["motion_detection", "person_detection", "recording"],
            "house/camera/garage"
        )
        
        self.devices["camera_living"] = Device(
            "camera_living", DeviceType.CAMERA, RoomType.LIVING,
            (-4, 3, 3), {"motion_detected": False, "person_detected": False},
            ["motion_detection", "person_detection", "recording"],
            "house/camera/living"
        )
        
        # Sensors
        self.devices["motion_sensor_living"] = Device(
            "motion_sensor_living", DeviceType.SENSOR, RoomType.LIVING,
            (-4, 3, 0), {"motion": False, "occupancy": False},
            ["motion_detection", "occupancy"], "house/sensor/living/motion"
        )
        
        self.devices["motion_sensor_kitchen"] = Device(
            "motion_sensor_kitchen", DeviceType.SENSOR, RoomType.KITCHEN,
            (4, 3, 0), {"motion": False, "occupancy": False},
            ["motion_detection", "occupancy"], "house/sensor/kitchen/motion"
        )
        
        self.devices["motion_sensor_bedroom"] = Device(
            "motion_sensor_bedroom", DeviceType.SENSOR, RoomType.BEDROOM,
            (-4, 3, 6), {"motion": False, "occupancy": False},
            ["motion_detection", "occupancy"], "house/sensor/bedroom/motion"
        )
        
        # Thermostats
        self.devices["thermostat_living"] = Device(
            "thermostat_living", DeviceType.THERMOSTAT, RoomType.LIVING,
            (-4, 2, 0), {"current_temperature": 22.0, "target_temperature": 22.0},
            ["temperature_control", "scheduling"], "house/thermostat/living"
        )
        
        # Security
        self.devices["door_sensor_front"] = Device(
            "door_sensor_front", DeviceType.SENSOR, RoomType.OUTDOOR,
            (0, 1.5, 6.1), {"state": "closed"},
            ["door_status"], "house/security/door/front"
        )
        
        self.devices["siren_main"] = Device(
            "siren_main", DeviceType.SIREN, RoomType.OUTDOOR,
            (0, 3, -5), {"state": "OFF", "volume": 0},
            ["alarm", "volume_control"], "house/security/siren/main"
        )
        
        # Add devices to rooms
        for device_id, device in self.devices.items():
            if device.room in self.rooms:
                self.rooms[device.room].devices.append(device_id)
    
    def _setup_scenarios(self):
        """Setup AI training scenarios"""
        self.scenarios = [
            {
                "name": "morning_routine",
                "description": "Morning automation routine",
                "triggers": ["time:07:00", "motion:bedroom"],
                "actions": [
                    "light_bedroom_main:ON",
                    "thermostat_living:22",
                    "light_living_main:ON"
                ],
                "ai_training": {
                    "input": ["time", "motion_sensor_bedroom", "light_bedroom_main"],
                    "output": ["light_living_main", "thermostat_living"],
                    "reward_function": "comfort_optimization"
                }
            },
            {
                "name": "security_breach",
                "description": "Security breach response",
                "triggers": ["motion:outdoor", "door_sensor_front:open"],
                "actions": [
                    "camera_front_door:record",
                    "siren_main:ON",
                    "light_outdoor_main:ON"
                ],
                "ai_training": {
                    "input": ["motion_sensor_outdoor", "door_sensor_front", "camera_front_door"],
                    "output": ["siren_main", "light_outdoor_main"],
                    "reward_function": "security_response"
                }
            },
            {
                "name": "energy_optimization",
                "description": "Energy consumption optimization",
                "triggers": ["occupancy:empty", "time:22:00"],
                "actions": [
                    "light_living_main:OFF",
                    "thermostat_living:18",
                    "light_kitchen_main:OFF"
                ],
                "ai_training": {
                    "input": ["occupancy_living", "occupancy_kitchen", "time"],
                    "output": ["light_living_main", "light_kitchen_main", "thermostat_living"],
                    "reward_function": "energy_efficiency"
                }
            }
        ]
    
    async def connect_mqtt(self):
        """Connect to MQTT broker"""
        try:
            import aiomqtt
            self.mqtt_client = aiomqtt.Client(
                hostname=self.mqtt_host,
                port=self.mqtt_port
            )
            await self.mqtt_client.connect()
            logger.info("Connected to MQTT broker")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
    
    async def publish_device_state(self, device_id: str):
        """Publish device state to MQTT"""
        if not self.mqtt_client:
            return
        
        try:
            device = self.devices[device_id]
            topic = device.mqtt_topic
            payload = {
                "device_id": device_id,
                "state": device.state,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.mqtt_client.publish(topic, json.dumps(payload))
            logger.debug(f"Published state for {device_id}")
            
        except Exception as e:
            logger.error(f"Failed to publish state for {device_id}: {e}")
    
    async def step(self, dt: float = 1.0):
        """Simulation step"""
        self.time += dt
        
        # Update weather
        self._update_weather(dt)
        
        # Update room conditions
        self._update_rooms(dt)
        
        # Update devices
        await self._update_devices(dt)
        
        # Generate training data
        self._generate_training_data()
        
        # Random events
        if random.random() < 0.01:  # 1% chance per second
            await self._trigger_random_event()
    
    def _update_weather(self, dt: float):
        """Update weather conditions"""
        self.weather["temperature"] += random.uniform(-0.1, 0.1) * dt
        self.weather["humidity"] += random.uniform(-0.5, 0.5) * dt
    
    def _update_rooms(self, dt: float):
        """Update room conditions"""
        for room in self.rooms.values():
            # Temperature drift
            target_temp = 22.0
            if room.occupancy:
                target_temp = 22.0
            else:
                target_temp = 18.0
            
            if room.temperature < target_temp:
                room.temperature += 0.1 * dt
            elif room.temperature > target_temp:
                room.temperature -= 0.1 * dt
    
    async def _update_devices(self, dt: float):
        """Update device states"""
        for device_id, device in self.devices.items():
            # Update thermostats
            if device.type == DeviceType.THERMOSTAT:
                room = self.rooms[device.room]
                target = device.state["target_temperature"]
                current = device.state["current_temperature"]
                
                if current < target:
                    device.state["current_temperature"] += 0.1 * dt
                elif current > target:
                    device.state["current_temperature"] -= 0.1 * dt
                
                # Publish state
                await self.publish_device_state(device_id)
    
    def _generate_training_data(self):
        """Generate AI training data"""
        data_point = {
            "timestamp": self.time,
            "weather": self.weather.copy(),
            "rooms": {name: {
                "occupancy": room.occupancy,
                "temperature": room.temperature,
                "humidity": room.humidity
            } for name, room in self.rooms.items()},
            "devices": {device_id: device.state.copy() 
                       for device_id, device in self.devices.items()},
            "security_mode": self.security_mode
        }
        
        self.training_data.append(data_point)
        
        # Keep only last 1000 data points
        if len(self.training_data) > 1000:
            self.training_data = self.training_data[-1000:]
    
    async def _trigger_random_event(self):
        """Trigger random smart home events"""
        events = [
            ("motion_sensor_living", {"motion": True, "occupancy": True}),
            ("motion_sensor_kitchen", {"motion": True, "occupancy": True}),
            ("camera_front_door", {"motion_detected": True, "person_detected": True}),
            ("door_sensor_front", {"state": "open"}),
            ("light_living_main", {"state": "ON", "brightness": 100})
        ]
        
        device_id, state = random.choice(events)
        if device_id in self.devices:
            self.devices[device_id].update_state(state)
            await self.publish_device_state(device_id)
            logger.info(f"Random event: {device_id} -> {state}")
    
    def get_house_state(self) -> Dict:
        """Get complete house state"""
        return {
            "time": self.time,
            "weather": self.weather,
            "security_mode": self.security_mode,
            "rooms": {name: {
                "name": room.name,
                "type": room.type.value,
                "position": room.position,
                "size": room.size,
                "occupancy": room.occupancy,
                "temperature": room.temperature,
                "humidity": room.humidity,
                "devices": room.devices
            } for name, room in self.rooms.items()},
            "devices": {device_id: {
                "id": device.id,
                "type": device.type.value,
                "room": device.room.value,
                "position": device.position,
                "state": device.state,
                "capabilities": device.capabilities,
                "mqtt_topic": device.mqtt_topic
            } for device_id, device in self.devices.items()}
        }
    
    def set_device_state(self, device_id: str, state: Dict) -> bool:
        """Set device state"""
        if device_id not in self.devices:
            return False
        
        device = self.devices[device_id]
        device.update_state(state)
        
        # Handle special cases
        if device.type == DeviceType.LIGHT and "state" in state:
            if state["state"] == "TOGGLE":
                current_state = device.state["state"]
                device.state["state"] = "ON" if current_state == "OFF" else "OFF"
        
        return True
    
    def set_room_occupancy(self, room_name: str, occupied: bool) -> bool:
        """Set room occupancy"""
        if room_name not in self.rooms:
            return False
        
        self.rooms[room_name].occupancy = occupied
        
        # Update motion sensors
        motion_sensor = f"motion_sensor_{room_name}"
        if motion_sensor in self.devices:
            self.devices[motion_sensor].update_state({
                "motion": occupied,
                "occupancy": occupied
            })
        
        return True
    
    def set_security_mode(self, mode: str) -> bool:
        """Set security mode"""
        valid_modes = ["disarmed", "armed_home", "armed_away"]
        if mode not in valid_modes:
            return False
        
        self.security_mode = mode
        return True
    
    def get_training_data(self) -> List[Dict]:
        """Get AI training data"""
        return self.training_data.copy()
    
    def get_scenarios(self) -> List[Dict]:
        """Get AI training scenarios"""
        return self.scenarios.copy()
    
    def reset(self):
        """Reset world state"""
        self.time = 0.0
        self.security_mode = "disarmed"
        self.alarm_triggered = False
        
        # Reset rooms
        for room in self.rooms.values():
            room.occupancy = False
            room.temperature = 22.0
            room.humidity = 45.0
        
        # Reset devices
        for device in self.devices.values():
            if device.type == DeviceType.LIGHT:
                device.state = {"state": "OFF", "brightness": 0}
            elif device.type == DeviceType.CAMERA:
                device.state = {"motion_detected": False, "person_detected": False}
            elif device.type == DeviceType.SENSOR:
                if "motion" in device.state:
                    device.state = {"motion": False, "occupancy": False}
                elif "state" in device.state:
                    device.state = {"state": "closed"}
            elif device.type == DeviceType.THERMOSTAT:
                device.state = {"current_temperature": 22.0, "target_temperature": 22.0}
        
        # Clear training data
        self.training_data.clear()
        
        logger.info("World state reset")
