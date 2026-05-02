# RGPD Minimum Checklist

Date: 2026-05-02

## Scope

This checklist reviews the current SONAR experiment stack against a minimum GDPR baseline for:

- experimental session data
- anti-duplicate bracelet handling
- telemetry and client context
- payout management
- paused-experiment interest signups

It is not a legal opinion and does not replace controller-specific legal review.

## Data currently stored

### Direct identifiers

- `bracelet_id` in `users`
- `bracelet_id` in `consent_records`
- `requested_phone` in `payout_requests`
- `email_normalized` in `interest_signups`
- `user_agent_raw` in `session_client_contexts`

### Pseudonymous identifiers

- `bracelet_hash`
- `device_hash`
- `ip_hash`
- `user_agent_hash`
- `email_hash`
- `referral_code`
- `payout_reference`
- `client_installation_id`

### Behavioural / experimental data

- treatment assignment
- dice results and rerolls
- report value and honesty
- payment eligibility and payout status
- consent interaction timings
- telemetry events
- browser / device context

## Minimum GDPR checklist

| Item | Status | Notes |
|---|---|---|
| Identify personal data and identifiers | `PARTIAL` | Hashing exists, but several direct identifiers remain in cleartext. |
| Distinguish anonymous vs pseudonymous data | `FAIL` | Current implementation is pseudonymized at best, not anonymous. |
| Valid first-layer privacy information | `FAIL` | Missing controller identity, legal basis, retention, recipients, rights, complaint path, and DPO/contact details where applicable. |
| Valid consent for participation | `PARTIAL` | Explicit checkboxes exist, but information required for informed consent is incomplete. |
| Separate purposes by processing activity | `FAIL` | Experiment, antifraud, payout, and interest-signup purposes are not clearly separated in the information layer. |
| Data minimization | `FAIL` | Excessive client context and raw user-agent are stored. |
| Pseudonymization by design | `PARTIAL` | Good use of peppered hashes, but direct identifiers coexist in the same system. |
| Security by design/default | `PARTIAL` | Hashing is good, but default secrets/passwords remain possible if env vars are not set. |
| Retention / deletion policy | `FAIL` | No explicit retention schedule or purge workflow found. |
| Access restriction to admin-sensitive data | `PARTIAL` | Admin datasets expose payout phone, normalized email, and bracelet identifiers. |
| Accuracy / transparency of user-facing privacy text | `FAIL` | Payment privacy copy says payment data are stored in a separate system/database, but the code stores them in the same application database. |
| Rights handling (access, erasure, withdrawal, complaint) | `PARTIAL` | Withdrawal is mentioned, but the mandatory Art. 13 information set is incomplete. |

## Critical changes required

1. Replace “anonymous/anonymized” wording with “pseudonymized” until a real anonymization workflow exists.
2. Complete the first-layer privacy notice with:
   - controller identity and contact details
   - DPO contact details if applicable
   - purposes split by activity
   - legal basis for each activity
   - recipients / processors
   - retention periods or criteria
   - rights and how to exercise them
   - right to lodge a complaint with the AEPD
   - whether providing each datum is mandatory or optional
3. Correct or remove any statement claiming that payment data are stored in a separate database unless that is made technically true.
4. In production, require non-default `APP_HASH_PEPPER` and non-default admin credentials.

## High-priority technical changes

1. Stop storing `user_agent_raw`.
2. Reduce client-context collection to the minimum strictly necessary for antifraud and operability.
3. Remove `bracelet_id` from consent exports and use `session_id` or `bracelet_hash` instead.
4. Restrict `requested_phone` and `email_normalized` to strictly operational datasets and workflows.
5. Define and implement retention / purge rules for:
   - `payout_requests`
   - `interest_signups`
   - `session_client_contexts`
   - detailed telemetry and operational exports

## Medium-priority changes

1. Document the legal basis separately for:
   - experiment participation
   - antifraud
   - payout management
   - paused-experiment contact list
2. Review whether consent-metrics fields are truly necessary for the stated purposes.
3. Keep a versioned snapshot of the exact privacy text shown to the user at consent time.

## Code references

- `api-sonar-main/api-sonar-main/models.py`
- `api-sonar-main/api-sonar-main/main.py`
- `api-sonar-main/api-sonar-main/experiment.py`
- `api-sonar-main/api-sonar-main/research_admin.py`
- `sorteo-sonar-main/app/utils/clientContext.ts`
- `sorteo-sonar-main/app/utils/uiLexicon.ts`
- `project_parameters.json`
