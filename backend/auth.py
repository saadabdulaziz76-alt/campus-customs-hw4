"""Password hashing and session tokens for Campus Customs.

Kept in its own module so the security-critical code is small enough to read in
one sitting.

Password storage
----------------
Passwords are never stored. What is stored is a PBKDF2-HMAC-SHA256 derivation:

    pbkdf2_sha256$<iterations>$<salt_hex>$<digest_hex>      (written by us)
    pbkdf2_sha256$<salt>$<digest_hex>                       (seed data, legacy)

Every password gets its own random 16-byte salt, so two users who pick the same
password still end up with different digests and one cracked hash reveals
nothing about the other. Verification is constant-time.

The seed database ships the shorter three-part form at a fixed 120,000
iterations. `verify_password` reads both, so the seeded test user keeps working
while anything we write uses the stronger current setting.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

ALGORITHM = "sha256"
PREFIX = "pbkdf2_sha256"

# OWASP's current floor for PBKDF2-HMAC-SHA256. The seed data uses 120,000; new
# hashes use this.
ITERATIONS = 600_000
LEGACY_ITERATIONS = 120_000

SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 8
TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60  # one week

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------------------
# passwords
# ---------------------------------------------------------------------------


def hash_password(password: str, *, iterations: int = ITERATIONS) -> str:
    """Derive a storable hash. Never store or log the password itself."""
    salt = secrets.token_hex(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(ALGORITHM, password.encode(), salt.encode(), iterations)
    return f"{PREFIX}${iterations}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash, in constant time.

    Handles both the four-part form we write and the three-part seed form.
    Returns False on anything malformed rather than raising, so a corrupt row
    cannot turn into an unhandled error on the login path.
    """
    if not stored:
        return False

    parts = stored.split("$")
    try:
        if len(parts) == 4:
            prefix, iterations, salt, expected = parts
            iterations = int(iterations)
        elif len(parts) == 3:
            prefix, salt, expected = parts
            iterations = LEGACY_ITERATIONS
        else:
            return False
    except (ValueError, TypeError):
        return False

    if prefix != PREFIX:
        return False

    computed = hashlib.pbkdf2_hmac(ALGORITHM, password.encode(), salt.encode(), iterations)
    # compare_digest, not ==, so the comparison does not leak how many leading
    # characters matched via timing.
    return hmac.compare_digest(computed.hex(), expected)


# A precomputed hash of a random value. Verifying against it on an unknown email
# costs the same as a real check, so response timing does not reveal whether an
# account exists.
_DUMMY_HASH = hash_password(secrets.token_hex(16), iterations=LEGACY_ITERATIONS)


def waste_time_like_a_real_check() -> None:
    """Equalise timing for a login attempt against an email we do not have."""
    verify_password("not-the-password", _DUMMY_HASH)


def password_problem(password: str) -> str | None:
    """Return a human-readable problem with the password, or None if it is fine."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if password.strip() == "":
        return "Password cannot be blank."
    return None


def normalise_email(email: str) -> str:
    return email.strip().lower()


def email_looks_valid(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


# ---------------------------------------------------------------------------
# session tokens
# ---------------------------------------------------------------------------

# A per-deployment secret. Set SESSION_SECRET in .env to keep sessions valid
# across restarts; otherwise a fresh one is generated and old tokens stop
# working when the server restarts, which is the safe default.
SESSION_SECRET = os.environ.get("SESSION_SECRET") or secrets.token_hex(32)


def _sign(payload: bytes) -> str:
    return hmac.new(SESSION_SECRET.encode(), payload, hashlib.sha256).hexdigest()


def create_token(user_id: int) -> str:
    """A signed, expiring token identifying one user.

    Format: base64(json payload).signature — the payload is readable but cannot
    be altered without the secret, so a user cannot edit it to become someone
    else.
    """
    payload = json.dumps({"uid": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS})
    encoded = urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{encoded}.{_sign(encoded.encode())}"


def read_token(token: str) -> int | None:
    """Return the user id in a valid, unexpired token, else None."""
    if not token or "." not in token:
        return None
    encoded, _, signature = token.rpartition(".")
    if not hmac.compare_digest(_sign(encoded.encode()), signature):
        return None
    try:
        padding = "=" * (-len(encoded) % 4)
        data = json.loads(urlsafe_b64decode(encoded + padding))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data.get("uid"), int) or data.get("exp", 0) < time.time():
        return None
    return data["uid"]
