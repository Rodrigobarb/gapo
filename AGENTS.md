# AGENTS.md — Manual Operacional para Agentes de IA

## 1. Visão Geral

**Gapo** — LoL Coach Discord Bot com OCR tempo real + LLM local + TTS PT-BR.
Stack: Python 3.11+, dxcam/mss (captura), YOLOv8n ONNX + PaddleOCR (OCR), Ollama (Qwen2.5-7B-Q4), Piper-TTS, discord.py.
Arquitetura: Clean Architecture (Controller/Service/Model/Repository/Infrastructure).
Pipeline: Capture (3 FPS) → OCR (CPU) → GameState → Event Detection → Coach (LLM) → TTS (CPU) → Discord Voice.

---

## 2. Setup

### Pré-requisitos
- Python 3.11+
- GPU NVIDIA (GTX 1660 6GB VRAM mínimo)
- Ollama instalado e rodando (`ollama serve`)
- FFmpeg no PATH
- Token Discord Bot com intents: `message_content`, `voice_states`, `guilds`

### Passos exatos
```bash
git clone <repo>
cd gapo
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux
pip install -e .[dev]          # instala dependências + dev tools

# Configure variáveis de ambiente
cp .env.example .env
# Edite .env com DISCORD_TOKEN e DISCORD_APPLICATION_ID

# Inicializa (baixa modelos ~5GB: LLM + TTS + YOLO)
gapo init
# ou: python -m scripts.init_gapo
```

### Variáveis de ambiente (.env)
| Variável | Obrigatória | Padrão |
|----------|-------------|--------|
| `DISCORD_TOKEN` | Sim | — |
| `DISCORD_APPLICATION_ID` | Sim | — |
| `GAPO_MODEL_LLM_NAME` | Não | `qwen2.5:7b-instruct-q4_K_M` |
| `GAPO_MODEL_TTS_MODEL` | Não | `pt_BR-faber-medium` |
| `GAPO_CAPTURE_FPS` | Não | `3` |
| `GAPO_LOG_LEVEL` | Não | `INFO` |

---

## 3. Comandos

| Ação | Comando |
|------|---------|
| Inicializar projeto (download modelos) | `gapo init` |
| Rodar bot completo (Discord + Voice) | `gapo run` |
| Rodar apenas captura + OCR (teste) | `gapo capture` |
| Calibrar ROIs para resolução | `gapo calibrate --width 1920 --height 1080` |
| Diagnóstico do sistema | `gapo doctor` |
| Baixar modelos manualmente | `python -m scripts.download_models` |
| Calibração interativa ROIs | `python -m scripts.calibrate_roi --width 1920 --height 1080` |
| Rodar testes | `pytest tests/ -v` |
| Rodar testes unitários | `pytest tests/unit/ -v` |
| Rodar testes integração | `pytest tests/integration/ -v` |
| Lint (ruff) | `ruff check .` |
| Format (ruff) | `ruff format .` |
| Typecheck (mypy) | `mypy gapo/` |
| Build package | `pip wheel . -w dist/` |

> **Nota**: Não há CI/CD configurado (sem `.github/workflows`). Comandos acima são os definidos no `pyproject.toml` e `cli.py`.

---

## 4. Estrutura do Projeto

