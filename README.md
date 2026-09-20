# Gapo - LoL Coach Discord Bot

Bot Discord inteligente para League of Legends que analisa sua partida em tempo real via OCR e fornece coaching por voz em português brasileiro.

## 🎯 Funcionalidades

- **Coach Automático (Event-Driven)**: Detecta ganks, objetivos, teamfights, erros de posicionamento e dá dicas por voz
- **Gapo Chat (Q&A por Voz)**: Pergunte "Gapo qual a melhor jogada?" e receba resposta contextualizada por voz
- **100% Local**: Roda na sua máquina (GTX 1660 6GB VRAM + 16GB RAM), sem custos de API
- **OCR em Tempo Real**: Captura HUD, minimapa, chat e aba Tab
- **LLM Local**: Qwen2.5-7B via Ollama para coaching inteligente
- **TTS Português**: Piper-TTS com voz natural PT-BR

## 🏗️ Arquitetura

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Screen    │────▶│   OCR       │────▶│  Game State │────▶│  Event      │
│  Capture    │     │  Pipeline   │     │  Aggregator │     │  Detector   │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                     │
                    ┌────────────────────────────────────────────────┘
                    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Discord    │◀────│   TTS       │◀────│   LLM       │◀────│  Prompt     │
│  Voice Bot  │     │  (Piper)    │     │  (Ollama)   │     │  Builder    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Clean Architecture (Controller/Service/Model)

```
gapo/
├── controllers/          # Entry points (CLI, Discord)
├── services/             # Business logic
├── models/               # Domain models (Pydantic)
├── repositories/         # Data access
├── infrastructure/       # External adapters
│   ├── discord/          # Discord.py bot + voice
│   ├── ollama/           # LLM client + prompts
│   ├── piper/            # TTS engine
│   ├── capture/          # Screen capture (dxcam/mss)
│   └── ocr/              # YOLO + PaddleOCR
└── core/                 # Shared utilities
```

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.11+
- GPU NVIDIA (GTX 1660 6GB VRAM mínimo)
- Ollama instalado
- Conta Discord Bot com token

### 1. Clone e configure
```bash
git clone <repo>
cd gapo
python -m venv venv
venv\Scripts\activate  # Windows
pip install -e .[dev]
```

### 2. Inicialize (baixa modelos)
```bash
gapo init
# ou
python -m scripts.init_gapo
```

Isso baixa:
- **Qwen2.5-7B-Instruct-Q4_K_M** (~4.2GB) via Ollama
- **Piper pt_BR-faber-medium** (~50MB) 
- **YOLOv8n ONNX** (~3MB)

### 3. Configure Discord
Crie arquivo `.env`:
```env
DISCORD_TOKEN=seu_token_aqui
DISCORD_APPLICATION_ID=seu_app_id
```

### 4. Execute
```bash
gapo run
```

## 🎮 Como Usar

### Coach Automático
1. Entre em uma partida no LoL (modo janela sem bordas, 1920x1080 recomendado)
2. No Discord, use `/coach start` no canal de voz
3. O bot fala dicas automaticamente:
   - *"Zed sumiu há 12s, provavelmente vindo bot. Recue pra torre AGORA."*
   - *"Dragão nasce em 5s, 3 inimigos lá. Smite steal é sua win condition."*

### Gapo Chat (Perguntas por Voz)
No chat do Discord (qualquer canal):
```
Gapo qual a melhor jogada agora?
Gapo o que countera Malphite top?
Gapo devo dar flash pra pegar esse kill?
Gapo qual build pro Zed contra tank?
```

O bot responde **por voz no canal de voz** onde está conectado.

### Comandos Slash
| Comando | Descrição |
|---------|-----------|
| `/coach start` | Inicia coach + entra no voice |
| `/coach stop` | Para tudo + sai do voice |
| `/coach status` | Mostra FPS, VRAM, eventos/min |
| `/coach config` | Ajusta cooldowns, agressividade |
| `/coach calibrate` | Ajuda para calibrar ROIs |

## ⚙️ Configuração

### Resoluções Suportadas
- 1920x1080 (padrão)
- 2560x1440
- 3840x2160

### Calibração de ROIs
```bash
gapo calibrate
# ou
python -m scripts.calibrate_roi --width 1920 --height 1080
```

### Ajuste de Agressividade
```bash
/coach config aggressiveness:7  # 1-10 (mais agressivo = mais dicas)
/coach config event_cooldown:3  # Segundos entre dicas auto
/coach config gapo_cooldown:5   # Segundos entre perguntas Gapo
```

## 🐳 Docker

```bash
# Configure .env com DISCORD_TOKEN
docker-compose up -d
```

Inclui:
- **gapo-bot**: Aplicação principal
- **ollama**: Servidor LLM local
- Volumes persistentes para modelos e dados

## 📁 Estrutura de Dados

```
data/
├── champions/           # Base de conhecimento
│   ├── matchups.json    # Matchups específicos
│   ├── builds.json      # Builds por champion
│   ├── counters.json    # Counters por champion
│   └── powerspikes.json # Powerspikes por champion
├── prompts/             # Templates de prompt versionados
│   ├── event_coach_v1.yaml
│   └── gapo_coach_v1.yaml
└── roi_presets/         # ROIs por resolução
    ├── 1920x1080.yaml
    ├── 2560x1440.yaml
    └── 3840x2160.yaml
```

## 🔧 Desenvolvimento

### Testes
```bash
pytest tests/ -v
pytest tests/unit/ -v
pytest tests/integration/ -v
```

### Linting
```bash
ruff check .
ruff format .
mypy gapo/
```

### Estrutura de Commits
```
feat: nova funcionalidade
fix: correção de bug
refactor: refatoração
docs: documentação
test: testes
chore: manutenção
```

## 📊 Monitoramento

Métricas Prometheus disponíveis em `/metrics`:
- `gapo_capture_frames_total` - Frames capturados
- `gapo_ocr_latency_seconds` - Latência OCR por ROI
- `gapo_llm_latency_seconds` - Latência LLM por modo
- `gapo_tts_latency_seconds` - Latência TTS
- `gapo_active_events` - Eventos ativos por tipo

## ⚠️ Limitações Conhecidas

1. **OCR sensível a patches do LoL** - ROIs podem quebrar após atualizações
2. **Requer LoL em janela sem bordas** - Fullscreen exclusivo não funciona
3. **VRAM limitada** - OCR e TTS rodam no CPU para caber na GTX 1660
4. **Latência ~1-2s** - Evento → Voz no Discord

## 🤝 Contribuindo

1. Fork o projeto
2. Crie branch: `git checkout -b feat/nova-feature`
3. Commit: `git commit -m 'feat: adiciona X'`
4. Push: `git push origin feat/nova-feature`
5. Abra Pull Request

## 📄 Licença

MIT License - veja [LICENSE](LICENSE)

---

**Desenvolvido com ❤️ para a comunidade LoL BR**