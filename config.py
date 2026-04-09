"""간단한 JSON 기반 설정 저장소."""
import json
from pathlib import Path

CONFIG_PATH = Path.home() / ".ft_messenger_config.json"

DEFAULTS = {
    "api_key": "",
    "provider": "claude",  # 'claude' | 'openai' | 'gemini'
    "relation": "친구",
    "hotkey": "ctrl+shift+space",
    # 프로바이더별 모델 오버라이드 (비우면 llm.DEFAULT_MODELS 사용)
    "model_claude": "",
    "model_openai": "",
    "model_gemini": "",
}


class Config:
    def __init__(self):
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        if CONFIG_PATH.exists():
            try:
                loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.data.update(loaded)
            except Exception:
                pass

    def save(self):
        try:
            CONFIG_PATH.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[config] save failed: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
