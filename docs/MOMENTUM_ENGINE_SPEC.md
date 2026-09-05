# Momentum Engine — Feature Spec (Glow · The Arc · Glow-Ups)

> **One engine, three legs, one story.** Glow shows you the *future*, The Arc builds the *present*, Glow-Ups shares the *result*. Together they turn the slow, sparse payoff of a 90-day looksmaxxing plan into a **daily, variable, genuinely happy habit** — the retention machine LookMaxx is missing.
>
> **Status:** Proposed — awaiting build go-ahead. Slice order: Glow → The Arc → Glow-Ups.
> **Read with:** `PSYCHOLOGY.md` (design/psych tokens), `PRODUCT_SPEC.md` (master spec), `CONTEXT.md` (current state).

---

## 1. The problem this solves

Looksmaxxing has one brutal retention flaw: **real physical change takes weeks-to-months.** A user uploads a photo, gets a score, gets a plan — and then the reward loop goes *silent* until the next re-score. Nothing pulls them back **daily**. Without a daily hook, streaks decay, plans get abandoned, and the free→paid funnel leaks.

The fix is not more content. It's a **daily variable-reward loop** built on assets the app already has (score, potential score, archetype, streak, photos, plan tasks) — so it costs ~$0 to run and slots into the existing Free/Pro/Elite ladder.

---

## 2. The psychology: gambling's engine, wired to genuine happiness

Gambling is addictive because of **six mechanisms**. The ethical move is to reuse the *mechanism* but rewire the *payoff* to something **true**. In gambling the "win" is fake and zero-sum; here the "win" is **real progress** (you actually showed up, you actually got closer). Same dopamine, produced by something honest — that is the difference between *genuine happiness* and *surface tension*.

| # | Gambling mechanism | Why it's addictive | Our ethical version | Genuine emotion it produces |
|---|---|---|---|---|
| 1 | **Variable-ratio reward** (slot machine) | You never know when the win lands | Daily "open" with a random *type* of true reward | Surprise + hope |
| 2 | **Anticipation / curiosity gap** | Tension before the reveal | "Tomorrow you'll see clearer" | Excitement + meaning |
| 3 | **Near-miss** | "Almost!" drives one more try | "You're +2% closer to your potential" (true) | Momentum + self-efficacy |
| 4 | **Progressive jackpot** | The pot grows; you can't walk away | Your future face sharpens across 90 days | Anticipation + identity |
| 5 | **Collection / completion** (Zeigarnik) | Open loops demand closure | Badge trees, quest lists, movie trailers | Competence + pride |
| 6 | **Social proof / status** | "People like me won" | Anonymized real transformations | Hope + belonging |

**The non-negotiables (carried from `PSYCHOLOGY.md`):**
- Every reward must be **true** — the surprise is *which* genuine insight you get, never a fabricated score or inflated "potential."
- **No shame, no loss-aversion dark patterns.** Missing a day = "pick up where you left off," never punishment. Streaks are **gain-framed** ("continue your streak") for daily action.
- **No leaderboards ranking real users.** Only self-vs-past.
- **No fake scarcity, no fake urgency, no fake reviews.**
- **Age gate 16+**; anything social (Glow-Ups feed) is **18+ only, opt-in, anonymized.**
- **Zero AI per interaction** — all loops are deterministic (see §4). The dopamine is manufactured with *randomness + timing*, which costs nothing.

---

## 3. Global rules (shared by all three features)

Hard constraints every screen must satisfy, drawn from `PSYCHOLOGY.md` and `PRODUCT_SPEC.md §2`.

