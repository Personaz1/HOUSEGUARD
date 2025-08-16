#!/usr/bin/env python3
"""
RT-DETR UAV Detector
ΔΣ Guardian Anti-Drone Detection
"""

import torch
import torch.nn as nn
from typing import List, Dict, Tuple, Optional
import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)

class RTDETRUAVDetector:
    """RT-DETR based UAV detector"""
    
    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        self.device = device
        self.model = None
        self.confidence_threshold = 0.5
        self.nms_threshold = 0.4
        
        # UAV class mapping
        self.class_names = ["uav", "bird", "ally", "trash"]
        self.uav_class_id = 0
        
        if model_path:
            self.load_model(model_path)
        else:
            self._create_mock_model()
    
    def _create_mock_model(self):
        """Create mock model for testing"""
        logger.info("Creating mock RT-DETR model for UAV detection")
        
        # Mock model that returns synthetic detections
        class MockRTDETR(nn.Module):
            def __init__(self):
                super().__init__()
                self.num_classes = 4
                
            def forward(self, x):
                batch_size = x.shape[0]
                # Return mock detections
                boxes = torch.tensor([[0.1, 0.1, 0.3, 0.3]], device=x.device)
                scores = torch.tensor([0.8], device=x.device)
                labels = torch.tensor([0], device=x.device)  # UAV class
                
                return {
                    'boxes': boxes.repeat(batch_size, 1, 1),
                    'scores': scores.repeat(batch_size, 1),
                    'labels': labels.repeat(batch_size, 1)
                }
        
        self.model = MockRTDETR().to(self.device)
        logger.info("Mock RT-DETR model created")
    
    def load_model(self, model_path: str):
        """Load pre-trained RT-DETR model"""
        try:
            # Load model from path
            self.model = torch.load(model_path, map_location=self.device)
            self.model.eval()
            logger.info(f"RT-DETR model loaded from {model_path}")
        except Exception as e:
            logger.error(f"Failed to load model from {model_path}: {e}")
            self._create_mock_model()
    
    def preprocess_image(self, image: np.ndarray) -> torch.Tensor:
        """Preprocess image for RT-DETR"""
        # Resize to 640x640
        image_resized = cv2.resize(image, (640, 640))
        
        # Normalize to [0, 1]
        image_normalized = image_resized.astype(np.float32) / 255.0
        
        # Convert to tensor and add batch dimension
        image_tensor = torch.from_numpy(image_normalized).permute(2, 0, 1).unsqueeze(0)
        
        return image_tensor.to(self.device)
    
    def postprocess_detections(self, outputs: Dict, image_shape: Tuple[int, int]) -> List[Dict]:
        """Postprocess model outputs to detection format"""
        detections = []
        
        if 'boxes' in outputs and 'scores' in outputs and 'labels' in outputs:
            boxes = outputs['boxes'][0]  # Remove batch dimension
            scores = outputs['scores'][0]
            labels = outputs['labels'][0]
            
            # Filter by confidence
            mask = scores > self.confidence_threshold
            boxes = boxes[mask]
            scores = scores[mask]
            labels = labels[mask]
            
            # Convert to image coordinates
            h, w = image_shape
            for box, score, label in zip(boxes, scores, labels):
                x1, y1, x2, y2 = box.cpu().numpy()
                
                # Scale to original image size
                x1 *= w
                y1 *= h
                x2 *= w
                y2 *= h
                
                detection = {
                    'bbox': [x1, y1, x2, y2],
                    'confidence': float(score),
                    'class_id': int(label),
                    'class_name': self.class_names[int(label)],
                    'area': (x2 - x1) * (y2 - y1)
                }
                detections.append(detection)
        
        return detections
    
    def detect(self, image: np.ndarray) -> List[Dict]:
        """Detect UAVs in image"""
        try:
            # Preprocess
            input_tensor = self.preprocess_image(image)
            
            # Inference
            with torch.no_grad():
                outputs = self.model(input_tensor)
            
            # Postprocess
            detections = self.postprocess_detections(outputs, image.shape[:2])
            
            # Filter UAV detections
            uav_detections = [d for d in detections if d['class_name'] == 'uav']
            
            logger.debug(f"Detected {len(uav_detections)} UAVs")
            return uav_detections
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []
    
    def detect_batch(self, images: List[np.ndarray]) -> List[List[Dict]]:
        """Detect UAVs in batch of images"""
        results = []
        for image in images:
            detections = self.detect(image)
            results.append(detections)
        return results
    
    def update_confidence_threshold(self, threshold: float):
        """Update confidence threshold"""
        self.confidence_threshold = threshold
        logger.info(f"Confidence threshold updated to {threshold}")
    
    def get_model_info(self) -> Dict:
        """Get model information"""
        return {
            'model_type': 'RT-DETR',
            'num_classes': len(self.class_names),
            'class_names': self.class_names,
            'confidence_threshold': self.confidence_threshold,
            'device': self.device,
            'input_size': (640, 640)
        }

# Factory function
def create_uav_detector(model_path: Optional[str] = None, device: str = "cpu") -> RTDETRUAVDetector:
    """Create UAV detector instance"""
    return RTDETRUAVDetector(model_path, device)




