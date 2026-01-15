from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from dateutil.relativedelta import relativedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.constance import (
    SUBSCRIPTION_INVOICE_DESCRIPTIONS,
    SUBSCRIPTION_INVOICE_TITLES,
    TELEGRAM_PAYMENT_PROVIDER_TOKEN,
    create_subscription_payload,
    get_subscription_price,
    parse_subscription_payload,
)
from src.bot.tools import get_user_positions_count
from src.database.enums import SubscriptionTierEnum
from src.database.models import User
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

router = Router()


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """
    Inline keyboard for subscription options.
    """
    basic_price = get_subscription_price(SubscriptionTierEnum.BASIC)
    pro_price = get_subscription_price(SubscriptionTierEnum.PRO)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🆓 FREE (1 position)", callback_data="sub:info:FREE"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⭐ BASIC (5 positions) - {basic_price.label}",
                    callback_data="sub:buy:BASIC",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"💎 PRO (10 positions) - {pro_price.label}",
                    callback_data="sub:buy:PRO",
                )
            ],
        ]
    )
    return keyboard


def format_subscription_info(user: User, positions_count: int) -> str:
    """
    Format user subscription information.

    Args:
        user: User instance
        positions_count: Number of positions (passed to avoid lazy loading)
    """
    tier = user.effective_subscription_tier
    basic_price = get_subscription_price(SubscriptionTierEnum.BASIC)
    pro_price = get_subscription_price(SubscriptionTierEnum.PRO)

    # Tier emoji and name
    tier_info = {
        SubscriptionTierEnum.FREE: ("🆓", "FREE"),
        SubscriptionTierEnum.BASIC: ("⭐", "BASIC"),
        SubscriptionTierEnum.PRO: ("💎", "PRO"),
    }
    emoji, name = tier_info.get(tier, ("🆓", "FREE"))

    text = f"{emoji} <b>Current subscription: {name}</b>\n\n"

    # Position limits
    text += f"📊 Positions: {positions_count}/{user.max_positions}\n"

    # Expiration info for paid subscriptions
    if user.subscription_tier != SubscriptionTierEnum.FREE:
        if user.subscription_expires_at:
            if user.is_subscription_active:
                days_left = (
                    user.subscription_expires_at - datetime.now(timezone.utc)
                ).days
                text += f"⏳ Expires: {user.subscription_expires_at.strftime('%Y-%m-%d')} ({days_left} days left)\n"
            else:
                text += "⚠️ <b>Subscription expired</b>\n"

    text += "\n<b>Available plans:</b>\n\n"
    text += "🆓 <b>FREE</b> - 1 position\n"
    text += f"⭐ <b>BASIC</b> - 5 positions ({basic_price.label} for 30 days)\n"
    text += f"💎 <b>PRO</b> - 10 positions ({pro_price.label} for 30 days)\n"

    return text


@router.message(F.text == "💎 Subscription")
async def subscription_menu(message: Message, session: AsyncSession, user: User):
    """
    Show subscription information and options.
    """
    # Get positions count without lazy loading
    positions_count = await get_user_positions_count(session, user.id)

    info_text = format_subscription_info(user, positions_count)

    await message.answer(
        info_text, reply_markup=get_subscription_keyboard(), parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("sub:info:"))
