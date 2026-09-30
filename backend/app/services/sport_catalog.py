"""
Role-aware sport exercise catalog.

Loaded from versioned JSON under app/data/sport/*.json rather than more
hardcoded Python dicts in plan_service.py — JSON diffs cleanly, ships
automatically via the Dockerfile's `COPY backend/ .`, and loads in a few ms.

Falls back to plan_service's original flat _SPORT dict (via select()/
role_template() returning None) if a JSON file is missing or fails to
parse, so a data-authoring mistake degrades to the old generic-per-sport
behaviour instead of 500-ing every request.

Two orthogonal personalization axes, so ~12 roles across 3 sports don't
require a combinatorial set of hand-written drills:
  - session TEMPLATES per role — an ordered subset of that sport's session
    keys (build_weekly_pool already dedupes/cyclic-pads these).
  - drill TAGS within a session — shared drills are untagged ("universal");
    role-specific drills are layered on top and only surface for that role.
"""
from __future__ import annotations

import hashlib
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sport"

_KNOWN_SPORTS = ("cricket", "football", "running")


@lru_cache(maxsize=None)
def _load(sport: str) -> dict[str, Any] | None:
    """Load and lightly validate one sport's JSON catalog. Cached — the file
    is only ever read once per process. Returns None (never raises) on any
    problem, so callers fall back to the legacy flat catalog."""
    if sport not in _KNOWN_SPORTS:
        return None
    path = _DATA_DIR / f"{sport}.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("sport") != sport or "sessions" not in data or "role_templates" not in data:
            raise ValueError("missing required keys (sport/sessions/role_templates)")
        return data
    except Exception as e:  # noqa: BLE001 - deliberately broad, this must never raise
        logger.warning("sport_catalog: failed to load %s.json (%s) — falling back to legacy _SPORT catalog", sport, e)
        return None


def startup_check() -> None:
    """Print catalog load status at app startup so a bad JSON file is visible
    immediately in the logs rather than discovered mid-demo. Uses print(),
    matching this file's existing startup-diagnostics style (main.py's
    Alembic block) rather than the logging module, whose INFO level isn't
    visible by default without explicit handler configuration."""
    parts = []
    for sport in _KNOWN_SPORTS:
        data = _load(sport)
        if data:
            n = sum(len(v) for v in data.get("sessions", {}).values())
            parts.append(f"{sport}={n}")
        else:
            parts.append(f"{sport}=FALLBACK")
    print(f"[sport_catalog] loaded: {', '.join(parts)}")


def version(sport: str | None) -> int:
    data = _load((sport or "").lower())
    return data.get("version", 0) if data else 0


def _normalize_token(value: str | None, aliases: dict[str, str]) -> str | None:
    if not value:
        return None
    v = value.strip().lower().replace(" ", "_").replace("-", "_")
    return aliases.get(v, v)


def normalize_role(profile) -> tuple[str | None, str | None]:
    """Resolve (role_key, sub_role) for this profile's sport — reads
    sport_role / sport_position / bowling_type, fields the flat catalog
    never consulted before this module existed."""
    sport = (profile.sport or "").lower()
    data = _load(sport)
    aliases = (data or {}).get("role_aliases", {})

    if sport == "cricket":
        role = _normalize_token(getattr(profile, "sport_role", None), aliases)
        sub = _normalize_token(getattr(profile, "bowling_type", None), aliases)
        if role in (None, "bowler"):
            if sub == "fast":
                role = "fast_bowler"
            elif sub == "spin":
                role = "spin_bowler"
        valid = {"batsman", "fast_bowler", "spin_bowler", "all_rounder", "wicketkeeper"}
        if role not in valid:
            role = "all_rounder"
        return role, sub

    if sport == "football":
        role = _normalize_token(getattr(profile, "sport_position", None), aliases) \
            or _normalize_token(getattr(profile, "sport_role", None), aliases)
        valid = {"goalkeeper", "defender", "midfielder", "forward"}
        if role not in valid:
            role = "midfielder"
        return role, None

    if sport == "running":
        # Zero-migration: the frontend sends the runner's distance-type answer
        # in the same `role` field sport-onboarding already writes to
        # sport_role, since running's onboarding asks no separate role question.
        role = _normalize_token(getattr(profile, "sport_role", None), aliases)
        valid = {"sprint", "middle", "long"}
        if role not in valid:
            role = "middle"
        return role, role

    return None, None


