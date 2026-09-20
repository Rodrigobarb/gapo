import ollama
import asyncio
from typing import AsyncGenerator
from gapo.core.logging import get_logger
from gapo.models.coach import CoachPrompt, CoachResponse, CoachMode
from gapo.core.metrics import llm_requests_total, llm_latency_seconds
import time

logger = get_logger("ollama_client")


class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen2.5:7b-instruct-q4_K_M"):
        self.client = ollama.AsyncClient(host=host)
        self.model = model
        self._model_loaded = False

    async def ensure_model(self) -> bool:
        try:
            listagem = await self.client.list()
            nomes = _model_names(listagem)
            alvo = self.model if ":" in self.model else f"{self.model}:latest"
            if not {self.model, alvo} & set(nomes):
                logger.info(f"Pulling model {self.model}...")
                await self.client.pull(self.model)
            self._model_loaded = True
            return True
        except Exception as e:
            logger.error(f"Failed to ensure model: {e}")
            return False

    async def generate(self, prompt: CoachPrompt) -> CoachResponse:
        start = time.monotonic()
        try:
            messages = prompt.to_messages()
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "num_ctx": prompt.context.get("ctx_size", 2048),
                    "temperature": prompt.temperature,
                    "num_predict": prompt.max_tokens,
                },
            )
            latency = (time.monotonic() - start) * 1000
            llm_requests_total.labels(mode=prompt.mode.value, status="success").inc()
            llm_latency_seconds.labels(mode=prompt.mode.value).observe(latency / 1000)

            text = response["message"]["content"].strip()
            return CoachResponse(
                text=text,
                mode=prompt.mode,
                latency_ms=int(latency),
                tokens_used=response.get("eval_count", 0),
                raw_response=text,
            )
        except Exception as e:
            llm_requests_total.labels(mode=prompt.mode.value, status="error").inc()
            logger.error(f"LLM generation failed: {e}")
            return CoachResponse(
                text="Erro ao gerar resposta. Tente novamente.",
                mode=prompt.mode,
                latency_ms=int((time.monotonic() - start) * 1000),
            )

    async def generate_stream(self, prompt: CoachPrompt) -> AsyncGenerator[str, None]:
        try:
            messages = prompt.to_messages()
            stream = await self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "num_ctx": prompt.context.get("ctx_size", 2048),
                    "temperature": prompt.temperature,
                    "num_predict": prompt.max_tokens,
                },
                stream=True,
            )
            async for chunk in stream:
                if chunk["message"]["content"]:
                    yield chunk["message"]["content"]
        except Exception as e:
            logger.error(f"LLM stream failed: {e}")
            yield "Erro na geração."

    async def health_check(self) -> bool:
        try:
            await self.client.list()
            return True
        except Exception:
            return False


def _model_names(listagem) -> list[str]:
    """Nomes dos modelos, tolerando as duas formas do cliente Ollama.

    Ate a 0.3 o list() devolvia dicts com a chave "name"; das 0.4 em diante sao
    objetos ListResponse.Model com o atributo `model`.
    """
    modelos = getattr(listagem, "models", None)
    if modelos is None and isinstance(listagem, dict):
        modelos = listagem.get("models", [])
    nomes = []
    for m in modelos or []:
        if isinstance(m, dict):
            nome = m.get("name") or m.get("model") or ""
        else:
            nome = getattr(m, "model", "") or getattr(m, "name", "")
        if nome:
            nomes.append(nome)
    return nomes
