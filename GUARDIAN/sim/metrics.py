#!/usr/bin/env python3
"""
Metrics for Anti-Drone Simulation
ΔΣ Guardian Performance Monitoring
"""

import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

@dataclass
class SimulationMetrics:
    """Simulation performance metrics"""
    
    # Timing metrics
    total_frames: int = 0
    total_detections: int = 0
    total_tracks: int = 0
    total_false_positives: int = 0
    total_missed_detections: int = 0
    
    # Performance metrics
    avg_processing_time: float = 0.0
    fps: float = 0.0
    detection_rate: float = 0.0
    tracking_accuracy: float = 0.0
    
    # Scenario metrics
    scenarios_run: int = 0
    successful_scenarios: int = 0
    failed_scenarios: int = 0
    success_rate: float = 0.0
    
    # Agent metrics
    uav_detections: int = 0
    bird_detections: int = 0
    ally_detections: int = 0
    trash_detections: int = 0
    
    # Weather impact
    weather_conditions: Dict = field(default_factory=dict)
    
    # Timestamps
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    
    def update_detection_metrics(self, detections: List[Dict], processing_time: float):
        """Update detection-related metrics"""
        self.total_frames += 1
        self.total_detections += len(detections)
        
        # Update processing time
        if self.total_frames == 1:
            self.avg_processing_time = processing_time
        else:
            self.avg_processing_time = (self.avg_processing_time * (self.total_frames - 1) + processing_time) / self.total_frames
        
        # Calculate FPS
        self.fps = 1.0 / self.avg_processing_time if self.avg_processing_time > 0 else 0.0
        
        # Update detection rate
        self.detection_rate = self.total_detections / self.total_frames if self.total_frames > 0 else 0.0
        
        # Count by class
        for det in detections:
            class_name = det.get('class_name', 'unknown')
            if class_name == 'uav':
                self.uav_detections += 1
            elif class_name == 'bird':
                self.bird_detections += 1
            elif class_name == 'ally':
                self.ally_detections += 1
            elif class_name == 'trash':
                self.trash_detections += 1
        
        self.last_update = datetime.now()
    
    def update_tracking_metrics(self, tracks: List):
        """Update tracking-related metrics"""
        self.total_tracks += len(tracks)
        
        # Calculate tracking accuracy (simplified)
        if self.total_detections > 0:
            self.tracking_accuracy = self.total_tracks / self.total_detections
    
    def update_scenario_metrics(self, success: bool):
        """Update scenario-related metrics"""
        self.scenarios_run += 1
        if success:
            self.successful_scenarios += 1
        else:
            self.failed_scenarios += 1
        
        self.success_rate = self.successful_scenarios / self.scenarios_run if self.scenarios_run > 0 else 0.0
    
    def update_weather_metrics(self, weather: Dict):
        """Update weather-related metrics"""
        self.weather_conditions = weather.copy()
    
    def get_summary(self) -> Dict:
        """Get metrics summary"""
        runtime = datetime.now() - self.start_time
        
        return {
            'runtime_seconds': runtime.total_seconds(),
            'total_frames': self.total_frames,
            'total_detections': self.total_detections,
            'total_tracks': self.total_tracks,
            'avg_processing_time': self.avg_processing_time,
            'fps': self.fps,
            'detection_rate': self.detection_rate,
            'tracking_accuracy': self.tracking_accuracy,
            'scenarios_run': self.scenarios_run,
            'successful_scenarios': self.successful_scenarios,
            'success_rate': self.success_rate,
            'detection_breakdown': {
                'uav': self.uav_detections,
                'bird': self.bird_detections,
                'ally': self.ally_detections,
                'trash': self.trash_detections
            },
            'weather_conditions': self.weather_conditions,
            'last_update': self.last_update.isoformat()
        }
    
    def reset(self):
        """Reset all metrics"""
        self.__init__()

class MetricsCollector:
    """Collect and manage simulation metrics"""
    
    def __init__(self):
        self.metrics = SimulationMetrics()
        self.historical_data: List[Dict] = []
        self.alert_thresholds = {
            'fps_min': 15.0,
            'detection_rate_min': 0.8,
            'success_rate_min': 0.9,
            'processing_time_max': 0.1
        }
    
    def record_frame(self, detections: List[Dict], tracks: List, processing_time: float, weather: Optional[Dict] = None):
        """Record frame processing metrics"""
        self.metrics.update_detection_metrics(detections, processing_time)
        self.metrics.update_tracking_metrics(tracks)
        
        if weather:
            self.metrics.update_weather_metrics(weather)
        
        # Store historical data (keep last 1000 entries)
        if len(self.historical_data) >= 1000:
            self.historical_data.pop(0)
        
        self.historical_data.append({
            'timestamp': datetime.now().isoformat(),
            'frame_id': self.metrics.total_frames,
            'detections': len(detections),
            'tracks': len(tracks),
            'processing_time': processing_time,
            'fps': self.metrics.fps
        })
    
    def record_scenario(self, success: bool):
        """Record scenario completion"""
        self.metrics.update_scenario_metrics(success)
    
    def get_current_metrics(self) -> Dict:
        """Get current metrics"""
        return self.metrics.get_summary()
    
    def get_historical_metrics(self, minutes: int = 10) -> List[Dict]:
        """Get historical metrics for the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [entry for entry in self.historical_data 
                if datetime.fromisoformat(entry['timestamp']) > cutoff_time]
    
    def check_alerts(self) -> List[str]:
        """Check for performance alerts"""
        alerts = []
        summary = self.metrics.get_summary()
        
        if summary['fps'] < self.alert_thresholds['fps_min']:
            alerts.append(f"Low FPS: {summary['fps']:.1f} (min: {self.alert_thresholds['fps_min']})")
        
        if summary['detection_rate'] < self.alert_thresholds['detection_rate_min']:
            alerts.append(f"Low detection rate: {summary['detection_rate']:.2f} (min: {self.alert_thresholds['detection_rate_min']})")
        
        if summary['success_rate'] < self.alert_thresholds['success_rate_min']:
            alerts.append(f"Low success rate: {summary['success_rate']:.2f} (min: {self.alert_thresholds['success_rate_min']})")
        
        if summary['avg_processing_time'] > self.alert_thresholds['processing_time_max']:
            alerts.append(f"High processing time: {summary['avg_processing_time']:.3f}s (max: {self.alert_thresholds['processing_time_max']}s)")
        
        return alerts
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file"""
        try:
            data = {
                'current_metrics': self.get_current_metrics(),
                'historical_data': self.historical_data,
                'alert_thresholds': self.alert_thresholds,
                'export_timestamp': datetime.now().isoformat()
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Metrics exported to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
    
    def reset(self):
        """Reset all metrics"""
        self.metrics.reset()
        self.historical_data.clear()
        logger.info("Metrics collector reset")

# Global metrics collector
_metrics_collector = MetricsCollector()

def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    return _metrics_collector

def record_frame_metrics(detections: List[Dict], tracks: List, processing_time: float, weather: Optional[Dict] = None):
    """Record frame metrics using global collector"""
    _metrics_collector.record_frame(detections, tracks, processing_time, weather)

def record_scenario_metrics(success: bool):
    """Record scenario metrics using global collector"""
    _metrics_collector.record_scenario(success)

def get_current_metrics() -> Dict:
    """Get current metrics from global collector"""
    return _metrics_collector.get_current_metrics()

def check_alerts() -> List[str]:
    """Check for alerts using global collector"""
    return _metrics_collector.check_alerts()




