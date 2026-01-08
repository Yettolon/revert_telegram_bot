from urllib.parse import urlparse

from src.bot import EXCHANGE_ENUM_TO_SLUG, EXCHANGE_SLUG_MAP, REVERT_POSITION_RE
from src.config import settings
from src.database.enums import ExchangeEnum, NetworkEnum


def parse_revert_position_url(url: str) -> tuple[ExchangeEnum, NetworkEnum, str]:
    parsed = urlparse(url)

    if parsed.netloc != "revert.finance":
        raise ValueError("Это не ссылка revert.finance")

    fragment = parsed.fragment
    if not fragment:
        raise ValueError("В ссылке отсутствует fragment (#/...)")

    match = REVERT_POSITION_RE.match(fragment)
    if not match:
        raise ValueError("Некорректный формат ссылки")

    exchange_slug = match.group("exchange")
    network_raw = match.group("network")
    nft_id = match.group("nft_id")

    exchange = EXCHANGE_SLUG_MAP.get(exchange_slug)
    if not exchange:
        raise ValueError("Неизвестная биржа")

    try:
        network = NetworkEnum(network_raw)
    except ValueError:
        raise ValueError("Неизвестная сеть")

    return exchange, network, nft_id


def build_revert_position_url(
    exchange: ExchangeEnum, network: NetworkEnum, nft_id: str | int
) -> str:
    exchange_slug = EXCHANGE_ENUM_TO_SLUG.get(exchange)
    if not exchange_slug:
        raise ValueError(f"Error mapping: {exchange}")

    return f"{settings.REVERT_FINANCE_URL}/#/{exchange_slug}-position/{network.value}/{nft_id}"
