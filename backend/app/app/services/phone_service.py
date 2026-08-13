"""
app/services/phone_service.py

Canonical phone-number handling.

All phone numbers entered through the PROPAURA forms are stored in E.164
format (+<country code><national number>), e.g. "+919876543210".
This module normalizes raw input (country code prefix, "00" prefix, or bare
national digits resolved against a default region) into that canonical form.
"""

import phonenumbers


def normalize_phone(raw, default_region="IN"):
    """
    Normalize a phone number to E.164 format, e.g. "+919876543210".

    Accepts:
      - Full E.164 input:  "+919876543210"
      - International prefix: "00919876543210"
      - National number with explicit country: "+1 202 555 0100"
      - Bare national digits: "9876543210" (resolved against default_region)

    Returns the E.164 string when the input parses and is a possible number,
    the stripped original input when non-empty but unparseable (so existing
    imports/flows never break on odd values), or None when empty.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        number = phonenumbers.parse(text, default_region or "IN")
    except phonenumbers.NumberParseException:
        return text
    if not phonenumbers.is_possible_number(number):
        return text
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def is_valid_phone(raw, default_region="IN"):
    """
    True when `raw` parses to a valid number for the given region
    (or as an international E.164 number).
    """
    if not raw:
        return False
    try:
        number = phonenumbers.parse(str(raw).strip(), default_region or "IN")
    except phonenumbers.NumberParseException:
        return False
    return phonenumbers.is_valid_number(number)
