import mss
import numpy as np
import time
from typing import Optional
from gapo.core.logging import get_logger
from gapo.core.metrics import capture_frames_total, capture_latency_seconds
from gapo.core.exceptions import CaptureError

logger = get_logger("mss_backend")


class MSSCapture:
    def __init__(self, monitor_index: int = 0, fps: int = 3):
        self.monitor_index = monitor_index
        self.target_fps = fps
        self.sct: Optional[mss.mss] = None
        self._running = False
        self._monitor = None
        self._frame_interval = 1.0 / fps
        self._last_frame_time = 0.0

    def start(self) -> bool:
        try:
            self.sct = mss.mss()
            monitors = self.sct.monitors
            if self.monitor_index >= len(monitors) - 1:
                self.monitor_index = 0
            self._monitor = monitors[self.monitor_index + 1]
            self._running = True
            logger.info(f"MSS started on monitor {self.monitor_index} at {self.target_fps} FPS")
            return True
        except Exception as e:
            logger.error(f"Failed to start MSS: {e}")
            return False

    def stop(self) -> None:
        if self.sct:
            self.sct.close()
            self.sct = None
        self._running = False
        logger.info("MSS stopped")

    def grab(self) -> Optional[np.ndarray]:
        if not self._running or not self.sct:
            return None

        now = time.monotonic()
        if now - self._last_frame_time < self._frame_interval:
            return None

        start = time.monotonic()
        try:
            screenshot = self.sct.grab(self._monitor)
            frame = np.array(screenshot)
            frame = frame[:, :, :3]
            latency = time.monotonic() - start

            capture_frames_total.inc()
            capture_latency_seconds.observe(latency)
            self._last_frame_time = now
            return frame
        except Exception as e:
            logger.error(f"MSS grab failed: {e}")
            return None

    def is_running(self) -> bool:
        return self._running

    def get_fps(self) -> float:
        return self.target_fps