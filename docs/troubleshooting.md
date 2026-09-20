# Troubleshooting - Gapo

## Problemas Comuns

### 1. Captura de Tela

#### "DXCam falhou, caindo para MSS"
**Sintoma**: Log mostra fallback para MSS
**Causa**: dxcam não consegue hook no jogo
**Solução**:
- Execute LoL em **Modo Janela Sem Bordas** (Borderless Windowed)
- Não use Fullscreen Exclusivo
- Resolução deve matchar a do Windows
- Tente: `GAPO_CAPTURE_USE_DXCAM=false` no .env

#### "Frame capturado é todo preto"
**Sintoma**: OCR retorna vazio, frames pretos
**Causa**: Proteção anti-cheat ou fullscreen exclusivo
**Solução**:
- Borderless Windowed obrigatório
- Desative "Modo de Tela Cheia Otimizado" no Windows:
  - Propriedades do LeagueClient.exe → Compatibilidade → Desmarcar "Modo de tela cheia otimizado"
- Tente capturar monitor específico: `GAPO_CAPTURE_MONITOR_INDEX=1`

#### FPS muito baixo (<1)
**Sintoma**: Log mostra FPS < 1
**Causa**: dxcam/mss lento ou GPU ocupada
**Solução**:
- Reduza `GAPO_CAPTURE_FPS=2`
- Feche outros apps pesados (OBS, navegador)
- Verifique `nvidia-smi` - GPU não deve estar em 100%

---

### 2. OCR

#### "OCR não lê nada / lê lixo"
**Sintoma**: ParsedHUD vazio ou valores absurdos
**Causa**: ROIs desalinhados para sua resolução
**Solução**:
```bash
gapo calibrate
# Ou
python -m scripts.calibrate_roi --width 1920 --height 1080
```

#### "HP/Mana sempre 0"
**Causa**: ROI do HUD errado ou pré-processamento falhando
**Debug**:
```python
# Teste manual
from gapo.infrastructure.ocr import PaddleEngine, Preprocessor
from gapo.models.ocr import UIRoi
import cv2

img = cv2.imread("test_hud.png")
roi = UIRoi("hud_hp", 15, 15, 180, 35)
preprocessor = Preprocessor()
processed = preprocessor.process(img, roi, method="hud")
engine = PaddleEngine()
results = engine.recognize(processed, "hud_hp")
print(results)
```

#### "Chat não detecta mensagens"
**Causa**: ROI do chat errado ou fundo transparente
**Solução**:
- Ajuste ROI do chat na calibração
- Tente método "chat" no pré-processador (inverte cores)

#### "Minimapa não detecta inimigos"
**Causa**: Minimapa muito pequeno ou ícones diferentes
**Workaround**: Use apenas HUD + eventos baseados em HP/level

---

### 3. LLM (Ollama)

#### "Ollama connection refused"
**Sintoma**: `httpx.ConnectError` ao chamar LLM
**Solução**:
```bash
# Verifique se rodando
ollama serve

# Verifique porta
curl http://localhost:11434/api/tags
```

#### "Model not found"
**Sintoma**: `ollama.ResponseError: model not found`
**Solução**:
```bash
ollama pull qwen2.5:7b-instruct-q4_K_M
# Ou configure outro modelo no .env
GAPO_MODEL_LLM_NAME=qwen2.5:3b-instruct-q4_K_M
```

#### "VRAM OOM / CUDA out of memory"
**Sintoma**: Erro de memória GPU
**Soluções**:
1. Reduza context: `GAPO_MODEL_LLM_CTX_SIZE=1024`
2. Use modelo menor: `qwen2.5:3b-instruct-q4_K_M` (~2GB VRAM)
3. Quantização mais agressiva: `qwen2.5:7b-instruct-q3_K_M`
4. Offload layers: `GAPO_MODEL_LLM_NUM_GPU_LAYERS=20` (parcial CPU)

#### "Resposta muito lenta (>5s)"
**Sintoma**: LLM demora muito
**Soluções**:
- Reduza `num_ctx` para 1024
- Reduza `max_tokens` para 80
- Use `--num-gpu-layers -1` (tudo na GPU)
- Verifique se não está swapping RAM

---

### 4. TTS (Piper)

#### "Piper model not found"
**Sintoma**: `FileNotFoundError` ao sintetizar
**Solução**:
```bash
piper --download-model pt_BR-faber-medium
# Ou modelo alternativo
piper --download-model pt_BR-cassi-medium
```

