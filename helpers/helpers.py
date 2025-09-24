BYTES_IN_GB = 1024 ** 3
BYTES_IN_MB = 1024 ** 2

def bytes_to_gb(bytes_value: int) -> float:
    return bytes_value / BYTES_IN_GB

def gb_to_bytes(gb_value: float) -> int:
    return int(gb_value * BYTES_IN_GB)

def mb_to_bytes(mb_value: float) -> int:
    return int(mb_value * BYTES_IN_MB)