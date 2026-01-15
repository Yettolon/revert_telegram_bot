from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.bot import EXCHANGE_ENUM_TO_SLUG, EXCHANGE_SLUG_MAP, REVERT_POSITION_RE
from src.config import settings
from src.database.enums import ExchangeEnum, NetworkEnum
from src.database.models import Position, User, user_positions


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


def parse_enum(enum_cls, value):
    try:
        return enum_cls(value)
    except ValueError:
        return None


async def get_user_with_positions(session: AsyncSession, user_id: int) -> User | None:
    """
    Get user with eagerly loaded positions to avoid lazy loading.

    Args:
        session: AsyncSession instance
        user_id: User ID

    Returns:
        User instance with loaded positions or None
    """
    stmt = select(User).where(User.id == user_id).options(selectinload(User.positions))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_positions_count(session: AsyncSession, user_id: int) -> int:
    """
    Get count of user positions efficiently without lazy loading.

    Args:
        session: AsyncSession instance
        user_id: User ID

    Returns:
        Number of positions
    """
    stmt = (
        select(func.count())
        .select_from(user_positions)
        .where(user_positions.c.user_id == user_id)
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


async def get_user_active_positions_count(session: AsyncSession, user_id: int) -> int:
    """
    Get count of active user positions.

    Args:
        session: AsyncSession instance
        user_id: User ID

    Returns:
        Number of active positions
    """
    stmt = (
        select(func.count())
        .select_from(user_positions)
        .where(user_positions.c.user_id == user_id, user_positions.c.is_active == True)
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


async def get_user_positions_stats(session: AsyncSession, user_id: int) -> dict:
    """
    Get comprehensive statistics about user positions.

    Args:
        session: AsyncSession instance
        user_id: User ID

    Returns:
        Dictionary with stats:
        {
            'total': int,
            'active': int,
            'in_range': int,
            'out_of_range': int
        }
    """
    # Get total and active counts
    total_count = await get_user_positions_count(session, user_id)
    active_count = await get_user_active_positions_count(session, user_id)

    # Get in_range count
    stmt_in_range = (
        select(func.count())
        .select_from(user_positions)
        .join(Position, user_positions.c.position_id == Position.id)
        .where(user_positions.c.user_id == user_id, Position.is_in_range == True)
    )
    result_in_range = await session.execute(stmt_in_range)
    in_range_count = result_in_range.scalar() or 0

    return {
        "total": total_count,
        "active": active_count,
        "in_range": in_range_count,
        "out_of_range": total_count - in_range_count,
    }


async def can_user_add_position(session: AsyncSession, user: User) -> tuple[bool, str]:
    """
    Check if user can add more positions based on their subscription.

    Args:
        session: AsyncSession instance
        user: User instance

    Returns:
        Tuple of (can_add: bool, error_message: str)
    """
    from src.database.enums import SubscriptionTierEnum

    positions_count = await get_user_positions_count(session, user.id)

    if user.telegram_id in settings.ADMIN_IDS:
        return True, ""

    if positions_count < user.max_positions:
        return True, ""

    tier = user.effective_subscription_tier

    if tier == SubscriptionTierEnum.FREE:
        message = (
            "⚠️ <b>Position limit reached</b>\n\n"
            "You've reached the FREE plan limit (1 position).\n\n"
            "Upgrade to add more positions:\n"
            "⭐ BASIC - 5 positions ($9.99/month)\n"
            "💎 PRO - 10 positions ($19.99/month)\n\n"
            "Use /subscription to upgrade."
        )
    elif tier == SubscriptionTierEnum.BASIC:
        message = (
            "⚠️ <b>Position limit reached</b>\n\n"
            "You've reached your BASIC plan limit (5 positions).\n\n"
            "Upgrade to PRO to track up to 10 positions ($19.99/month).\n\n"
            "Use /subscription to upgrade."
        )
    else:  # PRO
        message = (
            "⚠️ <b>Position limit reached</b>\n\n"
            "You've reached your PRO plan limit (10 positions).\n\n"
            "Please remove some positions to add new ones."
        )

    return False, message


async def get_user_positions_list(
    session: AsyncSession, user_id: int, active_only: bool = False
) -> list[Position]:
    """
    Get list of user positions with all data loaded.

    Args:
        session: AsyncSession instance
        user_id: User ID
        active_only: If True, return only active positions

    Returns:
        List of Position instances
    """
    stmt = (
        select(Position)
        .join(user_positions, user_positions.c.position_id == Position.id)
        .where(user_positions.c.user_id == user_id)
    )

    if active_only:
        stmt = stmt.where(user_positions.c.is_active == True)

    result = await session.execute(stmt)
    return list(result.scalars().all())
