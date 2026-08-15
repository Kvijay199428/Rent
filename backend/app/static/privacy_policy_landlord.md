# PROPAURA — Privacy Policy for Landlord Account Creation

**Effective Date:** 28 August 2026
**Version:** 2.0
**Platform:** PROPAURA (Rent Receipt & Property Management System v3.0.0)
**Website:** vijaykrsha.online
**Data Fiduciary / Platform Operator:** Vijay Kumar Sharma
**Postal Address:** 1E, Shiv Durga Vihar Lakarpur, Surajkund Faridabad, Faridabad, Haryana, Pin - 121009
**Privacy / Grievance Contact Email:** vijaykrsha@hotmail.com
**Privacy / Grievance Contact Phone:** +91 95913 0381
**Jurisdiction:** Republic of India

---

## 1. Purpose and Scope

This Privacy Policy explains how PROPAURA ("the Platform") processes the personal data of a person who creates or uses a **landlord account**.

PROPAURA is a rental-property management software platform. From the supplied source code it provides the following landlord-facing functions:

- Landlord account creation, login (password and Google sign-in), TOTP two-factor authentication, and secure sessions;
- Tenant profile management (name, company, phone, email, address, room number, occupation, notes, tenancy status);
- Rent and utility billing — rent, water charges, tank-water charges, electricity (meter-rate based), additional-person charges, maintenance charges, deposits, arrears and payment-status tracking;
- Professional PDF receipt generation, viewing and download;
- A tenant self-service portal (QR unlock, PIN and password login, password reset, receipt viewing/download, and KYC document upload);
- KYC document storage for tenants and occupants, including Aadhaar-related and employment-related documents;
- WhatsApp-based receipt sharing and payment-reminder messages;
- CSV, Excel and ZIP data export; Excel/CSV import with preview and execution;
- Automatic (event-triggered) and manual backups with integrity verification and restore;
- Tenant "recovery snapshots" kept after permanent tenant deletion;
- Full audit logging of landlord, tenant and platform-administrator actions.

**This Policy, together with the PropAura Terms and Conditions, is a condition of account creation.** A landlord account **cannot** be created unless the landlord actively accepts both this Policy and the Terms and Conditions by selecting the required consent checkboxes during signup. If either checkbox is not selected, the signup request is rejected and no account record is created.

For the purposes of India's **Digital Personal Data Protection Act, 2023** (the "DPDP Act"), Vijay Kumar Sharma, operating through vijaykrsha.online, is the **Data Fiduciary** in respect of the personal data described in Section 3 of this Policy. Where a landlord enters or uploads data about tenants, occupants or other individuals, the landlord is a Data Fiduciary for that data and PROPAURA acts as a Data Processor providing the tools described in this Policy.

---

## 2. Mandatory Consent at Account Creation

Under Section 6 of the DPDP Act, consent must be free, specific, informed, unconditional, unambiguous and given through a clear affirmative action.

By selecting the checkbox and submitting the signup form, you:

1. Acknowledge receipt of this notice under Section 5 of the DPDP Act;
2. Provide explicit, informed consent under Section 6 to the processing described in this Policy;
3. Confirm you are authorised to create a landlord account;
4. Confirm you understand that account creation is blocked unless this consent is recorded;
5. Accept responsibility for personal data you enter about tenants, occupants or other individuals through your account, including obtaining any notices and consents required by law.

**Consent is recorded and auditable.** On acceptance, PROPAURA stores the accepted policy version, the date and time of acceptance (UTC), the IP address and user-agent from which acceptance was made, and writes a `privacy_policy_accepted` entry to the landlord audit log. Renewed acceptance is required when a materially revised version of this Policy is issued.

**Google sign-in.** If you create your account through Google sign-in, acceptance of this Policy is recorded as part of the Google sign-in flow. No account created through any method is usable without acceptance of this Policy and the Terms and Conditions.

---

## 3. Personal Data We Collect

### 3.1 Landlord account data (provided by you)

| Data element | Purpose | Source |
|---|---|---|
| Full name | Account identity | Signup form / Google profile |
| Email address | Account identity, login, and account-related contact | Signup form / Google profile |
| Phone number | Account contact | Signup form |
| Username | Login identity | Signup form |
| Password | Authentication (stored only as an Argon2id hash; plaintext is never stored) | Signup form |
| Account UUID | Unique account identifier | Generated automatically |
| Google subject ID, avatar URL, auth provider | Google sign-in identity | Google sign-in |

### 3.2 Security and authentication data

