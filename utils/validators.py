import re

COMMON_PASSWORDS = {
    "password",
    "123456",
    "admin123",
    "password1",
    "admin@123",
    "student@123",
    "staff@123",
}


def validate_email(email: str) -> bool:
    if not email:
        return False
    return bool(re.match(r"^[\w\.\+\-]+@[\w\-]+\.[a-z]{2,}$", email, re.IGNORECASE))


def validate_phone(phone: str) -> bool:
    if not phone:
        return False
    # Indian mobile number format: 10 digits starting with 6-9
    return bool(re.match(r"^[6-9]\d{9}$", phone))


def validate_password(password: str) -> dict:
    return {
        "length": len(password) >= 8,
        "digit": bool(re.search(r"\d", password)),
        "special": bool(re.search(r"[!@#$%^&*()_\+\-=\[\]\{\}\|;:,.<>?]", password)),
        "uppercase": bool(re.search(r"[A-Z]", password)),
        "no_common": password.lower() not in COMMON_PASSWORDS,
    }


def get_password_strength(password: str) -> tuple[int, str, str]:
    # Returns (score, strength_name, color)
    if not password:
        return 0, "Weak", "#f38ba8"
    checks = validate_password(password)
    score = sum(checks.values())
    if score <= 2:
        return score, "Weak", "#f38ba8"  # red
    elif score <= 4:
        return score, "Medium", "#fab387"  # amber
    else:
        return score, "Strong", "#a6e3a1"  # green
