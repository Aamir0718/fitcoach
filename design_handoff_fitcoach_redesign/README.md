# Handoff: FitCoach UI/UX Redesign

## Overview
A full visual and UX redesign of FitCoach — every existing screen, restyled. The product structure is **unchanged**: same 8 tabs, same names, same order, same routes, same features, same backend contracts. Only the look, layout, hierarchy and interaction feel change.

Target repo: `Aamir0718/fitcoach`, branch `main`, folder `frontend/`.

## About the Design Files
The `.dc.html` files in this bundle are **design references** — prototypes that show the intended look and behaviour. They are **not** production code to paste in. FitCoach's frontend is vanilla HTML + CSS + JS (`frontend/index.html`, `frontend/static/style.css`, `frontend/static/script.js`), so the task is to **re-express these designs in that existing environment**: keep `index.html`'s element IDs, `onclick` handlers and DOM structure intact wherever possible, and replace the *styling layer* plus the small number of markup blocks called out below.

Do not port React, do not introduce a build step, do not rename IDs that `script.js` queries.

## Fidelity
**High-fidelity.** Colors, type, spacing and interaction states are final. Recreate pixel-perfectly.

---

## Scope of change — what to replace, what to keep

### Replace
| Current | Action |
| --- | --- |
| `frontend/static/style.css` (296 KB) | Replace with a new stylesheet built from the tokens below. Most of the old file is theme variants, glassmorphism, glow and particle rules that the redesign removes. |
| `frontend/static/home-premium.css` / `home-premium-v2.css` | Delete. The Home hero is now a single photo band with a solid scrim — no blobs, no particles, no custom cursor, no Ken Burns. |
| `frontend/static/home-premium.js` / `home-premium-v2.js` | Delete the particle system, custom cursor, gradient-blob animation and carousel. Keep nothing but the hero data wiring if any is still used. |
| `#tab-home` markup | Rewrite (see Home below). The `switchTab()` calls on the quick-action cards must survive as links elsewhere. |

### Keep exactly
- `switchTab('home'|'chat'|'planner'|'recovery'|'progress'|'calories'|'visualos'|'profile')` — all 8, same order, same labels.
- Sidebar `.nav-btn[data-tab]` and `.bottom-nav .bnav-btn[data-tab]` structure and handlers.
- Every element ID referenced by `script.js` (`#hero-recovery`, `#home-workout-type`, `#ws-exercise-name`, `#rs-score`, `#pm-streak-val`, `#cal-result-body`, `#pf-*`, `#ghost-*`, etc.). Restyle the containers, don't rename the hooks.
- All backend calls, auth flow, onboarding field order, and the AI/recovery/nutrition logic.

---

## Design tokens

### Color
| Token | Hex | Use |
| --- | --- | --- |
| `--paper` | `#F5F3EF` | App background |
| `--surface` | `#FFFFFF` | Sidebar, raised rows, inputs |
| `--ink` | `#14120E` | Primary text, filled buttons, dark panels |
| `--ink-2` | `#38352F` | Body copy in blocks |
| `--mid` | `#4A463F` | Secondary text |
| `--muted` | `#6D685F` | Tertiary text |
| `--faint` | `#9A948A` | Labels, meta, mono eyebrows |
| `--line` | `#E3DFD7` | Hairline dividers |
| `--line-strong` | `#D8D3CA` | Section rules, input borders |
| `--accent` | `#E8442A` | Primary CTA, progress fill, active state, PR/positive delta |
| `--accent-hover` | `#C7331C` | CTA hover |
| `--dark-bg` | `#0C0B09` | Workout mode background |
| `--dark-panel` | `#141210` | Workout rest panel |
| Dark hairline | `rgba(255,255,255,.12)` | Dividers in workout mode |
| Dark text 2nd | `rgba(255,255,255,.55)` | Labels in workout mode |

**One accent only.** No gradients anywhere except the photo scrims listed under Imagery. No glow, no glassmorphism, no neon.

