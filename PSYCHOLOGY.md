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

### 2.3 Motion — one law for the whole app ("weight, breath, reward")

Motion is how a dark, still screen earns trust. It is never decoration: every
animation either **confirms cause** (I pressed, it responded), **preserves
context** (this screen came from that one), or **pays off tension** (the wait,
the score). If an animation does none of the three, it does not ship.

**The three laws** (implemented as tokens in `globals.css`; every rule obeys
all three):

1. **Responsiveness.** Nothing on the critical path exceeds **260ms**. Under
   ~100ms a change reads as *instant* — the user credits their own action
   (causality). 150–260ms reads as deliberate and calm. 300ms+ is reserved for
   entrances that must be *noticed*, never for feedback.
2. **No lingering transforms.** Entrances animate **opacity + ≤6px** with
   `animation-fill-mode: backwards` and no forwards fill, so no `transform`
   survives them. A transform that sticks around silently becomes a containing
   block for `position: fixed` children (it breaks the mobile nav/drawer) and
   never satisfies Playwright's "element is stable" click check.
3. **Every rule has a kill switch.** All of it is disabled under
   `prefers-reduced-motion: reduce`. Motion is never load-bearing: with
   animations off every screen is complete and correct, just still.

| Token | Value | Use |
|---|---|---|
| `--dur-press` | 90ms | Contact — must read as instant |
| `--dur-quick` | 140ms | Hover / colour |
| `--dur-base` | 200ms | House default (the §2.3 band) |
| `--dur-slow` | 260ms | Arrival, settle, release |
| `--ease-arrive` | `cubic-bezier(0.16, 1, 0.3, 1)` | Decelerate = "arriving" |
| `--ease-exit` | `cubic-bezier(0.4, 0, 1, 1)` | Accelerate = "leaving" |
| `--ease-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | 1.56 overshoot = physical release |

**Physical surfaces (`.press`, `.lift`).** A press is felt *twice*: compress on
contact (90ms, `--ease-exit`, **no bounce** — bounce on contact reads as
hesitation) and spring back on release (260ms, `--ease-spring`). On touch there
is no hover, so this is the only feedback a user gets before the network
answers — it is what makes a tap feel *heard*, and it stops re-tapping. Applied
to `Button`, interactive `Card`s, mobile tabs and next-step links. Pair with
`touch-action: manipulation` (kills the 300ms double-tap delay) — the two
together are most of the difference between "website" and "app" on a phone.

**Continuity (`.screen-in`, `template.tsx`).** A screen *arrives*, it does not
hard-swap: 260ms, opacity + 6px, CSS-only (zero JS), applied once per segment in
`app/(app)/template.tsx` and `app/(auth)/template.tsx`. 6px is deliberately
below the threshold that registers as "content moved" — it reads as the page
settling, not as a slider.

**Sequencing beats simultaneity (the reveal).** At the emotional peak (the
score) the three beats are ordered and never simultaneous: the ring fills and the
number counts → the ring pops with **one** gold flare (620/900ms, finite) → the
verdict label rises in **340ms later**. Showing number and meaning together makes
a score read as *printed*; letting the number land first and answering "what does
it mean?" is what makes it feel *earned* (§4 peak-end). The label's animation has
no forwards fill, so a reduced-motion user — or a screenshot — always gets it.

**Honesty over theatre.** Progress only ever advances on a server-confirmed
stage; the `analyzing` screen shows a real elapsed timer, crossfades its rotating
copy (260ms) instead of hard-swapping, announces stage changes to screen readers
through a single `role="status"` region, and at **20s** — the point where silence
starts to feel like failure — says the one thing that matters: *nothing is lost*.
Fabricated progress bars are banned: they buy one calm minute and cost all trust.

**Haptics (`lib/haptics.ts`).** Android-only reinforcement, ≤26ms, never the
only signal. Gated on `navigator.userActivation.hasBeenActive` (no buzzing a
stranger's phone from a landing page) and on `prefers-reduced-motion` (a user who
asked the OS for calm gets calm in every channel). `tick()` on primary presses,
`success()` when a score lands, `celebrate()` reserved for Day 7/30/60/90 so it
stays special.

**Still Framer Motion** (`MotionConfig reducedMotion="user"`) for component-level
choreography that needs real springs or exit animations — drawers, celebrations,
confetti. CSS owns the system layer (entrances, press, flares) so it costs no JS
and cannot delay a tap; a second, drifting set of tokens is the thing to avoid.


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

- **Free tier**: 1 analysis + basic score + streak. Enough to get hooked, capped so users feel the loss when they hit the limit.
- **Paywall timing**: *after* the first score is revealed (the hook), never before. Reveal score → "Want your full 90-day plan + unlimited check-ins?" → paywall.
- **Anchoring**: show monthly price *first*, then the annual offer as a savings comparison with strike-through (`~~$119.88~~ → $50.40/yr`, `~~$239.88~~ → $100.80/yr`). Never show the annual price alone.
- **Decoy effect**: 3 tiers — **Free / Pro / Elite**. Pro is the target; Elite exists to make Pro look like the smart choice. Cards render **Elite → Pro → Free** so Elite anchors the price and Pro feels like a bargain.
- **Badges (social proof + aspiration)**: Pro = "Most popular" (everyone else is choosing it), Elite = "Best value" (aspirational), Free = "Start here" (low barrier).
- **$1 first month (low barrier + loss aversion)**: "Get started for $1 — your first month is $1, then $9.99/mo." A card is required up front, so the user is already "invested" and more likely to stay. Server-tracked (`has_used_first_month_offer`) so it can't be reused.
- **7-day free trial (Elite)**: card required (converts better than no-card trials); the audience is young and impulsive, so 7 days is enough to see value.
- **Loss framing**: "Your streak data and photo history stay synced on Pro" + "Cancel anytime" (reduces risk, the #1 objection). Downgrading loses Pro/Elite features.
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

