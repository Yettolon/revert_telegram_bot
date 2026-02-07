"""
Subscription pricing and configuration constants.
"""

from dataclasses import dataclass

from src.database.enums import SubscriptionTierEnum


@dataclass(frozen=True)
class SubscriptionPrice:
    """Subscription tier pricing in Telegram Stars"""

    tier: SubscriptionTierEnum
    stars: int  # Price in Telegram Stars
    positions_limit: int
    duration_days: int  # Subscription duration in days

    @property
    def label(self) -> str:
        """Human-readable price label"""
        return f"{self.stars} ⭐"


# Subscription pricing configuration
SUBSCRIPTION_PRICES = {
    SubscriptionTierEnum.FREE: SubscriptionPrice(
        tier=SubscriptionTierEnum.FREE,
        stars=0,
        positions_limit=1,
        duration_days=0,  # Unlimited
    ),
    SubscriptionTierEnum.BASIC: SubscriptionPrice(
        tier=SubscriptionTierEnum.BASIC,
        stars=100,  # 500 Telegram Stars (~$10 USD equivalent)
        positions_limit=5,
        duration_days=30,
    ),
    SubscriptionTierEnum.PRO: SubscriptionPrice(
        tier=SubscriptionTierEnum.PRO,
        stars=250,  # 1000 Telegram Stars (~$20 USD equivalent)
        positions_limit=10,
        duration_days=30,
    ),
}


def get_subscription_price(tier: SubscriptionTierEnum) -> SubscriptionPrice:
    """Get subscription price configuration for a tier"""
    return SUBSCRIPTION_PRICES[tier]


# Invoice titles and descriptions
SUBSCRIPTION_INVOICE_TITLES = {
    SubscriptionTierEnum.BASIC: "⭐ BASIC Subscription - 1 Month",
    SubscriptionTierEnum.PRO: "💎 PRO Subscription - 1 Month",
}

SUBSCRIPTION_INVOICE_DESCRIPTIONS = {
    SubscriptionTierEnum.BASIC: (
        "Track up to 5 positions with real-time notifications. " "Valid for 30 days."
    ),
    SubscriptionTierEnum.PRO: (
        "Track up to 10 positions with advanced features and priority support. "
        "Valid for 30 days."
    ),
}


# Payment provider token (use "provider_token" from BotFather or leave empty for Stars)
TELEGRAM_PAYMENT_PROVIDER_TOKEN = ""  # Empty string for Telegram Stars


# Invoice payload prefix for identifying subscription purchases
SUBSCRIPTION_PAYLOAD_PREFIX = "subscription"


def create_subscription_payload(tier: SubscriptionTierEnum, user_id: int) -> str:
    """Create unique payload for subscription purchase"""
    return f"{SUBSCRIPTION_PAYLOAD_PREFIX}:{tier.value}:{user_id}"


def parse_subscription_payload(
    payload: str,
) -> tuple[SubscriptionTierEnum | None, int | None]:
    """
    Parse subscription payload

    Returns:
        tuple: (tier, user_id) or (None, None) if invalid
    """
    try:
        parts = payload.split(":")
        if len(parts) != 3 or parts[0] != SUBSCRIPTION_PAYLOAD_PREFIX:
            return None, None

        tier = SubscriptionTierEnum(parts[1])
        user_id = int(parts[2])
        return tier, user_id
    except (ValueError, IndexError):
        return None, None