```
gapo/
├── pyproject.toml              # Config package, deps, ruff, mypy, pytest
├── docker-compose.yml          # Ollama + Gapo (GPU reservada)
├── Dockerfile                  # Multi-stage build
├── .env.example                # Template variáveis ambiente
├── scripts/                    # Scripts standalone
│   ├── init_gapo.py            # Setup completo (modelos + dirs + configs)
│   ├── download_models.py      # Baixa LLM, TTS, exporta YOLO ONNX
│   ├── calibrate_roi.py        # Calibração interativa ROIs (OpenCV)
│   └── doctor.py               # Health check sistema
├── data/                       # Dados versionados (Git)
│   ├── champions/              # matchups.json, builds.json, counters.json, powerspikes.json
│   ├── prompts/                # event_coach_v1.yaml, gapo_coach_v1.yaml
│   └── roi_presets/            # 1920x1080.yaml, 2560x1440.yaml, 3840x2160.yaml
├── gapo/
│   ├── __main__.py             # Entry point: cli()
│   ├── cli.py                  # Re-exporta CLI commands
│   ├── config/
│   │   └── settings.py         # Pydantic Settings (env + yaml), get_settings()
│   ├── controllers/
│   │   └── cli_controller.py   # CLIController: orquestra services, callbacks
│   ├── core/
│   │   ├── events.py           # EventBus (asyncio pub/sub)
│   │   ├── logging.py          # Loguru setup (stdout + file rotation)
│   │   ├── metrics.py          # Prometheus metrics (Counter, Histogram, Gauge)
│   │   └── exceptions.py       # Custom exceptions (GapoError, etc.)
│   ├── models/                 # Domain models (dataclasses + Pydantic)
│   │   ├── game_state.py       # GameState, PlayerState, MinimapState, History
│   │   ├── events.py           # GameEvent, EventType, EventPriority, Rules
│   │   ├── coach.py            # CoachPrompt, CoachResponse, Prompt Builders
│   │   ├── ocr.py              # UIRoi, ParsedHUD, ParsedMinimap, ROI Presets
│   │   ├── audio.py            # VoiceConfig, TTSRequest, AudioChunk, OpusPacket
│   │   └── config.py           # ROIConfig, ModelConfig, AppConfig
│   ├── repositories/           # Data access (Repository Pattern)
│   │   ├── prompt_repo.py      # Carrega prompts YAML (versionados)
│   │   ├── champion_repo.py    # Matchups, builds, counters (JSON)
│   │   ├── roi_repo.py         # ROI presets + user calibration
│   │   └── cache_repo.py       # AsyncCache (TTL + LRU) para LLM/OCR/TTS
│   ├── services/               # Business Logic (injetados no CLIController)
│   │   ├── model_service.py    # Gerencia Ollama, Piper, YOLO (lifecycle)
│   │   ├── capture_service.py  # DXCam/MSS loop, frame callback
│   │   ├── ocr_service.py      # Pipeline YOLO + PaddleOCR + Parser
│   │   ├── game_state_service.py # Aggregator + History (30s buffer)
│   │   ├── event_service.py    # Rule-based detector (8 event types)
│   │   ├── coach_service.py    # Event-driven + Gapo Q&A (com cache)
│   │   ├── gapo_service.py     # Wrapper Q&A com rate limit por user
│   │   ├── tts_service.py      # Piper streaming + PriorityQueue (prioridade Gapo)
│   │   └── knowledge_service.py # RAG leve: enriquece prompt com champion data
│   ├── infrastructure/         # External Adapters
│   │   ├── discord/            # Bot, VoiceManager, Commands, Gapo Listener
│   │   ├── ollama/             # AsyncClient + PromptBuilder (few-shot + RAG)
│   │   ├── piper/              # Engine (subprocess) + VoiceManager
│   │   ├── capture/            # DXCamCapture + MSSCapture (fallback)
│   │   └── ocr/                # YOLODetector (ONNX), PaddleEngine, Preprocessor, Parser
│   └── utils/
│       ├── image.py            # crop, resize, preprocess_for_ocr
│       ├── audio.py            # OpusEncoder/Decoder, resample, chunk
│       └── async.py            # throttle, debounce, RateLimiter, AsyncCache
└── tests/
    ├── unit/                   # Modelos, parsers, builders (rápidos)
    ├── integration/            # Serviços com deps reais (skip por padrão)
    └── conftest.py             # Fixtures: sample_game_state, sample_event
```

---

## 5. Convenções de Código

### Imports
- **Absolute imports** from `gapo.*` (não relativos)
- Agrupamento: stdlib → third-party → local
- `__all__` em `__init__.py` para exports explícitos

