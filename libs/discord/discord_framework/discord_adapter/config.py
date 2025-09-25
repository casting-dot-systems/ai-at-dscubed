from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(slots=True)
class DiscordConfig:
    bot_token: str
    bot_id: int | None = None
    max_response_length: int = 1999
    last_n_messages: int = 10
    request_timeout_sec: int = 60

    @classmethod
    def from_env(cls) -> "DiscordConfig":
        token = os.getenv("BOT_TOKEN", "")
        bot_id_env = os.getenv("BOT_ID")
        return cls(
            bot_token=token,
            bot_id=int(bot_id_env) if bot_id_env else None,
        )