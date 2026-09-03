# Data Protection Impact Assessment (DPIA) — LookMaxx

> **Draft for a solo founder.** Required under **GDPR Art. 35** because we process biometric data at scale for a potentially vulnerable (body-image-sensitive) audience. Complete the `[ ]` placeholders and have a privacy professional review before launch.

---

## 1. Why a DPIA is required

Art. 35(3) requires a DPIA before processing when it involves **special-category (biometric) data on a large scale** or new technologies with **high risk** to individuals. Both apply here.

## 2. Description of processing

- **Nature:** automated facial analysis — detect a face, extract features, compute an overall score (30–95) and per-feature scores, then generate a personalized 90-day plan.
- **Scope:** consumer web app; typically one photo per analysis; plans and progress per user.
- **Context:** voluntary self-improvement — users upload a selfie and receive feedback.
- **Purpose:** provide a facial-aesthetics score and self-improvement plan (commercial service).

## 3. Data subjects, data, and retention

- **Data subjects:** registered users aged 16+.
- **Data:** email, hashed password, **face photo (biometric)**, scores, plan, check-ins, payment (Stripe).
- **Retention:** photos auto-purge after 30 days unused or on deletion; scores/plan for account life; logs 90 days; consent log 6 years.

## 4. Necessity & proportionality

- The face photo is **necessary** to compute a face score — the core of the product.
- We **minimize**: no location/social data; the AI vendor (DeepSeek) receives **scores only, never the photo**; no third-party trackers; photos private by default.

## 5. Risk assessment (raw)

| Risk | Likelihood | Severity | Raw risk |
|---|---|---|---|
| Unauthorized access to face photos (breach) | Low | High | Medium |
| Re-identification via Explore | Medium | High | High |
| Body-image harm to vulnerable users | Medium | Medium | Medium |
| Transfer of data to non-EU AI (DeepSeek) | Low | Medium | Medium |
| Incomplete erasure on account deletion | Medium | High | High |
| Processing under-16 biometric data | Low | High | Medium |

## 6. Mitigations & controls

| Risk | Mitigation | Spec ref |
|---|---|---|
| Breach | TLS + at-rest encryption, JWT owner-scoping, logs never record faces/tokens | §5, §20.8, §21.3 |
| Re-identification | Explore opt-in + blurred, no raw face URLs (P1 fix) | §5.11, §20.5 |
| Body-image harm | neutral coaching tone, "never shame", explicit non-medical disclaimer | §2, §20.6, ToS §4 |
| AI transfer | DeepSeek scores-only + SCCs; deterministic rule-based fallback | §20.4 |
| Incomplete erasure | `DELETE /profile/delete` cascades + Cloudinary purge; 30-day purge cron | §20.6, §20.7 |
| Under-16 | age gate at signup (16+) | §20.1 |

## 7. Residual risk (after mitigations)

| Risk | Residual | Acceptable? |
|---|---|---|
| Breach | Low | Yes — with 72 h notification plan |
| Re-identification | Low | Yes |
| Body-image harm | Low–Medium | Yes — with clear disclaimers |
| AI transfer | Low | Yes |
| Incomplete erasure | Low | Yes |
| Under-16 | Low | Yes |

## 8. Conclusion & sign-off

The processing is **necessary and proportionate**. With the mitigations above, residual risk is **acceptable**.

- **Controller:** `[name]`
- **Date:** `[ ]`
- **Signature:** `[ ]`

## 9. Review

Review this DPIA annually, or immediately after any significant change (new AI vendor, new feature, new data type, new region).
