'Shared types and config between the discord automation and the reader service.'
import tomllib
from typing import TypedDict, cast

class Status:
    Online = 'Online'
    Away = 'Away'
    Dnd = 'Dnd'
    Invisible = 'Invisible'
    Custom = 'Custom'

class DiscordSideConfig(TypedDict):
    reader_address: str

class ReaderSideConfig(TypedDict):
    pins: dict[str, str] # { status: pin }
    port: int
    night_start_hour: int
    night_end_hour: int

class Config(TypedDict):
    discord_side: DiscordSideConfig
    reader_side: ReaderSideConfig
    cards: dict[str, str] # { status: card }

config = cast(Config, tomllib.load(open('config.toml', 'rb')))

_card_to_status = {card: status for status, card in config['cards'].items() }

def card_to_status(uid: str) -> str|None:
    return _card_to_status.get(uid, None)

def status_to_card(status: str) -> str|None:
    return config['cards'].get(status, None)