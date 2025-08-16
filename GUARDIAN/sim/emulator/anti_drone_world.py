"""
Anti-Drone Defense Simulation World
ΔΣ Guardian Training Environment
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from enum import Enum


class AgentType(Enum):
    UAV = "uav"           # Враждебный дрон
    BIRD = "bird"         # Ложная цель
    ALLY = "ally"         # Дружественный дрон
    TRASH = "trash"       # Воздушный мусор


class SensorType(Enum):
    RGB_CAMERA = "rgb_camera"
    IR_CAMERA = "ir_camera"
    RADAR = "radar"
    LIDAR = "lidar"
    MICROPHONE = "microphone"


@dataclass
class Vector3D:
    x: float
    y: float
    z: float
    
    def __add__(self, other: Vector3D) -> Vector3D:
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: Vector3D) -> Vector3D:
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def distance_to(self, other: Vector3D) -> float:
        return (self - other).magnitude()


@dataclass
class Agent:
    id: str
    agent_type: AgentType
    position: Vector3D
    velocity: Vector3D
    size: float = 1.0
    health: float = 100.0
    detected: bool = False
    tracked: bool = False
    track_id: Optional[int] = None
    
    def update_position(self, dt: float) -> None:
        self.position = self.position + Vector3D(
            self.velocity.x * dt,
            self.velocity.y * dt,
            self.velocity.z * dt
        )


@dataclass
class Turret:
    id: str
    position: Vector3D
    pan: float = 0.0  # -π to π
    tilt: float = 0.0  # -π/2 to π/2
    zoom: float = 1.0
    fov: float = math.pi / 4  # 45 degrees
    max_pan_speed: float = 2.0  # rad/s
    max_tilt_speed: float = 1.0  # rad/s
    target_id: Optional[str] = None
    search_mode: str = "idle"  # idle, sector_scan, track
    
    def can_see(self, target_pos: Vector3D) -> bool:
        """Check if target is within FOV"""
        direction = target_pos - self.position
        distance = direction.magnitude()
        
        # Calculate pan/tilt angles to target
        pan_to_target = math.atan2(direction.y, direction.x)
        tilt_to_target = math.asin(direction.z / distance)
        
        # Check if within FOV
        pan_diff = abs(pan_to_target - self.pan)
        pan_diff = min(pan_diff, 2*math.pi - pan_diff)
        
        return (pan_diff <= self.fov/2 and 
                abs(tilt_to_target - self.tilt) <= self.fov/2)


@dataclass
class Sensor:
    id: str
    sensor_type: SensorType
    position: Vector3D
    orientation: Vector3D  # Euler angles
    range: float
    fov: float
    noise_level: float = 0.1
    detection_probability: float = 0.95


@dataclass
class Weather:
    wind_speed: float = 0.0
    wind_direction: float = 0.0
    rain_intensity: float = 0.0
    fog_density: float = 0.0
    visibility: float = 1000.0  # meters
    temperature: float = 20.0


@dataclass
class GeoFence:
    """Geographic fence for safe zones"""
    polygons: List[List[Vector3D]] = field(default_factory=list)
    no_fire_zones: List[List[Vector3D]] = field(default_factory=list)
    safe_sectors: List[Tuple[float, float]] = field(default_factory=list)  # (min_angle, max_angle)


class AntiDroneWorld:
    def __init__(self, 
                 dt: float = 0.05,
                 seed: int = 1337,
                 world_bounds: Tuple[float, float, float] = (1000, 1000, 200)):
        self.dt = dt
        self.world_bounds = world_bounds
        self._rng = random.Random(seed)
        self.time = 0.0
        self.step_count = 0
        
        # World entities
        self.agents: Dict[str, Agent] = {}
        self.turrets: Dict[str, Turret] = {}
        self.sensors: Dict[str, Sensor] = {}
        self.weather = Weather()
        self.geo_fence = GeoFence()
        
        # Detection and tracking
        self.detections: List[Dict] = []
        self.tracks: List[Dict] = []
        self.next_track_id = 1
        
        # Performance metrics
        self.metrics = {
            "detections": 0,
            "false_positives": 0,
            "missed_detections": 0,
            "track_switches": 0,
            "response_time": 0.0
        }
        
        self._setup_default_scene()
    
    def _setup_default_scene(self):
        """Setup default house and perimeter"""
        # House position (center of world)
        house_center = Vector3D(0, 0, 0)
        
        # Turrets around perimeter
        turret_positions = [
            Vector3D(-50, -50, 10),   # Front left
            Vector3D(50, -50, 10),    # Front right
            Vector3D(-50, 50, 10),    # Back left
            Vector3D(50, 50, 10),     # Back right
        ]
        
        for i, pos in enumerate(turret_positions):
            turret_id = f"turret_{i+1}"
            self.turrets[turret_id] = Turret(
                id=turret_id,
                position=pos
            )
        
        # Sensors (cameras, radar, etc.)
        sensor_configs = [
            (SensorType.RGB_CAMERA, Vector3D(-30, -30, 15), 200, math.pi/3),
            (SensorType.IR_CAMERA, Vector3D(30, -30, 15), 150, math.pi/4),
            (SensorType.RADAR, Vector3D(0, -40, 20), 300, math.pi/2),
        ]
        
        for i, (sensor_type, pos, range_val, fov) in enumerate(sensor_configs):
            sensor_id = f"sensor_{sensor_type.value}_{i+1}"
            self.sensors[sensor_id] = Sensor(
                id=sensor_id,
                sensor_type=sensor_type,
                position=pos,
                orientation=Vector3D(0, 0, 0),
                range=range_val,
                fov=fov
            )
        
        # Geo fence (house perimeter)
        fence_points = [
            Vector3D(-100, -100, 0),
            Vector3D(100, -100, 0),
            Vector3D(100, 100, 0),
            Vector3D(-100, 100, 0),
        ]
        self.geo_fence.polygons.append(fence_points)
    
    def add_agent(self, agent: Agent) -> None:
        """Add agent to simulation"""
        self.agents[agent.id] = agent
    
    def spawn_uav(self, position: Vector3D, velocity: Vector3D, size: float = 1.0) -> str:
        """Spawn hostile UAV"""
        agent_id = f"uav_{len([a for a in self.agents.values() if a.agent_type == AgentType.UAV]) + 1}"
        uav = Agent(
            id=agent_id,
            agent_type=AgentType.UAV,
            position=position,
            velocity=velocity,
            size=size
        )
        self.add_agent(uav)
        return agent_id
    
    def spawn_bird(self, position: Vector3D, velocity: Vector3D) -> str:
        """Spawn bird (false target)"""
        agent_id = f"bird_{len([a for a in self.agents.values() if a.agent_type == AgentType.BIRD]) + 1}"
        bird = Agent(
            id=agent_id,
            agent_type=AgentType.BIRD,
            position=position,
            velocity=velocity,
            size=0.3
        )
        self.add_agent(bird)
        return agent_id
    
    def step(self, actions: Optional[Dict] = None) -> Dict:
        """Simulation step"""
        self.step_count += 1
        self.time += self.dt
        
        # Update weather
        self._update_weather()
        
        # Update agent positions
        self._update_agents()
        
        # Process sensor detections
        self._process_detections()
        
        # Update tracking
        self._update_tracking()
        
        # Process turret actions
        if actions:
            self._process_turret_actions(actions)
        
        # Remove out-of-bounds agents
        self._cleanup_agents()
        
        return self._observe()
    
    def _update_weather(self):
        """Update weather conditions"""
        # Simple weather model
        self.weather.wind_speed += self._rng.normalvariate(0, 0.1)
        self.weather.wind_speed = max(0, min(20, self.weather.wind_speed))
        
        # Affect agent movement with wind
        wind_vector = Vector3D(
            self.weather.wind_speed * math.cos(self.weather.wind_direction),
            self.weather.wind_speed * math.sin(self.weather.wind_direction),
            0
        )
        
        for agent in self.agents.values():
            # Apply wind effect (stronger on smaller objects)
            wind_factor = 0.1 / agent.size
            agent.velocity = agent.velocity + Vector3D(
                wind_vector.x * wind_factor * self.dt,
                wind_vector.y * wind_factor * self.dt,
                wind_vector.z * wind_factor * self.dt
            )
    
    def _update_agents(self):
        """Update agent positions and physics"""
        for agent in self.agents.values():
            # Apply physics
            agent.update_position(self.dt)
            
            # Add some realistic movement patterns
            if agent.agent_type == AgentType.UAV:
                # UAVs can hover and maneuver
                if self._rng.random() < 0.1:  # 10% chance to change direction
                    agent.velocity = Vector3D(
                        self._rng.uniform(-5, 5),
                        self._rng.uniform(-5, 5),
                        self._rng.uniform(-2, 2)
                    )
            
            elif agent.agent_type == AgentType.BIRD:
                # Birds have more erratic movement
                if self._rng.random() < 0.3:  # 30% chance to change direction
                    agent.velocity = Vector3D(
                        self._rng.uniform(-3, 3),
                        self._rng.uniform(-3, 3),
                        self._rng.uniform(-1, 1)
                    )
    
    def _process_detections(self):
        """Process sensor detections"""
        self.detections.clear()
        
        for sensor in self.sensors.values():
            for agent in self.agents.values():
                if self._can_detect(sensor, agent):
                    detection = self._create_detection(sensor, agent)
                    if detection:
                        self.detections.append(detection)
                        agent.detected = True
    
    def _can_detect(self, sensor: Sensor, agent: Agent) -> bool:
        """Check if sensor can detect agent"""
        distance = sensor.position.distance_to(agent.position)
        
        if distance > sensor.range:
            return False
        
        # Check if within FOV (simplified)
        direction = agent.position - sensor.position
        # Add weather effects
        if self.weather.fog_density > 0:
            visibility_reduction = 1.0 - self.weather.fog_density
            if distance > sensor.range * visibility_reduction:
                return False
        
        # Detection probability with noise
        base_prob = sensor.detection_probability
        noise_factor = 1.0 - (distance / sensor.range) * sensor.noise_level
        
        return self._rng.random() < base_prob * noise_factor
    
    def _create_detection(self, sensor: Sensor, agent: Agent) -> Optional[Dict]:
        """Create detection object"""
        if not self._can_detect(sensor, agent):
            return None
        
        # Add sensor noise
        noise = self._rng.normalvariate(0, sensor.noise_level)
        
        detection = {
            "sensor_id": sensor.id,
            "agent_id": agent.id,
            "agent_type": agent.agent_type.value,
            "position": {
                "x": agent.position.x + noise,
                "y": agent.position.y + noise,
                "z": agent.position.z + noise
            },
            "velocity": {
                "x": agent.velocity.x + noise,
                "y": agent.velocity.y + noise,
                "z": agent.velocity.z + noise
            },
            "confidence": max(0.1, 1.0 - (sensor.position.distance_to(agent.position) / sensor.range)),
            "timestamp": self.time
        }
        
        self.metrics["detections"] += 1
        return detection
    
    def _update_tracking(self):
        """Update tracking system"""
        # Simple tracking: assign track IDs to detected agents
        for detection in self.detections:
            agent_id = detection["agent_id"]
            agent = self.agents.get(agent_id)
            
            if agent and not agent.tracked:
                agent.tracked = True
                agent.track_id = self.next_track_id
                self.next_track_id += 1
        
        # Update tracks list
        self.tracks = [
            {
                "track_id": agent.track_id,
                "agent_id": agent.id,
                "agent_type": agent.agent_type.value,
                "position": {"x": agent.position.x, "y": agent.position.y, "z": agent.position.z},
                "velocity": {"x": agent.velocity.x, "y": agent.velocity.y, "z": agent.velocity.z},
                "confidence": 0.9 if agent.detected else 0.3,
                "age": self.time
            }
            for agent in self.agents.values()
            if agent.tracked
        ]
    
    def _process_turret_actions(self, actions: Dict):
        """Process turret control actions"""
        for turret_id, action in actions.get("turrets", {}).items():
            if turret_id not in self.turrets:
                continue
            
            turret = self.turrets[turret_id]
            
            # Update pan/tilt
            if "pan" in action:
                target_pan = action["pan"]
                pan_diff = target_pan - turret.pan
                max_pan_change = turret.max_pan_speed * self.dt
                pan_change = max(-max_pan_change, min(max_pan_change, pan_diff))
                turret.pan += pan_change
            
            if "tilt" in action:
                target_tilt = action["tilt"]
                tilt_diff = target_tilt - turret.tilt
                max_tilt_change = turret.max_tilt_speed * self.dt
                tilt_change = max(-max_tilt_change, min(max_tilt_change, tilt_diff))
                turret.tilt += tilt_change
            
            # Update search mode
            if "search_mode" in action:
                turret.search_mode = action["search_mode"]
            
            # Update target
            if "target_id" in action:
                turret.target_id = action["target_id"]
    
    def _cleanup_agents(self):
        """Remove agents that are out of bounds"""
        bounds_x, bounds_y, bounds_z = self.world_bounds
        
        agents_to_remove = []
        for agent_id, agent in self.agents.items():
            if (abs(agent.position.x) > bounds_x/2 or 
                abs(agent.position.y) > bounds_y/2 or 
                abs(agent.position.z) > bounds_z/2):
                agents_to_remove.append(agent_id)
        
        for agent_id in agents_to_remove:
            del self.agents[agent_id]
    
    def _observe(self) -> Dict:
        """Get current world observation"""
        return {
            "timestamp": self.time,
            "step": self.step_count,
            "agents": {
                agent_id: {
                    "type": agent.agent_type.value,
                    "position": {"x": agent.position.x, "y": agent.position.y, "z": agent.position.z},
                    "velocity": {"x": agent.velocity.x, "y": agent.velocity.y, "z": agent.velocity.z},
                    "size": agent.size,
                    "detected": agent.detected,
                    "tracked": agent.tracked,
                    "track_id": agent.track_id
                }
                for agent_id, agent in self.agents.items()
            },
            "turrets": {
                turret_id: {
                    "position": {"x": turret.position.x, "y": turret.position.y, "z": turret.position.z},
                    "pan": turret.pan,
                    "tilt": turret.tilt,
                    "zoom": turret.zoom,
                    "target_id": turret.target_id,
                    "search_mode": turret.search_mode
                }
                for turret_id, turret in self.turrets.items()
            },
            "detections": self.detections,
            "tracks": self.tracks,
            "weather": {
                "wind_speed": self.weather.wind_speed,
                "wind_direction": self.weather.wind_direction,
                "rain_intensity": self.weather.rain_intensity,
                "fog_density": self.weather.fog_density,
                "visibility": self.weather.visibility,
                "temperature": self.weather.temperature
            },
            "metrics": self.metrics.copy()
        }
    
    def reset(self, seed: Optional[int] = None) -> Dict:
        """Reset simulation"""
        if seed is not None:
            self._rng.seed(seed)
        
        self.time = 0.0
        self.step_count = 0
        self.agents.clear()
        self.detections.clear()
        self.tracks.clear()
        self.next_track_id = 1
        
        # Reset metrics
        for key in self.metrics:
            self.metrics[key] = 0
        
        # Reset turrets
        for turret in self.turrets.values():
            turret.pan = 0.0
            turret.tilt = 0.0
            turret.target_id = None
            turret.search_mode = "idle"
        
        return self._observe()



