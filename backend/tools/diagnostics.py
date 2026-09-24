"""Windows-first diagnostics that report observed state or an explicit unknown."""

from __future__ import annotations

import platform
import socket
import subprocess
from typing import Any


def _unknown(reason: str, **details: Any) -> dict[str, Any]:
    return {"status": "unknown", "reason": reason, **details}


def _windows_required() -> dict[str, Any] | None:
    if platform.system() != "Windows":
        return _unknown("Windows-only diagnostic unavailable on this platform")
    return None


def check_microphone(device: str = "default") -> dict[str, Any]:
    unsupported = _windows_required()
    if unsupported:
        return unsupported

    try:
        from pycaw.pycaw import AudioUtilities
        from pycaw.constants import DEVICE_STATE, EDataFlow

        devices = AudioUtilities.GetAllDevices(
            data_flow=EDataFlow.eCapture.value,
            device_state=DEVICE_STATE.ACTIVE.value,
        )
        capture_devices = []
        for audio_device in devices:
            name = getattr(audio_device, "FriendlyName", None) or str(audio_device)
            capture_devices.append(name)

        if not capture_devices:
            return {
                "status": "not_detected",
                "detected": False,
                "connected": False,
                "device": device,
                "permission": "unknown",
                "reason": "No active audio capture endpoint was found",
            }

        return {
            "status": "detected",
            "detected": True,
            "connected": True,
            "device": capture_devices[0] if device == "default" else device,
            "permission": "unknown",
            "reason": "Windows does not expose application microphone permission through this diagnostic",
        }
    except ImportError:
        return _unknown("Microphone diagnostic dependency unavailable")
    except Exception as error:
        return _unknown("Microphone state could not be read", error_code=type(error).__name__)


def check_camera(device: str = "default") -> dict[str, Any]:
    try:
        import cv2

        for index in range(5):
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            opened = capture.isOpened()
            readable = bool(opened and capture.read()[0])
            capture.release()
            if readable:
                return {
                    "status": "working",
                    "detected": True,
                    "connected": True,
                    "device": device,
                    "device_index": index,
                    "in_use": False,
                }
            if opened:
                return {
                    "status": "unavailable",
                    "detected": True,
                    "connected": True,
                    "device": device,
                    "device_index": index,
                    "in_use": True,
                }
        return {
            "status": "not_detected",
            "detected": False,
            "connected": False,
            "device": device,
            "in_use": False,
        }
    except ImportError:
        return _unknown("Camera diagnostic dependency unavailable", device=device)
    except Exception as error:
        return _unknown("Camera state could not be read", device=device, error_code=type(error).__name__)


def check_speaker(device: str = "default") -> dict[str, Any]:
    unsupported = _windows_required()
    if unsupported:
        return unsupported

    try:
        from comtypes import CLSCTX_ALL, cast
        from ctypes import POINTER
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        output = AudioUtilities.GetSpeakers()
        if output is None:
            return {"status": "not_detected", "detected": False, "device": device}
        endpoint = output.EndpointVolume if hasattr(output, "EndpointVolume") else cast(
            output.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None),
            POINTER(IAudioEndpointVolume),
        )
        muted = bool(endpoint.GetMute())
        volume = round(float(endpoint.GetMasterVolumeLevelScalar()) * 100, 1)
        return {
            "status": "muted" if muted else "working",
            "detected": True,
            "connected": True,
            "device": getattr(output, "FriendlyName", device),
            "volume_percent": volume,
            "muted": muted,
        }
    except ImportError:
        return _unknown("Speaker diagnostic dependency unavailable", device=device)
    except Exception as error:
        return _unknown("Speaker state could not be read", device=device, error_code=type(error).__name__)


def check_connectivity(host: str = "8.8.8.8", timeout_seconds: float = 2.0) -> dict[str, Any]:
    try:
        started = __import__("time").perf_counter()
        with socket.create_connection((host, 53), timeout=timeout_seconds):
            latency_ms = round((__import__("time").perf_counter() - started) * 1000, 1)
        return {
            "status": "working",
            "internet": True,
            "host": host,
            "latency_ms": latency_ms,
            "packet_loss_percent": 0,
        }
    except socket.timeout:
        return {
            "status": "timeout",
            "internet": False,
            "host": host,
            "packet_loss_percent": 100,
            "reason": "Connectivity check timed out",
        }
    except OSError as error:
        return {
            "status": "unavailable",
            "internet": False,
            "host": host,
            "packet_loss_percent": 100,
            "reason": "Connectivity check failed",
            "error_code": type(error).__name__,
        }


def check_app_state(application: str = "Teams") -> dict[str, Any]:
    if platform.system() != "Windows":
        return _unknown("Application process diagnostic requires Windows", application=application)

    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {application}.exe", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        running = f'"{application}.exe"' in result.stdout
        return {
            "status": "running" if running else "not_running",
            "application": application,
            "running": running,
            "signed_in": "unknown",
            "version": "unknown",
        }
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return _unknown("Windows process state could not be read", application=application)


def run_test(test_type: str) -> dict[str, Any]:
    if test_type == "microphone_test":
        microphone = check_microphone()
        return {
            "test_type": test_type,
            "result": "pass" if microphone.get("status") == "detected" else "unknown",
            "microphone": microphone,
        }
    if test_type == "speaker_test":
        speaker = check_speaker()
        return {
            "test_type": test_type,
            "result": "pass" if speaker.get("status") == "working" else "unknown",
            "speaker": speaker,
        }
    if test_type == "audio_test":
        microphone = check_microphone()
        speaker = check_speaker()
        passed = microphone.get("status") == "detected" and speaker.get("status") == "working"
        return {"test_type": test_type, "result": "pass" if passed else "unknown", "microphone": microphone, "speaker": speaker}
    if test_type == "camera_test":
        camera = check_camera()
        return {"test_type": test_type, "result": "pass" if camera.get("status") == "working" else "unknown", "camera": camera}
    if test_type == "connectivity_test":
        connectivity = check_connectivity()
        return {"test_type": test_type, "result": "pass" if connectivity.get("internet") else "unknown", "connectivity": connectivity}
    return {"test_type": test_type, "result": "unknown", "reason": "Unsupported test type"}