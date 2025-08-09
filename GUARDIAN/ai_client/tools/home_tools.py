"""
HomeTools — HTTP-обертки для управления SmartHouse Core из Guardian.

Все методы соответствуют эндпойнтам `SMARTHOUSE/core/app/main.py` (/tools/*, /state, /devices ...)
и возвращают краткий человекочитаемый результат для отображения в чате.
"""

from __future__ import annotations

import json
import uuid
import requests
from typing import Any, Dict, Optional


class HomeTools:
    def __init__(self, base_url: str, role: str = "admin", timeout_s: float = 5.0) -> None:
        self._base = base_url.rstrip("/")
        self._role = role
        self._timeout = timeout_s

    # ===== Helpers =====
    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"Content-Type": "application/json", "X-Role": self._role}
        if extra:
            h.update(extra)
        return h

    def _post(self, path: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        url = f"{self._base}{path}"
        r = requests.post(url, data=json.dumps(payload), headers=self._headers(headers), timeout=self._timeout)
        try:
            r.raise_for_status()
        except Exception as e:
            # Возвращаем полезное тело ошибки, чтобы чат и System Analysis видели детали
            detail = {}
            try:
                detail = r.json()
            except Exception:
                detail = {"raw": r.text}
            raise RuntimeError(f"HTTP {r.status_code} POST {url}: {detail}") from e
        return r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        url = f"{self._base}{path}"
        r = requests.get(url, params=params or {}, headers=self._headers(headers), timeout=self._timeout)
        r.raise_for_status()
        return r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}

    # ===== Core Tools (mirror SmartHouse /tools/*) =====
    def control_light(self, device_id: str, state: bool, brightness: Optional[int] = None) -> str:
        res = self._post("/tools/control_light", {"device_id": device_id, "state": bool(state), "brightness": brightness})
        return f"Light {device_id} → {'ON' if state else 'OFF'}" + (f", {brightness}%" if brightness is not None else "")

    def set_thermostat(self, device_id: str, temperature: float) -> str:
        res = self._post("/tools/set_thermostat", {"device_id": device_id, "temperature": float(temperature)})
        return f"Thermostat {device_id} → {temperature:.1f}°C"

    def lock_door(self, device_id: str) -> str:
        res = self._post("/tools/lock_door", {"device_id": device_id})
        return f"Door {device_id} → LOCKED"

    def unlock_door(self, device_id: str) -> str:
        res = self._post("/tools/unlock_door", {"device_id": device_id})
        return f"Door {device_id} → UNLOCKED"

    def cover_set_position(self, device_id: str, position: int) -> str:
        res = self._post("/tools/cover_set_position", {"device_id": device_id, "position": int(position)})
        return f"Cover {device_id} → {int(position)}%"

    def switch_on(self, device_id: str) -> str:
        res = self._post("/tools/switch_on", {"device_id": device_id})
        return f"Switch {device_id} → ON"

    def switch_off(self, device_id: str) -> str:
        res = self._post("/tools/switch_off", {"device_id": device_id})
        return f"Switch {device_id} → OFF"

    def siren_on(self, device_id: str) -> str:
        res = self._post("/tools/siren_on", {"device_id": device_id})
        return f"Siren {device_id} → ON"

    def siren_off(self, device_id: str) -> str:
        res = self._post("/tools/siren_off", {"device_id": device_id})
        return f"Siren {device_id} → OFF"

    def arm_security(self, mode: str = "away") -> str:
        res = self._post("/tools/arm_security", {"mode": mode or "away"})
        return f"Security → {mode or 'away'}"

    def disarm_security(self) -> str:
        res = self._post("/tools/disarm_security", {})
        return "Security → disarmed"

    def camera_snapshot(self, camera_id: str) -> str:
        res = self._post("/tools/camera_snapshot", {"camera_id": camera_id})
        info = res.get("result") or {}
        key = (info or {}).get("key") or (info or {}).get("last") or ""
        return f"Snapshot {camera_id} saved: {key}".strip()

    def camera_analyze(self, camera_id: str, prompt: str = "Опиши сцену кратко по фактам.") -> str:
        # X-Prompt заголовок принимает SmartHouse; добавим его к headers
        url = f"{self._base}/tools/camera_analyze"
        headers = self._headers({"X-Prompt": prompt})
        r = requests.post(url, data=json.dumps({"camera_id": camera_id}), headers=headers, timeout=self._timeout)
        r.raise_for_status()
        data = r.json()
        return f"Camera {camera_id} analysis: ok" if data else "Camera analyze done"

    # ===== State & Discovery =====
    def get_device_status(self, device_id: str) -> str:
        data = self._get("/tools/get_device_status", params={"device_id": device_id})
        return f"Status {device_id}: {json.dumps(data.get('result', {}), ensure_ascii=False)[:400]}"

    def get_sensor_data(self, sensor_id: str) -> str:
        data = self._get("/tools/get_sensor_data", params={"sensor_id": sensor_id})
        return f"Sensor {sensor_id}: {json.dumps(data.get('result', {}), ensure_ascii=False)[:400]}"

    def get_state(self) -> Dict[str, Any]:
        return self._get("/state")

    def list_devices(self) -> Dict[str, Any]:
        return self._get("/devices")


