"""
app/core/privacy.py

Single source of truth for the PROPAURA landlord privacy-policy and
terms-and-conditions versions and effective dates. Backend signup/consent
validation uses these constants so the accepted versions recorded for each
landlord always match the published documents
(see PRIVACY_POLICY_LANDLORD.md and TERMS_CONDITIONS_LANDLORD.md in the
repository root).
"""

PRIVACY_POLICY_VERSION = "2.0"
PRIVACY_POLICY_EFFECTIVE_DATE = "2026-08-28"

TERMS_CONDITIONS_VERSION = "1.0"
TERMS_CONDITIONS_EFFECTIVE_DATE = "2026-08-28"

# Header name used when a landlord account exists but privacy consent is still
# pending (e.g. a brand-new Google-created account). The landlord frontend uses
# this to route the user to the consent step.
PRIVACY_CONSENT_REQUIRED_HEADER = "X-Privacy-Consent-Required"
