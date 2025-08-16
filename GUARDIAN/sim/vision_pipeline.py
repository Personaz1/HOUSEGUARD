#!/usr/bin/env python3
"""
Vision Pipeline for Anti-Drone Detection
ΔΣ Guardian Vision Processing
"""

import asyncio
import json
import logging
from typing import List, Dict, Optional
import numpy as np
from datetime import datetime

# Import our models
from models.detect.rt_detr_uav import create_uav_detector
from models.track.bytetrack_uav import create_uav_tracker

logger = logging.getLogger(__name__)

class VisionPipeline:
    """Complete vision pipeline for UAV detection and tracking"""
    
    def __init__(self, 
                 detector_model_path: Optional[str] = None,
                 device: str = "cpu",
                 publish_mqtt: bool = True):
        
        # Initialize detector
        self.detector = create_uav_detector(detector_model_path, device)
        
        # Initialize tracker
        self.tracker = create_uav_tracker()
        
        # Pipeline state
        self.frame_count = 0
        self.detection_count = 0
        self.track_count = 0
        self.publish_mqtt = publish_mqtt
        
        # Performance metrics
        self.processing_times = []
        self.detection_rates = []
        
        logger.info("Vision pipeline initialized")
    
    async def process_frame(self, 
                          frame: np.ndarray, 
                          camera_id: str,
                          timestamp: Optional[float] = None) -> Dict:
        """Process single frame through detection and tracking"""
        
        start_time = datetime.now()
        self.frame_count += 1
        
        try:
            # Step 1: Detection
            detections = self.detector.detect(frame)
            self.detection_count += len(detections)
            
            # Step 2: Tracking
            tracks = self.tracker.update(detections)
            self.track_count += len(tracks)
            
            # Step 3: Post-process results
            results = self._post_process_results(detections, tracks, camera_id, timestamp)
            
            # Step 4: Publish to MQTT if enabled
            if self.publish_mqtt:
                await self._publish_results(results, camera_id)
            
            # Update metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            self.processing_times.append(processing_time)
            
            # Keep only last 100 measurements
            if len(self.processing_times) > 100:
                self.processing_times.pop(0)
            
            logger.debug(f"Frame {self.frame_count}: {len(detections)} detections, {len(tracks)} tracks, {processing_time:.3f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return {
                'detections': [],
                'tracks': [],
                'camera_id': camera_id,
                'timestamp': timestamp or datetime.now().timestamp(),
                'frame_id': self.frame_count,
                'error': str(e)
            }
    
    def _post_process_results(self, 
                            detections: List[Dict], 
                            tracks: List, 
                            camera_id: str,
                            timestamp: Optional[float]) -> Dict:
        """Post-process detection and tracking results"""
        
        # Convert detections to serializable format
        det_results = []
        for det in detections:
            det_results.append({
                'bbox': det['bbox'],
                'confidence': det['confidence'],
                'class_id': det['class_id'],
                'class_name': det['class_name'],
                'area': det['area']
            })
        
        # Convert tracks to serializable format
        track_results = []
        for track in tracks:
            track_results.append({
                'track_id': track.track_id,
                'bbox': track.bbox,
                'confidence': track.confidence,
                'class_id': track.class_id,
                'class_name': track.class_name,
                'state': track.state.name,
                'hits': track.hits,
                'age': track.age,
                'velocity': track.velocity,
                'time_since_update': track.time_since_update
            })
        
        return {
            'detections': det_results,
            'tracks': track_results,
            'camera_id': camera_id,
            'timestamp': timestamp or datetime.now().timestamp(),
            'frame_id': self.frame_count,
            'processing_time': self.processing_times[-1] if self.processing_times else 0.0
        }
    
    async def _publish_results(self, results: Dict, camera_id: str):
        """Publish results to MQTT topics"""
        try:
            # Import MQTT client here to avoid circular imports
            import aiomqtt
            
            # Publish detections
            if results['detections']:
                detection_topic = f"vision/detect/{camera_id}"
                detection_payload = {
                    'camera_id': camera_id,
                    'detections': results['detections'],
                    'timestamp': results['timestamp'],
                    'frame_id': results['frame_id']
                }
                
                # Note: This would need proper MQTT client setup
                # await self.mqtt_client.publish(detection_topic, json.dumps(detection_payload))
                logger.debug(f"Published {len(results['detections'])} detections to {detection_topic}")
            
            # Publish tracks
            if results['tracks']:
                track_topic = f"vision/track/{camera_id}"
                track_payload = {
                    'camera_id': camera_id,
                    'tracks': results['tracks'],
                    'timestamp': results['timestamp'],
                    'frame_id': results['frame_id']
                }
                
                # await self.mqtt_client.publish(track_topic, json.dumps(track_payload))
                logger.debug(f"Published {len(results['tracks'])} tracks to {track_topic}")
                
        except Exception as e:
            logger.error(f"Error publishing results: {e}")
    
    def get_pipeline_stats(self) -> Dict:
        """Get pipeline statistics"""
        avg_processing_time = np.mean(self.processing_times) if self.processing_times else 0.0
        fps = 1.0 / avg_processing_time if avg_processing_time > 0 else 0.0
        
        return {
            'frame_count': self.frame_count,
            'detection_count': self.detection_count,
            'track_count': self.track_count,
            'avg_processing_time': avg_processing_time,
            'fps': fps,
            'detector_info': self.detector.get_model_info(),
            'tracker_info': self.tracker.get_track_info()
        }
    
    def update_detector_threshold(self, threshold: float):
        """Update detector confidence threshold"""
        self.detector.update_confidence_threshold(threshold)
        logger.info(f"Detector threshold updated to {threshold}")
    
    def reset_pipeline(self):
        """Reset pipeline state"""
        self.tracker.reset()
        self.frame_count = 0
        self.detection_count = 0
        self.track_count = 0
        self.processing_times.clear()
        logger.info("Vision pipeline reset")

# Factory function
def create_vision_pipeline(**kwargs) -> VisionPipeline:
    """Create vision pipeline instance"""
    return VisionPipeline(**kwargs)



