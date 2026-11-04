from typing import Final

from src.core.enums import Currency, PaymentGatewayType

CRYPTO_PAYMENT_GATEWAYS: Final[frozenset[PaymentGatewayType]] = frozenset(
    {
        PaymentGatewayType.CRYPTOMUS,
        PaymentGatewayType.HELEKET,
        PaymentGatewayType.CRYPTOPAY,
    }
)

ACTIVE_PAYMENT_GATEWAYS: Final[tuple[PaymentGatewayType, ...]] = tuple(
    gateway for gateway in PaymentGatewayType if gateway not in CRYPTO_PAYMENT_GATEWAYS
)

NEW_PLAN_CURRENCIES: Final[tuple[Currency, ...]] = (
    Currency.RUB,
    Currency.XTR,
)

DEFAULT_PLAN_CURRENCY: Final[Currency] = Currency.RUB


def checkout_currency(configured_currency: Currency) -> Currency:
    if configured_currency in NEW_PLAN_CURRENCIES:
        return configured_currency
    return DEFAULT_PLAN_CURRENCY
