#!/usr/bin/env python
"""
Pre-review coverage check for the sport/exercise catalog.

Run before every review/demo:  python tools/exercise_coverage_report.py

This is a build-time tool — it lives at the repo root, not under
backend/app/, so it is never imported by the running service and never
ships as an app dependency.

Exits 1 (and prints every gap) if any of the following are true:
  - a sport JSON catalog failed to load (falling back to the legacy flat
    catalog silently would defeat the whole point of this check)
  - a role template references a session key that doesn't exist
  - a (sport, role, session) combination yields fewer than 4 drills after
    role-aware filtering — the number the green zone can ask for
  - a drill is missing a required field, or a field has the wrong type
  - [informational only, does not fail the build] an exercise's
    classify_movement_pattern() resolves to full_body_generic — the
    generic 3-second-timer pattern with no real rep counting. Block 5
    (per-exercise camera/form rules) will use this list.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services import sport_catalog  # noqa: E402
from app.services import plan_service as ps  # noqa: E402

REQUIRED_DRILL_FIELDS = {
    "name": str, "sets": int, "reps": (str, int), "rest": str,
    "muscle": str, "equipment_required": bool,
}

GREEN_ZONE_COUNT = 6  # ps._get_exercises() count for zone == "green"


def _profile(**kw) -> SimpleNamespace:
    base = dict(
        user_id=1, gender="male", goal="general_fitness", level="intermediate",
        workout_place="gym", days_per_week=4, injuries=None,
        plays_sport=True, sport=None, sport_role=None, sport_position=None,
        sport_focus=None, match_frequency=None, sport_injuries=None, bowling_type=None,
        age=25, weight=75.0, height=175.0, preferences=None,
    )
    base.update(kw)
    p = SimpleNamespace(**base)
    p.active_mode = "sport"
    return p


ROLE_PROFILES = {
    "cricket": {
        "batsman":      dict(sport_role="batsman"),
        "fast_bowler":  dict(sport_role="bowler", bowling_type="fast"),
        "spin_bowler":  dict(sport_role="bowler", bowling_type="spin"),
        "all_rounder":  dict(sport_role="all_rounder"),
        "wicketkeeper": dict(sport_role="wicketkeeper"),
    },
    "football": {
        "goalkeeper": dict(sport_position="goalkeeper"),
        "defender":   dict(sport_position="defender"),
        "midfielder": dict(sport_position="midfielder"),
        "forward":    dict(sport_position="forward"),
    },
    "running": {
        "sprint": dict(sport_role="sprint"),
        "middle": dict(sport_role="middle"),
        "long":   dict(sport_role="long"),
    },
}


def check_catalog_loaded(errors: list[str]) -> None:
    for sport in ("cricket", "football", "running"):
        data = sport_catalog._load(sport)  # noqa: SLF001 - this IS the coverage tool
        if data is None:
            errors.append(f"[catalog] {sport}.json failed to load — see startup warning for the reason")


def check_role_templates(errors: list[str]) -> None:
    for sport in ("cricket", "football", "running"):
        data = sport_catalog._load(sport)  # noqa: SLF001
        if not data:
            continue
        sessions = data.get("sessions", {})
        for role, tpl in data.get("role_templates", {}).items():
            for key in tpl:
                if key not in sessions:
                    errors.append(f"[template] {sport}/{role} references session '{key}' which has no drills")


def check_role_session_starvation(errors: list[str]) -> None:
    for sport, roles in ROLE_PROFILES.items():
        data = sport_catalog._load(sport)  # noqa: SLF001
        if not data:
            continue
        sessions = list(data.get("sessions", {}).keys())
        for role, extra in roles.items():
            profile = _profile(sport=sport, **extra)
            for session_key in sessions:
                result = sport_catalog.select(sport, session_key, profile, GREEN_ZONE_COUNT)
                n = len(result or [])
                if n < 4:
                    errors.append(f"[starvation] {sport}/{role}/{session_key}: only {n} drills (need >= 4)")


def check_drill_schema(errors: list[str]) -> None:
    for sport in ("cricket", "football", "running"):
        data = sport_catalog._load(sport)  # noqa: SLF001
        if not data:
            continue
        for session_key, drills in data.get("sessions", {}).items():
            for drill in drills:
                name = drill.get("name", "<unnamed>")
                for field, expected_type in REQUIRED_DRILL_FIELDS.items():
                    if field not in drill:
                        errors.append(f"[schema] {sport}/{session_key}/{name}: missing '{field}'")
                    elif not isinstance(drill[field], expected_type):
                        errors.append(f"[schema] {sport}/{session_key}/{name}: '{field}' has wrong type ({type(drill[field]).__name__})")
                roles = drill.get("roles")
                if roles is not None and not isinstance(roles, list):
                    errors.append(f"[schema] {sport}/{session_key}/{name}: 'roles' must be a list")


def report_full_body_generic(info: list[str]) -> None:
    """Informational only — every exercise whose movement_pattern resolves to
    the generic 3-second-timer bucket. Block 5 (per-exercise camera/form
    rules) needs this list; it does not fail this check."""
    seen = set()
    catalogs = [ps._GYM_MALE, ps._GYM_FEMALE, ps._HOME_MALE, ps._HOME_FEMALE, ps._INJURY_SAFE]
    for db in catalogs:
        for session_key, drills in db.items():
            if not drills:
                continue
            for drill in drills:
                name = drill.get("name", "")
                if name in seen:
                    continue
                seen.add(name)
                pattern = ps.classify_movement_pattern(name, session_key)
                if pattern == "full_body_generic":
                    info.append(f"{name} (session={session_key})")
    for sport in ("cricket", "football", "running"):
        data = sport_catalog._load(sport)  # noqa: SLF001
        if not data:
            continue
        for session_key, drills in data.get("sessions", {}).items():
            for drill in drills:
                name = drill.get("name", "")
                if name in seen:
                    continue
                seen.add(name)
                pattern = ps.classify_movement_pattern(name, session_key)
                if pattern == "full_body_generic":
                    info.append(f"{name} (session={sport}/{session_key})")


def main() -> int:
    errors: list[str] = []
    check_catalog_loaded(errors)
    check_role_templates(errors)
    check_role_session_starvation(errors)
    check_drill_schema(errors)

    info: list[str] = []
    report_full_body_generic(info)

    print("=" * 70)
    print("EXERCISE COVERAGE REPORT")
    print("=" * 70)

    if errors:
        print(f"\n[FAIL] {len(errors)} failing check(s):\n")
        for e in errors:
            print(f"  - {e}")
    else:
        print("\n[OK] All personalization coverage checks passed.")

    print(f"\n[INFO] {len(info)} exercise(s) resolve to 'full_body_generic' (no real rep pattern - informational, for Block 5):")
    for i in info:
        print(f"  - {i}")

    print("\n" + "=" * 70)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