```python
# Bom
from gapo.models.game_state import GameState, PlayerState
from gapo.services.coach_service import CoachService
from gapo.infrastructure.ollama import OllamaClient

# Evite
from ..models import GameState
from gapo.models import *
```

### Tipagem
- **Dataclasses** para domain models mutáveis (`@dataclass`)
- **Pydantic BaseModel** para config/validation (`BaseModel`)
- Type hints obrigatórios (`disallow_untyped_defs = true` no mypy)
- `Optional[T]` em vez de `T | None` (compatibilidade 3.11)

```python
@dataclass
class PlayerState:
    champion: str = ""
    level: int = 1
    hp: int = 0
    items: list[str] = field(default_factory=list)

class ModelConfig(BaseModel):
    llm_name: str = "qwen2.5:7b-instruct-q4_K_M"
    temperature: float = 0.3
```

### Logging
- Use `get_logger(__name__)` ou `get_logger("module_name")`
- Níveis: `logger.debug/info/warning/error`
- Logs estruturados em `logs/gapo_YYYY-MM-DD.log` + `logs/gapo_error_YYYY-MM-DD.log`

```python
from gapo.core.logging import get_logger
logger = get_logger("coach_service")
logger.info(f"Event coach response: {response.text[:100]}...")
```

### Async
- `async def` para I/O (Ollama, Discord, Piper subprocess, Cache)
- `asyncio.create_task()` para fire-and-forget (audio playback)
- `asyncio.gather(*tasks, return_exceptions=True)` para paralelismo
- `RateLimiter` e `AsyncCache` em `utils/async.py` para controle de taxa

### Error Handling
- Custom exceptions em `core/exceptions.py` (`GapoError`, `ModelNotFoundError`, etc.)
- `try/except` com logging + retorno de objeto de erro (não raise para caller em hot paths)
- Health checks assíncronos retornam `bool`

```python
async def generate(self, prompt: CoachPrompt) -> CoachResponse:
    try:
        ...
    except Exception as e:
        llm_requests_total.labels(mode=prompt.mode.value, status="error").inc()
        logger.error(f"LLM generation failed: {e}")
        return CoachResponse(text="Erro ao gerar resposta.", mode=prompt.mode, ...)
```

### Configuração
- `Pydantic Settings` em `config/settings.py` com `env_prefix="GAPO_"`
- YAML para prompts (`data/prompts/`) e ROIs (`data/roi_presets/`)
- JSON para champion knowledge (`data/champions/`)
- `get_settings()` singleton, `reload_settings()` para recarregar

---

## 6. Testes

### Framework
- **pytest** + `pytest-asyncio` (asyncio_mode = auto)
- Testes em `tests/unit/` (rápidos, sem deps externas)
- Testes em `tests/integration/` (marcados `@pytest.mark.integration`, skip por padrão)

### Convenções
- Arquivo: `test_<module>.py`
- Classe: `Test<ClassName>`
- Método: `test_<behavior>`
- Fixtures em `tests/conftest.py` (`sample_game_state`, `sample_event`)

### Rodar
```bash
pytest tests/ -v                    # todos
pytest tests/unit/ -v               # apenas unit
pytest tests/integration/ -v        # apenas integração (requer Ollama rodando)
pytest tests/unit/test_models.py::TestGameState::test_context_dict -v  # single test
```

### O que precisa passar antes de PR
- `pytest tests/unit/ -v` (100% pass)
- `ruff check .` (0 errors)
- `mypy gapo/` (0 errors)

---

## 7. Git e PRs

### Commits
Formato convencional:
```
<tipo>(<escopo>): <descrição curta>

<body opcional>

<footer opcional>
```

