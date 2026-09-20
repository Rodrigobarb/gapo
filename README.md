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
```

### 2. Inicialize (baixa tudo)
```bash
python scripts/bootstrap.py
```

`bootstrap.py` só usa a stdlib: instala o projeto (`pip install -e .`) e em
seguida chama `gapo init`. Se o comando `gapo` já existe, pule direto para:

```bash
gapo init
```

O `init` é idempotente — o que já estiver no lugar é pulado — e faz:

| Passo | O que baixa/cria |
|-------|------------------|
| Estrutura local | `logs/`, `config/config.yaml`, `data/cache/` e o `.env` |
| Dependências Python | `pip install -e .` |
| LLM | sobe o Ollama e baixa **Qwen2.5-7B-Instruct-Q4_K_M** (~4.2GB) |
| TTS | voz Piper **pt_BR-faber-medium** (~63MB) |
| Visão | exporta **YOLOv8n ONNX** (~3MB, opcional) |

Opções: `--skip-deps`, `--skip-ollama`, `--skip-piper`, `--skip-yolo`,
`--install-ollama` (instala o Ollama via winget no Windows), `--dev`,
`--no-check`.

### 3. Confira o ambiente
```bash
gapo doctor
```

Verifica Python, GPU/VRAM, dependências, arquivos de dados, `.env`, token do
Discord, servidor Ollama, modelo LLM, voz Piper, YOLO e Opus. Não baixa nada:
aponta o que falta, diz o que `gapo init` resolve sozinho e o que precisa de
você. Sai com código 1 se houver falha — use `--json` em scripts/CI.

### 4. Configure o Discord
Edite o `.env` criado pelo init:
```env
DISCORD_TOKEN=seu_token_aqui
DISCORD_APPLICATION_ID=seu_app_id
```

### 5. Execute
```bash
gapo run
```
