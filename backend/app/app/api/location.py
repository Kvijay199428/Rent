"""
app/api/location.py

IP-based country detection for address forms.
Returns the ISO 3166-1 alpha-2 country code for the requesting client.
"""
from fastapi import APIRouter, Request
import httpx

DEFAULT_COUNTRY = "IN"

# Provider chain — first success wins.
PROVIDERS = [
    {
        "name": "ipwho.is",
        "url": "https://ipwho.is/",
        "extract": lambda d: d.get("country_code"),
    },
    {
        "name": "ipapi.co",
        "url": "https://ipapi.co/json/",
        "extract": lambda d: d.get("country_code"),
    },
    {
        "name": "ip-api.com",
        "url": "http://ip-api.com/json/",
        "extract": lambda d: d.get("countryCode"),
    },
]

router = APIRouter(tags=["Location"])


@router.get("/api/location/country")
async def detect_country(request: Request):
    """Detect the requesting client's country via IP geolocation."""
    country_code = None

    async with httpx.AsyncClient(timeout=4.0) as client:
        for provider in PROVIDERS:
            try:
                resp = await client.get(provider["url"])
                if resp.status_code == 200:
                    data = resp.json()
                    code = provider["extract"](data)
                    if code and isinstance(code, str) and len(code) == 2:
                        country_code = code.upper()
                        break
            except Exception:
                continue

    if not country_code:
        country_code = DEFAULT_COUNTRY

    return {"country": country_code}