Tipos: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`

Exemplos:
```
feat(ocr): adiciona suporte a resolução 4K
fix(capture): fallback MSS quando DXCam falha
refactor(services): extrai CoachService do CLIController
docs: atualiza troubleshooting com VRAM OOM
```

### Branches
- `feat/<descricao>` — nova funcionalidade
- `fix/<descricao>` — correção de bug
- `refactor/<descricao>` — refatoração
- `chore/<descricao>` — manutenção

### PR Description
Incluir:
- **What**: O que muda (1-2 linhas)
- **Why**: Motivação / issue relacionado
- **How**: Resumo técnico (services/models alterados)
- **Test**: Como testou (comandos, cenários)
- **Breaking**: Se houver breaking changes

---

## 8. Armadilhas e Regras

### ❌ Não edite à mão (gerados)
- `gapo/**/__pycache__/` — compilado Python
- `logs/*.log` — logs runtime
- `data/roi_presets/*_user.yaml` — calibração usuário (gerado por `calibrate_roi.py`)
- Modelos baixados: `~/.ollama/`, `~/.local/share/piper/`, `yolov8n.onnx`

### ⚠️ Código sensível / Quebra não óbvia
| Área | Risco | Mitigação |
|------|-------|-----------|
| `CaptureService` | DXCam falha silenciosamente em fullscreen exclusivo | Sempre testar em **Borderless Windowed** |
| `OCRService` | ROIs hardcoded quebram a cada patch do LoL | Usar `gapo calibrate` após updates; ROIs em YAML versionado |
| `ModelService` | VRAM OOM se LLM + YOLO + OCR rodarem juntos na GPU | OCR e TTS **forçados para CPU** (config `use_gpu: false`) |
| `CoachService` | Cache key usa `hash(prompt.user_prompt)` — colisão possível | Incluir `prompt.mode.value` na key; TTL 300s |
| `TTSService` | Piper roda via subprocess — bloqueia event loop se sync | Usar `asyncio.create_subprocess_exec` (já implementado) |
| `DiscordVoiceManager` | Opus packets precisam 20ms frames @ 48kHz | `FRAME_SIZE = 960` hardcoded; não alterar sem testar audio |
| `EventService` | Heurísticas baseadas em thresholds arbitrários | Ajustar cooldowns via `/coach config`; não hardcodear |

### 🔒 Exige confirmação humana
- Mudanças em `pyproject.toml` (versão, deps, entry points)
- Alterações em `docker-compose.yml` / `Dockerfile`
- Modificação de prompts em `data/prompts/` (afeta qualidade coaching)
- Novos modelos LLM/TTS (impacto VRAM/latência)
- Schema de `GameState` ou `GameEvent` (quebra compatibilidade)

### 🐛 Debug rápido
```bash
# Ver logs tempo real
tail -f logs/gapo_$(date +%Y-%m-%d).log

# Ver erros apenas
tail -f logs/gapo_error_$(date +%Y-%m-%d).log

# Métricas Prometheus
curl http://localhost:9090/metrics | grep gapo

# VRAM uso
nvidia-smi -l 1

# Testar componentes isolados
python -m gapo.infrastructure.capture.dxcam_backend
python -m gapo.infrastructure.ocr.paddle_engine
python -m gapo.infrastructure.ollama.client
python -m gapo.infrastructure.piper.engine
```

---

## Pendências de Confirmação

- [ ] **CI/CD**: Não há `.github/workflows` — confirmar se será adicionado e quais jobs (lint, test, build, deploy)
- [ ] **Versionamento**: Como será feito o bump de versão (semver, calendar, etc.)?
- [ ] **Deploy produção**: Docker Compose é o padrão ou haverá Kubernetes/outro?
- [ ] **Secrets**: Como gerenciar `DISCORD_TOKEN` em produção (Docker secrets, Vault, .env)?
- [ ] **Testes integração**: Rodam em CI? Precisam de GPU? Como mockar Ollama/Piper?
- [ ] **Monitoramento**: Prometheus endpoint exposto? Grafana dashboards?
- [ ] **Atualização champion data**: Processo para atualizar `data/champions/` a cada patch do LoL?