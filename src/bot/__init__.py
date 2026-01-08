import re

from src.database.enums import ExchangeEnum

EXCHANGE_SLUG_MAP = {
    "uniswap": ExchangeEnum.uniswapv3,
    "uniswapv4": ExchangeEnum.uniswapv4,
    "pancake": ExchangeEnum.pancakeswap,
    "aerodrome": ExchangeEnum.aerodrome,
}

EXCHANGE_ENUM_TO_SLUG = {
    ExchangeEnum.uniswapv3: "uniswap",
    ExchangeEnum.uniswapv4: "uniswapv4",
    ExchangeEnum.pancakeswap: "pancake",
    ExchangeEnum.aerodrome: "aerodrome",
}


REVERT_POSITION_RE = re.compile(
    r"^/(?P<exchange>[a-z0-9]+)-position/"
    r"(?P<network>[a-z0-9]+)/"
    r"(?P<nft_id>\d+)$"
)