1. **One reveal per calendar day** — reuse the existing rule in `progress_engine.py` (a user can only check in once per real day). All daily loops share the same server UTC date, so they can never be farmed by refreshing or changing the device clock.
2. **Server-authoritative gating** — the browser is untrusted. Every premium endpoint calls `require_pro` / `require_elite` independently (see `entitlements_service.py`); the client only gets lock chips + teasers.
3. **Gold is scarce, not wallpaper** — gold (`#D4AF37`) is reserved for the reveal moment, the level-up "ding," the streak flame, and the score. Everything else stays monochrome.
4. **Banned words** — ugly, hopeless, broken, defective, disgusting, inferior, "fix yourself." Never shipped.
5. **Screenshot-able** — every win (reveal, level-up, badge, movie) must be a clean shareable card.
6. **Copy voice** — second person, active imperative ("Open today's Glow", "Lock in your streak"), specific numbers over adjectives.
7. **Deterministic-first** — follow `insights_service.py`: derive everything *locally* from an already-computed score/breakdown/streak. No DeepSeek, no Redis, no torch/mediapipe in the daily loop.
8. **Fast feels premium** — reveal animations 150–250ms (Framer Motion); pre-fetch state on screen load, no blocking network before a reveal.

---

## 4. Architecture (reuse, don't build new infra)

All three features follow the exact pattern of `insights_service.py` — deterministic, local, zero-cost — and reuse the existing models, streak engine, and entitlements matrix.

```
Browser (Next.js 15) ──HTTP/JSON──▶ FastAPI
   │ TanStack Query (cached state)      │ JWT auth (existing)
   │ CSS blur + Framer Motion reveal    │ new: glow.py, arc.py, glowups.py routers
   ▼                                    ▼
Cloudinary (existing photos)      Postgres (new tables below)
                                    │ no new services needed:
                                    │  • random picks = secrets.randbelow (stdlib)
                                    │  • streak/day  = progress_engine.py (existing)
                                    │  • archetype   = insights_service.py (existing)
                                    │  • potential   = score_calibration.py (existing)
```

**No new third-party service. No new AI calls. No ML in the loop.** The only new backend code is three routers, a few SQLAlchemy tables, and small pure-python reward/quest/badge generators — all unit-testable.

**New entitlements** (added to `entitlements_service.FEATURES` so `/entitlements` surfaces them for the paywall UX):

| key | name | tier |
|---|---|---|
| `glow_daily` | Daily Glow reveal | free (1/day) → richer reveals on Pro/Elite |
| `glow_full_reveal` | Day-90 full future-you reveal + share card | elite |
| `arc_engine` | XP, levels, quests, badges | pro |
| `glowups_feed` | Anonymized transformation feed | free (hook) |
| `glowups_movie` | Your personal transformation movie | elite |

---

## 5. Feature 1 — GLOW (daily future-you reveal)

### 5.1 One-liner
Every day you get **one free "open"** that reveals a piece of *your own future* — and the more days you show up, the **sharper** (and bigger) the reveal gets.

### 5.2 Curiosity driver (the hook)
**"What's behind today's reveal?"** + **"What will I look like?"** The open-box moment is pure anticipation — the user *wants* to see what they got, and *wants* to see their face come into focus one notch more. The blur→sharp mechanic is a literal, physical representation of "you're getting closer," far more gripping than a number.

### 5.3 Happiness driver (the genuine payoff)
**Hope + surprise + meaning.** The reveal is always *genuinely you* — your own photo, progressively sharper — so the win is "I'm becoming something," not "I won a prize." At Day 90 the jackpot is the full before/after: proof you changed.

### 5.4 The mechanic

**Daily open (variable reward).** One per calendar day. `POST /glow/open` returns one reward, weighted by rarity:

| Rarity | Weight | Reward | What the user feels |
|---|---|---|---|
| **Common** | ~60% | "Micro-win" — a *true* small positive (streak milestone, "+N% to potential", a 2-min tip) | "Something moved" |
| **Rare** | ~25% | "Future-you glimpse" — blur→sharp reveal of your own photo | "I can see it coming" |
| **Epic** | ~10% | "Unlock" — mini-lesson / affiliate spotlight / badge preview | "I got something real" |
| **Legendary** | ~5% | "Gold Glow" — streak-gated guaranteed glimpse + share card | "This is mine" |

