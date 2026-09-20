import dxcam
import numpy as np
import time
from typing import Optional
from gapo.core.logging import get_logger
from gapo.core.metrics import capture_frames_total, capture_latency_seconds
from gapo.core.exceptions import CaptureError

logger = get_logger("dxcam_backend")


class DXCamCapture:
    def __init__(self, monitor_index: int = 0, fps: int = 3):
        self.monitor_index = monitor_index
        self.target_fps = fps
        self.camera: Optional[dxcam.Camera] = None
        self._running = False
        self._last_frame_time = 0.0

    def start(self) -> bool:
        try:
            self.camera = dxcam.create(device_idx=self.monitor_index, output_color="BGR")
            self.camera.start(target_fps=self.target_fps, video_mode=True)
            self._running = True
            logger.info(f"DXCam started on monitor {self.monitor_index} at {self.target_fps} FPS")
            return True
        except Exception as e:
            logger.error(f"Failed to start DXCam: {e}")
            return False

    def stop(self) -> None:
        if self.camera:
            self.camera.stop()
            self.camera = None
        self._running = False
        logger.info("DXCam stopped")

    def grab(self) -> Optional[np.ndarray]:
        if not self._running or not self.camera:
            return None

        start = time.monotonic()
        frame = self.camera.get_latest_frame()
        latency = time.monotonic() - start

        if frame is not None:
            capture_frames_total.inc()
            capture_latency_seconds.observe(latency)
            self._last_frame_time = time.monotonic()
            return frame

        return None

    def is_running(self) -> bool:
        return self._running

    def get_fps(self) -> float:
        if not self.camera:
            return 0.0
        return self.camera.get_fps()