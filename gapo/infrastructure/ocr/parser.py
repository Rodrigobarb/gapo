import re
from typing import Optional
from gapo.models.ocr import OCRResult, ParsedHUD, ParsedMinimap, ParsedChat
from gapo.core.logging import get_logger

logger = get_logger("parser")


class OCRParser:
    def __init__(self):
        self.number_pattern = re.compile(r"[\d,.]+")
        self.item_keywords = [
            "botas", "espada", "adaga", "cetro", "cajado", "capa", "elmo", "armadura",
            "boots", "sword", "dagger", "staff", "cloak", "helm", "armor", "blade",
            "infinity", "edge", "phantom", "dancer", "guardian", "angel", "deathcap",
            "void", "staff", "rabadon", "lich", "bane", "morello", "zhonya", "banshee",
        ]

    def parse_hud(self, results: list[OCRResult]) -> ParsedHUD:
        hud = ParsedHUD()
        text = " ".join([r.text for r in results])

        hud.hp = self._extract_hp(text)
        hud.mana = self._extract_mana(text)
        hud.level = self._extract_level(text)
        hud.gold = self._extract_gold(text)
        hud.cs = self._extract_cs(text)
        hud.items = self._extract_items(text)

        return hud

    def _extract_hp(self, text: str) -> Optional[int]:
        patterns = [
            r"(\d+)\s*/\s*(\d+)\s*hp",
            r"hp\s*(\d+)\s*/\s*(\d+)",
            r"(\d+)\s*/\s*(\d+)",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def _extract_mana(self, text: str) -> Optional[int]:
        patterns = [
            r"(\d+)\s*/\s*(\d+)\s*mana",
            r"mana\s*(\d+)\s*/\s*(\d+)",
        ]
        for pat in patterns:
            match = re.search(pat, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def _extract_level(self, text: str) -> Optional[int]:
        match = re.search(r"level\s*(\d+)|lvl\s*(\d+)|lv\.?\s*(\d+)", text, re.IGNORECASE)
        if match:
            return int(match.group(1) or match.group(2) or match.group(3))
        return None

    def _extract_gold(self, text: str) -> Optional[int]:
        match = re.search(r"(\d+[,.]?\d*)\s*[gG]", text)
        if match:
            val = match.group(1).replace(",", "").replace(".", "")
            return int(val) * (1000 if "k" in match.group(0).lower() else 1)
        return None

    def _extract_cs(self, text: str) -> Optional[int]:
        match = re.search(r"(\d+)\s*[cC][sS]", text)
        if match:
            return int(match.group(1))
        return None

    def _extract_items(self, text: str) -> list[str]:
        items = []
        text_lower = text.lower()
        for keyword in self.item_keywords:
            if keyword in text_lower:
                items.append(keyword.capitalize())
        return list(set(items))

    def parse_minimap(self, results: list[OCRResult]) -> ParsedMinimap:
        minimap = ParsedMinimap()
        return minimap

    def parse_chat(self, results: list[OCRResult]) -> ParsedChat:
        chat = ParsedChat()
        for result in results:
            chat.messages.append({
                "text": result.text,
                "confidence": result.confidence,
                "roi": result.roi_name,
            })
        return chat