**Blur→sharp (zero-AI).** The glimpse is the user's **own baseline/latest photo** rendered with CSS `filter: blur(Xpx)`, where `X = clamp(0, 24 - (day * 24/90), 24)`. Day 1 = 24px (silhouette), Day 90 = 0px (full). **Honest copy always:** *"This is you — sharper every day you show up."* We never claim AI predicted a fake face (that would be expensive *and* a lie).

**Streak jackpot (progressive).** Consecutive daily opens build a **Glow Streak**:
- Day 7 → guaranteed **Rare** (glimpse).
- Day 30 → guaranteed **Epic** (unlock).
- Day 90 → **Legendary "full reveal"** (0 blur + before/after slider + share card).

This is the slot-machine jackpot — except the jackpot is *your own consistency*.

### 5.5 Screens & states

| State | What renders |
|---|---|
| **Locked (no photo)** | "Upload a photo to unlock your first glimpse" → nudges activation (the one place we gate the *hook*). |
| **Ready** | Gold card, blurred thumbnail teaser, "1 open available today", countdown to tomorrow. |
| **Opening (150–250ms)** | Shake → gold flash → reveal (the "slot machine" beat). |
| **Result** | Reward card + specific copy + share button. |
| **Already opened today** | "Come back tomorrow — your streak is 🔥N" (never shaming). |
| **Empty history** | "Your first reveal is waiting." |
| **Error** | "Couldn't open — tap to retry" (never crash; see `PRODUCT_SPEC.md §9`). |

### 5.6 API contract

```
GET  /glow/state        → { opened_today, glow_streak, next_milestone_day, today_unlocked }
POST /glow/open         → { rarity, reward_type, payload, glow_streak }  (idempotent: 200 + cached if already opened)
GET  /glow/reveals      → [ { day, rarity, reward_type, opened_at } ]  (paginated history)
```
Gating: `glow_daily` free (1/day); Pro/Elite get weighted-toward-rarer reveals; `glow_full_reveal` (Day-90 render) is **Elite**.

### 5.7 Data model (new tables)

```python
class GlowState(Base):
    __tablename__ = "glow_states"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    last_open_date = Column(Date, nullable=True)          # server UTC date
    glow_streak = Column(Integer, default=0)
    longest_glow_streak = Column(Integer, default=0)
    total_opens = Column(Integer, default=0)
    milestone_flags = Column(JSON, nullable=True)          # {"day30_claimed": true, ...}
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class GlowReveal(Base):
    __tablename__ = "glow_reveals"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    day = Column(Integer, nullable=False)                   # calendar day of the plan
    rarity = Column(String(16), nullable=False)             # common|rare|epic|legendary
    reward_type = Column(String(32), nullable=False)        # micro_win|glimpse|unlock|gold_glow
    payload = Column(JSON, nullable=True)                   # the deterministic reward
    opened_at = Column(DateTime, server_default=func.now(), index=True)
    __table_args__ = (Index("idx_glow_user_day", "user_id", "day"),)
```

### 5.8 Edge cases / side cases

1. **Double-open same day** → idempotent, return the already-generated reveal (no re-roll, no farming).
2. **Missed days** → `glow_streak` resets, but reveal *quality* is day-based not streak-based, so no loss-aversion panic. Copy: *"Pick up where you left off."*
3. **Clock/timezone manipulation** → all dates from `datetime.utcnow().date()` (same as `progress_engine`), not client time.
4. **No photo yet** → reward is a score-free micro-win; the glimpse variant is skipped until a photo exists.
5. **Free-tier first open** → guaranteed a **Rare glimpse** to hook (gain-framed first action, per `PSYCHOLOGY.md §3`), then normal weights.
6. **Unlucky streak of commons** → a "pity timer" guarantees a glimpse at least every 3rd open (prevents frustration, keeps hope alive).
7. **Deleted photo** → glimpse falls back to the next available photo; if none, micro-win.
8. **Milestone double-claim** → `milestone_flags` prevents duplicate Legendary rewards.

---

