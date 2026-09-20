# Documentação de Arquitetura - Gapo

## Visão Geral

O Gapo segue **Clean Architecture** com separação clara entre:
- **Controllers** (Entry points): CLI, Discord Bot
- **Services** (Business Logic): Coaching, OCR, Capture, TTS
- **Models** (Domain): GameState, Events, Coach, Audio
- **Repositories** (Data Access): Champions, Prompts, ROIs, Cache
- **Infrastructure** (External Adapters): Discord, Ollama, Piper, Capture, OCR

## Fluxo de Dados Principal

```
1. CaptureService (dxcam/mss) → Frame numpy (BGR)
                                    │
2. OCRService (YOLO + PaddleOCR) → ParsedHUD, ParsedMinimap, ParsedChat
                                    │
3. GameStateService → GameState atualizado + History (30s)
                                    │
4. EventService → GameEvent[] (regras heurísticas)
                                    │
5. CoachService → CoachResponse (via Ollama LLM)
                                    │
6. TTSService (Piper) → AudioChunk (streaming)
                                    │
7. DiscordVoiceManager → Opus packets → Discord Voice WS
```

## Pipeline Assíncrono

```
Capture Loop (3 FPS)
    │
    ├─▶ OCR (CPU, ~100ms) ──▶ GameState Update
    │                              │
    │                              ├─▶ Event Detection (sync, <5ms)
    │                              │      │
    │                              │      └─▶ CoachService (async, ~500ms)
    │                              │             │
    │                              │             └─▶ TTS (async, ~300ms)
    │                              │                    │
    │                              │                    └─▶ Discord Voice (stream)
    │                              │
    │                              └─▶ Disponível para "Gapo" Q&A
    │
    └─▶ Próximo frame
```

## Gerenciamento de VRAM (GTX 1660 6GB)

| Componente | Dispositivo | VRAM | Estratégia |
|------------|-------------|------|------------|
| YOLOv8n ONNX | GPU | ~500 MB | Compartilhado |
| PaddleOCR | **CPU** | 0 MB | Offload intencional |
| Qwen2.5-7B-Q4 | GPU | ~4.5 GB | Via Ollama (CUDA) |
| Piper-TTS | **CPU** | 0 MB | Offload intencional |
| **Total** | | **~5 GB** | **Folga 1GB** |

## Modelos de Dados Principais

### GameState
```python
GameState:
  - timestamp: datetime
  - game_time_seconds: float
  - phase: str
  - player: PlayerState
  - allies: dict[str, PlayerState]
  - enemies: dict[str, PlayerState]
  - minimap: MinimapState
  - chat_messages: list[dict]
  - tab_open: bool
```

### GameEvent
```python
GameEvent:
  - event_type: EventType (GANK, OBJECTIVE, FIGHT, etc.)
  - priority: EventPriority (LOW, MEDIUM, HIGH, CRITICAL)
  - message: str
  - context: dict
  - cooldown_seconds: float
```

### CoachPrompt (Two Modes)
```python
Event-Driven: "Dica 2 frases, acionável, AGORA"
Gapo Chat: "Resposta 3 frases, contextual, tom duo"
```

## Extensibilidade

### Adicionar Novo Evento
1. Adicionar `EventType` em `models/events.py`
2. Criar `EventRule` em `services/event_service.py`
3. Adicionar few-shot example em `data/prompts/event_coach_v1.yaml`

### Adicionar Novo Champion Knowledge
```json
// data/champions/matchups.json
"zed_vs_syndra": {
  "advice": "Dodge Q com W, all-in level 6 se ela errar E",
  "difficulty": "favorable",
  "key_levels": [3, 6]
}
```

### Novo Provedor TTS
Implementar interface em `infrastructure/tts/base.py` e registrar no `ModelService`.

## Testes

```
tests/
├── unit/           # Modelos, parsers, builders (rápidos)
├── integration/    # Serviços com dependências reais (lentos)
└── fixtures/       # Screenshots, áudio samples
```

## Deploy

### Docker Compose
```yaml
services:
  ollama:    # GPU reservada
  gapo:      # GPU compartilhada com ollama
```

### Health Checks
- `/health` endpoint (planejado)
- Prometheus metrics em `/metrics`
- Logs estruturados JSONL em `logs/`