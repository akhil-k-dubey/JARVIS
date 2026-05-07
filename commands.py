from __future__ import annotations

from difflib import SequenceMatcher
import re


def is_shutdown_command(text: str) -> bool:
    normalized = text.strip().lower()
    return any(word in normalized for word in {"exit", "quit", "shutdown"})


def is_wake_command(text: str, assistant_name: str) -> bool:
    normalized = text.strip().lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", normalized)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    name = assistant_name.lower()

    def name_matches(spoken_name: str) -> bool:
        candidate = spoken_name.strip()
        if not candidate:
            return False
        if candidate == name:
            return True
        return SequenceMatcher(None, candidate, name).ratio() >= 0.72

    wake_up_prefix = "wake up "
    hey_prefix = "hey "
    come_online_suffix = " come online"

    if cleaned.startswith(wake_up_prefix):
        return name_matches(cleaned[len(wake_up_prefix) :])
    if cleaned.startswith(hey_prefix):
        return name_matches(cleaned[len(hey_prefix) :])
    if cleaned.endswith(come_online_suffix):
        return name_matches(cleaned[: -len(come_online_suffix)])
    return False

