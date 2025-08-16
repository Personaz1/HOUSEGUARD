#!/usr/bin/env python3
"""
ByteTrack UAV Tracker
ΔΣ Guardian Anti-Drone Tracking
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)

class TrackState(Enum):
    """Track state enumeration"""
    NEW = 0
    TRACKED = 1
    LOST = 2
    REMOVED = 3

@dataclass
class Track:
    """Track object"""
    track_id: int
    bbox: List[float]  # [x1, y1, x2, y2]
    confidence: float
    class_id: int
    class_name: str
    state: TrackState
    time_since_update: int
    hits: int
    age: int
    velocity: Optional[List[float]] = None  # [vx, vy]
    last_update: float = 0.0

class ByteTrackUAVTracker:
    """ByteTrack based UAV tracker"""
    
    def __init__(self, 
                 track_thresh: float = 0.5,
                 high_thresh: float = 0.6,
                 match_thresh: float = 0.8,
                 track_buffer: int = 30,
                 frame_rate: int = 30):
        
        self.track_thresh = track_thresh
        self.high_thresh = high_thresh
        self.match_thresh = match_thresh
        self.track_buffer = track_buffer
        self.frame_rate = frame_rate
        
        self.tracked_tracks: List[Track] = []
        self.lost_tracks: List[Track] = []
        self.removed_tracks: List[Track] = []
        
        self.frame_id = 0
        self.next_id = 1
        
        logger.info("ByteTrack UAV tracker initialized")
    
    def update(self, detections: List[Dict]) -> List[Track]:
        """Update tracks with new detections"""
        self.frame_id += 1
        
        # Convert detections to numpy arrays
        det_bboxes = np.array([d['bbox'] for d in detections])
        det_scores = np.array([d['confidence'] for d in detections])
        det_classes = np.array([d['class_id'] for d in detections])
        
        # Separate high and low confidence detections
        high_mask = det_scores > self.high_thresh
        low_mask = (det_scores > self.track_thresh) & (det_scores <= self.high_thresh)
        
        high_dets = detections[:][high_mask]
        low_dets = detections[:][low_mask]
        
        # Update existing tracks
        self._update_tracks(high_dets)
        
        # Handle low confidence detections
        if len(low_dets) > 0:
            self._update_tracks_low_confidence(low_dets)
        
        # Update track states
        self._update_track_states()
        
        # Return active tracks
        active_tracks = [t for t in self.tracked_tracks if t.state == TrackState.TRACKED]
        
        logger.debug(f"Frame {self.frame_id}: {len(active_tracks)} active tracks")
        return active_tracks
    
    def _update_tracks(self, detections: List[Dict]):
        """Update tracks with high confidence detections"""
        if len(self.tracked_tracks) == 0:
            # Initialize new tracks
            for det in detections:
                track = self._create_track(det)
                self.tracked_tracks.append(track)
            return
        
        # Match detections to existing tracks
        matches, unmatched_dets, unmatched_tracks = self._match_detections_to_tracks(detections)
        
        # Update matched tracks
        for det_idx, track_idx in matches:
            track = self.tracked_tracks[track_idx]
            det = detections[det_idx]
            self._update_track(track, det)
        
        # Create new tracks for unmatched detections
        for det_idx in unmatched_dets:
            det = detections[det_idx]
            track = self._create_track(det)
            self.tracked_tracks.append(track)
        
        # Mark unmatched tracks as lost
        for track_idx in unmatched_tracks:
            track = self.tracked_tracks[track_idx]
            track.state = TrackState.LOST
            track.time_since_update += 1
    
    def _update_tracks_low_confidence(self, detections: List[Dict]):
        """Update tracks with low confidence detections"""
        if len(self.lost_tracks) == 0:
            return
        
        # Match low confidence detections to lost tracks
        matches, unmatched_dets, unmatched_tracks = self._match_detections_to_tracks(
            detections, self.lost_tracks
        )
        
        # Update matched lost tracks
        for det_idx, track_idx in matches:
            track = self.lost_tracks[track_idx]
            det = detections[det_idx]
            self._update_track(track, det)
            track.state = TrackState.TRACKED
            self.tracked_tracks.append(track)
            self.lost_tracks.pop(track_idx)
    
    def _match_detections_to_tracks(self, detections: List[Dict], tracks: Optional[List[Track]] = None) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """Match detections to tracks using IoU"""
        if tracks is None:
            tracks = self.tracked_tracks
        
        if len(detections) == 0 or len(tracks) == 0:
            return [], list(range(len(detections))), list(range(len(tracks)))
        
        # Calculate IoU matrix
        iou_matrix = np.zeros((len(detections), len(tracks)))
        for i, det in enumerate(detections):
            for j, track in enumerate(tracks):
                iou_matrix[i, j] = self._calculate_iou(det['bbox'], track.bbox)
        
        # Simple greedy matching
        matches = []
        unmatched_dets = list(range(len(detections)))
        unmatched_tracks = list(range(len(tracks)))
        
        # Find matches above threshold
        for i in range(len(detections)):
            for j in range(len(tracks)):
                if iou_matrix[i, j] > self.match_thresh:
                    if i in unmatched_dets and j in unmatched_tracks:
                        matches.append((i, j))
                        unmatched_dets.remove(i)
                        unmatched_tracks.remove(j)
        
        return matches, unmatched_dets, unmatched_tracks
    
    def _calculate_iou(self, bbox1: List[float], bbox2: List[float]) -> float:
        """Calculate IoU between two bounding boxes"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calculate union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _create_track(self, detection: Dict) -> Track:
        """Create new track from detection"""
        track = Track(
            track_id=self.next_id,
            bbox=detection['bbox'].copy(),
            confidence=detection['confidence'],
            class_id=detection['class_id'],
            class_name=detection['class_name'],
            state=TrackState.NEW,
            time_since_update=0,
            hits=1,
            age=1,
            velocity=[0.0, 0.0],
            last_update=time.time()
        )
        self.next_id += 1
        return track
    
    def _update_track(self, track: Track, detection: Dict):
        """Update track with new detection"""
        # Update bbox
        old_bbox = track.bbox.copy()
        track.bbox = detection['bbox'].copy()
        
        # Update velocity (simple linear velocity)
        if track.velocity is not None:
            dt = time.time() - track.last_update
            if dt > 0:
                vx = (track.bbox[0] - old_bbox[0]) / dt
                vy = (track.bbox[1] - old_bbox[1]) / dt
                track.velocity = [vx, vy]
        
        # Update other fields
        track.confidence = detection['confidence']
        track.state = TrackState.TRACKED
        track.time_since_update = 0
        track.hits += 1
        track.age += 1
        track.last_update = time.time()
    
    def _update_track_states(self):
        """Update track states and remove old tracks"""
        # Move lost tracks to removed if they're too old
        tracks_to_remove = []
        for i, track in enumerate(self.lost_tracks):
            if track.time_since_update > self.track_buffer:
                track.state = TrackState.REMOVED
                tracks_to_remove.append(i)
        
        # Remove old tracks
        for i in reversed(tracks_to_remove):
            removed_track = self.lost_tracks.pop(i)
            self.removed_tracks.append(removed_track)
    
    def get_track_info(self) -> Dict:
        """Get tracker information"""
        return {
            'tracker_type': 'ByteTrack',
            'frame_id': self.frame_id,
            'active_tracks': len([t for t in self.tracked_tracks if t.state == TrackState.TRACKED]),
            'lost_tracks': len(self.lost_tracks),
            'total_tracks': self.next_id - 1,
            'track_thresh': self.track_thresh,
            'high_thresh': self.high_thresh,
            'match_thresh': self.match_thresh
        }
    
    def reset(self):
        """Reset tracker state"""
        self.tracked_tracks.clear()
        self.lost_tracks.clear()
        self.removed_tracks.clear()
        self.frame_id = 0
        self.next_id = 1
        logger.info("ByteTrack tracker reset")

# Factory function
def create_uav_tracker(**kwargs) -> ByteTrackUAVTracker:
    """Create UAV tracker instance"""
    return ByteTrackUAVTracker(**kwargs)