## 6. Feature 2 — THE ARC (your transformation as an RPG character)

### 6.1 One-liner
Your already-existing **Archetype** (`insights_service.build_archetype`) becomes a **character class**. Every real action earns **XP**, XP levels you up a visible **skill tree**, and each level/title/badge is proof you *became* someone.

### 6.2 Curiosity driver (the hook)
**"What's today's quest?"** + **"What's my next level/title?"** + the XP bar **near-miss** ("14 XP to Level 12"). The user opens the app to close open loops: unfinished quests, an almost-full bar, a badge one action away.

### 6.3 Happiness driver (the genuine payoff)
**Mastery + identity + competence.** Leveling produces the *healthiest* form of motivation (why Duolingo/Strava work): "I am *The Sculptor*, Level 14." You feel happy because you *earned* who you are — not because the app tricked you.

### 6.4 The mechanic

**XP sources (all real actions — zero XP for just opening the app):**

| Action | XP | Cap |
|---|---|---|
| Daily check-in | +50 | 1/day |
| Daily quest complete | +100 | 1–3/day |
| Weekly photo re-score | +200 | 1/week |
| Plan task done | +20 each | 3/day |
| Streak milestone (7/14/21/30…) | +150 bonus | per milestone |

**Levels.** Deterministic curve: `level = floor(sqrt(total_xp / 100)) + 1`. A user can never "skip" levels; the number is derived from real XP, stored only for display.

**Daily quests (deterministic).** 1–3 per day, drawn from the existing `FOCUS_LIBRARY`-style task library and targeted at the user's **weakest features** (same logic as `insights_service.build_blueprint`). Completing a quest requires the matching `checkin.completed_tasks`, so XP can't be farmed by clicking "done."

**Archetype skill tree.** The archetype is the class; the tree's nodes are the plan's **milestones** (Day 7/14/21/30/45/60/75/90) plus **feats** (first re-score, 7-day streak, 30-day streak, "jawline focus completed"). Each node = a **badge + title**.

**Titles.** `"The {Archetype}, Level {N}"` plus milestone titles — *Disciplined* (7-day streak), *Unstoppable* (30-day), *Transformed* (Day 90).

**Near-miss.** The bar always shows "*X XP to next level*" — the single strongest driver of "just one more action."

### 6.5 Screens & states

| State | What renders |
|---|---|
| **Level 1 (new)** | "You're Level 1 — complete a quest to earn your first title." |
| **Active** | XP ring, current title, "X XP to next level", today's quests (with claim buttons), skill tree. |
| **Level-up (150–250ms)** | Gold "ding" + new title reveal + share card. |
| **No quests today** | "Quests refresh tomorrow — keep your streak alive." |
| **Quest already claimed** | Disabled with ✓ (idempotent). |
| **Error** | "Couldn't claim — tap to retry." |

### 6.6 API contract

```
GET  /arc/state              → { level, total_xp, xp_to_next, title, today_quests[], badges[] }
POST /arc/quests/{id}/claim  → { xp_awarded, level, leveled_up, new_title }   (validated vs check-in; 409 if not done)
GET  /arc/badges             → [ { badge_key, name, emoji, unlocked_at } ]    (collection view)
```
Gating: `arc_engine` is **Pro** (free tier sees the XP bar + teaser "unlock your full journey").

### 6.7 Data model (new tables)

```python
class ArcState(Base):
    __tablename__ = "arc_states"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    total_xp = Column(Integer, default=0)
    current_level = Column(Integer, default=1)       # denormalized for fast reads; derived from total_xp
    quest_date = Column(Date, nullable=True)          # server UTC date quests were generated for
    quests = Column(JSON, nullable=True)              # [{"id","focus","task","xp","claimed":false}]
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class UserBadge(Base):
    __tablename__ = "user_badges"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    badge_key = Column(String(64), nullable=False)
    awarded_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "badge_key", name="uq_user_badge"),)
```

### 6.8 Edge cases / side cases

