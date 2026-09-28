BYTES_IN_UNIT = 1024
LARGER_UNITS = ("КБ", "МБ", "ГБ")
FRACTION_BELOW = 10


def human_size(size: int) -> str:
    if size < BYTES_IN_UNIT:
        return f"{size} Б"
    value = size / BYTES_IN_UNIT
    unit_index = 0
    while value >= BYTES_IN_UNIT and unit_index < len(LARGER_UNITS) - 1:
        value /= BYTES_IN_UNIT
        unit_index += 1
    unit = LARGER_UNITS[unit_index]
    if value < FRACTION_BELOW:
        return f"{value:.1f}".replace(".", ",") + f" {unit}"
    return f"{round(value)} {unit}"