### Typography
- Display + UI: **Archivo** (400, 500, 600, 700, 800) — Google Fonts.
- Numeric / label: **IBM Plex Mono** (400, 500, 600) — used only for eyebrows, unit labels, timers and table meta, always uppercase with wide tracking.

| Role | Spec |
| --- | --- |
| Screen title (desktop) | Archivo 800, 44px, line-height 1, letter-spacing −0.03em |
| Hero title (Home) | Archivo 800, 76px, line-height 0.94, −0.035em, white |
| Hero title (mobile) | Archivo 800, 42px, line-height 0.96, −0.035em |
| Section heading | Archivo 800, 22px, −0.02em |
| Big number | Archivo 800, 34–84px, −0.03em |
| Body | Archivo 400, 15–17px, line-height 1.5–1.55 |
| Row title | Archivo 700, 15–17px, −0.01em |
| Eyebrow / meta | IBM Plex Mono 500–600, 10–12px, letter-spacing .14–.24em, uppercase, `--faint` |
| Button | Archivo 700–800, 12–15px, letter-spacing .1em, uppercase, `white-space:nowrap` |
| Timer | IBM Plex Mono 600, 40–84px |

### Geometry
- **Border radius: 0** everywhere except the phone-frame illustration. Squared corners are a deliberate part of the identity.
- Borders: 1px `--line` for rows, 1px `--line-strong` for inputs and section rules, 2px `--ink` for the "Coach's note" top rule.
- **Shadows: none** in the UI. The only shadow in the bundle is on the mock phone bezel.
- Desktop page padding: 40–48px. Sidebar width **236px**, 22px/14px padding.
- Mobile padding: 22px. Bottom nav 8px top / 22px bottom (safe area).
- Minimum touch target: 44px; workout-mode controls are 52–60px.

### Motion
Only three: `fcIn` (opacity 0→1, translateY 8px→0, 250ms ease-out) for the workout overlay; a bar-fill grow on progress; standard 150ms color transitions on hover. No floating, no pulsing, no particles.

---

## Screens

### Global shell
**Desktop** — 236px white sidebar, 1px right border. Logo: 30×30 black square, "FC" Archivo 800/12px white, then "FitCoach" Archivo 800/17px. Nav buttons: 42px min height, 10px/12px padding, 12px gap, a 6×6px square marker before the label (accent when active, `--line-strong` when not). Active = `--ink` background, white text, 700. Inactive = transparent, `--mid`, 500; hover `#F0EDE7`. Bottom of sidebar: Gym/Sport segmented control (1px border, active half `--ink`), then Mode / Streak readouts split left-right above a `--line` rule.

**Mobile** — white bottom nav, 1px top border, 8 equal buttons; each is an 18×3px bar (accent active / `--line-strong` inactive) over a 9px Archivo label. No icons — the labels are the affordance at this width.

### 1. Home
Purpose: answer "what am I doing today, how am I progressing, what's next".
- **Hero band** 520px tall, full-bleed photo (`deadlift.webp`, `object-position:center 35%`), scrim `linear-gradient(90deg, rgba(12,11,9,.92), rgba(12,11,9,.72) 45%, rgba(12,11,9,.15))`. Top strip: date left, "Week 6 of 12 · Hypertrophy block" right, both mono 11px `rgba(255,255,255,.65)`.
- Content left-aligned, 48px inset, max 820px: accent mono eyebrow "TODAY'S TRAINING" → 76px title → three stat columns (`45 / Minutes`, `6 / Exercises`, `7.4k / Est. volume kg`) separated by 1px×38px white-20% rules → `START WORKOUT` (accent, 20px/40px padding) + `VIEW PLAN` (1px white-35% outline).
- **Stat row** 3 equal white columns, 1px dividers, 32px/48px padding: week consistency (7 bars, 46px tall — accent = done, white with 1.5px accent border = today, `#EDEAE4` = empty), 7-day volume `28,940 kg` with accent delta, latest PR.
- **Two-column body** (1.55fr / 1fr, 48px gap): left = today's exercises as rows (96×68px photo, name, mono muscle·type, sets, last weight right-aligned, 1px bottom rule, hover `#EFECE6`); right = Coach's note (2px `--ink` top rule, mono label, 17px body, outline CTA), Recovery (86 + bar + inputs summary), Nutrition today (three label/value rows).
- Mobile: 430px photo hero with bottom-up scrim, full-width accent Start button, week strip, coach note, exercise rows at 72×54px thumbs.

