from urllib.parse import urlparse

from sqlalchemy import select

from src.bot import EXCHANGE_ENUM_TO_SLUG, EXCHANGE_SLUG_MAP, REVERT_POSITION_RE
from src.config import settings
from src.database.enums import ExchangeEnum, NetworkEnum
from src.database.models import user_positions


def parse_revert_position_url(url: str) -> tuple[ExchangeEnum, NetworkEnum, str]:
    parsed = urlparse(url)

    if parsed.netloc != "revert.finance":
        raise ValueError("This is not a revert.finance URL")

    fragment = parsed.fragment
    if not fragment:
        raise ValueError("The URL is missing a fragment (#/...)")

    match = REVERT_POSITION_RE.match(fragment)
    if not match:
        raise ValueError("Invalid URL format")

    exchange_slug = match.group("exchange")
    network_raw = match.group("network")
    nft_id = match.group("nft_id")

    exchange = EXCHANGE_SLUG_MAP.get(exchange_slug)
    if not exchange:
        raise ValueError("Unknown exchange")

    try:
        network = NetworkEnum(network_raw)
    except ValueError:
        raise ValueError("Unknown network")

    return exchange, network, nft_id


def build_revert_position_url(
    exchange: ExchangeEnum, network: NetworkEnum, nft_id: str | int
) -> str:
    exchange_slug = EXCHANGE_ENUM_TO_SLUG.get(exchange)
    if not exchange_slug:
        raise ValueError(f"Error mapping: {exchange}")

    return f"{settings.REVERT_FINANCE_URL}/#/{exchange_slug}-position/{network.value}/{nft_id}"


async def get_position_active_for_user(
    session,
    user_id: int,
    position_id: int,
) -> bool:
    result = await session.execute(
        select(user_positions.c.is_active).where(
            user_positions.c.user_id == user_id,
            user_positions.c.position_id == position_id,
        )
    )
    return result.scalar_one_or_none() is True
