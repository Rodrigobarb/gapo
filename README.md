# Gapo - LoL Coach Discord Bot

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
