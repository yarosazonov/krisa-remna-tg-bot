BYTES_IN_GB = 1024 ** 3
BYTES_IN_MB = 1024 ** 2

def bytes_to_gb(bytes_value: int) -> float:
    return bytes_value / BYTES_IN_GB

def gb_to_bytes(gb_value: float) -> int:
    return int(gb_value * BYTES_IN_GB)

def mb_to_bytes(mb_value: float) -> int:
    return int(mb_value * BYTES_IN_MB)



def get_subscription_map(settings):
    return {
        "1_month": {
            "months": 1,
            "price": settings.RUB_PRICE_1_MONTH,
            "description": "Подписка на 1 месяц"
        },
        "3_months": {
            "months": 3,
            "price": settings.RUB_PRICE_3_MONTHS,
            "description": "Подписка на 3 месяца"
        },
        "6_months": {
            "months": 6,
            "price": settings.RUB_PRICE_6_MONTHS,
            "description": "Подписка на 6 месяцев"
        }
    }



def months_to_days(months:int) -> int:
    """
    Returns the amount of days in monts provided

    1 month = 30 days
    """
    return months * 30