def role_template(sport: str, role_key: str | None) -> list[str] | None:
    data = _load((sport or "").lower())
    if not data or not role_key:
        return None
    templates = data.get("role_templates", {})
    return templates.get(role_key) or templates.get("default")


def _risk_score(drill: dict, role_key, sub_role, focus, level) -> int | None:
    roles = drill.get("roles") or []
    if roles and role_key not in roles:
        return None  # this drill is reserved for a different role
    score = drill.get("priority", 0)
    if role_key and role_key in roles:
        score += 3
    if sub_role and sub_role in (drill.get("sub_roles") or []):
        score += 2
    if focus and focus in (drill.get("focus") or []):
        score += 2
    if level and level in (drill.get("levels") or []):
        score += 1
    return score


def _rotate(items: list[dict], user_id: int, seed: str) -> list[dict]:
    if len(items) <= 1:
        return items
    h = int(hashlib.md5(f"{user_id}:{seed}".encode()).hexdigest(), 16)
    offset = h % len(items)
    return items[offset:] + items[:offset]


def select(sport: str, category: str, profile, count: int) -> list[dict] | None:
    """Role-aware drill selection for one session category.

    Returns None if this sport has no JSON catalog (caller falls back to the
    legacy flat _SPORT dict). Returns [] only if the sport catalog loaded but
    has no drills reachable at all for this category through any fallback —
    the caller must not fall back to gym exercises in that case, only to a
    bodyweight full-body session.
    """
    data = _load((sport or "").lower())
    if not data:
        return None

    role_key, sub_role = normalize_role(profile)
    aliases = data.get("role_aliases", {})
    focus = _normalize_token(getattr(profile, "sport_focus", None), aliases)
    level = (profile.level or "intermediate").lower()

    sessions = data.get("sessions", {})

    # Three-stage sport-aware fallback chain for a missing/empty session —
    # never gym: this session's declared fallbacks, then the sport's
    # mobility/conditioning session, then whatever exists at all.
    chain = [category]
    chain += data.get("session_fallbacks", {}).get(category, [])
    mobility = data.get("mobility_session")
    if mobility:
        chain.append(mobility)

    pool: list[dict] = []
    used_key = None
    for key in chain:
        candidate = sessions.get(key) or []
        if candidate:
            pool, used_key = candidate, key
            break

    if not pool:
        logger.warning("sport_catalog: no drills reachable for %s/%s via chain %s", sport, category, chain)
        return []

    scored = []
    for drill in pool:
        s = _risk_score(drill, role_key, sub_role, focus, level)
        if s is not None:
            scored.append((s, drill))
    scored.sort(key=lambda t: t[0], reverse=True)

    role_specific = [d for _, d in scored if role_key and role_key in (d.get("roles") or [])]
    universal = [d for _, d in scored if not (d.get("roles") or [])]

    uid = getattr(profile, "user_id", 0) or 0
    role_specific = _rotate(role_specific, uid, f"{used_key}:role")
    universal = _rotate(universal, uid, f"{used_key}:universal")

    combined = role_specific + universal

    # Pool-starvation guard — several sessions are thin (e.g. running's
    # easy_run has only 3 drills) while green-zone count asks for 6; top up
    # from every untagged drill in the sport rather than serve too few.
    if len(combined) < count:
        seen_names = {d.get("name") for d in combined}
        extra = [
            d for key_sessions in sessions.values() for d in key_sessions
            if not (d.get("roles") or []) and d.get("name") not in seen_names
        ]
        combined += extra

    combined = combined[: max(count, 4)]

    result = []
    for d in combined:
        item = dict(d)
        note_parts = []
        if role_key:
            note_parts.append(role_key.replace("_", " "))
        if focus:
            note_parts.append(f"{focus} focus")
        if note_parts:
            item["personalization_note"] = f"Selected for: {' · '.join(note_parts)}"
        result.append(item)
    return result
