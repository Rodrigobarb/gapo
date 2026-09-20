from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

registry = CollectorRegistry()

capture_frames_total = Counter(
    "gapo_capture_frames_total",
    "Total frames captured",
    registry=registry,
)

capture_latency_seconds = Histogram(
    "gapo_capture_latency_seconds",
    "Screen capture latency",
    registry=registry,
)

ocr_processed_total = Counter(
    "gapo_ocr_processed_total",
    "Total OCR regions processed",
    ["roi", "status"],
    registry=registry,
)

ocr_latency_seconds = Histogram(
    "gapo_ocr_latency_seconds",
    "OCR processing latency",
    ["roi"],
    registry=registry,
)

llm_requests_total = Counter(
    "gapo_llm_requests_total",
    "Total LLM requests",
    ["mode", "status"],
    registry=registry,
)

llm_latency_seconds = Histogram(
    "gapo_llm_latency_seconds",
    "LLM inference latency",
    ["mode"],
    registry=registry,
)

tts_requests_total = Counter(
    "gapo_tts_requests_total",
    "Total TTS requests",
    ["status"],
    registry=registry,
)

tts_latency_seconds = Histogram(
    "gapo_tts_latency_seconds",
    "TTS generation latency",
    registry=registry,
)

discord_voice_connected = Gauge(
    "gapo_discord_voice_connected",
    "Discord voice connection status (1=connected, 0=disconnected)",
    registry=registry,
)

active_events = Gauge(
    "gapo_active_events",
    "Number of active game events",
    ["event_type"],
    registry=registry,
)

game_state_updates = Counter(
    "gapo_game_state_updates_total",
    "Total game state updates",
    registry=registry,
)