1. **XP farming** → XP only awarded for *server-verified* actions (one check-in/day already enforced by `progress_engine`); claim requires `completed_tasks` to contain the quest task.
2. **Double-claim quest** → 409 / idempotent ✓; `claimed` flag persisted.
3. **Quest generation** → deterministic per (user_id, quest_date); if none generated yet, generate on first `/arc/state` read. Same UTC-date rule.
4. **Level derivation drift** → `current_level` is recomputed from `total_xp` on every write; never trusted from the client.
5. **Badge idempotency** → `UniqueConstraint("user_id", "badge_key")`; award is insert-or-ignore.
6. **Archetype missing** (no analysis yet) → class = "The Rookie" until first score; no error, no shame.
7. **Free tier** → sees XP bar + locked quests (teaser); no XP math runs for a user who can't claim (same `enforce_*` pattern as `entitlements_service`).
8. **Quest completed but check-in rejected (dup day)** → quest stays unclaimable; consistent with existing one-check-in/day rule.

---

## 7. Feature 3 — GLOW-UPS (the payoff, in motion)

### 7.1 One-liner
Two parts. **Personal:** your photos auto-compile into a **transformation movie** with teaser trailers at Day 14/30/60 and the full cut at Day 90. **Social:** an **anonymized, opt-in** feed of real transformations — proof "guys like you did it."

### 7.2 Curiosity driver (the hook)
**"What transformation is next in the feed?"** + **"What will MY movie look like?"** The trailer mechanic creates a *Zeigarnik* loop: you've seen the opening frames, so you must see the rest. The feed is an endless, always-fresh scroll of hope.

### 7.3 Happiness driver (the genuine payoff)
**Hope + pride + belonging.** The feed shows real people's real progress (no fake faces), so it's *believable* hope. Your own movie is the emotional **peak** of the whole plan (`PSYCHOLOGY.md §4` Peak-End rule): the before/after moment of "I did that."

### 7.4 The mechanic

**Part A — Personal transformation movie (Elite).**
- Auto-compiles baseline + progress photos into a video. **MVP = Ken Burns slideshow** (CSS/`ffmpeg.wasm` crossfade, zero server cost); upgrade to server `ffmpeg` later if demand warrants.
- **Trailers** at Day 14/30/60 (10s teasers); **full movie** at Day 90 or once the user has ≥2 photos.
- **Zero-AI:** it is *their* real photos. No fabricated "future face."

**Part B — Anonymized transformation feed (free hook, 18+ only).**
- **Opt-in:** user toggles *"Share my transformation (anonymized)."* Default **off**.
- Card = blurred/cropped photo (eyes covered or silhouette) + "*Jordan, 19 · Day 78 · +11 pts*" + one-line reflection.
- **No leaderboard, no rank, no "you vs them."** Framing is always *"what's possible."*
- Seeded honest examples if empty ("these are early testers"), never fake.
- Moderation: report + block + admin review queue (reuse `AdminAction` audit pattern).

**Tier:** feed is **free** (retention hook); your own movie is **Elite**.

### 7.5 Screens & states

| State | What renders |
|---|---|
| **Feed (empty)** | Honest seeded examples + "be the first" + invite. |
| **Feed (populated)** | Infinite scroll of blurred cards; tap to reveal a fuller (still anonymized) view. |
| **Feed (locked, <18)** | Hidden entirely — minors get only their own solo movie. |
| **My movie (no photos)** | "Upload your first photo to start your movie." |
| **My movie (trailer ready)** | Teaser + "full movie unlocks Day 90 / after your next re-score." |
| **My movie (ready)** | Full before/after playback + share card. |
| **Consent toggle** | One tap on/off; "remove from feed" is instant. |
| **Error** | "Couldn't load — tap to retry." |

### 7.6 API contract

