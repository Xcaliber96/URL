import secrets
import string

def generate_short_string(length: int = 6) -> str:
    """Generate a random string of letters and digits."""
    characters = string.ascii_letters + string.digits
    return "".join(secrets.choice(characters) for _ in range(length))