# LookMaxx — Psychology & Conversion Playbook

> **Single source of truth** for every visual, word, and interaction decision in the LookMaxx web MVP.
> **Rule: if a design or copy choice isn't justified in this file, it does not ship.**
> Read order: this file → `ROADMAP.md` (what we build) → `CONTEXT.md` (what exists today).

---

## 1. Who we sell to — and who we refuse to hurt

### Primary user
- Young men, **16–30** (core: 16–24).
- High screen-time; TikTok / Instagram / YouTube native.
- Feels "invisible" or "average" in dating and social situations.
- Already searches "looksmaxxing", "mewing", "jawline exercises", "skincare for men".

### Psychological drivers → product mapping
| Driver | What the product must do |
|---|---|
| **Insecurity** | Give a number that tells them where they stand — framed as a *baseline to beat*, never a verdict. |
| **Hope** | Make change feel possible *within weeks*, not years. |
| **Status** | Give a score they can screenshot and send to a friend. |
| **Control** | A 90-day plan with daily 2-minute tasks = agency over their own face. |
| **Identity** | "Become a better version of you" — never "fix your flaws". |

### Emotional-safety guardrails (non-negotiable — this is a young, anxious audience)
1. The score is always **"your starting point"**, never "you are ugly".
2. **Banned words**: ugly, hopeless, broken, defective, hopeless, disgusting, inferior.
3. Improvement is always framed as achievable: *"Up to +8 points in 90 days."*
4. **No leaderboards ranking real users against each other** (humiliation risk). Only self-vs-past comparison.
5. **Age gate 16+** with explicit disclaimer: *"This is an AI estimate for motivation, not medical or psychological advice."*
6. Never promise surgery-level results or body-dysmorphic outcomes.

---

## 2. Visual design system (black + gold premium)

### 2.1 Color tokens
| Token | Hex | Use |
|---|---|---|
| `--bg` | `#0A0A0A` | App background (near-black, not pure `#000` to avoid eye strain) |
| `--surface` | `#141414` | Cards, panels |
| `--surface-2` | `#1C1C1C` | Elevated / hovered cards |
| `--border` | `#2A2A2A` | Hairline borders |
| `--gold` | `#D4AF37` | Primary accent (buttons, highlights, score ring) |
| `--gold-bright` | `#E6C25A` | Hover / active gold |
| `--gold-dim` | `#8A7433` | Muted gold (secondary text, disabled) |
| `--text` | `#F5F5F0` | Primary text (off-white, warm) |
| `--text-muted` | `#9A9A93` | Secondary text |
| `--text-faint` | `#5C5C57` | Captions, placeholders |
| `--success` | `#4ADE80` | Positive deltas, "improving" |
| `--danger` | `#F87171` | Errors, "declining" |
| `--warning` | `#FBBF24` | Warnings, "stable" |

**Gold is scarce, not wallpaper.** Gold is for: the big score number, the primary CTA, the streak flame, the active nav state, and progress highlights. Everything else stays monochrome so gold reads as "premium/achievement".

**Score color scale** (0–100): `<40` `#F87171` · `40–54` `#FB923C` · `55–69` `#FBBF24` · `70–84` `#4ADE80` · `85+` `#D4AF37`.

### 2.2 Typography
- **Display / numbers**: **Space Grotesk** (geometric, technical, masculine). Used for headings, hero, the score, and any stat.
- **Body**: **Inter** (neutral, readable at 14–16px).
- **Numbers**: always `font-variant-numeric: tabular-nums` so animated scores/countdowns don't jitter.
- Load via `next/font/google` (zero layout shift, self-hosted, no tracking).
- Type scale (1.25 ratio): 12 / 14 / 16 / 20 / 25 / 31 / 39 / 48. The hero score can go up to **88px** bold.

### 2.3 Motion (Framer Motion, 150–250ms)
- Purposeful, never decorative: score count-up, progress-bar fill, streak pulse, before/after slider, page transitions.
- Easing: `cubic-bezier(0.22, 1, 0.36, 1)` (ease-out-expo feel).
- Respect `prefers-reduced-motion` (disable all non-essential animation).