#### "Áudio não sai no Discord"
**Sintoma**: Bot conectado mas sem som
**Verificações**:
1. Bot tem permissão "Falar" no canal
2. `GAPO_DISCORD_VOICE_CHANNEL_ID` correto (se configurado)
3. Opuslib instalado: `pip install opuslib`
4. FFmpeg no PATH

#### "Voz robótica / ruim"
**Soluções**:
- Tente modelo `pt_BR-cassi-medium` (voz feminina)
- Ajuste `length_scale`: 1.0 = normal, 0.9 = mais rápido, 1.1 = mais lento
- `noise_scale`: 0.667 padrão, 0.5 = menos variação

---

### 5. Discord Bot

#### "Bot não responde a comandos"
**Sintoma**: `/coach` não aparece ou não funciona
**Verificações**:
1. `DISCORD_APPLICATION_ID` correto no .env
2. Bot tem escopo `applications.commands` no OAuth2
3. Slash commands sincronizados: log mostra "Slash commands synced"
4. Permissões do bot no servidor: `Use Slash Commands`

#### "Gapo não responde no chat"
**Sintoma**: Digita "Gapo ..." mas nada acontece
**Verificações**:
1. `message_content` intent habilitado no Developer Portal
2. Bot vê a mensagem (log: "Gapo question from...")
3. Cooldown não excedido (padrão 10s por usuário)
4. Bot não está mutado no voice

#### "Bot desconecta do voice aleatoriamente"
**Sintoma**: Desconecta sozinho durante partida
**Causas**:
- Internet instável
- Discord rate limit
- Voice region issues
**Mitigação**: Reconexão automática implementada, verifique logs

---

### 6. Performance

#### "Sistema travando / FPS jogo caindo"
**Sintoma**: LoL fica laggy com Gapo rodando
**Soluções**:
1. `GAPO_CAPTURE_FPS=2` ou `1`
2. `GAPO_OCR_USE_GPU=false` (já é padrão)
3. Feche Chrome/OBS/Discord desktop
4. Use `powercfg /setactive SCHEME_MIN` (modo performance Windows)

#### "RAM subindo constantemente"
**Sintoma**: Memória crescendo sem parar
**Causa**: Memory leak no history buffer ou cache
**Verificação**:
```python
# Verifique tamanho do history
len(game_state_service.history._states)  # Deve ser < 100
```
**Fix**: Reiniciar bot periodicamente ou implementar cleanup mais agressivo

---

### 7. Modelos e Atualizações

#### "Patch do LoL quebrou OCR"
**Sintoma**: Após update do LoL, OCR para de funcionar
**Solução Rápida**:
```bash
gapo calibrate
# Recalibra ROIs para nova UI
```

**Solução Definitiva**:
1. Atualize `data/roi_presets/{resolution}.yaml`
2. Commit e deploy

#### "Conhecimento desatualizado (patch novo)"
**Sintoma**: Dicas erradas sobre items/champions novos
**Solução**:
```bash
# Atualize data/champions/
# builds.json, counters.json, matchups.json, powerspikes.json
# Use dados do U.GG, OP.GG, LoLalytics
```

---

## Logs e Debug

### Níveis de Log
```bash
# Debug detalhado
GAPO_LOG_LEVEL=DEBUG gapo run

# Apenas erros
GAPO_LOG_LEVEL=ERROR gapo run
```

### Logs Estruturados
```bash
# Ver últimas 50 linhas
tail -50 logs/gapo_$(date +%Y-%m-%d).log

# Filtrar por componente
grep "ocr_service" logs/gapo_$(date +%Y-%m-%d).log

# Ver erros
grep "ERROR" logs/gapo_error_$(date +%Y-%m-%d).log
```

### Métricas Prometheus
```bash
# Scrape manual
curl http://localhost:9090/metrics | grep gapo
```

---

## Comandos de Diagnóstico

```bash
# Verificação completa
python -m scripts.doctor

# Testar componentes isolados
python -m gapo.infrastructure.capture.dxcam_backend
python -m gapo.infrastructure.ocr.paddle_engine
python -m gapo.infrastructure.ollama.client
python -m gapo.infrastructure.piper.engine

# Verificar VRAM
nvidia-smi -l 1
```

---

## Contato e Suporte

- **Issues**: GitHub Issues do repositório
- **Logs para debug**: Anexe `logs/gapo_*.log` e `logs/gapo_error_*.log`
- **Info do sistema**: `python -m scripts.doctor` output