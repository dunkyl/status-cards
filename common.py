import tomllib
from typing import TypedDict, cast, Literal as L

Config = TypedDict('Config', {
    'discord_side': TypedDict('', { 'reader_address': str }),
    'reader_side': TypedDict('', { 'pins': dict[str, str] }),
    'cards': dict[str, str]
    },total=True)

config = cast(Config, tomllib.load(open('config.toml', 'rb')))

_card_to_status = {card: status for status, card in config['cards'].items() }

def card_to_status(uid: str) -> str|None:
    return _card_to_status.get(uid, None)