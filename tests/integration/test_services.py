import pytest
from gapo.services.ocr_service import OCRService
from gapo.repositories.roi_repo import ROIRepository


@pytest.mark.integration
@pytest.mark.skip(reason="Requires actual screen capture")
def test_ocr_service_initialization():
    roi_repo = ROIRepository()
    ocr_service = OCRService(roi_repo)
    ocr_service.set_resolution(1920, 1080)
    assert "hud_hp" in ocr_service._current_rois


@pytest.mark.integration
@pytest.mark.skip(reason="Requires Ollama running")
def test_ollama_connection():
    from gapo.infrastructure.ollama import OllamaClient
    client = OllamaClient()
    # This would need actual Ollama running
    assert client is not None