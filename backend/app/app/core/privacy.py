"""
app/core/privacy.py

Single source of truth for the PROPAURA landlord privacy-policy version and
effective date. Backend signup/consent validation uses these constants so the
accepted version recorded for each landlord always matches the published policy
(see PRIVACY_POLICY_LANDLORD.md in the repository root).
"""

PRIVACY_POLICY_VERSION = "1.0"
PRIVACY_POLICY_EFFECTIVE_DATE = "2026-08-28"

# Header name used when a landlord account exists but privacy consent is still
# pending (e.g. a brand-new Google-created account). The landlord frontend uses
# this to route the user to the consent step.
PRIVACY_CONSENT_REQUIRED_HEADER = "X-Privacy-Consent-Required"
