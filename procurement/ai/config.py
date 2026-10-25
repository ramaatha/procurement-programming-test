# filepath: procurement/ai/config.py
from dataclasses import dataclass
import json
import os
from pathlib import Path


class AIError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class AIConfig:
    api_key: str


def configuration() -> AIConfig | None:
    key = os.environ.get('GROQ_API_KEY','').strip()
    if not key:
        path = Path(os.environ.get('PROCUREMENT_AI_CONFIG',str(Path.home()/'.config/procurement-demo/ai.json')))
        try:
            if path.stat().st_size > 8192:
                return None
            data = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data,dict) or set(data) != {'api_key'}:
                return None
            key = data['api_key']
        except (OSError,ValueError,UnicodeError):
            return None
    if not isinstance(key,str) or not 10 <= len(key) <= 4096 or any(c.isspace() for c in key):
        return None
    return AIConfig(key)