| Data element | Purpose |
|---|---|
| Password hash (Argon2id) | Secure authentication |
| TOTP secret and enable flag | Optional two-factor authentication |
| Temporary-password records | Administrator-initiated password resets |
| Failed-login counter and lockout timestamp | Brute-force protection (5 failed attempts lock the account for 15 minutes) |
| Encrypted password copy in the platform-administrator vault | Password recovery / reset by authorised platform administration (encrypted) |
| Session records | Device name, browser, operating system, IP address, session creation/last-activity/expiry, remember-me flag |

### 3.3 Technical data (collected automatically)

When you use the Platform, the following are logged in session and audit-log records: IP address, user-agent string, browser/OS information, login and logout times, failed-login attempts, and actions performed. These are retained as described in Section 5.

### 3.4 Rental-management data you enter

Tenant and occupant profiles, room details, rent and utility amounts, meter readings, security deposits, billing records, payment statuses, arrears, maintenance details, receipts, PDF files, tenant-portal credentials (tenant PINs, tenant usernames and password hashes), QR access keys, and notes.

### 3.5 KYC and identity documents

Where you use the KYC feature, the Platform stores occupant identity documents — including Aadhaar-related documents (front/back/combined) and employment-related documents — together with the occupant's name, mobile number and upload date. These are sensitive records; you must only upload them where lawful, necessary and supported by required consent or another valid legal basis.

### 3.6 Data you export, import, or back up

Export files (CSV, Excel, ZIP), imported datasets, and backup archives contain the tenant, billing and KYC data described above. The Excel export, for example, may contain decrypted tenant PINs; you are responsible for handling such files securely.

**We do not intentionally collect** biometric data, bank-account passwords, card numbers, CVVs, or any information unnecessary for operating the Platform. The Platform has no advertising or behavioral-profiling modules.

---

## 4. Purposes of Processing

PROPAURA processes personal data only for the following purposes connected with providing the Platform:

1. Creating, authenticating, securing and administering landlord accounts;
2. Providing rental-property, tenant, occupant, room, billing, receipt, payment and reporting functions;
3. Generating professional receipt PDFs and calculating rent, utility, maintenance, arrears, deposit and payment figures from data you enter;
4. Operating the tenant self-service portal (QR unlock, PIN/password login, password reset, receipt access, KYC upload);
5. Storing and managing KYC and identity documents where you lawfully use that feature;
6. Facilitating WhatsApp receipt-sharing and reminder messages that you initiate (the Platform only generates a `wa.me`-style link; the message is composed and sent from your own WhatsApp application/account);
7. Enabling data export, import, backup, restore and tenant-recovery functions you request;
8. Maintaining audit logs and protecting the Platform against unauthorized access, fraud and abuse;
9. Complying with applicable legal, accounting, tax and security obligations;
10. Responding to support, privacy and grievance requests.

PROPAURA does **not** process data for advertising, data brokerage, or any purpose outside this list. The landlord's data entered into the Platform is processed for these purposes; the Platform does not independently determine the landlord's purpose for entering tenant or occupant data.

---

## 5. Data Retention

| Data category | Retention approach | Basis in code/configuration |
|---|---|---|
| Active landlord-account data | Retained while your account is active, plus a reasonable wind-down period | `landlord_accounts` table |
| Audit logs (landlord and tenant) | Approximately 30 days, then cleaned up | `audit_log_retention_days: 30` configuration |
| Sessions | Until session expiry; 30 days without "remember me", 180 days with | `expires_at` on `landlord_sessions` |
| Receipts and billing records | Retained while your account is active; archiving marks records `ARCHIVED` | `receipts` table, `archive_bill()` |
| Tenant PIN history | Last 5 PINs (rolling history) | `tenantPin_history` table |
| KYC/occupant documents | Until you delete them or the account closes | `occupants` table; file deletion on occupant delete |
| Tenant recovery snapshots | 30 days after permanent tenant deletion, then auto-purged | `tenantRecoveryRetention` (30 days) |
| Backups | Managed by rotation — approximately 30 daily and 12 weekly backup archives | `max_daily: 30`, `max_weekly: 12` |
| Import-job records | Kept for audit of import activity | `import_jobs` tables |

Where consent is withdrawn and no other lawful basis or legal retention requirement applies, personal data will be deleted or anonymised within a reasonable period, subject to lawful retention, security, backup, fraud-prevention and dispute-resolution requirements. Backups and recovery archives may survive the underlying deletion for a limited period to protect against data loss.

---

## 6. Sharing and Disclosure

PROPAURA may disclose personal data only as necessary to operate the Platform or comply with law, including to:

