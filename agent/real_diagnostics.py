"""Windows system diagnostics for the meeting support agent."""

from __future__ import annotations

import json
import platform
import re
import subprocess
from typing import Any


_mic_permission = False


def _result(status: str, error_code: str, message: str, **details: Any) -> str:
    return json.dumps({
        "status": status,
        "error_code": error_code,
        "message": message,
        **details,
    })


def _windows_only() -> str | None:
    if platform.system() != "Windows":
        return _result(
            "error",
            "unsupported_platform",
            "These diagnostics require Windows.",
        )
    return None


def _endpoint_volume(device: Any) -> Any:
    if hasattr(device, "EndpointVolume"):
        return device.EndpointVolume

    from comtypes import CLSCTX_ALL, cast
    from ctypes import POINTER
    from pycaw.pycaw import IAudioEndpointVolume

    interface = device.Activate(
        IAudioEndpointVolume._iid_,
        CLSCTX_ALL,
        None,
    )
    return cast(interface, POINTER(IAudioEndpointVolume))


def _device_state(device: Any) -> int:
    state = getattr(device, "state", None)
    if state is not None:
        return int(state)
    return int(device.GetState())


def check_mic() -> dict[str, Any]:
    """Return the deterministic microphone state used by the approval demo."""
    return {
        "detected": True,
        "selected_device": "Bluetooth Headset",
        "permission": _mic_permission,
        "muted": False,
    }


def approved_action(action_id: str) -> dict[str, bool]:
    """Apply the mocked microphone permission action."""
    global _mic_permission
    if action_id == "fix_mic_permission":
        _mic_permission = True
        return {"success": True}
    return {"success": False}


def check_camera() -> str:
    """Detect a webcam and test whether its first frame can be opened."""
    unsupported = _windows_only()
    if unsupported:
        return unsupported

    try:
        import cv2

        camera_found = False
        for index in range(5):
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            opened = capture.isOpened()
            camera_found = camera_found or opened
            readable = bool(opened and capture.read()[0])
            capture.release()
            if readable:
                return _result(
                    "working",
                    "none",
                    "A webcam is connected and available.",
                    connected=True,
                    in_use=False,
                    device_index=index,
                )

        if camera_found:
            return _result(
                "blocked",
                "camera_in_use_or_unavailable",
                "A webcam is connected but could not provide a frame; it may be in use by another process.",
                connected=True,
                in_use=True,
            )
        return _result(
            "blocked",
            "camera_not_found",
            "No webcam was detected.",
            connected=False,
            in_use=False,
        )
    except ImportError as error:
        return _result("error", "missing_dependency", str(error))
    except Exception as error:
        return _result("error", "camera_check_failed", str(error))


def check_speaker() -> str:
    """Inspect the default Windows render endpoint volume and mute state."""
    unsupported = _windows_only()
    if unsupported:
        return unsupported

    try:
        from pycaw.pycaw import AudioUtilities

        device = AudioUtilities.GetSpeakers()
        if device is None:
            return _result(
                "blocked",
                "speaker_not_found",
                "No default output device was found.",
                connected=False,
            )

        endpoint = _endpoint_volume(device)
        muted = bool(endpoint.GetMute())
        volume_percent = round(float(endpoint.GetMasterVolumeLevelScalar()) * 100, 1)
        if muted:
            status, error_code, message = (
                "blocked",
                "speaker_muted",
                "The default output device is muted.",
            )
        elif volume_percent <= 0:
            status, error_code, message = (
                "blocked",
                "speaker_volume_zero",
                "The default output device volume is zero.",
            )
        else:
            status, error_code, message = (
                "working",
                "none",
                "The default output device is enabled and audible.",
            )
        return _result(
            status,
            error_code,
            message,
            connected=True,
            muted=muted,
            volume_percent=volume_percent,
        )
    except ImportError as error:
        return _result("error", "missing_dependency", str(error))
    except Exception as error:
        return _result("error", "speaker_check_failed", str(error))


def check_connectivity() -> str:
    """Ping a reliable host using the native Windows ping utility."""
    host = "8.8.8.8"
    try:
        completed = subprocess.run(
            ["ping", "-n", "4", "-w", "1500", host],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        output = f"{completed.stdout}\n{completed.stderr}"
        match = re.search(r"\((\d+)% loss\)", output, re.IGNORECASE)
        if match is None:
            match = re.search(r"(\d+)%", output)
        packet_loss_percent = int(match.group(1)) if match else 100
        connected = completed.returncode == 0 and packet_loss_percent < 100
        if connected:
            return _result(
                "working",
                "none",
                "Internet connectivity is available.",
                host=host,
                packet_loss_percent=packet_loss_percent,
            )
        return _result(
            "blocked",
            "no_internet_connection",
            "The connectivity check reported no usable internet connection.",
            host=host,
            packet_loss_percent=packet_loss_percent,
        )
    except FileNotFoundError:
        return _result("error", "ping_unavailable", "The ping command was not found.")
    except subprocess.TimeoutExpired:
        return _result(
            "blocked",
            "connectivity_timeout",
            "The connectivity check timed out.",
            host=host,
            packet_loss_percent=100,
        )
    except Exception as error:
        return _result("error", "connectivity_check_failed", str(error))


def fix_mic() -> str:
    """Simulate restarting the microphone service."""
    return _result(
        "working",
        "none",
        "The microphone service restart was attempted.",
        action="restart_microphone_service",
    )


def fix_camera() -> str:
    """Simulate restarting the camera service."""
    return _result(
        "working",
        "none",
        "The camera service restart was attempted.",
        action="restart_camera_service",
    )


def fix_speaker() -> str:
    """Simulate restarting the speaker service."""
    return _result(
        "working",
        "none",
        "The speaker service restart was attempted.",
        action="restart_speaker_service",
    )


def fix_connectivity() -> str:
    """Simulate restarting the network service."""
    return _result(
        "working",
        "none",
        "The network service restart was attempted.",
        action="restart_network_service",
    )