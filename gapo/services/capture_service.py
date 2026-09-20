import asyncio
import time
from gapo.infrastructure.capture import DXCamCapture, MSSCapture
from gapo.config.settings import get_settings
from gapo.core.logging import get_logger
from gapo.core.events import event_bus
from gapo.core.exceptions import CaptureError

logger = get_logger("capture_service")


class CaptureService:
    def __init__(self):
        self.settings = get_settings()
        self.dxcam: DXCamCapture | None = None
        self.mss: MSSCapture | None = None
        self._running = False
        self._capture_task: asyncio.Task | None = None
        self._frame_callback = None
        self._fps_counter = 0
        self._last_fps_time = time.time()
        self._current_fps = 0.0

    def set_frame_callback(self, callback):
        self._frame_callback = callback

    async def start(self) -> bool:
        if self._running:
            return True

        if self.settings.capture.use_dxcam:
            self.dxcam = DXCamCapture(
                monitor_index=self.settings.capture.monitor_index,
                fps=self.settings.capture.fps,
            )
            if not self.dxcam.start():
                logger.warning("DXCam failed, falling back to MSS")
                self.dxcam = None

        if not self.dxcam:
            self.mss = MSSCapture(
                monitor_index=self.settings.capture.monitor_index,
                fps=self.settings.capture.fps,
            )
            if not self.mss.start():
                logger.error("Both DXCam and MSS failed to start")
                return False

        self._running = True
        self._capture_task = asyncio.create_task(self._capture_loop())
        logger.info("Capture service started")
        return True

    async def stop(self) -> None:
        self._running = False
        if self._capture_task:
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:
                pass

        if self.dxcam:
            self.dxcam.stop()
        if self.mss:
            self.mss.stop()

        logger.info("Capture service stopped")

    async def _capture_loop(self) -> None:
        while self._running:
            frame = None
            if self.dxcam:
                frame = self.dxcam.grab()
            elif self.mss:
                frame = self.mss.grab()

            if frame is not None and self._frame_callback:
                try:
                    await self._frame_callback(frame)
                except Exception as e:
                    logger.error(f"Frame callback error: {e}")

            self._update_fps()
            await asyncio.sleep(1.0 / self.settings.capture.fps)

    def _update_fps(self) -> None:
        self._fps_counter += 1
        now = time.time()
        if now - self._last_fps_time >= 1.0:
            self._current_fps = self._fps_counter / (now - self._last_fps_time)
            self._fps_counter = 0
            self._last_fps_time = now

    def get_fps(self) -> float:
        return self._current_fps

    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> dict:
        return {
            "capturing": self._running,
            "fps": self._current_fps,
            "backend": "dxcam" if self.dxcam else "mss",
        }