### 2.4 Layout & spacing
- 8px grid. Max content width `1200px`. Cards `radius 16px`, buttons `radius 12px`, pills `radius 999px`.
- Mobile-first; the 16-year-old is on a phone.

---

## 3. Copy that converts (Cialdini's levers, applied)

| Lever | Application in LookMaxx |
|---|---|
| **Reciprocity** | Give the first score **free** with zero friction → they feel they "owe" a signup. |
| **Social proof** | Real anonymised transformations from `/explore`. Only use a count ("12,400+ guys scored") if it's *true*. |
| **Authority** | "Built on facial-analysis models + a 90-day coach plan." Never claim medical accuracy. |
| **Liking** | Coach-like voice, first name, warm-but-direct. Never corporate robot tone. |
| **Scarcity** | "Your 🔥 streak resets tonight", "Free analyses left: 1". |
| **Commitment & consistency** | Onboarding micro-commitments: "pick one goal" → then the plan. Small yes leads to the big yes. |
| **Unity** | "Guys like you", "the ones who stick with it" — tribal identity, not shame. |

### Word-level rules
1. Second person: **"you"**, never "the user".
2. Active imperative CTAs: *"See your score"*, *"Start Day 1"*, *"Lock in your streak"*.
3. **Specific numbers beat adjectives**: "+2.3 since last week" > "you improved".
4. **Loss framing beats gain framing** for retention ("don't lose your streak") while **gain framing** wins for first-time action ("unlock your plan").
5. One emoji per line, max. No exclamation spam. No "!!!".

---

## 4. Engagement loops (Hooked + Peak-End + Zeigarnik)

- **Hooked model**: `Trigger` (streak-about-to-expire push) → `Action` (upload/check-in, <2 min) → `Variable reward` (new score, new AI tip, new milestone) → `Investment` (streak count, plan progress, photo timeline).
- **Peak-End rule**: The Day-30/60/90 **before/after photo comparison** is the emotional "peak" and the plan's "end" — make it a celebration.
- **Zeigarnik effect**: Show incomplete tasks ("2 of 5 done today") on the dashboard — open loops pull users back.
- **Streak = the loss-aversion engine** — already implemented in backend `_update_streak()` and surfaced via `/progress/streak`.

---

## 5. Monetization psychology (freemium)

- **Free tier**: 1 analysis + basic score + streak. Enough to get hooked.
- **Paywall timing**: *after* the first score is revealed (the hook), never before. Reveal score → "Want your full 90-day plan + unlimited check-ins?" → paywall.
- **Anchoring**: show monthly equivalent *next to* the annual price ("$9.99/mo, billed yearly — save 58%").
- **Decoy effect**: 3 tiers — **Free / Pro / Elite**. Pro is the target; Elite exists to make Pro look like the smart choice.
- **Loss framing**: "Your streak data and photo history stay synced on Pro" + "Cancel anytime" (reduces risk, the #1 objection).
- **Affiliate products** (`/products`) are the *secondary* monetization — never before the plan value.

---

## 6. The 16-year-old consumer — final acceptance checklist

Every screen must pass this: **"Would a 16-year-old actually keep using this, or screenshot it to mock it?"**

1. ⚡ **5-second rule** — score visible in <5s of finishing upload.
2. 📸 **Screenshot-able** — the result is a clean, shareable card.
3. 🆓 **Free first** — no card required to see the number.
4. 🚫 **No cringe** — confident tone, zero desperate vibes.
5. ⏱️ **2-minute tasks** — daily actions a real teenager can do.
6. 🖤 **Premium dark look** — black + gold reads "premium", not "scam".
7. 🔥 **Streak fear** — losing a streak must feel like a real loss.

---

## 7. Measurement (what "working" means)

| Funnel step | Metric | Target |
|---|---|---|
| Visit → Signup | Conversion | ≥ 15% |
| Signup → First upload (activation) | Activation rate | ≥ 60% |
| Upload → Day-2 return | D2 retention | ≥ 40% |
| Free → Pro | Pay conversion | ≥ 3% |
| Pro → Referral/share | Viral coefficient | > 0.3 |

> If activation or D2 retention misses target, fix **friction** and **hook** before adding features. More features do not fix a leaky funnel.

