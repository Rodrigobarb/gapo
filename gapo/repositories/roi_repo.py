import yaml
from pathlib import Path
from typing import Optional
from gapo.models.ocr import UIRoi, get_roi_preset
from gapo.core.logging import get_logger

logger = get_logger("roi_repo")


class ROIRepository:
    def __init__(self, roi_dir: Path = Path("data/roi_presets")):
        self.roi_dir = roi_dir
        self._presets: dict[str, dict[str, UIRoi]] = {}
        self._user_calibration: dict[str, UIRoi] = {}

    def get_preset(self, resolution: str) -> dict[str, UIRoi]:
        if resolution in self._presets:
            return self._presets[resolution]

        path = self.roi_dir / f"{resolution}.yaml"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            rois = {k: UIRoi(**v) for k, v in data.items()}
            self._presets[resolution] = rois
            return rois

        logger.warning(f"Preset not found for {resolution}, using default")
        return get_roi_preset(resolution)

    def save_calibration(self, resolution: str, rois: dict[str, UIRoi]) -> None:
        self._user_calibration[resolution] = rois
        path = self.roi_dir / f"{resolution}_user.yaml"
        data = {k: v.__dict__ for k, v in rois.items()}
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)
        logger.info(f"Saved user calibration for {resolution}")

    def get_effective_rois(self, resolution: str) -> dict[str, UIRoi]:
        base = self.get_preset(resolution)
        if resolution in self._user_calibration:
            base = {**base, **self._user_calibration[resolution]}
        return base