### 2. Coach
Chat, not an AI demo. White header bar: mono "COACH" eyebrow + "Marcus · Strength coach" 26px, right side readiness / session readouts and an accent Start workout button. Messages max 900px centred: coach messages white with 1px `--line` border, user messages solid `--ink` white text, both 18px/22px padding, mono timestamp above. Inline exercise suggestion = 104×74px photo + name + mono muscle + sets + outline Open button. Composer: white bar, 1px top rule, input + `--ink` Send.

### 3. Planner
Header with "Weekly planner" eyebrow, 44px "Your training pool", progress line (4px, accent fill 80%), outline Regenerate. Grid of 3 session cards: 180px photo with a black day chip top-left, then 20px padding with 20px name, mono meta, accent uppercase status. Hover = border `--ink`. Mobile: 150px full-bleed photo cards with bottom-up scrim and text over the image.

### 4. Recovery
Two columns (1.3fr / 1fr, 56px gap).
- Left: the five existing check-in questions (sleep, quality, energy, soreness, yesterday's load), each a row of 5 equal buttons — selected `--ink`/white, unselected white with `--line-strong` border. Accent submit.
- Right: black score panel (84px score + accent zone word + bar + sentence), metric rows, coach's note under a 2px rule.
- Below, full width: **Readiness · last 14 days** bar chart (160px tall — `--ink` ≥70, `#C9C3B9` <70, accent for today), **Muscle group recovery** rows (`150px / bar / state / last`, accent bar = loaded, ink = ready), **Recent check-ins** list with scores, and a short "what moves your score" explainer.

### 5. Progress
Fitness progress, not analytics. Title block, then a 4-up white stat strip (streak, workouts, training time, bodyweight) with 1px dividers and 44px numbers. Below: bench-press estimated-1RM bar chart (12 bars, `--ink`, 220px tall, W1/W6/W12 mono axis) with an accent "+7.5 kg / 4 weeks" note; right column = personal records and recent workouts as label/value rows.

### 6. Calories
Left: type/photo segmented control, 130px textarea, accent Analyze button, logged meals as rows (name + mono macros + 20px kcal). Right: black totals panel (`1,840 / 2,400 kcal` + bar), three macro bars in `--ink`, coach's note under a 2px rule.

### 7. Themes
Five theme cards in a 3-col grid: 130px preview split 2:1:1 into the theme's surface/panel/ink, then name + "IN USE" chip, mono descriptor, one sentence of guidance, and a 4-swatch palette row (20×20px, 1px border). Below, three columns: **Atmosphere** (Motion / Contrast / Haptics sliders — 3px track, 15px square handle), **Layout** (Compact / Standard / Focus as full-width buttons, active `--ink`), **Auto theme** rules as label + sentence rows. Note: the old "glow intensity" and "particle density" controls are intentionally retired.

### 8. Profile
260px photo header with a left-to-right scrim and name over it; 4-up body stat strip (weight, height, BMI, days/week). Then 1.4fr/1fr: left = "Your details" 2-col form (10 fields: name, age, gender, weight, height, days/week, goal, level, workout place, injuries) with mono uppercase labels above 1px-bordered inputs, then accent Save + outline Log out. Right rail = Athlete level (XP rank + progress to next threshold, from `xp_level_info`), training profile bars, sport-mode summary with Edit sport setup, badges earned.

### Workout mode (dark, both states)
Opens as a full-cover overlay inside the app shell — **`z-index:50`**, `--dark-bg`, `fcIn` animation. Header: session name, "Exercise 2 of 6", elapsed timer (mono 20px), a Log sets / Form camera segmented switch (active half white on dark), and an outline End workout.
- **Log sets**: 1.25fr/1fr. Left = 300×200px exercise photo + 46px uppercase name + mono "Chest · Compound" + "Previous: 60 kg × 10", then a set table (`70px / 1fr / 1fr / 90px`: set number, 34px weight, 34px reps, 56×56px check button — accent when done, outline when pending) and a `+ Add set` outline button. Right = rest panel on `--dark-panel` (accent "REST" label, 84px mono countdown, accent bar, Skip rest / +30s), the up-next queue, and a Skip exercise / Next exercise footer.
- **Form camera**: 1.5fr/1fr. Left = camera feed with a top-left accent "LIVE FORM ANALYSIS" chip, a 108px rep count over `/ 10`, and a cue card. Right = exercise name, three accuracy bars (accent for form, white for the rest), live coach line, and Log set / Complete set.
- Mobile mirrors both states at `z-index:30`, with 52–60px controls.

### Entry & states (second file)
Auth (split hero + form, sign in / sign up, password vs OTP, 6-box code), the 11-step onboarding (verbatim questions from `ONBOARDING_QUESTIONS` in `backend/app/services/ai_service.py`, including the full 8-item goal list), 5-step sport setup (`SportOnboardRequest` fields), workout complete (6 metrics + lifts + badges), and six states: progress empty, nutrition loading, coach unavailable, OTP error, low-confidence food confirm, planner skeleton.

---

## Interactions & behavior
- Nav click → `switchTab(key)`; active state updates sidebar and bottom nav together.
- "Start workout" anywhere → open the workout overlay in `log` mode.
- Header switch toggles `log` ⇄ `cam` without leaving the session.
- Set check button toggles that set's done state (accent fill).
- `+ Add set` appends a set row seeded from the last set.
- Onboarding Continue/Back move through the 11 fields; progress bar = `(step+1)/11`.
- Hover: outline buttons invert to `--ink`/white; accent buttons darken to `--accent-hover`; list rows tint `#EFECE6`.
- Empty / loading / error states are specified in the second design file — use those, not spinners over whole pages.

## State
`tab` (one of the 8 keys), `workoutOpen`, `workoutMode` (`log` | `cam`), `sets[]` (`{kg, reps, done}`), onboarding `step` + `answer`. Everything else is server data already handled by `script.js`.

## Assets
All photography is already in the repo: `frontend/assets/images/home/` — `deadlift.webp`, `boxing.webp`, `runner.webp`, `gym_portrait.webp`, `hero_athlete.webp`, `luxury_gym.webp`. **These six are reused across exercises as placeholders.** Before shipping, commission or license one photo per exercise (bench press, incline press, barbell row, lat pulldown, landmine press, cable curl) at roughly 1200×800, shot in a real gym, and drop them in the same folder.

The old 2 MB+ hero JPGs (`hero_0*.jpg`, `feature_0*.jpg`, `background_0*.jpg`, `portrait_0*.jpg`) are no longer used — delete them or move them out of the deploy.

## Files in this bundle
- `FitCoach Redesign.dc.html` — all 8 tabs + workout mode, desktop and mobile, clickable.
- `FitCoach Redesign — Entry & States.dc.html` — auth, onboarding, sport setup, workout complete, states.
- `FitCoach Current.dc.html` — the current UI recreated, for before/after comparison.
- `assets/` — the six photos used.

## Suggested commit sequence
1. `chore: remove unused hero JPGs and premium-home css/js`
2. `feat(ui): new token layer + global shell (sidebar, bottom nav, buttons, inputs)`
3. `feat(ui): redesign Home`
4. `feat(ui): redesign workout mode (log + form camera)`
5. `feat(ui): redesign Coach, Planner, Recovery, Progress, Calories, Themes, Profile`
6. `feat(ui): auth, onboarding, sport setup, complete screen, empty/loading/error states`

Ship behind a branch (`redesign/v2`) and diff the tab list before merging — the 8 tabs, their labels and their order must be byte-identical to `main`.
