"""OpenAI-compatible async LLM helpers for the public evaluation scripts.

Credentials are read from environment variables. Do not commit API keys.
"""

import asyncio
import json
import os
from typing import Any

try:
    import httpx
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - depends on user environment
    httpx = None
    AsyncOpenAI = None


def get_openai_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing API key. Please set OPENAI_API_KEY.")
    return api_key


class GPT:
    def __init__(self, base_url: str = "https://yunwu.ai/v1", api_key: str | None = None):
        if httpx is None or AsyncOpenAI is None:
            raise ImportError("Please install required dependencies: pip install openai httpx")
        api_key = api_key or get_openai_key()
        self._httpx_client = httpx.AsyncClient(
            base_url=base_url,
            follow_redirects=True,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
        # AsyncOpenAI 接受 httpx.AsyncClient
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, http_client=self._httpx_client)

    async def generate(self, messages, model: str = "gpt-5-nano", max_retries: int = 2, backoff: float = 1.0):
        """
        异步生成，返回字符串（尽量与原 generate 保持一致）
        """
        attempt = 0
        last_exc = None
        while attempt <= max_retries:
            try:
                # 注意：OpenAI Async 接口这里使用 create（不是 acreate）
                completion = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"}
                )
                # 兼容各种返回格式
                content = None
                if hasattr(completion, "choices") and completion.choices:
                    choice = completion.choices[0]
                    # 有些 SDK 把内容放在 choice.message.content
                    if getattr(choice, "message", None) is not None:
                        content = choice.message.content
                    # 或者直接在 choice.text
                    elif getattr(choice, "text", None) is not None:
                        content = choice.text
                # fallback: 直接尝试解析为 dict->string
                if content is None:
                    content = str(completion)

                content = content.strip() if isinstance(content, str) else json.dumps(content, ensure_ascii=False)

                if content == "broken":
                    # 简单重试策略
                    attempt += 1
                    await asyncio.sleep(backoff * attempt)
                    continue

                return content

            except Exception as e:
                last_exc = e
                # 简单指数回退
                attempt += 1
                if attempt > max_retries:
                    return f"Error: {type(e).__name__} - {e}"
                await asyncio.sleep(backoff * attempt)

        # 如果循环结束仍未成功
        return f"Error: RetryFailed - {last_exc}"

    async def aclose(self):
        try:
            await self._httpx_client.aclose()
        except Exception:
            pass


async def parse_llm_response(model_name: str, response: Any) -> dict[str, Any] | str:
    """Parse a model response that should contain one JSON object.

    Returns an empty string on failure to match the behavior of the internal
    scripts this public version was derived from.
    """
    if isinstance(response, dict):
        return response

    try:
        text = str(response).strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or start >= end:
            return ""

        return json.loads(text[start : end + 1])
    except Exception:
        return ""
