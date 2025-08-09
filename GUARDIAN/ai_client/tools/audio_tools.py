"""
AudioTools — захват звука с микрофона, базовый анализ и распознавание речи

Особенности:
- Пытается писать через sounddevice (CoreAudio)
- Фолбэк через ffmpeg (avfoundation) на macOS, если sounddevice недоступен
- Распознавание речи через SpeechRecognition (Google Web Speech API)
"""

from __future__ import annotations

import os
import json
import shutil
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any

import numpy as np


class AudioTools:
    def __init__(self) -> None:
        os.makedirs("memory/audio", exist_ok=True)

    # ===== Internals =====
    def _default_wav_path(self) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.abspath(os.path.join("memory", "audio", f"capture_{ts}.wav"))

    def _analyze_wave(self, wav_path: str) -> Dict[str, Any]:
        try:
            import soundfile as sf  # type: ignore
        except Exception:
            # Fallback: use scipy if available
            try:
                from scipy.io import wavfile  # type: ignore
                sr, data = wavfile.read(wav_path)
                if data.dtype.kind == 'i':
                    peak = float(np.max(np.abs(data))) / float(np.iinfo(data.dtype).max)
                    rms = float(np.sqrt(np.mean((data.astype(np.float32) / np.iinfo(data.dtype).max) ** 2)))
                else:
                    peak = float(np.max(np.abs(data)))
                    rms = float(np.sqrt(np.mean((data.astype(np.float32)) ** 2)))
            except Exception:
                # Minimal stats via ffmpeg
                return {"error": "analyze failed"}
        else:
            data, sr = sf.read(wav_path, always_2d=False)
            if isinstance(data, np.ndarray) and data.ndim > 1:
                data = np.mean(data, axis=1)
            peak = float(np.max(np.abs(data)))
            rms = float(np.sqrt(np.mean(np.square(data))))

        def to_db(x: float) -> float:
            try:
                return 20.0 * float(np.log10(max(x, 1e-9)))
            except Exception:
                return -120.0

        return {
            "sample_rate": int(sr),
            "rms": rms,
            "rms_db": to_db(rms),
            "peak": peak,
            "peak_db": to_db(peak),
            "duration_s": self._probe_duration(wav_path),
        }

    def _probe_duration(self, wav_path: str) -> float:
        try:
            import soundfile as sf  # type: ignore
            data, sr = sf.read(wav_path, always_2d=False)
            n = len(data) if isinstance(data, np.ndarray) else 0
            return float(n) / float(sr) if sr else 0.0
        except Exception:
            return 0.0

    def _record_sounddevice(self, seconds: int, samplerate: int, channels: int, wav_path: str, device: Optional[str]) -> bool:
        try:
            import sounddevice as sd  # type: ignore
            import soundfile as sf  # type: ignore
            duration = max(1, int(seconds))
            samplerate = int(samplerate)
            channels = int(channels)
            device_kw = {"device": device} if device else {}
            stream = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='float32', **device_kw)
            sd.wait()
            sf.write(wav_path, stream, samplerate)
            return True
        except Exception:
            return False

    def _record_ffmpeg(self, seconds: int, samplerate: int, channels: int, wav_path: str, av_index: str = ":0") -> bool:
        if not shutil.which("ffmpeg"):
            return False
        duration = max(1, int(seconds))
        cmd = [
            "ffmpeg", "-y",
            "-f", "avfoundation", "-i", f"{av_index}",
            "-t", str(duration),
            "-ac", str(channels), "-ar", str(samplerate),
            wav_path,
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return True
        except Exception:
            return False

    # ===== Public API =====
    def record(self, seconds: int = 5, samplerate: int = 16000, channels: int = 1, device: Optional[str] = None) -> str:
        """Записать с микрофона и вернуть путь к .wav"""
        wav = self._default_wav_path()
        ok = self._record_sounddevice(seconds, samplerate, channels, wav, device)
        if not ok:
            av_index = os.getenv("AVFOUNDATION_INDEX", ":0")
            ok = self._record_ffmpeg(seconds, samplerate, channels, wav, av_index)
        if not ok:
            raise RuntimeError("Audio capture failed: need sounddevice or ffmpeg")
        return wav

    def transcribe(self, wav_path: str, language: str = "ru-RU") -> str:
        """Распознать речь из wav. Использует SpeechRecognition (Google Web Speech API)."""
        try:
            import speech_recognition as sr  # type: ignore
            r = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio = r.record(source)
            try:
                text = r.recognize_google(audio, language=language)
            except Exception as e:
                text = f"<stt unavailable: {e}>"
            return text
        except Exception as e:
            return f"<stt init failed: {e}>"

    def listen(self, seconds: int = 5, language: str = "ru-RU") -> str:
        """Быстрый триггер: записать звук, посчитать метрики и распознать речь. Возвращает JSON-строку."""
        wav = self.record(seconds=seconds)
        metrics = self._analyze_wave(wav)
        text = self.transcribe(wav, language=language)
        result = {
            "audio_path": wav,
            "metrics": metrics,
            "transcript": text,
            "timestamp": datetime.now().isoformat(),
        }
        return json.dumps(result, ensure_ascii=False)


