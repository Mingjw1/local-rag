"""Ollama API 客户端"""

import json
from typing import AsyncGenerator

import httpx

from app.core.config import settings


class OllamaClient:
    """与本地 Ollama 服务通信"""

    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.client = httpx.AsyncClient(timeout=120.0)

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        """获取文本的 embedding 向量"""
        model = model or settings.ollama_embedding_model
        resp = await self.client.post(
            f"{self.base_url}/api/embeddings",
            json={"model": model, "prompt": text},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["embedding"]

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        """批量获取 embedding（Ollama 不支持原生 batch，逐个调用）"""
        results = []
        for text in texts:
            vec = await self.embed(text, model)
            results.append(vec)
        return results

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        model: str | None = None,
        stream: bool = False,
        temperature: float = 0.3,
    ) -> str | AsyncGenerator[str, None]:
        """生成文本"""
        model = model or settings.ollama_generation_model
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system

        if stream:
            return self._stream_generate(payload)
        else:
            resp = await self.client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json()["response"]

    async def _stream_generate(self, payload: dict) -> AsyncGenerator[str, None]:
        async with self.client.stream("POST", f"{self.base_url}/api/generate", json=payload) as resp:
            async for line in resp.aiter_lines():
                if line.strip():
                    data = json.loads(line)
                    yield data.get("response", "")
                    if data.get("done", False):
                        break

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = False,
        temperature: float = 0.3,
    ) -> str | AsyncGenerator[str, None]:
        """聊天补全"""
        model = model or settings.ollama_generation_model
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {"temperature": temperature},
        }

        if stream:
            return self._stream_chat(payload)
        else:
            resp = await self.client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def _stream_chat(self, payload: dict) -> AsyncGenerator[str, None]:
        async with self.client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
            async for line in resp.aiter_lines():
                if line.strip():
                    data = json.loads(line)
                    if msg := data.get("message", {}).get("content", ""):
                        yield msg
                    if data.get("done", False):
                        break

    async def check_health(self) -> bool:
        """检查 Ollama 服务是否可用"""
        try:
            resp = await self.client.get(f"{self.base_url}/api/tags")
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()


ollama_client = OllamaClient()
