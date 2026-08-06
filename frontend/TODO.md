# Ghost Trainer Repair — Task List

## Root Cause
- `ghost-form-analysis.js` uses `export` keywords inside a classic (non-module) script → SyntaxError → `window.GhostFormAnalysis` never defined.
- `ghost-trainer.js` redeclares top-level consts (`LM`, `POSE_EDGES`, `getPoseLandmarker`) already declared in `ghost-pose.js` → `Identifier already declared` SyntaxError → `window.fitCoachGhostTrainer` never defined.
- Result: `switchTab("trainer")` calls `window.fitCoachGhostTrainer?.init()` which silently no-ops → no cards render.

## Fixes (minimal, no redesign)
- [ ] Wrap `ghost-form-analysis.js` in an IIFE and remove `export` keywords
- [ ] Wrap `ghost-trainer.js` in an IIFE
- [ ] Syntax-validate both files with `node --check`
- [ ] Confirm `window.GhostFormAnalysis` and `window.fitCoachGhostTrainer` are exported

## Not Touched
- Home page, sidebar, switchTab(), other tabs, camera logic, pose detection, CSS, HTML
