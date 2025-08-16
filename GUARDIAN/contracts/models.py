from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any

CONTRACT_VERSION: str = "2025-08-14"


class VisionDetectionEvent(BaseModel):
    ts: str = Field(..., description="ISO8601 timestamp")
    source: Literal["guardian-vision"] = "guardian-vision"
    camera_id: str
    type: str
    confidence: Optional[float] = None
    bbox: Optional[List[int]] = None
    artifacts: Optional[List[str]] = None


class SecurityIntent(BaseModel):
    ts: str
    actor: str = "guardian-core"
    intent: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class DeviceCommand(BaseModel):
    request_id: str
    ts: str
    device: Dict[str, str]
    action: Dict[str, Any]


class DeviceState(BaseModel):
    ts: str
    device_id: str
    state: Dict[str, Any]


class WhyCard(BaseModel):
    task_id: str
    goal: str
    context: Dict[str, Any] = Field(default_factory=dict)
    steps: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    safeties: List[str] = Field(default_factory=list)
    policy_summary: Optional[str] = None
    kpis: Dict[str, Any] = Field(default_factory=dict)
    outcome: Literal["approved", "denied", "pending", "executed"] = "pending"
    next_hint: Optional[str] = None


class DecideRequest(BaseModel):
    event: Dict[str, Any]


class DecideResponse(BaseModel):
    action: Optional[str] = None
    intents: List[Dict[str, Any]] = Field(default_factory=list)
    whycard: WhyCard

