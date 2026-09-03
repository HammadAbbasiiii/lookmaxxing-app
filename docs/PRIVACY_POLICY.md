# Privacy Policy — LookMaxx

**Last updated:** 27 August 2026

> **Disclaimer:** this is a startup-quality draft for a solo founder. **Have it reviewed by a qualified lawyer in your jurisdiction before public launch.** Placeholders are marked `[like this]`.

---

## Plain-language summary

- We analyze a photo you choose to upload to give you a score and a 90-day plan.
- Your face photo is treated as sensitive **biometric data** and is **private by default** — never shown publicly unless you explicitly opt in (and then it is blurred).
- You can **export** or **delete** everything at any time, in one tap.
- We use a small number of carefully chosen service providers (listed below). None may use your data for their own purposes.

---

## 1. Who we are (data controller)

LookMaxx ("we", "us", "our"). Contact: `[support email]`.

## 2. What we collect

| Data | Example | Why we collect it |
|---|---|---|
| Account | email address, password (stored hashed) | create and secure your account |
| Profile (optional) | name, age, gender, goals, height, weight | personalize your plan |
| **Face photo (biometric)** | the image you upload | generate your score and plan |
| Analysis results | overall score, per-feature scores, strengths/weaknesses | show your result and track progress |
| Plan & check-ins | 90-day plan, daily tasks, streaks | deliver the core service |
| Payment | handled by Stripe (we never store card numbers) | billing |
| Usage | IP address, logs, rate-limit counters | security and abuse prevention |

## 3. How we use it (and the legal basis)

- **Provide the service** (contract / legitimate interest): analyze your photo, generate a plan, track progress, bill you.
- **Explicit consent** (GDPR Art. 6(1)(a) + 9(2)(a)): processing your **biometric** face photo, and any optional "feature me in Explore" sharing. You can withdraw consent at any time in Settings.
- **Legitimate interest**: security, abuse prevention, and aggregated (anonymized) service improvement.

## 4. Biometric data — special notice

Your face photo is "special category" biometric data under GDPR. We commit to:

- process it **only** to generate your score and plan;
- keep it **private by default**;
- **never** sell it or use it for advertising;
- **never** show it publicly unless you opt in to Explore (and then it is blurred/anonymized);
- delete it on request, or automatically after **30 days** of inactivity.

## 5. Who we share with (sub-processors)

| Provider | Purpose | Location |
|---|---|---|
| Cloudinary | stores and optimizes your photos | USA |
| DeepSeek | generates your plan from **scores only — never your photo** | China |
| Stripe | payment processing | USA |
| Render | app + database hosting | USA |
| Vercel | website hosting | USA |
| Upstash (Redis) | rate limiting | USA |

Each provider is bound by a data-processing agreement and may use your data **only** to provide their service to us.

## 6. International transfers

Where data leaves your region, we rely on **Standard Contractual Clauses (SCCs)**. DeepSeek receives only numeric scores — not your photo — minimizing the exposure.

## 7. How long we keep it

- **Photos:** until you delete them, or auto-purge after **30 days** of inactivity.
- **Scores / plan:** for the life of your account.
- **Consent records:** 6 years (legal requirement).
- **Logs / IP:** 90 days.

## 8. Your rights

You may ask us to **access**, **export** (machine-readable), **rectify**, **erase**, **restrict**, or **object** to processing, and **withdraw consent** — from Settings or by contacting us. You also have the right to complain to your local data-protection authority.

## 9. Children

LookMaxx is for users aged **16 and over**. We do not knowingly process the biometric data of anyone under 16.

## 10. Cookies & analytics

We do **not** use third-party advertising trackers. Any analytics we run is privacy-first and never includes your face, email, or identity.

## 11. Security

Encryption in transit and at rest, strict access controls, and logging that never records your face or password. See the security section of the project README for details.

## 12. Changes to this policy

We will post changes here and, for material changes, notify you in-app or by email.

## 13. Contact

Privacy contact: `[privacy contact email]`