- The landlord and authorised users of the landlord's account;
- Tenants/occupants through the access-controlled tenant portal associated with their tenancy;
- Authorised platform-administrator and support personnel who operate, secure and maintain the Platform;
- Infrastructure, hosting, storage, authentication, email, backup and support service providers used to operate the Platform;
- Google, if you choose Google sign-in (governed by Google's own terms and privacy policy);
- WhatsApp/Meta only to the extent that a link you initiate opens WhatsApp on your own device; PROPAURA does not transmit tenant data to Meta;
- Regulators, courts, law-enforcement agencies or other parties where disclosure is required by law or necessary to protect rights, safety or the Platform's security.

PROPAURA does **not sell** personal data. PROPAURA is not responsible for a landlord's independent sharing of exported files, PDFs, screenshots, WhatsApp messages, emails, or data downloaded from the Platform.

---

## 7. Data Security Measures

The Platform implements the following technical and organisational measures (as present in the supplied source code):

- **Password hashing** with Argon2id; plaintext passwords are not stored;
- **Hybrid encryption** using RSA-OAEP key exchange and AES-256-GCM encryption for protected payloads;
- **JWT-based session tokens** with HMAC-SHA256 signing and session rotation on refresh;
- **TOTP two-factor authentication** support for landlord accounts;
- **Brute-force protection** — account lockout after repeated failed login attempts;
- **Access separation** between platform administrators, landlords and tenants, with tenant access scoped to the owning landlord;
- **Audit logging** of login, signup, password, TOTP, tenant and administrative events;
- **Backup integrity verification** using SHA-256 checksums;
- **SQLite WAL mode** for database consistency.

No online service is completely secure. You are responsible for keeping your credentials, devices, tenant portal links, PINs, exported files, backups and downloaded records confidential, and for promptly reporting suspected unauthorized access.

---

## 8. Your Obligations as Landlord

As a condition of account creation and continued use, you agree:

1. You will not create an account with false or misleading identity information;
2. You have lawful authority for every tenant, occupant or third-party record you enter, and you will provide affected individuals with an appropriate notice and obtain valid consent where required;
3. You will not upload unlawful, inaccurate, irrelevant, excessive, misleading or unauthorized data, including KYC or Aadhaar-related documents without a lawful basis;
4. You are responsible for tenancy, billing, KYC, communication and legal-compliance decisions made using the Platform, and for responding to tenant requests about data you hold;
5. You will not use the Platform for surveillance, discrimination, harassment, fraud, unlawful eviction or any illegal activity, and you will not attempt to bypass access controls or access another landlord's data;
6. You understand that Platform outputs — receipts, calculations, exports and reports — are generated from data **you** enter and are not legal, tax, accounting or compliance advice; you must verify them independently.

---

## 9. Data Principal Rights

Subject to the DPDP Act and applicable law, as a landlord you may:

- **Access** a summary of personal data held about you;
- **Correct** inaccurate or incomplete personal data (including by updating profile settings or contacting the Privacy contact);
- **Erase** personal data that is no longer necessary, where no legal or retention obligation prevents it (including permanent deletion of tenant records and requesting account closure);
- **Withdraw consent** for consent-based processing (note: withdrawal may prevent account creation or continued service where the data is essential; prior lawful processing remains valid);
- **Nominate** another individual to exercise your rights in case of incapacity or death;
- **Grieve** — raise concerns through the contact details in Section 11.

For tenant data you enter, you remain responsible for responding to those individuals' access, correction and erasure requests, using the Platform's own tools (export, delete, archive) where available.

---

## 10. Retention of Your Own Data and Account Closure

You may request account closure and early deletion of your account by contacting the Privacy / Grievance contact. Upon verification, PROPAURA will revoke active sessions, delete the account record and its directly linked data to the extent required, subject to lawful retention, backup, audit, fraud-prevention and dispute-resolution obligations. A deletion certificate may be provided within a reasonable period after processing.

---

## 11. Contact, Grievance Redressal and Data Protection Board

**Privacy / Grievance Contact (also acting as the Data Protection Officer contact):**

| Attribute | Detail |
|---|---|
| Name | Vijay Kumar Sharma |
| Email | vijaykrsha@hotmail.com |
| Phone | +91 95913 0381 |
| Postal address | 1E, Shiv Durga Vihar Lakarpur, Surajkund Faridabad, Faridabad, Haryana, Pin - 121009 |
| Website | vijaykrsha.online |

For rights requests, use the subject line `Privacy Request – Access / Correction / Erasure / Consent Withdrawal / Grievance` and include your registered email or username and a description of your request. PROPAURA will acknowledge requests promptly and respond within the period prescribed by applicable law.

If your grievance is not resolved to your satisfaction through the mechanism above, you may lodge a complaint with the **Data Protection Board of India** through the portal or mechanism notified by the Government of India. Complaints to the Board generally follow use of the Data Fiduciary's grievance mechanism first.

---

## 12. Limitation of Liability

To the maximum extent permitted by the DPDP Act, 2023 and other applicable laws:

1. **Scope of responsibility.** Vijay Kumar Sharma / vijaykrsha.online is responsible **only** for the source code and default configuration of the PROPAURA Platform. Liability is limited to defects in the logic of the provided source code and default configurations.

2. **No responsibility is accepted** — unless and to the extent the issue arises from a defect in the provided source code — for:
   - Data entered, uploaded, imported, exported, shared, deleted, restored or retained by a landlord, tenant, occupant or other user, including incorrect, incomplete, outdated, fraudulent, unauthorized or unlawful data;
   - Deployment configuration, including Docker volumes, environment variables, reverse proxies, server hardware, hosting providers, operating systems, or any environment other than the default configuration supplied with the source code;
   - Any tenancy, billing, rent, meter, payment, receipt, KYC, communication, eviction, legal, tax or compliance decision made by a landlord using the Platform;
   - Loss, compromise or misuse of login credentials, tenant PINs, tenant portal links, exported files, PDFs, backups or third-party communication channels resulting from landlord or user conduct;
   - Third-party services — including Google sign-in, WhatsApp, email, hosting, network, browser, operating-system and device providers — and their privacy practices, availability, security or failures;
   - Platform interruption, maintenance, data corruption, cyber incidents or data loss where the landlord failed to use available backup/export features or to maintain independent copies;
   - A landlord's failure to obtain required consents, provide privacy notices, comply with applicable law, or verify Platform-generated information.

3. **No warranty.** The Platform is provided "as is" and "as available" without warranties of uninterrupted, error-free, secure or loss-free operation, except where mandatorily implied by the Indian Contract Act, 1872.

4. **Statutory carve-out.** Nothing in this Policy excludes or limits liability that applicable law does not permit to be excluded or limited, including liability for fraud, wilful misconduct, or legally non-waivable privacy and security obligations.

---

## 13. Personal Data Breaches

If PROPAURA becomes aware of a personal-data breach, it will take reasonable steps to assess, contain, mitigate and investigate the incident, and — where required by applicable law — notify affected individuals and the Data Protection Board of India with the required information.

---

## 14. Children's Data

Landlord accounts are intended for use by persons who have legal capacity to enter into the PropAura Terms and Conditions. If you process data of a minor tenant, you must obtain verifiable guardian consent where required by law and comply with all applicable obligations before entering or uploading that data.

---

## 15. Changes to this Policy

PROPAURA may update this Policy from time to time to reflect changes in the Platform, legal requirements, data practices or security measures. Each revision will carry a new effective date and version number, and the current version will always be available through PropAura or vijaykrsha.online.

Where a change materially affects how personal data is processed, PROPAURA will provide an appropriate notice and seek renewed consent where required before continuing that processing. Continued use of the Platform after an updated version is published constitutes acceptance of the revised Policy, except where renewed consent is required by law.

---

## 16. Governing Law

This Policy is governed by the laws of India. Subject to applicable law, disputes arising under this Policy will be subject to the exclusive jurisdiction of the competent courts at **Faridabad, Haryana, India**.

---

## 17. Consent Declaration and Checkbox

By selecting the checkbox below and submitting account creation, I declare that:

1. I have read, understood and agree to this Privacy Policy;
2. I consent, under the Digital Personal Data Protection Act, 2023, to the processing of my personal data for the purposes described in this Policy;
3. I understand that my landlord account cannot be created unless I accept this Policy and the PropAura Terms and Conditions;
4. I confirm that I am authorised to create this account;
5. I accept that I am the Data Fiduciary for tenant, occupant and third-party data I enter, and that I am responsible for lawful collection, notice, consent and handling of that data;
6. I accept the liability limitations and exclusions in Section 12, to the maximum extent permitted by law;
7. I agree to the retention practices in Section 5 and understand my rights under Sections 9–11.

> **[ ] I have read and agree to the PROPAURA Privacy Policy. I consent to the processing of my personal data for landlord account creation and rental-property management, and I accept the responsibility and liability provisions above. I understand that my account cannot be created unless I accept this Policy.**

---

*This Privacy Policy is issued in compliance with the Digital Personal Data Protection Act, 2023 (Act No. 22 of 2023), Government of India.*
*Document was prepared from a review of the PROPAURA source code (v3.0.0). It is a practical document, not a substitute for legal advice — an Indian privacy/technology lawyer should review the final wording, retention periods and consent workflow before production use.*
*Version 2.0 — Effective 28 August 2026.*
