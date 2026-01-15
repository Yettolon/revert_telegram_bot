"""
Subscription service for managing user subscriptions.
"""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.constance import get_subscription_price
from src.database.enums import SubscriptionTierEnum
from src.database.models import User


async def activate_subscription(
    session: AsyncSession, user: User, tier: SubscriptionTierEnum, extend: bool = False
) -> User:
    """
    Activate or extend user subscription.

    Args:
        session: Database session
        user: User instance
        tier: Subscription tier to activate
        extend: If True, extend existing subscription; if False, replace it

    Returns:
        Updated user instance
    """
    if tier == SubscriptionTierEnum.FREE:
        user.subscription_tier = SubscriptionTierEnum.FREE
        user.subscription_expires_at = None
        await session.commit()
        return user

    price_info = get_subscription_price(tier)

    # Calculate expiration date
    if (
        extend
        and user.subscription_expires_at
        and user.subscription_expires_at > datetime.now()
    ):
        # Extend from current expiration date
        expiration_date = user.subscription_expires_at + timedelta(
            days=price_info.duration_days
        )
    else:
        # Start from now
        expiration_date = datetime.now() + timedelta(days=price_info.duration_days)

    user.subscription_tier = tier
    user.subscription_expires_at = expiration_date

    await session.commit()
    await session.refresh(user)

    return user


async def check_and_downgrade_expired_subscriptions(session: AsyncSession) -> int:
    """
    Check all users and downgrade expired subscriptions to FREE.
    Should be run periodically (e.g., daily cron job).

    Returns:
        Number of subscriptions downgraded
    """
    now = datetime.now()

    # Find users with expired subscriptions
    stmt = select(User).where(
        User.subscription_tier != SubscriptionTierEnum.FREE,
        User.subscription_expires_at < now,
    )

    result = await session.execute(stmt)
    expired_users = result.scalars().all()

    count = 0
    for user in expired_users:
        user.subscription_tier = SubscriptionTierEnum.FREE
        user.subscription_expires_at = None
        count += 1

    await session.commit()

    return count


async def get_subscription_stats(session: AsyncSession) -> dict:
    """
    Get subscription statistics for admin dashboard.

    Returns:
        Dictionary with subscription statistics
    """
    from sqlalchemy import func

    # Count users by tier
    stmt = select(User.subscription_tier, func.count(User.id)).group_by(
        User.subscription_tier
    )

    result = await session.execute(stmt)
    tier_counts = dict(result.all())

    # Count active paid subscriptions
    stmt_active = select(func.count(User.id)).where(
        User.subscription_tier != SubscriptionTierEnum.FREE,
        User.subscription_expires_at > datetime.now(),
    )

    result_active = await session.execute(stmt_active)
    active_paid = result_active.scalar() or 0

    return {
        "free": tier_counts.get(SubscriptionTierEnum.FREE, 0),
        "basic": tier_counts.get(SubscriptionTierEnum.BASIC, 0),
        "pro": tier_counts.get(SubscriptionTierEnum.PRO, 0),
        "active_paid": active_paid,
        "total": sum(tier_counts.values()),
    }
