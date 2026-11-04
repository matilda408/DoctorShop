from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

MONEY_STEP = Decimal("0.01")
PERCENT_STEP = Decimal("0.01")


@dataclass(frozen=True)
class ExpertEarningAmounts:
    gross: Decimal
    commission_percent: Decimal
    commission: Decimal
    net: Decimal


def calculate_expert_earning(
    gross_amount: Decimal,
    commission_percent: Decimal,
) -> ExpertEarningAmounts:
    gross = Decimal(gross_amount).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)
    percent = Decimal(commission_percent).quantize(PERCENT_STEP, rounding=ROUND_HALF_UP)
    if gross < 0:
        raise ValueError("Оборот не может быть отрицательным")
    if percent < 0 or percent > 100:
        raise ValueError("Комиссия должна быть от 0 до 100%")

    commission = (gross * percent / Decimal("100")).quantize(
        MONEY_STEP,
        rounding=ROUND_HALF_UP,
    )
    net = (gross - commission).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)
    return ExpertEarningAmounts(
        gross=gross,
        commission_percent=percent,
        commission=commission,
        net=net,
    )
