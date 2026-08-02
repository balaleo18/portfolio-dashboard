import datetime
from typing import Optional

def calculate_fd_value(
    principal: float,
    interest_rate: float,  # E.g. 7.5 for 7.5%
    start_date: datetime.date,
    maturity_date: Optional[datetime.date],
    compounding_frequency: Optional[str] = "Quarterly",
    target_date: Optional[datetime.date] = None
) -> float:
    if target_date is None:
        target_date = datetime.date.today()
        
    if target_date < start_date:
        return principal
        
    # Interest stops compounding after maturity date (standard behavior unless auto-renewed)
    accrual_end_date = target_date
    if maturity_date and target_date > maturity_date:
        accrual_end_date = maturity_date
        
    days_elapsed = (accrual_end_date - start_date).days
    t = days_elapsed / 365.25
    
    # Frequency to compounding periods per year
    freq_map = {
        "monthly": 12,
        "quarterly": 4,
        "half-yearly": 2,
        "yearly": 1,
        "cumulative": 4  # Standard in Indian banking system
    }
    
    freq_str = str(compounding_frequency).lower().strip() if compounding_frequency else "quarterly"
    n = freq_map.get(freq_str, 4)
    
    r = interest_rate / 100.0
    
    # Formula: A = P * (1 + r/n)^(n*t)
    accrued_value = principal * ((1 + r / n) ** (n * t))
    return round(accrued_value, 2)