async def subscription_info(callback: CallbackQuery):
    """
    Show information about a specific subscription tier.
    """
    tier = callback.data.split(":")[-1]

    basic_price = get_subscription_price(SubscriptionTierEnum.BASIC)
    pro_price = get_subscription_price(SubscriptionTierEnum.PRO)

    info_texts = {
        "FREE": (
            "🆓 <b>FREE Plan</b>\n\n"
            "• Track 1 position\n"
            "• Real-time notifications\n"
            "• Basic features\n\n"
            "Perfect for trying out the service!"
        ),
        "BASIC": (
            f"⭐ <b>BASIC Plan - {basic_price.label}</b>\n\n"
            "• Track up to 5 positions\n"
            "• Real-time notifications\n"
            "• Priority support\n"
            "• Advanced analytics\n"
            "• Valid for 30 days\n\n"
            "Great for active traders!"
        ),
        "PRO": (
            f"💎 <b>PRO Plan - {pro_price.label}</b>\n\n"
            "• Track up to 10 positions\n"
            "• Real-time notifications\n"
            "• Priority support\n"
            "• Advanced analytics\n"
            "• Custom alerts\n"
            "• Valid for 30 days\n\n"
            "For professional traders!"
        ),
    }

    await callback.answer()
    await callback.message.edit_text(
        info_texts.get(tier, "Unknown plan"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="« Back", callback_data="sub:back")]
            ]
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("sub:buy:"))
async def subscription_buy(callback: CallbackQuery, user: User):
    """
    Handle subscription purchase via Telegram Stars.
    """
    tier_str = callback.data.split(":")[-1]

    try:
        tier = SubscriptionTierEnum(tier_str)
    except ValueError:
        await callback.answer("Invalid subscription tier", show_alert=True)
        return

    if tier == SubscriptionTierEnum.FREE:
        await callback.answer("You are already on the FREE plan!", show_alert=True)
        return

    # Get pricing info
    price_info = get_subscription_price(tier)

    # Create invoice
    title = SUBSCRIPTION_INVOICE_TITLES[tier]
    description = SUBSCRIPTION_INVOICE_DESCRIPTIONS[tier]
    payload = create_subscription_payload(tier, user.id)

    # Price in Telegram Stars (smallest unit)
    prices = [LabeledPrice(label=title, amount=price_info.stars)]

    await callback.answer()

    # Send invoice
    await callback.message.answer_invoice(
        title=title,
        description=description,
        payload=payload,
        provider_token=TELEGRAM_PAYMENT_PROVIDER_TOKEN,  # Empty for Stars
        currency="XTR",  # Telegram Stars currency code
        prices=prices,
        start_parameter=f"sub_{tier.value}",
    )


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """
    Handle pre-checkout query (validate payment before processing).
    """
    # Parse payload to validate
    tier, user_id = parse_subscription_payload(pre_checkout_query.invoice_payload)

    if tier is None or user_id is None:
        await pre_checkout_query.answer(
            ok=False, error_message="Invalid subscription data"
        )
        return

    # All validations passed
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(
    message: Message, session: AsyncSession, user: User
):
    """
    Handle successful payment and activate subscription.
    """
    payment = message.successful_payment

    # Parse payload
    tier, user_id = parse_subscription_payload(payment.invoice_payload)

    if tier is None or user_id != user.id:
        await message.answer(
            "❌ Payment processing error. Please contact support.", parse_mode="HTML"
        )
        logger.warning(
            "Payment payload error: payload=%s, user_id=%s, expected=%s",
            payment.invoice_payload,
            user.id,
            user_id,
        )
        return

    # Get pricing info
    price_info = get_subscription_price(tier)

    # Update user subscription
    user.subscription_tier = tier
    user.subscription_expires_at = datetime.now(timezone.utc) + relativedelta(months=1)

    await session.commit()

    logger.info(
        "User %s (%s) purchased %s plan. Expires at %s",
        user.id,
        user.username,
        tier.value,
        user.subscription_expires_at.isoformat(),
    )

    # Send confirmation
    tier_emoji = "⭐" if tier == SubscriptionTierEnum.BASIC else "💎"

    await message.answer(
        f"🎉 <b>Subscription activated!</b>\n\n"
        f"{tier_emoji} You now have <b>{tier.value}</b> plan\n"
        f"📊 Track up to <b>{price_info.positions_limit} positions</b>\n"
        f"⏳ Valid until: <b>{user.subscription_expires_at.strftime('%Y-%m-%d')}</b>\n\n"
        f"Thank you for your purchase!",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "sub:back")
async def subscription_back(callback: CallbackQuery, session: AsyncSession, user: User):
    """
    Return to subscription menu.
    """
    # Get positions count without lazy loading
    positions_count = await get_user_positions_count(session, user.id)

    info_text = format_subscription_info(user, positions_count)

    await callback.answer()
    await callback.message.edit_text(
        info_text, reply_markup=get_subscription_keyboard(), parse_mode="HTML"
    )


@router.callback_query(F.data == "subscription_menu")
async def open_subscription_from_limit(
    callback: CallbackQuery, session: AsyncSession, user: User
):
    """
    Open subscription menu from position limit message.
    """
    from src.bot.handlers.subscription import (
        format_subscription_info,
        get_subscription_keyboard,
    )
    from src.bot.tools import get_user_positions_count

    positions_count = await get_user_positions_count(session, user.id)
    info_text = format_subscription_info(user, positions_count)

    await callback.message.edit_text(
        info_text, reply_markup=get_subscription_keyboard(), parse_mode="HTML"
    )
    await callback.answer()
