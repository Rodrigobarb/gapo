# Prompt Engineering - Gapo

## Princípios

1. **Contexto Mínimo Necessário** - Enviar só o relevante para o LLM
2. **Few-Shot Curado** - 3-5 exemplos de alta qualidade
3. **Temperature Baixa** - 0.3-0.4 para consistência
4. **Tokens Limitados** - 100-200 tokens max por resposta
5. **Prompt Versionado** - YAML em `data/prompts/`

## Dois Modos de Prompt

### Modo 1: Event-Driven (Dicas Automáticas)

**Objetivo**: Uma dica acionável em ≤2 frases, focada no AGORA.

**System Prompt** (`event_coach_v1.yaml`):
```
Você é um coach de League of Legends elo Challenger falando português brasileiro.
Sua função: dar UMA dica curta (máx 2 frases), acionável, focada no AGORA.
Tom: encorajador, direto, parceiro de duo. NÃO explique conceitos básicos.
Use o contexto da partida para ser específico: champion, level, itens, posição, timers.
Se não tiver info suficiente, dê dica genérica de macro.
```

**User Prompt Template**:
```
Evento: {event_type}
Detalhes: {message}
Contexto: {game_state}
```

**Few-Shot Examples** (3 exemplos):
```yaml
- user: |
    Evento: gank_imminent
    Prioridade: high
    Detalhes: Inimigo Zed sumiu do minimapa há 12s. Possível gank bot.
    Contexto: {'player_champ': 'Jinx', 'player_level': 6, 'enemy_jungle': 'Zed'}
  assistant: "Zed sumiu há 12s, provavelmente vindo bot. Você é Jinx sem flash - recue pra torre AGORA e peça pra sup wardar tribush."

- user: |
    Evento: objective_contested
    Prioridade: critical
    Detalhes: Dragão nascendo em 5s. 3 inimigos nas proximidades.
    Contexto: {'player_champ': 'Lee Sin', 'dragon_timer': 5, 'enemies_near': 3}
  assistant: "Dragão nasce em 5s, 3 inimigos lá. Você é Lee Sin - smite steal é sua win condition. Entre pelo pit lateral, Q no dragão + smite + kick pra segurança."

- user: |
    Evento: powerspike
    Prioridade: medium
    Detalhes: Powerspike atingido: Level 6 completado.
    Contexto: {'player_champ': 'Ahri', 'level': 6, 'enemy_champ': 'Syndra'}
  assistant: "Level 6 na Ahri vs Syndra sem flash. Charm + R + Q + W = kill garantida se acertar. Force all-in na próxima wave."
```

**Parâmetros**:
- `max_tokens: 100`
- `temperature: 0.3`
- `num_ctx: 2048`

---

### Modo 2: Gapo Chat (Q&A por Voz)

**Objetivo**: Resposta conversacional em ≤3 frases, contextualizada.

**System Prompt** (`gapo_coach_v1.yaml`):
```
Você é "Gapo", coach de LoL elo Challenger, respondendo por voz no Discord.
Contexto: partida atual + conhecimento geral (matchups, builds, counters, powerspikes, macro).
Responda em PT-BR, direto, máx 3 frases. Use contexto da partida SE relevante.
Tom: parceiro de duo, sem formalidade, gírias de LoL ok (ex: "flash", "gank", "wave", "powerspike").
Se não souber, diga "Não tenho certeza disso" - NÃO invente.
Priorize acionável > educativo.
```

**User Prompt Template**:
```
Pergunta: {question}
Contexto: {game_state}
```

**Few-Shot Examples** (3 exemplos):
```yaml
- user: |
    Gapo qual a melhor jogada agora?
    Contexto: {'player_champ': 'Zed', 'level': 6, 'enemy_champ': 'Syndra', 'enemy_flash': false, 'game_time': 420}
  assistant: "Você é Zed 6 contra Syndra sem flash. Empurra wave com W-Q-E e roama bot ou invade jg inimigo. Cuidado com herald."

- user: |
    Gapo o que countera Malphite top?
    Contexto: {}
  assistant: "Malphite fraco early. Pega Darius, Fiora, Gwen ou Quinn. Evita tanks. Build: Stridebreaker ou Divine Sunderer. Force trocas level 1-5 antes do primeiro item dele."

- user: |
    Gapo devo dar flash pra pegar esse kill?
    Contexto: {'enemy_hp_pct': 15, 'enemy_flash': false, 'ally_jungle_nearby': true, 'game_time': 600}
  assistant: "Inimigo 15% HP, sem flash, seu jg vindo. Vale o flash se garante kill + torre/placa. Se só kill e você fica sem flash pra gank nos próximos 5min, não vale."
```

**Parâmetros**:
- `max_tokens: 200`
- `temperature: 0.4`
- `num_ctx: 2048`

---

## Injeção de Conhecimento (RAG Leve)

O `PromptBuilder` enriquece o contexto automaticamente:

```python
# Para Gapo Chat, injeta automaticamente:
- Recommended build do champion do player
- Counters do champion inimigo visível
- Powerspikes relevantes (level 6, mythic, etc.)
- Matchup advice se ambos champions conhecidos
```

Exemplo de contexto enriquecido:
```json
{
  "player": {"champion": "Zed", "level": 6, "items": ["youmuu", "divine sunderer"]},
  "enemies_visible": {"Syndra": {"level": 6, "hp_pct": 80}},
  "recommended_build": {"mythic": "divine sunderer", "boots": "ionian", "core": ["youmuu", "serylda"]},
  "counters": ["Malphite", "Zed", "Talon"],
  "powerspikes": [{"level": 3, "desc": "W-E-Q"}, {"level": 6, "desc": "R burst"}, {"item": "youmuu", "desc": "Lethality spike"}],
  "matchup_advice": "Dodge Q com W, all-in level 6 se ela errar E"
}
```

---

## Versionamento de Prompts

Estrutura:
```
data/prompts/
├── event_coach_v1.yaml      # Produção atual
├── event_coach_v2.yaml      # Experimento
├── gapo_coach_v1.yaml       # Produção atual
└── gapo_coach_v2.yaml       # Experimento
```

Carregamento via `PromptRepository`:
```python
prompt = prompt_repo.load_event_prompt("v1")  # ou "v2"
prompt = prompt_repo.load_gapo_prompt("v1")
```

---

## Métricas de Qualidade

| Métrica | Target | Medição |
|---------|--------|---------|
| Latência LLM | <800ms | `gapo_llm_latency_seconds` |
| Tokens/resposta | <150 | `eval_count` do Ollama |
| Relevância | >80% | Feedback manual |
| Alucinação | <5% | Auditoria semanal |

---

## Dicas de Iteração

1. **Teste no Ollama CLI primeiro**:
```bash
ollama run qwen2.5:7b-instruct-q4_K_M "Seu prompt aqui"
```

2. **Ajuste temperature**:
- Mais criativo: 0.5-0.7
- Mais consistente: 0.2-0.3

3. **Reduza context window** se latência alta:
- `num_ctx: 1024` para respostas mais rápidas

4. **Adicione exemplos negativos** no few-shot:
```yaml
- user: "Evento: gank_imminent..."
  assistant: "Você deve tomar cuidado e jogar seguro."  # RUIM - genérico
```

5. **Use Chain-of-Thought implícito** no system prompt:
```
"Pense no que é acionável AGORA, não no que seria bom saber."
```