from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Optional
from urllib import error, request


@dataclass
class Brain:
    """Local LLM brain powered by Ollama."""

    enabled: bool = True
    base_url: str = "http://127.0.0.1:11434"
    model: str = "auto"
    timeout_s: float = 20.0
    debug: bool = False
    system_prompt: str = (
        "You are Jarvis, a concise helpful voice assistant. "
        "Reply in 1-2 short sentences unless the user asks for details."
    )
    active_model: Optional[str] = None

    def _debug(self, message: str) -> None:
        if self.debug:
            print(f"[brain-debug] {message}")

    def _post_json(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url.rstrip('/')}{path}"
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout_s) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}

    def _get_json(self, path: str) -> dict:
        url = f"{self.base_url.rstrip('/')}{path}"
        req = request.Request(url, method="GET")
        with request.urlopen(req, timeout=self.timeout_s) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}

    def _resolve_model(self) -> Optional[str]:
        if self.model != "auto":
            return self.model
        try:
            tags = self._get_json("/api/tags")
            installed = [item.get("name", "") for item in tags.get("models", [])]
            preferred = [
                "qwen2.5:7b-instruct",
                "llama3.1:8b-instruct",
                "mistral:7b-instruct",
                "gemma2:9b",
                "phi3:mini",
            ]
            for candidate in preferred:
                if candidate in installed:
                    return candidate
            if installed:
                return installed[0]
        except Exception as exc:
            self._debug(f"Model discovery failed: {type(exc).__name__}: {exc}")
        return None

    def generate(self, user_text: str, memory_hint: str = "") -> Optional[str]:
        if not self.enabled:
            return None
        if self.active_model is None:
            self.active_model = self._resolve_model()
            if self.active_model:
                self._debug(f"Using Ollama model: {self.active_model}")
            else:
                self._debug("No Ollama model available.")
                return None
        prompt = user_text.strip()
        if memory_hint:
            prompt = f"Recent memory: {memory_hint}\n\nUser: {user_text.strip()}"
        payload = {
            "model": self.active_model,
            "prompt": prompt,
            "system": self.system_prompt,
            "stream": False,
        }
        try:
            data = self._post_json("/api/generate", payload)
            text = str(data.get("response", "")).strip()
            return text if text else None
        except (error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            self._debug(f"Ollama request failed: {type(exc).__name__}: {exc}")
            return None

