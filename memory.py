from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ShortMemory:
    messages: list[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.messages.append(message)

    def clear(self) -> None:
        self.messages.clear()

    def recent(self, count: int = 5) -> list[str]:
        return self.messages[-count:]

    def count(self) -> int:
        return len(self.messages)

