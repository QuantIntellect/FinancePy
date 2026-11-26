"""Settlement on the maturity date falls in the final coupon period, and Bond analytics
must not depend on the coupon period found by an earlier call for another date."""

import pytest

from financepy.products.bonds.bond import Bond
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


########################################################################################


@pytest.mark.parametrize("earlier_dt", [None, Date(1, 3, 2027), Date(1, 12, 2029)])
@pytest.mark.parametrize(
    "ex_div_days, accrued, dirty_price", [(0, 2.0, 102.0), (7, 0.0, 100.0)]
)
def test_settlement_on_maturity(earlier_dt, ex_div_days, accrued, dirty_price):

    # The final coupon period runs from 15 Jul 2029 to 15 Jan 2030
    bond = _bond(ex_div_days)
    if earlier_dt is not None:
        bond.accrued_interest(earlier_dt, 100.0)
    assert bond.accrued_interest(MATURITY_DT, 100.0) == pytest.approx(accrued)

    bond = _bond(ex_div_days)
    if earlier_dt is not None:
        bond.accrued_interest(earlier_dt, 100.0)
    assert bond.dirty_price_from_ytm(MATURITY_DT, YTM) == pytest.approx(dirty_price)

    # The clean price on the maturity date is par
    assert dirty_price - accrued == pytest.approx(
        _bond(ex_div_days).clean_price_from_ytm(MATURITY_DT, YTM)
    )


########################################################################################


@pytest.mark.parametrize("earlier_dt", [None, Date(1, 3, 2027)])
def test_settlement_after_maturity_raises(earlier_dt):

    bond = _bond()
    if earlier_dt is not None:
        bond.accrued_interest(earlier_dt, 100.0)

    with pytest.raises(FinError):
        bond.accrued_interest(Date(20, 1, 2030), 100.0)


########################################################################################


def test_rate_of_return_held_to_maturity():

    # Bought on 1 Mar 2027, the bond pays five coupons of 2 before maturity, and the
    # final coupon and the principal on the maturity date
    buy_dt = Date(1, 3, 2027)
    buy_price = _bond().dirty_price_from_ytm(buy_dt, YTM)

    _, _, pnl = _bond().calc_ror(buy_dt, MATURITY_DT, YTM, YTM)

    assert pnl == pytest.approx(5 * 2.0 + 102.0 - buy_price)
