import enum


class ExchangeEnum(str, enum.Enum):
    uniswapv3 = "uniswapv3"
    uniswapv4 = "uniswapv4"
    pancakeswap = "pancakeswap"
    aerodrome = "aerodrome"


class NetworkEnum(str, enum.Enum):
    mainnet = "mainnet"
    optimism = "optimism"
    unichain = "unichain"
    polygon = "polygon"
    bnb = "bnb"
    base = "base"
    arbitrum = "arbitrum"
