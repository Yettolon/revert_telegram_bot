from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.types import Message

from src.bot.keyboards.settings import get_settings_keyboard
from src.bot.tools import get_user_positions_count
from src.database.enums import SubscriptionTierEnum
from src.database.models import User
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Создаём роутер для этого модуля
router = Router(name="settings")


@router.message(F.text == "⚙️ Settings")
async def settings_handler(
    message: Message,
    session,
    user: User,
):
    """
    Show settings menu with subscription info.
    """
    # Get positions count
    positions_count = await get_user_positions_count(session, user.id)

    # Tier display
    tier = user.effective_subscription_tier
    tier_emoji = {
        SubscriptionTierEnum.FREE: "🆓",
        SubscriptionTierEnum.BASIC: "⭐",
        SubscriptionTierEnum.PRO: "💎",
    }
    emoji = tier_emoji.get(tier, "🆓")

    # Build subscription text
    sub_text = f"{emoji} {tier.value} ({positions_count}/{user.max_positions})"

    # Add expiration if paid
    if (
        user.subscription_tier != SubscriptionTierEnum.FREE
        and user.subscription_expires_at
    ):
        if user.is_subscription_active:
            now = datetime.now(timezone.utc)
            days_left = (user.subscription_expires_at - now).days
            sub_text += f" • expires in {days_left}d"
        else:
            sub_text += " • expired"

    await message.answer(
        f"""⚙️ Settings

💎 Subscription: {sub_text}

Manage bot preferences.

🔔 System notifications""",
        reply_markup=get_settings_keyboard(user),
    )


@router.message(
    lambda message: message.text
    in {
        "🔕 Disable system notifications",
        "🔔 Enable system notifications",
    }
)
async def toggle_system_notifications_handler(
    message: Message,
    user: User,
    session,
):
    user.is_system_notifications_enabled = not user.is_system_notifications_enabled

    await session.commit()

    status_text = (
        "🔔 System notifications enabled"
        if user.is_system_notifications_enabled
        else "🔕 System notifications disabled"
    )

    await message.answer(
        status_text,
        reply_markup=get_settings_keyboard(user),
    )
