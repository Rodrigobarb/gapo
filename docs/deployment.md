# Guia de Deploy - Gapo

## Requisitos de Hardware

### Mínimo
- GPU: GTX 1660 6GB VRAM
- RAM: 16GB
- CPU: 6 cores (Ryzen 5 / i5 10th gen+)
- Armazenamento: 15GB livres (modelos + logs)
- OS: Windows 10/11 ou Linux (Ubuntu 22.04+)

### Recomendado
- GPU: RTX 3060 12GB+ VRAM
- RAM: 32GB
- CPU: 8+ cores
- NVMe SSD

## Instalação Windows (Nativo)

### 1. Python 3.11+
```powershell
winget install Python.Python.3.11
```

### 2. Ollama
```powershell
winget install Ollama.Ollama
ollama serve  # Em terminal separado
```

### 3. Dependências do Sistema
```powershell
# Visual C++ Redistributable (para dxcam)
winget install Microsoft.VCRedist.2015+

# FFmpeg (para áudio)
winget install Gyan.FFmpeg
```

### 4. Projeto
```powershell
git clone <repo>
cd gapo
python -m venv venv
venv\Scripts\activate
pip install -e .[dev]
```

### 5. Inicialização
```powershell
gapo init
# ou
python -m scripts.init_gapo
```

### 6. Configuração Discord
```powershell
copy .env.example .env
# Edite .env com seu token
```

### 7. Execução
```powershell
gapo run
```

## Instalação Linux (Ubuntu 22.04+)

### 1. Dependências
```bash
sudo apt update && sudo apt install -y \
    python3.11 python3.11-venv python3.11-dev \
    ffmpeg libgl1-mesa-glx libglib2.0-0 \
    nvidia-driver-535 nvidia-container-toolkit
```

### 2. Ollama
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
```

### 3. Projeto
```bash
git clone <repo>
cd gapo
python3.11 -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

### 4. Inicialização
```bash
gapo init
```

### 5. Screen Capture no Linux
Para captura de tela no Linux, configure:
```bash
# Permitir captura de tela
sudo usermod -a -G video $USER
# Reinicie sessão
```

Ou use Docker (recomendado no Linux).

## Docker Deploy (Recomendado para Produção)

### 1. Pré-requisitos
- Docker 24+
- Docker Compose 2+
- NVIDIA Container Toolkit

### 2. Configuração
```bash
cp .env.example .env
# Edite .env com DISCORD_TOKEN
```

### 3. Build e Execução
```bash
docker-compose up -d --build
```

### 4. Logs
```bash
docker-compose logs -f gapo
docker-compose logs -f ollama
```

### 5. Parar
```bash
docker-compose down
```

## Configuração de Resolução

### Presets Inclusos
- `1920x1080.yaml` (padrão)
- `2560x1440.yaml`
- `3840x2160.yaml`

### Calibração Personalizada
```bash
# No Windows/Linux nativo
gapo calibrate

# Ou script direto
python -m scripts.calibrate_roi --width 1920 --height 1080
```

Isso abre janela interativa - clique e arraste sobre cada elemento do HUD.

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DISCORD_TOKEN` | **obrigatório** | Token do bot Discord |
| `DISCORD_APPLICATION_ID` | - | Application ID para slash commands |
| `GAPO_MODEL_LLM_NAME` | `qwen2.5:7b-instruct-q4_K_M` | Modelo Ollama |
| `GAPO_MODEL_TTS_MODEL` | `pt_BR-faber-medium` | Modelo Piper |
| `GAPO_CAPTURE_FPS` | `3` | FPS de captura |
| `GAPO_LOG_LEVEL` | `INFO` | Nível de log |
| `GAPO_COACH_EVENT_COOLDOWN_SECONDS` | `5.0` | Cooldown dicas auto |
| `GAPO_COACH_GAPO_COOLDOWN_SECONDS` | `10.0` | Cooldown perguntas Gapo |

## Troubleshooting

### "DXCam falhou, caindo para MSS"
- Normal no Windows se dxcam não conseguir hook
- MSS é mais lento mas funciona

### "Ollama connection refused"
```bash
ollama serve
# Verifique se porta 11434 está livre
```

### "Piper model not found"
```bash
piper --download-model pt_BR-faber-medium
```

### "VRAM OOM"
- Reduza `GAPO_CAPTURE_FPS` para 2
- Use modelo menor: `qwen2.5:3b-instruct-q4_K_M`
- Verifique `nvidia-smi` durante execução

### "OCR não lê nada"
- Calibre ROIs: `gapo calibrate`
- Verifique se LoL está em **janela sem bordas**
- Resolução deve matchar preset

### "Bot não entra no voice"
- Verifique permissões do bot no servidor
- Intents: `voice_states`, `message_content`, `guilds`
- Token correto no `.env`

## Atualização de Modelos

```bash
# Novo modelo LLM
ollama pull qwen2.5:7b-instruct-q4_K_M

# Novo modelo TTS
piper --download-model pt_BR-cassi-medium

# Atualizar YOLO
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt').export(format='onnx')"
```

## Backup e Restore

### Dados Importantes
```bash
# Backup
tar -czf gapo-backup-$(date +%Y%m%d).tar.gz \
    data/champions/ \
    data/prompts/ \
    data/roi_presets/ \
    config/config.yaml \
    .env
```

### Restore
```bash
tar -xzf gapo-backup-20240115.tar.gz
```

## Monitoramento

### Métricas Prometheus
```bash
# Scrape config
- job_name: 'gapo'
  static_configs:
    - targets: ['localhost:9090']
```

### Logs
```bash
# Tempo real
tail -f logs/gapo_$(date +%Y-%m-%d).log

# Erros apenas
tail -f logs/gapo_error_$(date +%Y-%m-%d).log
```

## Segurança

- Nunca commite `.env` ou tokens
- Use secrets do Docker em produção
- Mantenha Ollama sem exposição externa (apenas localhost)
- Discord token com permissões mínimas necessárias