from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings


class LLMClientError(RuntimeError):
    pass


class GeminiPlannerClient:
    def __init__(self, api_key: str, model: str, temperature: float = 0.1) -> None:
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    def generate_json_plan(self, prompt: str) -> dict[str, Any]:
        if not self.api_key:
            raise LLMClientError("Missing LLM_API_KEY. Set it in your environment.")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": self.temperature, "responseMimeType": "application/json"},
        }
        with httpx.Client(timeout=40.0) as client:
            response = client.post(url, json=payload)
        if response.status_code >= 400:
            hint = ""
            if response.status_code == 404:
                hint = (
                    " Check LLM_MODEL: use any model `name` from "
                    "GET https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY "
                    "that lists generateContent in supportedGenerationMethods."
                )
            raise LLMClientError(f"Gemini API error {response.status_code}: {response.text}{hint}")
        data = response.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise LLMClientError(f"Unable to parse Gemini JSON response: {exc}") from exc


def get_planner_client() -> GeminiPlannerClient:
    if settings.llm_provider.lower() != "gemini":
        raise LLMClientError(f"Unsupported llm_provider: {settings.llm_provider}")
    if not settings.llm_api_key:
        raise LLMClientError("Missing LLM_API_KEY. Configure .env before querying.")
    if not (settings.llm_model or "").strip():
        raise LLMClientError(
            "Missing LLM_MODEL. Set it in .env to any Gemini model id your API key can call "
            "via generateContent (list models: GET "
            "https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY)."
        )
    return GeminiPlannerClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model.strip(),
        temperature=settings.llm_temperature,
    )