```
GET  /glowups/feed              → { items: [ { id, age, day, delta, headline } ], next_cursor }   (18+, paginated)
POST /glowups/consent           → { share_enabled }                                              (opt-in/out)
GET  /glowups/movie             → { status, trailers[], full_movie_url }                          (Elite)
POST /glowups/movie/generate    → { job_id, status }                                             (Elite, throttled)
POST /glowups/items/{id}/report → { reported: true }                                             (moderation)
```
Gating: feed is free (18+), movie is Elite; consent only applies to 18+ users.

### 7.7 Data model (new tables)

```python
class Transformation(Base):
    __tablename__ = "transformations"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_ids = Column(JSON, nullable=True)              # ordered baseline → latest
    share_enabled = Column(Boolean, default=False)        # opt-in only
    status = Column(String(32), default="pending")        # pending|trailer|ready|removed
    movie_url = Column(String(500), nullable=True)
    delta_score = Column(Float, nullable=True)
    headline = Column(String(255), nullable=True)         # the user's own one-liner
    reported_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True) # soft-delete for moderation
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

### 7.8 Edge cases / side cases

1. **Consent revoked** → instant removal from feed (status `removed`); GDPR delete already covers photo purging.
2. **Minors** → feed is **18+ only** for *both* viewing and being featured (safety); minors only ever see their own movie.
3. **Empty feed** → honest seeded examples, clearly labeled; never fabricated "12,400 guys."
4. **Identifier leak** → crop + blur + never show a full face; strip name to first name + age + day + delta.
5. **Movie with <2 photos** → status `pending` with nudge to re-score; never render an empty movie.
6. **Movie generation abuse** → throttled (e.g., 1 render / 24h) + reuses cached render if inputs unchanged.
7. **Reported item** → auto-hidden pending review (reuse `AdminAction` audit log); `reported_count` tracks spam.
8. **Same user re-opts-in** → requires re-consent + admin re-approval (prevents flip-flop abuse).

---

## 8. Unified data model (all new tables)

| Table | Purpose | Key columns |
|---|---|---|
| `glow_states` | Daily Glow open state + streak | `user_id`, `last_open_date`, `glow_streak`, `milestone_flags` |
| `glow_reveals` | Audit of every opened reward | `user_id`, `day`, `rarity`, `reward_type`, `payload` |
| `arc_states` | XP, level, daily quests | `user_id`, `total_xp`, `current_level`, `quests` |
| `user_badges` | Earned badges (idempotent) | `user_id`, `badge_key` (unique pair) |
| `transformations` | Movie + feed consent | `user_id`, `photo_ids`, `share_enabled`, `status` |

All reference `users.id` with `ondelete="CASCADE"` (consistent with existing `Photo`/`Plan`). **No changes to the existing `User`/`Photo`/`Plan` models** — the loops read what's already there (score, streak, photos) and write only their own tables.

## 9. API contract map (summary)

| Feature | Endpoints | Auth | Gating |
|---|---|---|---|
| Glow | `GET /glow/state`, `POST /glow/open`, `GET /glow/reveals` | JWT | `glow_daily` free; richer reveals Pro/Elite; full reveal Elite |
| Arc | `GET /arc/state`, `POST /arc/quests/{id}/claim`, `GET /arc/badges` | JWT | `arc_engine` Pro |
| Glow-Ups | `GET /glowups/feed`, `POST /glowups/consent`, `GET /glowups/movie`, `POST /glowups/movie/generate`, `POST /glowups/items/{id}/report` | JWT | feed free (18+); movie Elite |

All responses wrapped in the existing `APIResponse` envelope; all errors use the existing `PRODUCT_SPEC.md` Appendix A codes (`upgrade_required`, `rate_limited`, etc.).

## 10. Cross-cutting edge cases & abuse

1. **Multi-device / double-submit** → every mutation is idempotent by (user_id, server-UTC-date) or a unique constraint.
2. **Rate limiting** → reuse existing Redis rate limiter on all POSTs (prevent scrape/spam of feed and open/claim endpoints).
3. **Timezone travel** → all "today" values derive from `datetime.utcnow().date()`, never the client clock.
4. **Deactivated/deleted account** → `ondelete="CASCADE"` removes all loop state automatically.
5. **Subscription lapse** → server-authoritative `get_tier()` degrades gracefully: Arc/Elite loops return `upgrade_required` without deleting history (history returns on re-subscribe).
6. **Minor safety** → Glow and Arc are solo (safe); Glow-Ups feed is 18+ for viewing *and* featuring.
7. **Honesty** → every number shown (streak, XP, delta, "top N%") is computed from real data; no fabricated social proof or scarcity.
8. **Privacy** → faces remain private-by-default; the feed only ever shows anonymized, opted-in, adult transformations (see `docs/PRIVACY_POLICY.md` + `docs/DPIA.md`).

---

## 11. Rollout order & build sequence

Build **one leg at a time**, each additive and Elite-gated at the premium end. Do not start the next until the previous ships.

1. **Slice 1 — Glow** (highest retention-per-effort, zero cost, no social surface → lowest risk).
   - New tables + `glow.py` router + `glow_daily`/`glow_full_reveal` entitlements + frontend reveal screen + tests.
2. **Slice 2 — The Arc** (builds on the streak/check-in already shipping in Glow).
   - `arc.py` router + XP/quest/badge generators + `arc_engine` entitlement + tests.
3. **Slice 3 — Glow-Ups** (last, because it needs moderation + privacy care).
   - `transformations` table + `glowups.py` router + Ken Burns movie (client-side) + anonymized feed + consent + report + tests.

Each slice is independently shippable; the engine is fully coherent only after all three.

## 12. Testing matrix (every scenario before ship)

| Feature | Must-test |
|---|---|
| Glow | open once/day idempotent · calendar day rollover · missed-day reset · pity timer · milestone no double-claim · free→pro reveal weighting · no-photo fallback · 403 on Elite full-reveal |
| Arc | XP only from verified actions · quest claim requires completed_tasks · double-claim 409 · level derived from XP · badge idempotency · free-tier teaser 403 · quest regeneration per UTC date |
| Glow-Ups | consent default off · revoke = instant removal · <18 hidden · empty-feed seeding · report auto-hides · movie <2 photos pending · render throttle · identifier anonymization |

Unit-test every pure generator (reward weights, XP curve, blur formula, quest library, badge catalog) — deterministic, so they're fast and exact. Integration-test the routers against the existing `progress_engine` + entitlements.

## 13. Definition of done (a leg ships only when ALL are true)

1. New tables + router land with `ondelete="CASCADE"` and the same `APIResponse` envelope.
2. Every mutation is idempotent (no farming) and server-authoritative (gating enforced server-side, not client-side).
3. Copy passes the `PSYCHOLOGY.md` word rules (no banned words, gain-framed streaks, no fake scarcity).
4. Every state in §5.5/§6.5/§7.5 has a designed UI (no blank screens, no crash states).
5. Deterministic generators are unit-tested; routers integration-tested; `pytest` green.
6. The 16-year-old checklist passes: ⚡ <5s to reward · 📸 screenshot-able · 🆓 free first · 🚫 no cringe · ⏱️ <2-min actions · 🖤 black+gold · 🔥 streak fear.
7. GDPR/privacy honored (opt-in feed, deletion cascades, no biometric leak).

## 14. Cost & performance budget

| Item | Cost at MVP | Cost at scale |
|---|---|---|
| Glow (deterministic, stdlib `secrets`) | $0 | $0 (a few rows/user/day) |
| Arc (deterministic, stdlib) | $0 | $0 |
| Glow-Ups feed (DB reads) | $0 | ~$0 (paginated reads) |
| Glow-Ups movie (client Ken Burns) | $0 | $0; server ffmpeg only if video export demanded, ~$7–30/mo |
| **Total incremental** | **$0** | **~$7–30/mo** (mostly hosting, only if ffmpeg export ships) |

**No AI tokens, no new ML, no Redis growth beyond existing rate limiting.** The dopamine is manufactured with randomness + timing, not with expensive inference — that's the entire point of the Momentum engine.
