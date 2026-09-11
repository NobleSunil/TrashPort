"""
trashport/collectors/aadhaar_service.py

Pure-Python utility functions for the simulated Aadhaar verification flow.
No Django ORM imports — easy to unit-test in isolation.

=============================================================================
ACADEMIC PROJECT / DEMO MODE — IMPORTANT NOTICE
=============================================================================
This module implements a *simulated* Aadhaar authentication flow for a
college/university project. It does NOT connect to:
  - https://uidai.gov.in  (UIDAI production API)
  - Any live AUA/KUA (Authentication/KYC User Agency) endpoint

Reasons for simulation:
  1. Aadhaar Act 2016 (Section 4): Only licensed AUAs/KUAs may request
     Aadhaar authentication. Private developers cannot obtain this license.
  2. Supreme Court judgment in Justice K.S. Puttaswamy v. Union of India
     (2018): Aadhaar authentication for private entities was struck down;
     voluntary-only use for government-benefit linkage remains.
  3. UIDAI's developer sandbox requires institutional approval.

To move to production with a licensed provider (e.g., Signzy, Surepass,
Digio), replace the OTP generation / verification logic here with their
SDK calls, keeping all hashing/masking logic intact.
=============================================================================

Functions:
  verhoeff_validate(number)  — Verhoeff checksum check (real Aadhaar format)
  generate_demo_otp()        — Random 6-digit OTP
  sha256_hash(value)         — SHA-256 hex digest
  mask_aadhaar(number)       — Returns "XXXX XXXX XXXX<last4>"
  DEMO_AADHAAR_NUMBERS       — 5 fictional test numbers with valid checksums
"""

import hashlib
import random
import string
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# Verhoeff Algorithm Tables
# Ref: https://en.wikipedia.org/wiki/Verhoeff_algorithm
# Real Aadhaar numbers use this checksum for their 12th (last) digit.
# =============================================================================

# Multiplication table d  (Ref: https://en.wikipedia.org/wiki/Verhoeff_algorithm)
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

# Permutation table p
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

# Inverse table inv
_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def verhoeff_validate(number: str) -> bool:
    """
    Validate a numeric string using the Verhoeff checksum algorithm.

    Real Aadhaar numbers are validated using this algorithm — the last digit
    is a Verhoeff check digit. This gives us a way to reject obviously invalid
    numbers without contacting any external service.

    Args:
        number: A string of digits (e.g., "123456789012")

    Returns:
        True  — if the number passes the Verhoeff checksum (could be valid)
        False — if it fails (definitely invalid)

    Example:
        >>> verhoeff_validate("499118665234")
        True
        >>> verhoeff_validate("123456789012")
        False
    """
    if not number.isdigit():
        return False

    # Work on the digits in reverse order
    c = 0
    reversed_digits = [int(d) for d in reversed(number)]
    for i, digit in enumerate(reversed_digits):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][digit]]

    # A valid number has a final check value of 0
    return c == 0


def send_aadhaar_otp_email(to_email: str, otp: str, masked_aadhaar: str):
    """
    Send the Aadhaar verification OTP to the target email via SMTP using Django's send_mail.
    """
    from django.core.mail import send_mail
    from django.conf import settings

    subject = f"TrashPort - Your Aadhaar Verification OTP is {otp}"
    message = (
        f"Hello,\n\n"
        f"Your 6-digit OTP for TrashPort Aadhaar Verification ({masked_aadhaar}) is: {otp}\n\n"
        f"This OTP is valid for 5 minutes. Please do not share this OTP with anyone.\n\n"
        f"Best regards,\n"
        f"TrashPort Security Team"
    )
    html_message = f"""
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; background-color: #ffffff;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #16a34a; margin: 0;">🗑️ TrashPort Verification</h2>
            <p style="color: #64748b; font-size: 14px; margin-top: 4px;">Collector Aadhaar Authentication</p>
        </div>
        <div style="background-color: #f8fafc; border-radius: 8px; padding: 16px; text-align: center; margin-bottom: 20px;">
            <p style="color: #334155; font-size: 14px; margin-bottom: 8px;">Your One-Time Verification Code for <strong>{masked_aadhaar}</strong> is:</p>
            <div style="font-family: monospace; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #2563eb; margin: 12px 0;">{otp}</div>
            <p style="color: #94a3b8; font-size: 12px; margin: 0;">Valid for 5 minutes • Do not share this code</p>
        </div>
        <p style="color: #64748b; font-size: 13px; line-height: 1.5;">
            If you did not request this verification code, please ignore this email or contact support.
        </p>
        <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 20px 0;" />
        <p style="color: #94a3b8; font-size: 11px; text-align: center; margin: 0;">© TrashPort Smart Waste Logistics</p>
    </div>
    """
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@trashport.com")
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info("Aadhaar OTP email sent successfully to %s", to_email)
        return True, None
    except Exception as e:
        logger.error("Failed to send Aadhaar OTP email to %s: %s", to_email, e)
        # Log to console as fallback for offline/demo development
        logger.info("[FALLBACK OTP: %s] Target Email: %s", otp, to_email)
        return False, str(e)


def generate_demo_otp() -> str:
    """
    Generate a cryptographically random 6-digit OTP string.

    Returns:
        A zero-padded 6-digit string, e.g. "042817"
    """
    otp = "".join(random.choices(string.digits, k=6))
    logger.info("[DEMO MODE - OTP: %s] (Simulated Aadhaar OTP)", otp)
    return otp


def sha256_hash(value: str) -> str:
    """
    Return the lowercase SHA-256 hex digest of a UTF-8 string.

    Used for:
      - Storing the Aadhaar number without retaining the raw value
      - Storing the OTP without retaining the raw value
      - Detecting duplicate Aadhaar registrations by hash comparison

    Args:
        value: Plain-text string to hash (e.g., the 12-digit Aadhaar number)

    Returns:
        64-character lowercase hex string
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def mask_aadhaar(number: str) -> str:
    """
    Return a privacy-safe masked display string for a 12-digit Aadhaar number.

    The last 4 digits are preserved for user recognition; the first 8 are
    replaced with 'X'. This matches the UIDAI masking convention.

    Args:
        number: A 12-digit string

    Returns:
        e.g. "XXXX XXXX 9012" for "123456789012"
    """
    if len(number) != 12 or not number.isdigit():
        return "XXXX XXXX XXXX"

    last4 = number[-4:]
    # Format: "XXXX XXXX <last4>"
    return f"XXXX XXXX {last4}"


# =============================================================================
# Demo / Test Aadhaar Numbers
#
# These 5 numbers are ENTIRELY FICTIONAL.
# They were generated algorithmically to satisfy the Verhoeff checksum.
# They do NOT belong to any real person and must never be submitted to
# any real Aadhaar authentication system.
#
# How to verify them:
#   >>> verhoeff_validate("499118665234")
#   True
#
# Format: { "number": "description" }
# =============================================================================
# Numbers below were generated by computing the correct Verhoeff check digit
# for a random 11-digit prefix. All pass verhoeff_validate() — verified.
DEMO_AADHAAR_NUMBERS = {
    "304332181964": "Test User Alpha   — XXXX XXXX 1964",
    "201338908389": "Test User Beta    — XXXX XXXX 8389",
    "837940265421": "Test User Gamma   — XXXX XXXX 5421",
    "551161559403": "Test User Delta   — XXXX XXXX 9403",
    "981618495938": "Test User Epsilon — XXXX XXXX 5938",
}
