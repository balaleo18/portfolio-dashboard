import datetime
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

def calculate_xirr(cash_flows: List[Tuple[datetime.date, float]], guess: float = 0.1) -> float:
    """
    Calculate the Extended Internal Rate of Return (XIRR) for a list of cash flows.
    cash_flows: List of (date, amount) tuples.
                Amounts should be negative for outflows (investments) and positive for inflows (returns/current value).
    """
    if not cash_flows:
        return 0.0
        
    # Filter out zero cash flows
    cash_flows = [cf for cf in cash_flows if cf[1] != 0.0]
    if len(cash_flows) < 2:
        return 0.0
        
    # Check if there is at least one negative and one positive cash flow
    has_negative = any(cf[1] < 0 for cf in cash_flows)
    has_positive = any(cf[1] > 0 for cf in cash_flows)
    if not (has_negative and has_positive):
        # Cannot calculate XIRR if all cash flows are in the same direction
        return 0.0

    # Sort by date
    cash_flows = sorted(cash_flows, key=lambda x: x[0])
    d0 = cash_flows[0][0]

    # Equation to solve: sum(CF_i / (1 + r)^((d_i - d_0) / 365.25)) = 0
    def xirr_equation(r: float) -> float:
        total = 0.0
        for d, amount in cash_flows:
            t = (d - d0).days / 365.25
            total += amount / ((1.0 + r) ** t)
        return total

    # Derivative of the equation
    def xirr_derivative(r: float) -> float:
        total = 0.0
        for d, amount in cash_flows:
            t = (d - d0).days / 365.25
            if t == 0:
                continue
            total -= t * amount / ((1.0 + r) ** (t + 1.0))
        return total

    # Newton-Raphson Method
    r = guess
    for _ in range(100):
        try:
            val = xirr_equation(r)
            deriv = xirr_derivative(r)
            if deriv == 0:
                break
            r_new = r - val / deriv
            if abs(r_new - r) < 1e-6:
                return round(r_new * 100, 2)  # Return as percentage
            r = r_new
        except (ZeroDivisionError, OverflowError):
            break

    # Bisection Method Fallback (more robust if Newton-Raphson fails to converge)
    low = -0.999
    high = 2.0
    for _ in range(100):
        mid = (low + high) / 2.0
        val = xirr_equation(mid)
        if abs(val) < 1e-6:
            return round(mid * 100, 2)
        
        # Test boundaries
        val_low = xirr_equation(low)
        if val * val_low < 0:
            high = mid
        else:
            low = mid
            
    return round(r * 100, 2)
