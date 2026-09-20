#!/usr/bin/env python3
"""
Script de calibração interativa de ROIs.
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
import click
from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()


class ROICalibrator:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.rois = {}
        self.current_roi = None
        self.start_point = None
        self.image = None

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.start_point = (x, y)
        elif event == cv2.EVENT_LBUTTONUP and self.start_point:
            x1, y1 = self.start_point
            x2, y2 = x, y
            x_min, x_max = sorted([x1, x2])
            y_min, y_max = sorted([y1, y2])
            w = x_max - x_min
            h = y_max - y_min
            if w > 10 and h > 10:
                self.rois[self.current_roi] = {
                    "name": self.current_roi,
                    "x": x_min,
                    "y": y_min,
                    "width": w,
                    "height": h,
                }
                console.print(f"✅ {self.current_roi}: ({x_min}, {y_min}) {w}x{h}")
            self.start_point = None

    def calibrate(self, screenshot) -> dict:
        self.image = screenshot.copy()
        cv2.namedWindow("Calibração ROI - Gapo", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Calibração ROI - Gapo", min(1280, self.width), min(720, self.height))
        cv2.setMouseCallback("Calibração ROI - Gapo", self.mouse_callback)

        roi_names = [
            "hud_hp", "hud_mana", "hud_level", "hud_gold", "hud_cs",
            "hud_items", "hud_spells", "minimap", "chat",
        ]

        for roi_name in roi_names:
            self.current_roi = roi_name
            console.print(f"\n[bold cyan]Selecione região para: {roi_name}[/bold cyan]")
            console.print("Clique e arraste para selecionar a área. Pressione ESPAÇO para confirmar, 's' para pular.")

            while True:
                display = self.image.copy()
                for name, roi in self.rois.items():
                    cv2.rectangle(display, (roi["x"], roi["y"]), 
                                (roi["x"] + roi["width"], roi["y"] + roi["height"]), (0, 255, 0), 2)
                    cv2.putText(display, name, (roi["x"], roi["y"] - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                if self.start_point:
                    cv2.rectangle(display, self.start_point, (cv2.getWindowImageRect("Calibração ROI - Gapo")[2], cv2.getWindowImageRect("Calibração ROI - Gapo")[3]), (255, 0, 0), 2)

                cv2.imshow("Calibração ROI - Gapo", display)
                key = cv2.waitKey(1) & 0xFF
                if key == ord(' '):
                    break
                elif key == ord('s'):
                    console.print(f"⏭️  Pulando {roi_name}")
                    break
                elif key == 27:
                    cv2.destroyAllWindows()
                    return self.rois

        cv2.destroyAllWindows()
        return self.rois


def capture_screenshot() -> np.ndarray:
    """Captura screenshot usando mss."""
    import mss
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        return screenshot[:, :, :3]


@click.command()
@click.option("--width", default=1920, help="Largura da tela")
@click.option("--height", default=1080, help="Altura da tela")
@click.option("--output", default="data/roi_presets", help="Diretório de saída")
def main(width: int, height: int, output: str):
    console.print(Panel("🎯 Calibração de ROIs - Gapo", style="bold magenta"))
    console.print(f"Resolução: {width}x{height}")
    console.print("Posicione o LoL em modo janela sem bordas na resolução correta.")
    
    if not Confirm.ask("Continuar?"):
        return

    console.print("Capturando tela em 3 segundos...")
    import time
    time.sleep(3)

    screenshot = capture_screenshot()
    console.print(f"Screenshot capturado: {screenshot.shape}")

    calibrator = ROICalibrator(width, height)
    rois = calibrator.calibrate(screenshot)

    if rois:
        output_path = Path(output) / f"{width}x{height}_user.yaml"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(rois, f, allow_unicode=True)
        console.print(f"\n✅ ROIs salvos em: {output_path}")
    else:
        console.print("\n❌ Nenhum ROI calibrado")


from rich.panel import Panel

if __name__ == "__main__":
    main()