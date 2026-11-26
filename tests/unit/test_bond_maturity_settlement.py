"""Settlement on a bond's maturity date falls in the final coupon period, whatever was
called before, and calc_ror attributes a coupon paid on a settlement date the way the
dirty prices do."""

import pytest

from financepy.products.bonds.bond import Bond, YTMCalcType
from financepy.utils.date import Date
from financepy.utils.day_count import DayCountTypes
from financepy.utils.error import FinError
from financepy.utils.frequency import FrequencyTypes

ISSUE_DT = Date(15, 1, 2025)
MATURITY_DT = Date(15, 1, 2030)
YTM = 0.05

########################################################################################


def _bond(ex_div_days=0):
    return Bond(
        ISSUE_DT,
        MATURITY_DT,
        0.04,
        FrequencyTypes.SEMI_ANNUAL,
        DayCountTypes.ACT_ACT_ICMA,
        ex_div_days,
    )


EARLIER_DTS = [None, Date(1, 3, 2027), Date(1, 12, 2029)]
EARLIER_IDS = ["new_bond", "after_2027_call", "after_final_period_call"]

########################################################################################


@pytest.mark.parametrize("earlier_dt", EARLIER_DTS, ids=EARLIER_IDS)
@pytest.mark.parametrize(
    "ex_div_days, accrued, dirty_price",
    [(0, 2.0, 102.0), (7, 0.0, 100.0)],
    ids=["no_ex_div", "ex_div"],
)
def test_settlement_on_maturity(earlier_dt, ex_div_days, accrued, dirty_price):

    # The final coupon period runs from 15 Jul 2029 to 15 Jan 2030
    bond = _bond(ex_div_days)
    if earlier_dt is not None:
        bond.accrued_interest(earlier_dt, 100.0)
    computed_accrued = bond.accrued_interest(MATURITY_DT, 100.0)

    bond = _bond(ex_div_days)
    if earlier_dt is not None:
        bond.accrued_interest(earlier_dt, 100.0)
    computed_dirty_price = bond.dirty_price_from_ytm(MATURITY_DT, YTM)

    assert computed_accrued == pytest.approx(accrued)
    assert computed_dirty_price == pytest.approx(dirty_price)
    assert computed_dirty_price - computed_accrued == pytest.approx(100.0)


########################################################################################


@pytest.mark.parametrize("earlier_dt", EARLIER_DTS[:2], ids=EARLIER_IDS[:2])
def test_settlement_after_maturity_raises(earlier_dt):

    bond = _bond()
    if earlier_dt is not None:
        bond.accrued_interest(earlier_dt, 100.0)

    with pytest.raises(FinError, match="after maturity date"):
        bond.accrued_interest(Date(20, 1, 2030), 100.0)


########################################################################################


@pytest.mark.parametrize(
    "buy_dt, sell_dt, num_cpns",
    [
        (Date(1, 3, 2027), MATURITY_DT, 5),
        (Date(15, 1, 2029), MATURITY_DT, 1),
        (Date(15, 1, 2027), Date(1, 3, 2028), 2),
        (Date(1, 3, 2027), Date(15, 1, 2029), 4),
    ],
    ids=[
        "held_to_maturity",
        "bought_on_coupon_date_held_to_maturity",
        "bought_on_coupon_date",
        "sold_on_coupon_date",
    ],
)
def test_rate_of_return_coupons(buy_dt, sell_dt, num_cpns):

    # A coupon paid on a settlement date goes to the seller, as the dirty prices
    # assume, so the holder receives the num_cpns coupons of 2 paid after the buy date
    # and up to the sell date. On the maturity date the sell price is par plus the
    # final coupon.
    convention = YTMCalcType.US_STREET
    buy_price = _bond().dirty_price_from_ytm(buy_dt, YTM, convention)

    if sell_dt == MATURITY_DT:
        sell_price = 102.0
    else:
        sell_price = _bond().dirty_price_from_ytm(sell_dt, YTM, convention)

    _, _, pnl = _bond().calc_ror(buy_dt, sell_dt, YTM, YTM, convention)

    assert pnl == pytest.approx(2.0 * num_cpns + sell_price - buy_price)
