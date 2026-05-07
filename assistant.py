from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import random
import re

from brain import Brain
from memory import ShortMemory


@dataclass
class Jarvis:
    """A minimal terminal-based agent scaffold."""

    name: str = "jarvis"
    awake: bool = True
    activated: bool = False
    memory: ShortMemory = field(default_factory=ShortMemory)
    brain: Optional[Brain] = None

    def standby(self) -> str:
        return f"{self.name.title()} in standby. Say 'wake up {self.name}' to activate."

    def wake(self) -> str:
        self.activated = True
        now = datetime.now().strftime("%I:%M %p")
        return f"{self.name.title()} online. Systems restored at {now}."

    def handle(self, user_input: str) -> str:
        message = user_input.strip()
        if not message:
            return "I am listening."

        normalized = message.lower()
        cleaned = re.sub(r"[^a-z0-9\s]", " ", normalized)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        self.memory.add(message)

        if any(word in normalized for word in {"exit", "quit", "shutdown"}):
            self.awake = False
            return "Powering down. Until next time."
        if cleaned in {"help", "commands"}:
            return (
                "Available commands: help, status, memory, clear memory, "
                "time, exit, and natural requests like 'who are you', "
                "'what can you do', 'tell me a joke', or 'motivate me'."
            )
        if cleaned in {"status", "system status"}:
            return (
                f"Status: {'awake' if self.awake else 'sleeping'} | "
                f"Messages in memory: {self.memory.count()}"
            )
        if cleaned in {"memory", "show memory", "short memory", "track short memory"}:
            if self.memory.count() == 0:
                return "Memory is empty."
            return "Recent memory: " + " | ".join(self.memory.recent(5))
        if cleaned in {
            "clear memory",
            "delete memory",
            "reset memory",
            "clean memory",
            "crack short memory",
            "write short memory",
            "track shop memory",
        }:
            self.memory.clear()
            return "Memory cleared."
        if cleaned in {"time", "current time"}:
            return "Current time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if cleaned in {"voice on", "turn voice on", "enable voice"}:
            return "Voice mode enabled."
        if cleaned in {"voice off", "turn voice off", "disable voice"}:
            return "Voice mode disabled."
        if any(word in normalized for word in {"hello", "hi", "hey"}):
            return random.choice(
                [
                    "Hello. Jarvis at your service.",
                    "Hi. Systems are stable and I am ready.",
                    "Hey there. What should I handle next?",
                ]
            )
        if "how are you" in normalized:
            return random.choice(
                [
                    "Operating at optimal efficiency.",
                    "Fully functional and ready to assist.",
                    "All systems nominal. I am doing great.",
                ]
            )
        if "who are you" in normalized or "your name" in normalized:
            return (
                "I am Jarvis, your voice-enabled assistant. "
                "I can listen, respond, and help automate tasks."
            )
        if "what can you do" in normalized or "capabilities" in normalized:
            return (
                "I can respond to voice and text, track short memory, report status and time, "
                "and execute your assistant workflows as we extend features."
            )
        if "thank you" in normalized or cleaned == "thanks":
            return random.choice(
                [
                    "Always a pleasure.",
                    "You're welcome.",
                    "Anytime. Ready for the next task.",
                ]
            )
        if "motivate me" in normalized:
            return random.choice(
                [
                    "Small steps, consistently done, beat big plans that never start.",
                    "You are one focused session away from real progress.",
                    "Discipline today becomes freedom tomorrow. Keep going.",
                ]
            )
        if "tell me a joke" in normalized or cleaned == "joke":
            return random.choice(
                [
                    "Why do programmers prefer dark mode? Because light attracts bugs.",
                    "I told my CPU a joke. It still needs time to process it.",
                    "I would tell you a UDP joke, but you might not get it.",
                ]
            )
        if "good morning" in normalized:
            return "Good morning. Let us make today productive."
        if "good night" in normalized:
            return "Good night. I will remain on standby."
        if "what time" in normalized:
            return "Current time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.brain is not None and self.brain.enabled:
            llm_reply = self.brain.generate(
                message, memory_hint=" | ".join(self.memory.recent(5))
            )
            if llm_reply:
                return llm_reply

        return f"Understood: '{message}'. I can help expand this behavior next."

