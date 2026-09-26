import math

IMAGE_TOO_LARGE_TEXT = (
    "Картинка больше 5 МБ — такую модель не примет. Сожми её или пришли меньше."
)


# Лимит Claude на картинку считается по base64-представлению, а не по сырым байтам
def image_exceeds_limit(raw_size: int, max_image_bytes: int) -> bool:
    return 4 * math.ceil(raw_size / 3) > max_image_bytes
