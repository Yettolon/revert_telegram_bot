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


class SubscriptionTierEnum(str, enum.Enum):
    """Subscription tiers with position limits"""

    FREE = "FREE"  # 1 position
    BASIC = "BASIC"  # 5 positions
    PRO = "PRO"  # 10 positions
