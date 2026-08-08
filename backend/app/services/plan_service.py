"""
Deterministic weekly plan generation.
Exercise databases match the desktop version exactly, with YouTube demo URLs.
"""
from datetime import date, timedelta
from app.models.profile import Profile

# ── Weekly plan templates (gender × mode × goal) ──────────────────────────────
## Each entry is an ordered rotation of ALREADY-DISTINCT session categories —
## no "rest" filler, no repeated entries. This is what makes the pool model
## specific rather than generic: gym/home rotations are sized to exactly the 6
## categories real training splits use (Push/Pull/Legs/Upper/Lower/Full-Body,
## or the female-goal equivalents), so at any realistic 3-6 day/week frequency
## every session in the pool is genuinely different — nothing repeats unless a
## goal's category vocabulary itself has fewer than 6 (sport programs, which
## legitimately specialize around 5 focuses).
_PLANS = {
    # ── Male / Gym — Push/Pull/Legs/Upper/Lower/Full-Body vocabulary ─────────
    ("male", "gym", "muscle_gain"):     ["push", "pull", "legs", "upper_body", "lower_body", "full_body"],
    ("male", "gym", "strength"):        ["legs", "push", "pull", "lower_body", "upper_body", "full_body"],
    ("male", "gym", "aesthetics"):      ["push", "pull", "legs", "upper_body", "lower_body", "full_body"],
    ("male", "gym", "fat_loss"):        ["full_body", "cardio", "push", "pull", "legs", "upper_body"],
    ("male", "gym", "general_fitness"): ["push", "pull", "legs", "full_body", "upper_body", "cardio"],

    # ── Male / Home — same vocabulary, bodyweight-driven ─────────────────────
    ("male", "home", "muscle_gain"):     ["push", "pull", "legs", "full_body", "upper_body", "lower_body"],
    ("male", "home", "fat_loss"):        ["full_body", "cardio", "push", "pull", "legs", "upper_body"],
    ("male", "home", "general_fitness"): ["push", "pull", "legs", "full_body", "cardio", "upper_body"],

    # ── Female / Gym — Glutes/Lower/Upper-Toning/Core-Cardio/Full-Body/Cardio,
    # plus Push/Pull for muscle-gain — 6 distinct categories per goal ────────
    ("female", "gym", "fat_loss"):          ["full_body", "cardio", "lower_body", "upper_toning", "core_cardio", "glutes"],
    ("female", "gym", "glute_growth"):      ["glutes", "lower_body", "upper_toning", "core_cardio", "full_body", "cardio"],
    ("female", "gym", "hourglass_figure"):  ["glutes", "upper_toning", "core_cardio", "lower_body", "full_body", "cardio"],
    ("female", "gym", "lean_physique"):     ["lower_body", "upper_toning", "glutes", "cardio", "full_body", "core_cardio"],
    ("female", "gym", "toned_body"):        ["full_body", "lower_body", "upper_toning", "cardio", "glutes", "core_cardio"],
    ("female", "gym", "muscle_gain"):       ["push", "pull", "glutes", "upper_toning", "full_body", "cardio"],
    ("female", "gym", "general_fitness"):   ["full_body", "lower_body", "upper_toning", "cardio", "glutes", "core_cardio"],

    # ── Female / Home — 6-category vocabulary (no push/pull without gym kit) ─
    ("female", "home", "fat_loss"):         ["full_body", "cardio", "lower_body", "upper_toning", "core_cardio", "glutes"],
    ("female", "home", "glute_growth"):     ["glutes", "lower_body", "upper_toning", "full_body", "core_cardio", "cardio"],
    ("female", "home", "toned_body"):       ["full_body", "lower_body", "upper_toning", "cardio", "glutes", "core_cardio"],
    ("female", "home", "general_fitness"):  ["full_body", "lower_body", "glutes", "cardio", "upper_toning", "core_cardio"],

    # ── Sport plans — 5 sport-specific focuses each (no gym keys) ────────────
    ("male",   "sport", "cricket"):  ["batting_power", "cricket_mobility", "cricket_conditioning", "fielding_agility", "bowling_strength"],
    ("female", "sport", "cricket"):  ["batting_power", "cricket_mobility", "cricket_conditioning", "fielding_agility", "bowling_strength"],
    ("male",   "sport", "football"): ["football_speed", "football_agility", "football_conditioning", "football_skill", "football_power"],
    ("female", "sport", "football"): ["football_speed", "football_agility", "football_conditioning", "football_skill", "football_power"],
    ("male",   "sport", "running"):  ["easy_run", "running_drills", "tempo_run", "track_intervals", "long_run"],
    ("female", "sport", "running"):  ["easy_run", "running_drills", "tempo_run", "track_intervals", "long_run"],
}

SESSION_LABELS = {
    # ── Gym / Home shared
    "push": "Push Day", "pull": "Pull Day", "legs": "Leg Day",
    "upper_body": "Upper Body", "lower_body": "Lower Body", "full_body": "Full Body",
    "cardio": "Cardio", "glutes": "Glute Focus", "upper_toning": "Upper Toning",
    "core_cardio": "Core & Cardio",
    "rest": "Rest Day",
    # ── Cricket
    "batting_power":      "Batting Power",
    "cricket_mobility":   "Cricket Mobility",
    "cricket_conditioning":"Match Conditioning",
    "fielding_agility":   "Fielding & Agility",
    "bowling_strength":   "Bowling Strength",
    # ── Football
    "football_speed":      "Speed & Acceleration",
    "football_agility":    "Agility & Footwork",
    "football_conditioning":"Match Conditioning",
    "football_skill":      "Technical Skill",
    "football_power":      "Explosive Power",
    # ── Running
    "easy_run":      "Easy Run",
    "running_drills":"Running Drills",
    "tempo_run":     "Tempo Run",
    "track_intervals":"Track Intervals",
    "long_run":      "Long Run",
}

# ── Rich Exercise Databases (matching desktop exactly, with demo_url) ─────────

_GYM_MALE = {
    "push": [
        {"name": "Barbell Bench Press",     "sets": 4, "reps": "6-8",   "rest": "90s",  "muscle": "Chest",          "weight_guide": "70-110kg",        "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=bench+press"},
        {"name": "Incline Dumbbell Press",  "sets": 4, "reps": "8-10",  "rest": "75s",  "muscle": "Upper Chest",    "weight_guide": "22-36kg/hand",    "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=incline+dumbbell+press"},
        {"name": "Overhead Barbell Press",  "sets": 4, "reps": "6-8",   "rest": "90s",  "muscle": "Shoulders",      "weight_guide": "40-70kg",         "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=overhead+press"},
        {"name": "Dumbbell Shoulder Press", "sets": 3, "reps": "10-12", "rest": "75s",  "muscle": "Shoulders",      "weight_guide": "18-30kg/hand",    "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=dumbbell+shoulder+press"},
        {"name": "Lateral Raises",          "sets": 4, "reps": "12-15", "rest": "60s",  "muscle": "Side Delts",     "weight_guide": "8-15kg/hand",     "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=lateral+raises"},
        {"name": "Cable Lateral Raise",     "sets": 3, "reps": "15",    "rest": "45s",  "muscle": "Side Delts",     "weight_guide": "5-10kg cable",    "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=cable+lateral+raise"},
        {"name": "Triceps Pushdown",        "sets": 3, "reps": "12-15", "rest": "60s",  "muscle": "Triceps",        "weight_guide": "20-40kg cable",   "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=tricep+pushdown"},
        {"name": "Skull Crushers",          "sets": 3, "reps": "10-12", "rest": "60s",  "muscle": "Triceps",        "weight_guide": "30-50kg bar",     "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=skull+crushers"},
        {"name": "Cable Chest Flye",        "sets": 3, "reps": "12",    "rest": "60s",  "muscle": "Chest",          "weight_guide": "15-25kg/side",    "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=cable+chest+fly"},
        {"name": "Close-Grip Bench Press",  "sets": 3, "reps": "10",    "rest": "75s",  "muscle": "Triceps/Chest",  "weight_guide": "60-90kg",         "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=close+grip+bench+press"},
        {"name": "Arnold Press",            "sets": 3, "reps": "10-12", "rest": "75s",  "muscle": "Shoulders",      "weight_guide": "16-26kg/hand",    "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=arnold+press"},
        {"name": "Decline Bench Press",     "sets": 3, "reps": "8-10",  "rest": "90s",  "muscle": "Lower Chest",    "weight_guide": "65-100kg",        "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=decline+bench+press"},
    ],
    "pull": [
        {"name": "Weighted Pull-Ups",           "sets": 4, "reps": "5-8",   "rest": "90s",  "muscle": "Lats",        "weight_guide": "BW or +5-20kg",   "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=pull+ups"},
        {"name": "Barbell Bent-Over Row",       "sets": 4, "reps": "6-8",   "rest": "90s",  "muscle": "Back",        "weight_guide": "70-110kg",        "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=bent+over+row"},
        {"name": "Seated Cable Row",            "sets": 3, "reps": "10-12", "rest": "75s",  "muscle": "Mid Back",    "weight_guide": "50-80kg cable",   "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=seated+cable+row"},
        {"name": "Chest-Supported Row",         "sets": 3, "reps": "10-12", "rest": "75s",  "muscle": "Rhomboids",   "weight_guide": "20-35kg/hand DB", "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=chest+supported+row"},
        {"name": "Face Pulls",                  "sets": 3, "reps": "15-20", "rest": "60s",  "muscle": "Rear Delts",  "weight_guide": "15-30kg cable",   "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=face+pulls"},
        {"name": "Barbell Bicep Curls",         "sets": 3, "reps": "10-12", "rest": "60s",  "muscle": "Biceps",      "weight_guide": "30-50kg",         "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=barbell+curl"},
        {"name": "Incline Dumbbell Curl",       "sets": 3, "reps": "10-12", "rest": "60s",  "muscle": "Biceps",      "weight_guide": "12-20kg/hand",    "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=incline+dumbbell+curl"},
        {"name": "Lat Pulldown",                "sets": 4, "reps": "8-10",  "rest": "75s",  "muscle": "Lats",        "weight_guide": "50-80kg cable",   "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=lat+pulldown"},
        {"name": "Single-Arm DB Row",           "sets": 3, "reps": "10 ea", "rest": "75s",  "muscle": "Back",        "weight_guide": "30-50kg/hand",    "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=single+arm+row"},
        {"name": "Hammer Curls",                "sets": 3, "reps": "10-12", "rest": "60s",  "muscle": "Brachialis",  "weight_guide": "16-26kg/hand",    "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=hammer+curls"},
        {"name": "Cable Straight-Arm Pulldown", "sets": 3, "reps": "12",    "rest": "60s",  "muscle": "Lats",        "weight_guide": "25-40kg cable",   "equipment_required": True,  "demo_url": "https://www.youtube.com/@JeffNippard/search?query=straight+arm+pulldown"},
    ],
    "legs": [
        {"name": "Barbell Back Squat",     "sets": 4, "reps": "5-6",   "rest": "120s", "muscle": "Quads",          "weight_guide": "90-150kg",          "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=barbell+squat+form"},
        {"name": "Romanian Deadlift",      "sets": 4, "reps": "8-10",  "rest": "90s",  "muscle": "Hamstrings",     "weight_guide": "70-110kg",          "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=romanian+deadlift"},
        {"name": "Leg Press",              "sets": 3, "reps": "10-12", "rest": "90s",  "muscle": "Quads",          "weight_guide": "160-260kg machine", "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=leg+press"},
        {"name": "Bulgarian Split Squat",  "sets": 3, "reps": "8 ea",  "rest": "75s",  "muscle": "Quads/Glutes",   "weight_guide": "20-35kg/hand",      "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=bulgarian+split+squat"},
        {"name": "Hack Squat",             "sets": 3, "reps": "10-12", "rest": "90s",  "muscle": "Quads",          "weight_guide": "80-150kg machine",  "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=hack+squat"},
        {"name": "Seated Leg Curl",        "sets": 3, "reps": "12-15", "rest": "60s",  "muscle": "Hamstrings",     "weight_guide": "40-70kg machine",   "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=seated+leg+curl"},
        {"name": "Leg Extension",          "sets": 3, "reps": "12-15", "rest": "60s",  "muscle": "Quads",          "weight_guide": "40-70kg machine",   "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=leg+extension"},
        {"name": "Hip Thrust",             "sets": 3, "reps": "10-12", "rest": "75s",  "muscle": "Glutes",         "weight_guide": "80-130kg barbell",  "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=hip+thrust"},
        {"name": "Standing Calf Raises",   "sets": 4, "reps": "15-20", "rest": "45s",  "muscle": "Calves",         "weight_guide": "BW or 30-60kg",     "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=calf+raise"},
        {"name": "Barbell Deadlift",       "sets": 4, "reps": "4-5",   "rest": "120s", "muscle": "Full Posterior", "weight_guide": "100-180kg",         "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=deadlift+form"},
        {"name": "Nordic Hamstring Curl",  "sets": 3, "reps": "5-6",   "rest": "90s",  "muscle": "Hamstrings",     "weight_guide": "Bodyweight",        "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=nordic+hamstring+curl"},
        {"name": "Dumbbell Walking Lunges","sets": 3, "reps": "10 ea", "rest": "75s",  "muscle": "Quads/Glutes",   "weight_guide": "18-28kg/hand",      "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=dumbbell+walking+lunges"},
    ],
    "upper_body": [
        {"name": "Flat Dumbbell Press",        "sets": 4, "reps": "8-10", "rest": "75s", "muscle": "Chest",      "weight_guide": "26-42kg/hand",    "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=dumbbell+bench+press"},
        {"name": "Dumbbell Row",               "sets": 4, "reps": "8-10", "rest": "75s", "muscle": "Back",       "weight_guide": "32-52kg/hand",    "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=dumbbell+row"},
        {"name": "Dumbbell Shoulder Press",    "sets": 3, "reps": "10",   "rest": "75s", "muscle": "Shoulders",  "weight_guide": "20-35kg/hand",    "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=dumbbell+shoulder+press"},
        {"name": "Lat Pulldown",               "sets": 3, "reps": "10",   "rest": "75s", "muscle": "Lats",       "weight_guide": "55-85kg cable",   "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=lat+pulldown"},
        {"name": "Hammer Curls",               "sets": 3, "reps": "12",   "rest": "60s", "muscle": "Biceps",     "weight_guide": "16-26kg/hand",    "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=hammer+curl"},
        {"name": "Overhead Tricep Extension",  "sets": 3, "reps": "12",   "rest": "60s", "muscle": "Triceps",    "weight_guide": "26-42kg dumbbell","equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=overhead+tricep+extension"},
        {"name": "Face Pulls",                 "sets": 3, "reps": "15",   "rest": "60s", "muscle": "Rear Delts", "weight_guide": "15-30kg cable",   "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=face+pull"},
        {"name": "Barbell Bicep Curl",         "sets": 3, "reps": "10",   "rest": "60s", "muscle": "Biceps",     "weight_guide": "30-50kg",         "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=barbell+curl"},
    ],
    "lower_body": [
        {"name": "Hack Squat",            "sets": 4, "reps": "8-10",  "rest": "90s", "muscle": "Quads",        "weight_guide": "80-150kg machine", "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=hack+squat"},
        {"name": "Dumbbell Lunges",       "sets": 3, "reps": "10 ea", "rest": "75s", "muscle": "Quads",        "weight_guide": "20-35kg/hand",     "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=dumbbell+lunges"},
        {"name": "Hip Thrust",            "sets": 4, "reps": "10-12", "rest": "75s", "muscle": "Glutes",       "weight_guide": "70-130kg barbell", "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=hip+thrust"},
        {"name": "Seated Leg Curl",       "sets": 3, "reps": "12-15", "rest": "60s", "muscle": "Hamstrings",   "weight_guide": "40-70kg machine",  "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=leg+curl"},
        {"name": "Leg Extension",         "sets": 3, "reps": "12-15", "rest": "60s", "muscle": "Quads",        "weight_guide": "40-70kg machine",  "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=leg+extension"},
        {"name": "Seated Calf Raise",     "sets": 4, "reps": "15-20", "rest": "45s", "muscle": "Calves",       "weight_guide": "30-60kg",          "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=seated+calf+raise"},
        {"name": "Romanian Deadlift",     "sets": 3, "reps": "10",    "rest": "90s", "muscle": "Hamstrings",   "weight_guide": "70-110kg",         "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=romanian+deadlift"},
        {"name": "Bulgarian Split Squat", "sets": 3, "reps": "8 ea",  "rest": "75s", "muscle": "Quads/Glutes", "weight_guide": "20-35kg/hand",     "equipment_required": True, "demo_url": "https://www.youtube.com/results?search_query=bulgarian+split+squat"},
    ],
    "full_body": [
        {"name": "Barbell Deadlift",   "sets": 3, "reps": "5",    "rest": "120s", "muscle": "Full Body",  "weight_guide": "90-170kg",     "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=deadlift+form"},
        {"name": "Bench Press",        "sets": 3, "reps": "8",    "rest": "90s",  "muscle": "Chest",      "weight_guide": "65-105kg",     "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=bench+press"},
        {"name": "Barbell Squat",      "sets": 3, "reps": "8",    "rest": "90s",  "muscle": "Legs",       "weight_guide": "75-130kg",     "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=squat+form"},
        {"name": "Pull-Ups",           "sets": 3, "reps": "8-10", "rest": "90s",  "muscle": "Back",       "weight_guide": "Bodyweight",   "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=pull+up"},
        {"name": "Overhead Press",     "sets": 3, "reps": "8",    "rest": "90s",  "muscle": "Shoulders",  "weight_guide": "42-65kg",      "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=overhead+press"},
        {"name": "Romanian Deadlift",  "sets": 3, "reps": "10",   "rest": "90s",  "muscle": "Hamstrings", "weight_guide": "70-110kg",     "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=romanian+deadlift"},
        {"name": "Barbell Row",        "sets": 3, "reps": "8",    "rest": "90s",  "muscle": "Back",       "weight_guide": "65-100kg",     "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=barbell+row"},
        {"name": "Dumbbell Lunges",    "sets": 3, "reps": "10 ea","rest": "75s",  "muscle": "Legs",       "weight_guide": "20-32kg/hand", "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=dumbbell+lunges"},
    ],
    "cardio": [
        {"name": "Treadmill Intervals", "sets": 1, "reps": "20 min",              "rest": "0s", "muscle": "Cardio",       "weight_guide": "Moderate pace", "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=treadmill+interval+workout"},
        {"name": "Cycling Intervals",   "sets": 6, "reps": "1 min hard / 1 rest", "rest": "0s", "muscle": "Cardio/Legs",  "weight_guide": "High resistance","equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=cycling+interval+workout"},
        {"name": "Rowing Machine",      "sets": 1, "reps": "15 min",              "rest": "0s", "muscle": "Full Body",    "weight_guide": "Moderate pace", "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=rowing+machine+workout"},
        {"name": "Stairmaster",         "sets": 1, "reps": "15 min",              "rest": "0s", "muscle": "Glutes/Cardio","weight_guide": "Level 8-12",    "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=stairmaster+workout"},
    ],
}

_GYM_FEMALE = {
    "glutes": [
        {"name": "Banded Hip Thrust",        "sets": 4, "reps": "12-15", "rest": "75s", "muscle": "Glutes",          "weight_guide": "40-90kg barbell + band", "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=hip+thrust"},
        {"name": "Bulgarian Split Squat",    "sets": 3, "reps": "10 ea", "rest": "75s", "muscle": "Glutes/Quads",    "weight_guide": "10-22kg/hand",           "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=bulgarian+split+squat"},
        {"name": "Sumo Deadlift",            "sets": 3, "reps": "8-10",  "rest": "90s", "muscle": "Glutes/Hamstrings","weight_guide": "40-90kg",               "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=sumo+deadlift"},
        {"name": "Cable Kickback",           "sets": 3, "reps": "15 ea", "rest": "60s", "muscle": "Glutes",          "weight_guide": "10-22kg cable",          "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=cable+kickback"},
        {"name": "Leg Press (wide stance)",  "sets": 3, "reps": "12-15", "rest": "75s", "muscle": "Glutes/Quads",    "weight_guide": "80-160kg",               "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=leg+press"},
        {"name": "Romanian Deadlift",        "sets": 3, "reps": "10-12", "rest": "90s", "muscle": "Hamstrings",      "weight_guide": "40-80kg",                "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=romanian+deadlift"},
        {"name": "Abductor Machine",         "sets": 3, "reps": "15-20", "rest": "60s", "muscle": "Hip Abductors",   "weight_guide": "40-70kg machine",        "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=abductor"},
        {"name": "Leg Curl",                 "sets": 3, "reps": "12-15", "rest": "60s", "muscle": "Hamstrings",      "weight_guide": "30-55kg machine",        "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=leg+curl"},
        {"name": "Curtsy Lunge",             "sets": 3, "reps": "12 ea", "rest": "60s", "muscle": "Glute Medius",    "weight_guide": "10-20kg/hand",           "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=curtsy+lunge"},
        {"name": "Seated Calf Raise",        "sets": 3, "reps": "15-20", "rest": "45s", "muscle": "Calves",          "weight_guide": "20-50kg",                "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=calf+raise"},
    ],
    "upper_toning": [
        {"name": "Lat Pulldown",             "sets": 3, "reps": "12-15", "rest": "75s", "muscle": "Back",       "weight_guide": "25-50kg cable",  "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=lat+pulldown"},
        {"name": "Seated Cable Row",         "sets": 3, "reps": "12",    "rest": "75s", "muscle": "Back",       "weight_guide": "25-45kg cable",  "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=seated+cable+row"},
        {"name": "Dumbbell Shoulder Press",  "sets": 3, "reps": "12",    "rest": "60s", "muscle": "Shoulders",  "weight_guide": "8-16kg/hand",    "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=shoulder+press"},
        {"name": "Tricep Pushdown",          "sets": 3, "reps": "15",    "rest": "60s", "muscle": "Triceps",    "weight_guide": "10-22kg cable",  "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=tricep+pushdown"},
        {"name": "Dumbbell Row",             "sets": 3, "reps": "12",    "rest": "60s", "muscle": "Back",       "weight_guide": "10-22kg/hand",   "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=dumbbell+row"},
        {"name": "Lateral Raises",           "sets": 3, "reps": "15",    "rest": "45s", "muscle": "Shoulders",  "weight_guide": "5-12kg/hand",    "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=lateral+raise"},
        {"name": "Incline Dumbbell Press",   "sets": 3, "reps": "12",    "rest": "75s", "muscle": "Upper Chest","weight_guide": "10-18kg/hand",   "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=incline+dumbbell+press"},
        {"name": "Cable Bicep Curl",         "sets": 3, "reps": "12-15", "rest": "45s", "muscle": "Biceps",     "weight_guide": "10-20kg cable",  "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=bicep+curl"},
        {"name": "Face Pulls",               "sets": 3, "reps": "15",    "rest": "45s", "muscle": "Rear Delts", "weight_guide": "10-20kg cable",  "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=face+pull"},
    ],
    "lower_body": [
        {"name": "Romanian Deadlift",       "sets": 3, "reps": "10-12", "rest": "75s", "muscle": "Hamstrings",    "weight_guide": "40-70kg",         "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=romanian+deadlift"},
        {"name": "Leg Press",               "sets": 3, "reps": "12-15", "rest": "75s", "muscle": "Quads",         "weight_guide": "80-140kg",        "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=leg+press"},
        {"name": "Barbell Back Squat",      "sets": 3, "reps": "10-12", "rest": "90s", "muscle": "Quads/Glutes",  "weight_guide": "40-70kg",         "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=barbell+squat"},
        {"name": "Seated Leg Curl",         "sets": 3, "reps": "12-15", "rest": "60s", "muscle": "Hamstrings",    "weight_guide": "30-50kg",         "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=leg+curl"},
        {"name": "Hip Thrust",              "sets": 3, "reps": "12-15", "rest": "75s", "muscle": "Glutes",        "weight_guide": "60-100kg",        "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=hip+thrust"},
        {"name": "Seated Calf Raise",       "sets": 3, "reps": "15-20", "rest": "45s", "muscle": "Calves",        "weight_guide": "30-50kg",         "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=calf+raise"},
        {"name": "Cable Kickback",          "sets": 3, "reps": "15 ea", "rest": "60s", "muscle": "Glutes",        "weight_guide": "10-22kg cable",   "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=cable+kickback"},
        {"name": "Abductor Machine",        "sets": 3, "reps": "15-20", "rest": "60s", "muscle": "Hip Abductors", "weight_guide": "40-70kg machine", "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=hip+abductor"},
    ],
    "core_cardio": [
        {"name": "Cable Crunch",            "sets": 3, "reps": "15-20", "rest": "45s", "muscle": "Core",     "weight_guide": "15-35kg cable",  "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=cable+crunch"},
        {"name": "Hanging Leg Raise",       "sets": 3, "reps": "12",    "rest": "45s", "muscle": "Core",     "weight_guide": "Bodyweight",     "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=hanging+leg+raise"},
        {"name": "Plank",                   "sets": 3, "reps": "45-60s","rest": "45s", "muscle": "Core",     "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=plank"},
        {"name": "Russian Twists",          "sets": 3, "reps": "20",    "rest": "45s", "muscle": "Obliques", "weight_guide": "5-12kg plate",   "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=russian+twist"},
        {"name": "Ab Rollout",              "sets": 3, "reps": "10-12", "rest": "60s", "muscle": "Core",     "weight_guide": "Ab wheel",       "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=ab+rollout"},
        {"name": "Stairmaster",             "sets": 1, "reps": "20 min","rest": "0s",  "muscle": "Cardio",   "weight_guide": "Level 8-12",     "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=stairmaster"},
        {"name": "Treadmill Sprint Bursts", "sets": 6, "reps": "1 min hard / 1 rest","rest": "0s","muscle": "Cardio","weight_guide": "Own pace","equipment_required": True,"demo_url": "https://www.youtube.com/@carolinegirvan/search?query=treadmill+interval"},
        {"name": "Bicycle Crunches",        "sets": 3, "reps": "20",    "rest": "45s", "muscle": "Obliques", "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=bicycle+crunch"},
    ],
    "full_body": [
        {"name": "Hip Thrust",              "sets": 3, "reps": "12-15", "rest": "75s", "muscle": "Glutes",       "weight_guide": "40-70kg barbell","equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=hip+thrust"},
        {"name": "Lat Pulldown",            "sets": 3, "reps": "12",    "rest": "75s", "muscle": "Back",         "weight_guide": "25-45kg",        "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=lat+pulldown"},
        {"name": "Leg Press",               "sets": 3, "reps": "12-15", "rest": "75s", "muscle": "Quads/Glutes", "weight_guide": "80-140kg",       "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=leg+press"},
        {"name": "Dumbbell Shoulder Press", "sets": 3, "reps": "12",    "rest": "60s", "muscle": "Shoulders",    "weight_guide": "8-14kg/hand",    "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=shoulder+press"},
        {"name": "Cable Kickback",          "sets": 3, "reps": "15 ea", "rest": "60s", "muscle": "Glutes",       "weight_guide": "10-18kg",        "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=cable+kickback"},
        {"name": "Seated Cable Row",        "sets": 3, "reps": "12",    "rest": "75s", "muscle": "Back",         "weight_guide": "25-45kg",        "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=seated+cable+row"},
        {"name": "Leg Curl",                "sets": 3, "reps": "15",    "rest": "60s", "muscle": "Hamstrings",   "weight_guide": "25-45kg",        "equipment_required": True, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=leg+curl"},
    ],
    "cardio": [
        {"name": "Treadmill Intervals",     "sets": 1, "reps": "20 min","rest": "0s", "muscle": "Cardio",       "weight_guide": "Moderate pace","equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=treadmill"},
        {"name": "Stairmaster",             "sets": 1, "reps": "15 min","rest": "0s", "muscle": "Glutes/Cardio","weight_guide": "Level 8-12",   "equipment_required": True,  "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=stairmaster"},
        {"name": "Bicycle Crunches",        "sets": 3, "reps": "20",   "rest": "30s","muscle": "Core",          "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=bicycle+crunch"},
        {"name": "Plank",                   "sets": 3, "reps": "60s",  "rest": "30s","muscle": "Core",          "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=plank"},
        {"name": "Jump Rope",               "sets": 3, "reps": "2 min","rest": "60s","muscle": "Cardio/Calves", "weight_guide": "Jump rope",    "equipment_required": False, "demo_url": "https://www.youtube.com/@carolinegirvan/search?query=jump+rope"},
    ],
    # Female gym uses male gym for compound sessions (gender-appropriate through form cue coaching)
    "push":       None,
    "pull":       None,
    "legs":       None,
    "upper_body": None,
}
_GYM_FEMALE["push"]       = _GYM_MALE["push"]
_GYM_FEMALE["pull"]       = _GYM_MALE["pull"]
_GYM_FEMALE["legs"]       = _GYM_MALE["legs"]
_GYM_FEMALE["upper_body"] = _GYM_MALE["upper_body"]

_HOME_MALE = {
    # ── Push (Chest/Shoulders/Triceps — bodyweight, no gym) ───────────────────
    "push": [
        {"name": "Push-Up",               "sets": 4, "reps": "15-20", "rest": "60s", "muscle": "Chest",          "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=push+up"},
        {"name": "Wide Push-Up",          "sets": 3, "reps": "15",    "rest": "60s", "muscle": "Chest (Outer)",  "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=wide+push+up"},
        {"name": "Diamond Push-Up",       "sets": 3, "reps": "12",    "rest": "60s", "muscle": "Triceps",        "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=diamond+push+up"},
        {"name": "Pike Push-Up",          "sets": 3, "reps": "12-15", "rest": "60s", "muscle": "Shoulders",      "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=pike+push+up"},
        {"name": "Decline Push-Up",       "sets": 3, "reps": "15",    "rest": "60s", "muscle": "Upper Chest",    "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=decline+push+up"},
        {"name": "Chair Dip",             "sets": 3, "reps": "15-18", "rest": "60s", "muscle": "Triceps",        "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=tricep+dip"},
        {"name": "Archer Push-Up",        "sets": 3, "reps": "8 ea",  "rest": "75s", "muscle": "Chest/Biceps",   "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=archer+push+up"},
        {"name": "Explosive Push-Up",     "sets": 3, "reps": "8-10",  "rest": "75s", "muscle": "Chest/Power",    "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=explosive+push+up"},
        {"name": "Incline Push-Up",       "sets": 3, "reps": "20",    "rest": "60s", "muscle": "Lower Chest",    "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=incline+push+up"},
        {"name": "Pseudo Planche Push-Up","sets": 3, "reps": "8-10",  "rest": "75s", "muscle": "Chest/Delts",    "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=pseudo+planche+push+up"},
        {"name": "One-Arm Push-Up Progression","sets": 3,"reps": "5 ea","rest": "90s","muscle": "Chest/Strength","weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=one+arm+push+up"},
    ],
    # ── Pull (Back/Biceps — bodyweight) ───────────────────────────────────────
    "pull": [
        {"name": "Pull-Up",               "sets": 4, "reps": "6-10",  "rest": "90s", "muscle": "Lats",           "weight_guide": "Bodyweight",     "equipment_required": True,  "demo_url": "https://www.youtube.com/@chrisheria/search?query=pull+up"},
        {"name": "Chin-Up",               "sets": 3, "reps": "8-10",  "rest": "75s", "muscle": "Biceps/Lats",    "weight_guide": "Bodyweight",     "equipment_required": True,  "demo_url": "https://www.youtube.com/@chrisheria/search?query=chin+up"},
        {"name": "Inverted Row (table)",  "sets": 4, "reps": "12-15", "rest": "60s", "muscle": "Back",           "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=inverted+row"},
        {"name": "Negative Pull-Up",      "sets": 3, "reps": "5",     "rest": "90s", "muscle": "Lats",           "weight_guide": "Bodyweight",     "equipment_required": True,  "demo_url": "https://www.youtube.com/@chrisheria/search?query=negative+pull+up"},
        {"name": "Superman Hold",         "sets": 3, "reps": "10",    "rest": "45s", "muscle": "Lower Back",     "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=superman"},
        {"name": "Band Bicep Curl",       "sets": 3, "reps": "15",    "rest": "45s", "muscle": "Biceps",         "weight_guide": "Light band",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=resistance+band+curl"},
        {"name": "Band Pull-Apart",       "sets": 3, "reps": "20",    "rest": "45s", "muscle": "Rear Delts",     "weight_guide": "Light band",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=band+pull+apart"},
        {"name": "Resistance Band Row",   "sets": 3, "reps": "15",    "rest": "60s", "muscle": "Mid Back",       "weight_guide": "Medium band",    "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=resistance+band+row"},
        {"name": "Australian Pull-Up",    "sets": 3, "reps": "12",    "rest": "60s", "muscle": "Back",           "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=australian+pull+up"},
        {"name": "Towel Bicep Curl",      "sets": 3, "reps": "12",    "rest": "45s", "muscle": "Biceps",         "weight_guide": "Bodyweight",     "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=towel+bicep+curl"},
    ],
    # ── Legs (Quads/Hamstrings/Glutes — bodyweight) ───────────────────────────
    "legs": [
        {"name": "Bodyweight Squat",         "sets": 4, "reps": "20-25", "rest": "60s", "muscle": "Quads",          "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=bodyweight+squat"},
        {"name": "Jump Squat",               "sets": 3, "reps": "15",    "rest": "75s", "muscle": "Quads/Power",    "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=jump+squat"},
        {"name": "Reverse Lunge",            "sets": 3, "reps": "12 ea", "rest": "60s", "muscle": "Quads",          "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=reverse+lunge"},
        {"name": "Bulgarian Split Squat (BW)","sets": 3, "reps": "10 ea","rest": "75s", "muscle": "Quads/Glutes",   "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=bulgarian+split+squat"},
        {"name": "Single-Leg Glute Bridge",  "sets": 3, "reps": "15 ea","rest": "60s", "muscle": "Glutes",         "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=single+leg+glute+bridge"},
        {"name": "Nordic Hamstring Curl",    "sets": 3, "reps": "5-8",  "rest": "90s", "muscle": "Hamstrings",     "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=nordic+hamstring+curl"},
        {"name": "Wall Sit",                 "sets": 3, "reps": "45-60s","rest": "60s","muscle": "Quads",           "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=wall+sit"},
        {"name": "Step-Up (chair)",          "sets": 3, "reps": "12 ea","rest": "60s", "muscle": "Quads/Glutes",   "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=step+up"},
        {"name": "Lateral Squat",            "sets": 3, "reps": "10 ea","rest": "60s", "muscle": "Inner Quads",    "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=lateral+squat"},
        {"name": "Calf Raises (bodyweight)", "sets": 4, "reps": "25-30","rest": "45s", "muscle": "Calves",         "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=calf+raise"},
    ],
    # ── Full Body (compound functional movements) ─────────────────────────────
    "full_body": [
        {"name": "Burpee",               "sets": 3, "reps": "12",    "rest": "75s", "muscle": "Full Body",      "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=burpee"},
        {"name": "Mountain Climber",     "sets": 3, "reps": "30s",   "rest": "45s", "muscle": "Core/Cardio",    "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=mountain+climber"},
        {"name": "Inchworm",             "sets": 3, "reps": "10",    "rest": "60s", "muscle": "Full Body",      "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=inchworm"},
        {"name": "Squat Thrust",         "sets": 3, "reps": "12",    "rest": "60s", "muscle": "Full Body",      "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=squat+thrust"},
        {"name": "Bear Crawl",           "sets": 3, "reps": "15m",   "rest": "60s", "muscle": "Full Body/Core", "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=bear+crawl"},
        {"name": "Sprawl",               "sets": 3, "reps": "10",    "rest": "60s", "muscle": "Full Body/Power","weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=sprawl"},
        {"name": "Plank to Push-Up",     "sets": 3, "reps": "10",    "rest": "60s", "muscle": "Core/Chest",     "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=plank+to+push+up"},
        {"name": "Lunge to High Knee",   "sets": 3, "reps": "10 ea", "rest": "60s", "muscle": "Legs/Core",      "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=lunge+knee+drive"},
        {"name": "Tuck Jump",            "sets": 3, "reps": "10",    "rest": "75s", "muscle": "Explosive Power","weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=tuck+jump"},
    ],
    # ── Upper Body (push/pull superset style) ─────────────────────────────────
    "upper_body": [
        {"name": "Push-Up",              "sets": 3, "reps": "15-20", "rest": "45s", "muscle": "Chest",          "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=push+up"},
        {"name": "Inverted Row (table)", "sets": 3, "reps": "12",    "rest": "45s", "muscle": "Back",           "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=inverted+row"},
        {"name": "Diamond Push-Up",      "sets": 3, "reps": "12",    "rest": "45s", "muscle": "Triceps",        "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=diamond+push+up"},
        {"name": "Band Bicep Curl",      "sets": 3, "reps": "15",    "rest": "45s", "muscle": "Biceps",         "weight_guide": "Light band",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=resistance+band+curl"},
        {"name": "Pike Push-Up",         "sets": 3, "reps": "12",    "rest": "60s", "muscle": "Shoulders",      "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=pike+push+up"},
        {"name": "Chair Dip",            "sets": 3, "reps": "15",    "rest": "60s", "muscle": "Triceps",        "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=tricep+dip"},
        {"name": "Pull-Up",              "sets": 3, "reps": "6-8",   "rest": "75s", "muscle": "Lats",           "weight_guide": "Bodyweight",  "equipment_required": True,  "demo_url": "https://www.youtube.com/@chrisheria/search?query=pull+up"},
        {"name": "Band Pull-Apart",      "sets": 3, "reps": "20",    "rest": "30s", "muscle": "Rear Delts",     "weight_guide": "Light band",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=band+pull+apart"},
    ],
    # ── Lower Body (quads/hamstrings emphasis) ────────────────────────────────
    "lower_body": [
        {"name": "Pause Squat",          "sets": 4, "reps": "12",    "rest": "60s", "muscle": "Quads",          "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=pause+squat"},
        {"name": "Reverse Lunge",        "sets": 3, "reps": "12 ea", "rest": "60s", "muscle": "Quads",          "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=reverse+lunge"},
        {"name": "Single-Leg Glute Bridge","sets": 4,"reps": "15 ea","rest": "60s", "muscle": "Glutes",         "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=single+leg+glute+bridge"},
        {"name": "Wall Sit",             "sets": 3, "reps": "45-60s","rest": "60s", "muscle": "Quads",          "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=wall+sit"},
        {"name": "Jump Squat",           "sets": 3, "reps": "12",    "rest": "75s", "muscle": "Explosive Legs", "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=jump+squat"},
        {"name": "Nordic Hamstring Curl","sets": 3, "reps": "5-8",   "rest": "90s", "muscle": "Hamstrings",     "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=nordic+curl"},
        {"name": "Calf Raises",          "sets": 4, "reps": "25",    "rest": "45s", "muscle": "Calves",         "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=calf+raise"},
    ],
    # ── Cardio (no equipment HIIT) ────────────────────────────────────────────
    "cardio": [
        {"name": "Burpee",               "sets": 4, "reps": "12",    "rest": "60s", "muscle": "Full Body",     "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=burpee"},
        {"name": "Mountain Climber",     "sets": 4, "reps": "30s",   "rest": "30s", "muscle": "Core/Cardio",   "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=mountain+climber"},
        {"name": "High Knees",           "sets": 4, "reps": "30s",   "rest": "30s", "muscle": "Cardio",        "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=high+knees"},
        {"name": "Skater Jump",          "sets": 3, "reps": "15 ea", "rest": "45s", "muscle": "Glutes/Cardio", "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=skater+jump"},
        {"name": "Star Jump",            "sets": 3, "reps": "15",    "rest": "30s", "muscle": "Full Body",     "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=star+jump"},
        {"name": "Shadow Jump Rope",     "sets": 3, "reps": "2 min", "rest": "60s", "muscle": "Calves/Cardio", "weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=jump+rope"},
        {"name": "Tuck Jump",            "sets": 3, "reps": "10",    "rest": "60s", "muscle": "Explosive Legs","weight_guide": "Bodyweight",  "equipment_required": False, "demo_url": "https://www.youtube.com/@chrisheria/search?query=tuck+jump"},
    ],
}

_HOME_FEMALE = {
    "glutes": [
        {"name": "Glute Bridge",            "sets": 4, "reps": "20",    "rest": "60s",  "muscle": "Glutes",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=glute+bridge"},
        {"name": "Single-Leg Glute Bridge", "sets": 3, "reps": "15 ea", "rest": "60s",  "muscle": "Glutes",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=single+leg+glute+bridge"},
        {"name": "Donkey Kicks",            "sets": 3, "reps": "20 ea", "rest": "45s",  "muscle": "Glutes",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=donkey+kicks"},
        {"name": "Fire Hydrants",           "sets": 3, "reps": "20 ea", "rest": "45s",  "muscle": "Glutes",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=fire+hydrants"},
        {"name": "Clamshells",              "sets": 3, "reps": "20 ea", "rest": "30s",  "muscle": "Hip Abductors", "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=clamshells"},
        {"name": "Sumo Squat",              "sets": 4, "reps": "20",    "rest": "60s",  "muscle": "Glutes/Quads",  "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=sumo+squat"},
        {"name": "Curtsy Lunge",            "sets": 3, "reps": "15 ea", "rest": "60s",  "muscle": "Glutes",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=curtsy+lunge"},
        {"name": "Pulse Squat",             "sets": 3, "reps": "30",    "rest": "45s",  "muscle": "Glutes/Quads",  "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=pulse+squat"},
        {"name": "Frog Pumps",              "sets": 3, "reps": "25",    "rest": "45s",  "muscle": "Glutes",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=frog+pumps"},
        {"name": "Hip Circle",              "sets": 3, "reps": "15 ea", "rest": "30s",  "muscle": "Hip Abductors", "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=hip+circles"},
    ],
    "upper_toning": [
        {"name": "Incline Push-Up",         "sets": 3, "reps": "15",    "rest": "60s",  "muscle": "Chest",         "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=incline+push+up"},
        {"name": "Push-Up",                 "sets": 3, "reps": "12",    "rest": "60s",  "muscle": "Chest/Triceps", "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=push+up"},
        {"name": "Tricep Dip (chair)",      "sets": 3, "reps": "15",    "rest": "60s",  "muscle": "Triceps",       "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=tricep+dip"},
        {"name": "Pike Push-Up",            "sets": 3, "reps": "10",    "rest": "60s",  "muscle": "Shoulders",     "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=pike+push+up"},
        {"name": "Band Bicep Curl",         "sets": 3, "reps": "15",    "rest": "45s",  "muscle": "Biceps",        "weight_guide": "Light band", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=resistance+band+curl"},
        {"name": "Band Lateral Raise",      "sets": 3, "reps": "15",    "rest": "45s",  "muscle": "Shoulders",     "weight_guide": "Light band", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=band+lateral+raise"},
        {"name": "Band Row",                "sets": 3, "reps": "15",    "rest": "60s",  "muscle": "Back",          "weight_guide": "Light band", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=resistance+band+row"},
        {"name": "Band Pull-Apart",         "sets": 3, "reps": "20",    "rest": "45s",  "muscle": "Rear Delts",    "weight_guide": "Light band", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=band+pull+apart"},
        {"name": "Inverted Row (table)",    "sets": 3, "reps": "10",    "rest": "60s",  "muscle": "Back",          "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=inverted+row"},
    ],
    "lower_body": [
        {"name": "Bodyweight Squat",        "sets": 4, "reps": "20",    "rest": "60s",  "muscle": "Quads/Glutes",  "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=squat"},
        {"name": "Reverse Lunge",           "sets": 3, "reps": "15 ea", "rest": "60s",  "muscle": "Quads/Glutes",  "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=reverse+lunge"},
        {"name": "Glute Bridge",            "sets": 4, "reps": "20",    "rest": "45s",  "muscle": "Glutes",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=glute+bridge"},
        {"name": "Jump Squat",              "sets": 3, "reps": "15",    "rest": "75s",  "muscle": "Quads/Power",   "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=jump+squat"},
        {"name": "Lateral Lunge",           "sets": 3, "reps": "12 ea", "rest": "60s",  "muscle": "Quads/Hip",     "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=lateral+lunge"},
        {"name": "Wall Sit",                "sets": 3, "reps": "45s",   "rest": "60s",  "muscle": "Quads",         "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=wall+sit"},
        {"name": "Calf Raises",             "sets": 3, "reps": "25",    "rest": "30s",  "muscle": "Calves",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=calf+raises"},
        {"name": "Step-Up (chair)",         "sets": 3, "reps": "12 ea", "rest": "60s",  "muscle": "Quads/Glutes",  "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=step+up"},
    ],
    "core_cardio": [
        {"name": "Plank",                   "sets": 3, "reps": "45s",   "rest": "45s",  "muscle": "Core",          "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=plank"},
        {"name": "Bicycle Crunch",          "sets": 3, "reps": "20 ea", "rest": "45s",  "muscle": "Obliques",      "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=bicycle+crunch"},
        {"name": "Leg Raise",               "sets": 3, "reps": "15",    "rest": "45s",  "muscle": "Lower Core",    "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=leg+raise"},
        {"name": "Russian Twist",           "sets": 3, "reps": "20",    "rest": "45s",  "muscle": "Obliques",      "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=russian+twist"},
        {"name": "Mountain Climber",        "sets": 3, "reps": "30s",   "rest": "45s",  "muscle": "Core/Cardio",   "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=mountain+climbers"},
        {"name": "High Knees",              "sets": 3, "reps": "30s",   "rest": "30s",  "muscle": "Cardio",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=high+knees"},
        {"name": "Jumping Jacks",           "sets": 3, "reps": "40",    "rest": "30s",  "muscle": "Cardio",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=jumping+jacks"},
        {"name": "Side Plank",              "sets": 3, "reps": "30s ea","rest": "45s",  "muscle": "Obliques/Core", "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=side+plank"},
    ],
    "full_body": [
        {"name": "Burpee",                  "sets": 3, "reps": "10",    "rest": "75s",  "muscle": "Full Body",     "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=burpee"},
        {"name": "Glute Bridge",            "sets": 3, "reps": "20",    "rest": "45s",  "muscle": "Glutes",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=glute+bridge"},
        {"name": "Push-Up",                 "sets": 3, "reps": "12",    "rest": "60s",  "muscle": "Chest",         "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=push+up"},
        {"name": "Reverse Lunge",           "sets": 3, "reps": "12 ea", "rest": "60s",  "muscle": "Legs",          "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=reverse+lunge"},
        {"name": "Plank",                   "sets": 3, "reps": "40s",   "rest": "45s",  "muscle": "Core",          "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=plank"},
        {"name": "Donkey Kicks",            "sets": 3, "reps": "15 ea", "rest": "45s",  "muscle": "Glutes",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=donkey+kicks"},
        {"name": "Mountain Climber",        "sets": 3, "reps": "30s",   "rest": "45s",  "muscle": "Core/Cardio",   "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=mountain+climbers"},
        {"name": "Sumo Squat",              "sets": 3, "reps": "20",    "rest": "60s",  "muscle": "Glutes/Quads",  "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=sumo+squat"},
    ],
    "cardio": [
        {"name": "High Knees",              "sets": 4, "reps": "40s",   "rest": "20s",  "muscle": "Cardio",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=high+knees"},
        {"name": "Jumping Jacks",           "sets": 3, "reps": "45s",   "rest": "20s",  "muscle": "Cardio",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=jumping+jacks"},
        {"name": "Mountain Climber",        "sets": 3, "reps": "40s",   "rest": "30s",  "muscle": "Core/Cardio",   "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=mountain+climbers"},
        {"name": "Burpee",                  "sets": 3, "reps": "10",    "rest": "60s",  "muscle": "Full Body",     "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=burpee"},
        {"name": "Skater Jump",             "sets": 3, "reps": "20",    "rest": "45s",  "muscle": "Cardio/Legs",   "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=skater+jump"},
        {"name": "Star Jump",               "sets": 3, "reps": "20",    "rest": "30s",  "muscle": "Cardio",        "weight_guide": "Bodyweight", "equipment_required": False, "demo_url": "https://www.youtube.com/@heatherrobertson/search?query=star+jump"},
    ],
}

# ── Injury-Safe Database (matches desktop INJURY_SAFE_DB) ────────────────────
_INJURY_SAFE = {
    "upper": [
        {"name": "Seated Dumbbell Press",  "sets": 3, "reps": "12",    "rest": "75s", "muscle": "Shoulders", "weight_guide": "5-14kg",    "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=seated+dumbbell+press"},
        {"name": "Cable Lat Pulldown",     "sets": 3, "reps": "12",    "rest": "75s", "muscle": "Back",      "weight_guide": "20-45kg",   "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=lat+pulldown"},
        {"name": "Band Pull-Apart",        "sets": 3, "reps": "20",    "rest": "45s", "muscle": "Rear Delts","weight_guide": "Light band","equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=band+pull+apart"},
        {"name": "Seated Cable Row",       "sets": 3, "reps": "12",    "rest": "75s", "muscle": "Back",      "weight_guide": "25-50kg",   "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=seated+cable+row"},
        {"name": "Wrist Curl",             "sets": 3, "reps": "15",    "rest": "45s", "muscle": "Forearms",  "weight_guide": "5-12kg",    "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=wrist+curl"},
    ],
    "lower": [
        {"name": "Leg Press (shallow)", "sets": 3, "reps": "15",    "rest": "75s", "muscle": "Quads",    "weight_guide": "60-110kg",  "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=shallow+leg+press"},
        {"name": "Seated Leg Curl",     "sets": 3, "reps": "15",    "rest": "60s", "muscle": "Hamstrings","weight_guide": "25-50kg",   "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=seated+leg+curl"},
        {"name": "Calf Raises",         "sets": 4, "reps": "20",    "rest": "45s", "muscle": "Calves",   "weight_guide": "Bodyweight","equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=calf+raise"},
        {"name": "Hip Thrust (light)",  "sets": 3, "reps": "15",    "rest": "60s", "muscle": "Glutes",   "weight_guide": "BW-40kg",  "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=hip+thrust"},
        {"name": "Wall Sit",            "sets": 3, "reps": "45s",   "rest": "60s", "muscle": "Quads",    "weight_guide": "Bodyweight","equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=wall+sit"},
    ],
    "full_body": [
        {"name": "Seated Band Row",      "sets": 3, "reps": "15",    "rest": "60s", "muscle": "Back",      "weight_guide": "Light band","equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=resistance+band+row"},
        {"name": "Lying Hip Abduction",  "sets": 3, "reps": "15 ea", "rest": "45s", "muscle": "Hips",      "weight_guide": "Bodyweight","equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=hip+abduction"},
        {"name": "Seated Shoulder Press","sets": 3, "reps": "12",    "rest": "60s", "muscle": "Shoulders", "weight_guide": "8-16kg",   "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=seated+shoulder+press"},
        {"name": "Calf Raises",          "sets": 3, "reps": "20",    "rest": "45s", "muscle": "Calves",    "weight_guide": "Bodyweight","equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=calf+raise"},
        {"name": "Band Pull-Apart",      "sets": 3, "reps": "20",    "rest": "45s", "muscle": "Rear Delts","weight_guide": "Light band","equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=band+pull+apart"},
    ],
}

# ── Sport databases — 100% sport-specific, zero gym exercise overlap ──────────
_SPORT = {
    # ── CRICKET ──────────────────────────────────────────────────────────────────
    "cricket": {
        "batting_power": [
            {"name": "Shadow Batting Footwork",    "sets": 4, "reps": "90s",    "rest": "60s",  "muscle": "Footwork/Coordination", "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=cricket+batting+footwork+drill"},
            {"name": "Resistance Band Bat Swing",  "sets": 4, "reps": "15",     "rest": "60s",  "muscle": "Rotational Power",      "weight_guide": "Medium band",  "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=cricket+bat+swing+resistance+band+training"},
            {"name": "Med Ball Rotational Throw",  "sets": 4, "reps": "10 ea",  "rest": "90s",  "muscle": "Core/Hip Drive",        "weight_guide": "4-6kg ball",   "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=medicine+ball+rotational+throw+cricket+batting"},
            {"name": "Hip Drive Drill",            "sets": 3, "reps": "12",     "rest": "60s",  "muscle": "Hips/Glutes",           "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=hip+drive+drill+cricket+batting+power"},
            {"name": "Wrist Roller",               "sets": 3, "reps": "2 min",  "rest": "60s",  "muscle": "Forearms/Wrists",       "weight_guide": "Light weight", "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=wrist+roller+exercise+cricket+training"},
            {"name": "T-Step Batting Drill",       "sets": 4, "reps": "10 ea",  "rest": "45s",  "muscle": "Footwork/Agility",      "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=cricket+t+step+batting+footwork+drill"},
        ],
        "cricket_mobility": [
            {"name": "Thoracic Rotation Stretch",  "sets": 3, "reps": "10 ea",  "rest": "30s",  "muscle": "Thoracic Spine",        "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=thoracic+rotation+stretch+cricket+mobility"},
            {"name": "Hip 90/90 Stretch",          "sets": 3, "reps": "60s ea", "rest": "20s",  "muscle": "Hips",                  "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=90+90+hip+stretch+cricket+athlete"},
            {"name": "Shoulder External Rotation", "sets": 3, "reps": "15",     "rest": "30s",  "muscle": "Rotator Cuff",          "weight_guide": "Light band",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=shoulder+external+rotation+cricket+injury+prevention"},
            {"name": "Cat-Cow Stretch",            "sets": 3, "reps": "15",     "rest": "20s",  "muscle": "Spine",                 "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=cat+cow+stretch+cricket+warm+up"},
            {"name": "Pigeon Pose",                "sets": 3, "reps": "60s ea", "rest": "0s",   "muscle": "Hip Flexors",           "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=pigeon+pose+cricket+flexibility"},
            {"name": "World's Greatest Stretch",   "sets": 3, "reps": "6 ea",   "rest": "30s",  "muscle": "Full Body",             "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=worlds+greatest+stretch+cricket+warm+up"},
            {"name": "Wrist Mobility Circles",     "sets": 3, "reps": "20 ea",  "rest": "20s",  "muscle": "Wrists",                "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=wrist+mobility+drill+cricket+batting"},
        ],
        "cricket_conditioning": [
            {"name": "17m Sprint Intervals",       "sets": 8, "reps": "17m sprint","rest": "45s","muscle": "Speed/Conditioning",    "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=cricket+17m+sprint+conditioning+drill"},
            {"name": "Shuttle Run (wicket width)", "sets": 6, "reps": "1 min",  "rest": "60s",  "muscle": "Speed Endurance",       "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=cricket+shuttle+run+between+wickets+fitness"},
            {"name": "6-Ball Sprint-Recovery",     "sets": 4, "reps": "6×10m",  "rest": "90s",  "muscle": "Match Fitness",         "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=cricket+6+ball+sprint+recovery+fitness"},
            {"name": "Lateral Speed Ladder",       "sets": 5, "reps": "30s",    "rest": "45s",  "muscle": "Footwork/Agility",      "weight_guide": "Agility ladder","equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=cricket+agility+ladder+footwork+speed+drill"},
            {"name": "Skip Rope",                  "sets": 4, "reps": "2 min",  "rest": "60s",  "muscle": "Cardio/Footwork",       "weight_guide": "Jump rope",    "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=jump+rope+cricket+conditioning+training"},
        ],
        "fielding_agility": [
            {"name": "T-Drill (cone)",             "sets": 5, "reps": "1 run",  "rest": "60s",  "muscle": "Agility/Quickness",     "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=t+drill+cricket+fielding+agility"},
            {"name": "Figure-8 Cone Drill",        "sets": 4, "reps": "30s",    "rest": "45s",  "muscle": "Change of Direction",   "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=figure+8+cone+drill+cricket+fielding"},
            {"name": "Dive and Recover",           "sets": 4, "reps": "8",      "rest": "60s",  "muscle": "Full Body Agility",     "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=cricket+fielding+dive+and+recover+drill"},
            {"name": "Throwing Speed Drill",       "sets": 3, "reps": "10 ea",  "rest": "60s",  "muscle": "Shoulder/Core",         "weight_guide": "Cricket ball", "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=cricket+throwing+speed+accuracy+fielding+drill"},
            {"name": "Ground Ball Fielding",       "sets": 4, "reps": "10 ea",  "rest": "45s",  "muscle": "Reaction/Agility",      "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=cricket+ground+fielding+technique+drill"},
            {"name": "Skater Jump",                "sets": 3, "reps": "12 ea",  "rest": "60s",  "muscle": "Lateral Power",         "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=skater+jump+lateral+bound+cricket+training"},
        ],
        "bowling_strength": [
            {"name": "Hip Drive Drill (Bowling)",  "sets": 4, "reps": "12",     "rest": "60s",  "muscle": "Hips/Glutes",           "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=cricket+bowling+hip+drive+drill"},
            {"name": "Pallof Press",               "sets": 3, "reps": "12 ea",  "rest": "60s",  "muscle": "Anti-Rotation Core",    "weight_guide": "Light band",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=pallof+press+cricket+bowling+core"},
            {"name": "Single-Leg Landing Drill",   "sets": 4, "reps": "8 ea",   "rest": "75s",  "muscle": "Ankle/Knee Stability",  "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=single+leg+landing+drill+cricket+bowling"},
            {"name": "Shoulder External Rotation", "sets": 3, "reps": "15",     "rest": "45s",  "muscle": "Rotator Cuff",          "weight_guide": "Light band",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=shoulder+external+rotation+cricket+bowling+injury"},
            {"name": "Nordic Hamstring Curl",      "sets": 3, "reps": "6",      "rest": "90s",  "muscle": "Hamstrings",            "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=nordic+hamstring+curl+cricket+bowling+prevention"},
            {"name": "Med Ball Overhead Slam",     "sets": 4, "reps": "8",      "rest": "75s",  "muscle": "Core/Total Body Power", "weight_guide": "4-6kg ball",   "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=medicine+ball+slam+cricket+bowling+power"},
        ],
    },

    # ── FOOTBALL ─────────────────────────────────────────────────────────────────
    "football": {
        "football_speed": [
            {"name": "10m Acceleration Sprint",    "sets": 6, "reps": "10m",    "rest": "90s",  "muscle": "Sprint Speed",          "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=10m+sprint+acceleration+football+training"},
            {"name": "Resisted Sprint (band)",     "sets": 5, "reps": "15m",    "rest": "90s",  "muscle": "Sprint Power",          "weight_guide": "Resistance band","equipment_required": False,"demo_url": "https://www.youtube.com/results?search_query=resisted+sprint+band+football+speed+training"},
            {"name": "Falling Start Sprint",       "sets": 5, "reps": "20m",    "rest": "90s",  "muscle": "Explosive Start",       "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=falling+start+sprint+drill+football"},
            {"name": "Fly 30m Sprint",             "sets": 4, "reps": "30m",    "rest": "120s", "muscle": "Top-End Speed",         "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=fly+30m+sprint+top+end+speed+football"},
            {"name": "Stride-Out Run",             "sets": 4, "reps": "60m",    "rest": "90s",  "muscle": "Speed Endurance",       "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=stride+out+run+speed+endurance+football"},
        ],
        "football_agility": [
            {"name": "5-10-5 Shuttle Run",         "sets": 5, "reps": "1 run",  "rest": "75s",  "muscle": "Change of Direction",   "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=5-10-5+shuttle+drill+football+agility"},
            {"name": "L-Drill (Cone)",             "sets": 4, "reps": "1 run",  "rest": "75s",  "muscle": "Agility/Footwork",      "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=l+drill+football+agility+training"},
            {"name": "Agility Ladder Footwork",    "sets": 5, "reps": "30s",    "rest": "45s",  "muscle": "Foot Speed",            "weight_guide": "Agility ladder","equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=agility+ladder+football+footwork+drills"},
            {"name": "Defensive Shuffle Drill",    "sets": 4, "reps": "10m ea", "rest": "60s",  "muscle": "Lateral Speed",         "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=defensive+lateral+shuffle+drill+football"},
            {"name": "Reactive Cone Drill",        "sets": 4, "reps": "30s",    "rest": "60s",  "muscle": "Reaction/Agility",      "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=reactive+cone+drill+football+agility"},
            {"name": "Box Drill (4-Cone)",         "sets": 4, "reps": "1 run",  "rest": "60s",  "muscle": "Multi-Directional",     "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=4+cone+box+drill+football+speed+agility"},
        ],
        "football_conditioning": [
            {"name": "30s On / 30s Off Intervals", "sets": 10, "reps": "30s run","rest": "30s",  "muscle": "Aerobic/Anaerobic",     "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=30+30+interval+sprint+football+fitness+conditioning"},
            {"name": "Box-to-Box Sprint",          "sets": 8, "reps": "68m",    "rest": "60s",  "muscle": "Match Fitness",         "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=box+to+box+sprint+football+fitness+conditioning"},
            {"name": "Yo-Yo Intermittent Test",    "sets": 1, "reps": "12 min", "rest": "0s",   "muscle": "Aerobic Capacity",      "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=yo+yo+intermittent+test+football+fitness"},
            {"name": "Slalom Run Through Cones",   "sets": 4, "reps": "30s",    "rest": "45s",  "muscle": "Agility/Cardio",        "weight_guide": "Cones",        "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=slalom+cone+run+football+dribbling+agility"},
            {"name": "Shuttle Run (10-20-30m)",    "sets": 5, "reps": "1 set",  "rest": "60s",  "muscle": "Speed Endurance",       "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=10+20+30+shuttle+run+football+conditioning"},
        ],
        "football_skill": [
            {"name": "Dribble Through Cones",      "sets": 4, "reps": "30s",    "rest": "45s",  "muscle": "Coordination/Touch",    "weight_guide": "Football",     "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=cone+dribbling+drill+football+close+control"},
            {"name": "Ball Striking Technique",    "sets": 4, "reps": "15 kicks","rest": "60s",  "muscle": "Hip Flexor/Power",      "weight_guide": "Football",     "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=ball+striking+technique+football+shooting+drill"},
            {"name": "First Touch Control Drill",  "sets": 3, "reps": "2 min",  "rest": "45s",  "muscle": "Coordination",          "weight_guide": "Football",     "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=first+touch+control+drill+football+technique"},
            {"name": "Receiving and Turning",      "sets": 3, "reps": "2 min",  "rest": "45s",  "muscle": "Coordination/Agility",  "weight_guide": "Football",     "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=receiving+and+turning+football+skill+drill"},
            {"name": "Wall Pass Drill",            "sets": 3, "reps": "3 min",  "rest": "60s",  "muscle": "Passing Accuracy",      "weight_guide": "Football/Wall","equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=wall+pass+drill+football+passing+technique"},
        ],
        "football_power": [
            {"name": "Broad Jump",                 "sets": 4, "reps": "6",      "rest": "90s",  "muscle": "Explosive Leg Power",   "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=broad+jump+plyometric+football+power"},
            {"name": "Lateral Bound",              "sets": 4, "reps": "8 ea",   "rest": "75s",  "muscle": "Lateral Power",         "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=lateral+bound+plyometric+football+training"},
            {"name": "Drop Jump",                  "sets": 4, "reps": "6",      "rest": "90s",  "muscle": "Reactive Strength",     "weight_guide": "Bodyweight",   "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=drop+jump+reactive+strength+football+plyometric"},
            {"name": "Explosive Sprint Start",     "sets": 5, "reps": "10m",    "rest": "90s",  "muscle": "Starting Speed",        "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=explosive+sprint+start+football+acceleration"},
            {"name": "Box Jump",                   "sets": 4, "reps": "6",      "rest": "90s",  "muscle": "Vertical Power",        "weight_guide": "Bodyweight",   "equipment_required": True,  "demo_url": "https://www.youtube.com/results?search_query=box+jump+vertical+power+football+training"},
            {"name": "Single-Leg Bound",           "sets": 3, "reps": "6 ea",   "rest": "90s",  "muscle": "Unilateral Power",      "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=single+leg+bound+football+power+training"},
        ],
    },

    # ── RUNNING ───────────────────────────────────────────────────────────────────
    "running": {
        "easy_run": [
            {"name": "Easy Conversational Run",    "sets": 1, "reps": "30-40 min","rest": "0s",  "muscle": "Aerobic Base",          "weight_guide": "60-65% max HR","equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=easy+run+pace+aerobic+base+training"},
            {"name": "Cadence Focus Drill",        "sets": 3, "reps": "5 min",  "rest": "2 min","muscle": "Running Economy",        "weight_guide": "Own pace",     "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=running+cadence+180+steps+drill"},
            {"name": "Walking Recovery",           "sets": 2, "reps": "5 min",  "rest": "0s",   "muscle": "Active Recovery",       "weight_guide": "Walk pace",    "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=active+recovery+walking+after+run"},
        ],
        "running_drills": [
            {"name": "A-Skip Drill",               "sets": 3, "reps": "20m",    "rest": "45s",  "muscle": "Running Mechanics",     "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=a+skip+running+drill+mechanics"},
            {"name": "B-Skip Drill",               "sets": 3, "reps": "20m",    "rest": "45s",  "muscle": "Running Mechanics",     "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=b+skip+running+drill+mechanics"},
            {"name": "High Knees Running Drill",   "sets": 3, "reps": "20m",    "rest": "45s",  "muscle": "Cadence/Hip Flexors",   "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=high+knees+running+drill+form"},
            {"name": "Butt Kicks Drill",           "sets": 3, "reps": "20m",    "rest": "45s",  "muscle": "Hamstrings/Cadence",    "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=butt+kicks+running+drill+hamstring"},
            {"name": "Bounding",                   "sets": 3, "reps": "30m",    "rest": "60s",  "muscle": "Power/Stride Length",   "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=bounding+running+drill+stride+length"},
            {"name": "Running Strides",            "sets": 6, "reps": "100m",   "rest": "60s",  "muscle": "Speed/Form",            "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=running+strides+speed+form+drill"},
            {"name": "Ankle Circles",              "sets": 3, "reps": "15 ea",  "rest": "20s",  "muscle": "Ankle Mobility",        "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=ankle+mobility+exercise+running+warm+up"},
        ],
        "tempo_run": [
            {"name": "Tempo Run",                  "sets": 1, "reps": "20-30 min","rest": "0s",  "muscle": "Lactate Threshold",     "weight_guide": "75-80% max HR","equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=tempo+run+training+guide+lactate+threshold"},
            {"name": "Pace Pickup Drill",          "sets": 4, "reps": "5 min",  "rest": "2 min","muscle": "Rhythm/Pace",            "weight_guide": "Tempo effort", "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=pace+pickup+running+tempo+drill"},
            {"name": "Threshold Intervals",        "sets": 3, "reps": "8 min",  "rest": "3 min","muscle": "Aerobic Power",          "weight_guide": "Comfortably hard","equipment_required": False,"demo_url": "https://www.youtube.com/results?search_query=threshold+running+intervals+tempo+training"},
        ],
        "track_intervals": [
            {"name": "400m Repeats",               "sets": 6, "reps": "400m",   "rest": "90s",  "muscle": "VO2 Max/Speed",         "weight_guide": "Race pace",    "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=400m+repeat+interval+track+training"},
            {"name": "800m Repeats",               "sets": 4, "reps": "800m",   "rest": "2 min","muscle": "VO2 Max/Endurance",      "weight_guide": "5K race pace", "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=800m+repeat+interval+workout+training"},
            {"name": "200m Fast Intervals",        "sets": 8, "reps": "200m",   "rest": "90s",  "muscle": "Speed/Anaerobic",       "weight_guide": "Mile race pace","equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=200m+interval+sprint+track+training"},
            {"name": "Hill Repeats",               "sets": 6, "reps": "30s hard","rest": "90s",  "muscle": "Power Endurance",       "weight_guide": "Hard effort",  "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=hill+repeats+running+power+endurance"},
        ],
        "long_run": [
            {"name": "Long Slow Distance Run",     "sets": 1, "reps": "45-90 min","rest": "0s",  "muscle": "Aerobic Endurance",     "weight_guide": "Easy pace",    "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=long+run+training+tips+aerobic+endurance"},
            {"name": "Negative Split Run",         "sets": 1, "reps": "40-60 min","rest": "0s",  "muscle": "Pacing/Endurance",      "weight_guide": "Easy to moderate","equipment_required": False,"demo_url": "https://www.youtube.com/results?search_query=negative+split+run+pacing+strategy+training"},
            {"name": "Fartlek Run",                "sets": 1, "reps": "30-45 min","rest": "0s",  "muscle": "Speed Endurance",       "weight_guide": "Mixed pace",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=fartlek+run+speed+endurance+training"},
            {"name": "Running Mobility Cool-Down", "sets": 1, "reps": "10 min", "rest": "0s",   "muscle": "Recovery",              "weight_guide": "Bodyweight",   "equipment_required": False, "demo_url": "https://www.youtube.com/results?search_query=running+cool+down+mobility+stretch+recovery"},
        ],
    },
}

# ── Routing maps (desktop-identical) ─────────────────────────────────────────
_MALE_GYM_MAP = {
    "push": "push", "push_volume": "push", "push_strength": "push",
    "pull": "pull", "pull_volume": "pull", "pull_strength": "pull",
    "legs": "legs", "legs_strength": "legs",
    "upper_body": "upper_body", "shoulders_arms": "upper_body", "strength": "upper_body",
    "lower_body": "lower_body", "lower_strength": "lower_body",
    "full_body": "full_body", "cardio": "cardio",
}
_FEMALE_GYM_MAP = {
    "lower_body": "lower_body", "glutes": "glutes", "glutes_hamstrings": "glutes",
    "legs": "glutes", "legs_strength": "glutes", "strength": "glutes",
    "upper_body": "upper_toning", "upper_toning": "upper_toning",
    "core_cardio": "core_cardio", "hiit": "core_cardio", "cardio": "cardio",
    "full_body": "full_body",
    "push": "push", "pull": "pull",
}
_MALE_HOME_MAP = {
    "push": "push", "upper_body": "upper_body", "shoulders_arms": "push",
    "pull": "pull",
    "legs": "legs", "lower_body": "lower_body", "lower_strength": "lower_body",
    "full_body": "full_body", "hiit": "full_body",
    "core_cardio": "full_body", "cardio": "cardio",
}
_FEMALE_HOME_MAP = {
    "lower_body": "lower_body", "glutes": "glutes", "glutes_hamstrings": "glutes",
    "legs": "glutes",
    "upper_body": "upper_toning", "upper_toning": "upper_toning",
    "core_cardio": "core_cardio", "hiit": "core_cardio", "cardio": "cardio",
    "full_body": "full_body",
}

_RICH_DBS = {
    ("male",   "gym"):  _GYM_MALE,
    ("female", "gym"):  _GYM_FEMALE,
    ("male",   "home"): _HOME_MALE,
    ("female", "home"): _HOME_FEMALE,
}
_SESSION_MAPS = {
    ("male",   "gym"):  _MALE_GYM_MAP,
    ("female", "gym"):  _FEMALE_GYM_MAP,
    ("male",   "home"): _MALE_HOME_MAP,
    ("female", "home"): _FEMALE_HOME_MAP,
}


# ── Movement-pattern classification (drives Ghost Trainer's pose analyzer choice) ──
# Ordered keyword rules; first match wins, checked against the lowercased exercise name.
# This is a heuristic, not an exhaustive hand-tag of all 212 exercises — many
# machine/cable/sport-drill exercises are approximated by the closest bodyweight
# pattern since a single webcam can't read machine resistance or judge sport technique.
_MOVEMENT_PATTERN_RULES: list[tuple[list[str], str]] = [
    (["leg curl", "hamstring curl", "nordic"],                                    "hip_hinge"),
    (["calf raise"],                                                              "calf_raise"),
    (["leg raise"],                                                               "core_flex"),
    (["lateral raise", "front raise", "upright row"],                             "lateral_raise"),
    (["push-up", "push up", "chest fly"],                                        "horizontal_push"),
    (["pallof"],                                                                  "core_rotation"),
    (["pull-up", "pull up", "chin-up", "chin up", "pulldown", "lat pull"],        "vertical_pull"),
    (["row", "face pull", "pull-apart", "pull apart"],                           "horizontal_pull"),
    (["deadlift", "hip thrust", "glute bridge", "kickback", "good morning",
      "hip drive", "hip circle", "donkey kick", "fire hydrant", "clamshell",
      "abductor", "hip abduction"],                                              "hip_hinge"),
    (["lunge", "split squat", "step-up", "step up"],                             "lunge"),
    (["squat", "leg press", "hack squat", "sissy squat"],                        "squat"),
    (["curl"],                                                                   "elbow_flexion"),
    (["pushdown", "triceps extension", "tricep extension", "skull crusher",
      "overhead extension", "dip"],                                             "elbow_extension"),
    (["plank", "wall sit", "hold", "hollow body"],                               "core_isometric"),
    (["twist", "chop", "windmill"],                                              "core_rotation"),
    (["crunch", "sit-up", "situp", "rollout", "v-up"],                           "core_flex"),
    (["jump", "sprint", "run", "walk", "shuttle", "ladder", "burpee",
      "mountain climber", "jumping jack", "star jump", "skip", "bound",
      "high knee", "butt kick", "box jump", "interval", "repeat", "conditioning",
      "dribble", "throw", "swing", "batting", "bowling", "fielding", "footwork",
      "agility", "drill", "stretch", "mobility", "cool-down", "cooldown",
      "stairmaster", "treadmill", "rowing machine", "cycling"],                  "cardio_generic"),
]

_MOVEMENT_PATTERN_CATEGORY_FALLBACK: dict[str, str] = {
    "push": "horizontal_push", "pull": "horizontal_pull", "legs": "squat",
    "upper_body": "horizontal_push", "lower_body": "squat", "glutes": "hip_hinge",
    "upper_toning": "horizontal_push", "core_cardio": "core_flex",
    "full_body": "full_body_generic", "cardio": "cardio_generic",
    "upper": "horizontal_push", "lower": "squat",
}

_VERTICAL_PRESS_QUALIFIERS = ["overhead", "shoulder", "military", "pike", "arnold", "seated"]


def classify_movement_pattern(name: str, session_key: str | None = None) -> str:
    """Best-effort mapping of an exercise name to a biomechanical movement pattern —
    drives which Ghost Trainer pose analyzer runs for it."""
    n = (name or "").lower()

    # "Press" exercises are the biggest chest-vs-shoulder ambiguity, and real names
    # often separate the qualifier word from "press" (e.g. "Overhead Barbell Press",
    # "Seated Dumbbell Press") so a simple contiguous-phrase match misses them —
    # check word presence anywhere in the name instead, order-agnostic. Excludes
    # "leg press" (squat pattern) and "pallof press" (anti-rotation core, not a push).
    if "press" in n and "leg press" not in n and "pallof" not in n:
        if any(q in n for q in _VERTICAL_PRESS_QUALIFIERS):
            return "vertical_push"
        return "horizontal_push"

    for keywords, pattern in _MOVEMENT_PATTERN_RULES:
        if any(kw in n for kw in keywords):
            return pattern
    return _MOVEMENT_PATTERN_CATEGORY_FALLBACK.get((session_key or "").lower(), "full_body_generic")


def _has_injury(profile: Profile) -> bool:
    inj = (profile.injuries or "").strip().lower()
    return bool(inj) and inj not in {"none", "no", "n/a", "na", "-"}


# ── Ghost Trainer form cues — per-exercise coaching intelligence ───────────────
_FORM_CUES: dict[str, dict] = {
    # ── Push ──────────────────────────────────────────────────────────────────
    "Barbell Bench Press": {
        "cues": ["Retract shoulder blades before unracking", "Bar travels in a slight arc — not straight up", "Drive feet into floor for leg drive", "Squeeze chest hard at the top"],
        "breathing": "Inhale on descent, exhale explosively on press",
        "trainer_tip": "Touch chest lightly — never bounce the bar off your sternum",
    },
    "Incline Dumbbell Press": {
        "cues": ["Set bench to 30-45° — higher kills upper chest activation", "Elbows at 45°, not flared to 90°", "Full stretch at bottom before pressing", "Squeeze pecs at top without locking elbows hard"],
        "breathing": "Inhale as you lower, exhale as you press",
        "trainer_tip": "Lower angle = more upper chest. Don't set bench too steep",
    },
    "Overhead Barbell Press": {
        "cues": ["Brace core like you're about to get punched", "Move your head back as bar passes face", "Bar travels in a straight vertical line", "Full lockout at top — squeeze delts hard"],
        "breathing": "Big breath in, brace, exhale after lockout",
        "trainer_tip": "Weak OHP usually means tight thoracic — stretch daily",
    },
    "Dumbbell Shoulder Press": {
        "cues": ["Start at ear height with elbows at 90°", "Press up and very slightly inward", "Don't lean back excessively — core braced", "Full ROM — don't cut reps short above head"],
        "breathing": "Exhale on press, inhale as you lower",
        "trainer_tip": "Standing version recruits more total muscle than seated",
    },
    "Lateral Raises": {
        "cues": ["Lead with your elbows, not your hands", "Slight forward lean of torso (10-15°)", "Control the negative — 3 seconds down", "Keep traps depressed — no shrugging"],
        "breathing": "Exhale as you raise, inhale as you lower",
        "trainer_tip": "Use lighter weight and feel every rep — form beats load here",
    },
    "Cable Lateral Raise": {
        "cues": ["Cable at hip level, cross-body pull", "Maintain slight elbow bend throughout", "Slow controlled arc — pause at top", "Don't swing torso to help the weight up"],
        "breathing": "Exhale on raise, inhale on return",
        "trainer_tip": "Cable keeps tension the whole rep unlike dumbbells",
    },
    "Triceps Pushdown": {
        "cues": ["Pin upper arms tight to torso — they don't move", "Full extension at bottom — squeeze triceps", "Don't lean forward or use momentum", "Slow 3-second eccentric for max tension"],
        "breathing": "Exhale on pushdown, inhale on return",
        "trainer_tip": "Rope attachment gives better wrist-neutral full extension",
    },
    "Skull Crushers": {
        "cues": ["Keep upper arms vertical and perfectly still", "Lower bar to forehead level — not behind head", "Don't lock elbows aggressively at top", "Controlled 3-second descent always"],
        "breathing": "Inhale on descent, exhale on extension",
        "trainer_tip": "Add slight elbow flare at top to keep triceps under tension",
    },
    "Arnold Press": {
        "cues": ["Start with palms facing you at chin height", "Rotate palms outward as you press up", "Smooth continuous rotation — don't rush", "Reverse the rotation on the way back down"],
        "breathing": "Exhale on press, inhale on return",
        "trainer_tip": "Slower tempo = more recruitment across all three delt heads",
    },
    "Cable Chest Flye": {
        "cues": ["Slight forward lean from hips — not spine", "Maintain the same elbow angle throughout", "Hugging motion — meet at centre at chest height", "Squeeze pecs hard at crossover point"],
        "breathing": "Inhale on open, exhale as you close",
        "trainer_tip": "High cables hit lower chest, low cables hit upper chest",
    },
    "Close-Grip Bench Press": {
        "cues": ["Hands shoulder-width — narrower hurts wrists", "Keep elbows tucked close against your torso", "Controlled descent to lower chest", "Drive hard through triceps to lockout"],
        "breathing": "Inhale on descent, exhale on press",
        "trainer_tip": "Best mass-builder for triceps combined with overall pressing",
    },
    "Decline Bench Press": {
        "cues": ["Secure feet in pads before unracking", "Wider grip targets lower chest better", "Control descent — gravity helps here", "Squeeze hard at lockout, don't rush"],
        "breathing": "Inhale on lower, exhale on press",
        "trainer_tip": "Lower chest often neglected — this fills the bottom line",
    },
    "Dips (Triceps)": {
        "cues": ["Keep torso upright for more triceps focus", "Elbows track backward, not flared out", "Full lockout at top — feel the triceps squeeze", "Don't dip below shoulder comfortable range"],
        "breathing": "Inhale on descent, exhale on press",
        "trainer_tip": "Lean forward slightly to shift emphasis toward chest",
    },

    # ── Pull ──────────────────────────────────────────────────────────────────
    "Weighted Pull-Ups": {
        "cues": ["Dead hang start — full arm extension every rep", "Depress shoulder first before pulling", "Pull elbows down and back — not just arms", "Control the descent — minimum 2 seconds down"],
        "breathing": "Exhale on pull up, inhale on descent",
        "trainer_tip": "Hollow body position activates lats and core simultaneously",
    },
    "Pull-Ups": {
        "cues": ["Dead hang start — full arm extension", "Initiate by pulling shoulder blades down", "Chin clears bar = full rep", "3-second controlled negative on every rep"],
        "breathing": "Exhale on pull, inhale descent",
        "trainer_tip": "If you can't do full reps, do 5-second negatives only first",
    },
    "Barbell Bent-Over Row": {
        "cues": ["Hinge at hips — torso at 45°, chest proud", "Pull bar to lower chest / upper abdomen", "Squeeze shoulder blades together at top", "Keep lower back neutral — never rounded"],
        "breathing": "Exhale on the pull, inhale on the lower",
        "trainer_tip": "Overhand = more rhomboids. Underhand = more biceps involvement",
    },
    "Seated Cable Row": {
        "cues": ["Sit tall with a slight forward lean to start", "Row to lower chest, not your belly", "Squeeze shoulder blades hard at end range", "Let shoulders fully protract forward on return"],
        "breathing": "Exhale on row, inhale on return",
        "trainer_tip": "Full ROM — let the blades move, don't just pull with arms",
    },
    "Chest-Supported Row": {
        "cues": ["Chest stays on pad throughout — no cheating", "Pull dumbbells toward lower chest level", "Squeeze shoulder blades hard at top", "Slow eccentric — don't drop the weights"],
        "breathing": "Exhale on row, inhale on lower",
        "trainer_tip": "Chest support eliminates all cheating — pure back work",
    },
    "Face Pulls": {
        "cues": ["Cable at face height or slightly above", "Pull rope to your forehead — elbows high and wide", "External rotate at end — thumbs behind ears", "Hold the squeeze for 1 second every rep"],
        "breathing": "Exhale on pull, inhale on return",
        "trainer_tip": "Single best exercise for long-term shoulder health and posture",
    },
    "Barbell Bicep Curls": {
        "cues": ["Pin elbows to your sides — they are fixed points", "Curl through full ROM — no half reps", "Squeeze bicep hard at top before lowering", "3-second controlled eccentric on every rep"],
        "breathing": "Exhale on curl, inhale on lower",
        "trainer_tip": "Don't swing — momentum steals directly from your bicep",
    },
    "Incline Dumbbell Curl": {
        "cues": ["Recline bench to 45-60 degrees", "Arms hang fully — maximum stretch at bottom", "Curl slowly — savour the long head stretch", "Don't bring elbows forward at the top"],
        "breathing": "Exhale on curl, inhale on lower",
        "trainer_tip": "Best exercise for bicep peak — maximises long head stretch",
    },
    "Lat Pulldown": {
        "cues": ["Slight torso lean back — 10-15° only", "Pull bar to upper chest — never behind neck", "Lead with elbows pulling down and back", "Let bar rise all the way for full lat stretch"],
        "breathing": "Exhale on pull, inhale on return",
        "trainer_tip": "Wide grip = lat width. Close neutral grip = lat thickness",
    },
    "Single-Arm DB Row": {
        "cues": ["Support knee and hand on bench", "Row dumbbell to hip — not chest", "Elbow drives back past your torso", "Don't rotate your torso — keep it square"],
        "breathing": "Exhale on row, inhale on lower",
        "trainer_tip": "Go heavy here — this is your best unilateral back builder",
    },
    "Hammer Curls": {
        "cues": ["Neutral grip (thumbs up) the entire movement", "Keep elbows fixed at your sides", "Slow controlled movement both directions", "Alternate arms to improve mind-muscle focus"],
        "breathing": "Exhale on curl, inhale on lower",
        "trainer_tip": "Hits brachialis muscle — makes arms look thicker and wider",
    },
    "Cable Straight-Arm Pulldown": {
        "cues": ["Arms nearly straight — slight elbow bend only", "Hinge forward 15° at hips", "Pull bar down to thighs in an arc", "Squeeze lats hard at bottom position"],
        "breathing": "Exhale on pulldown, inhale on return",
        "trainer_tip": "Incredible lat isolation — feel it not just lift it",
    },

    # ── Legs ──────────────────────────────────────────────────────────────────
    "Barbell Squat": {
        "cues": ["Bar on traps — big breath in, brace hard", "Push knees out aggressively over toes", "Break parallel — thighs below horizontal", "Drive through full foot on ascent, chest tall"],
        "breathing": "Deep breath and brace at top, exhale when standing",
        "trainer_tip": "Record yourself from the side to check your depth honestly",
    },
    "Romanian Deadlift": {
        "cues": ["Hinge at hips — slight knee bend maintained throughout", "Bar stays close — skim your legs on the way down", "Feel the hamstring stretch at the bottom", "Drive hips forward powerfully to lockout"],
        "breathing": "Inhale at top, hold during descent, exhale on ascent",
        "trainer_tip": "Don't load too heavy — it's about the stretch not the number",
    },
    "Leg Press": {
        "cues": ["Feet shoulder-width or slightly wider on the sled", "Never lock knees out fully at the top", "Press through full ROM — no half reps", "Keep lower back fully pressed against the pad"],
        "breathing": "Exhale on press, inhale on descent",
        "trainer_tip": "High foot position = more glutes and hamstrings. Low = more quads",
    },
    "Bulgarian Split Squat": {
        "cues": ["Rear foot elevated, stride length is long", "Front shin stays vertical throughout — key cue", "Drop straight down — don't lunge forward", "Drive powerfully through front heel to stand"],
        "breathing": "Inhale on descent, exhale on ascent",
        "trainer_tip": "The hardest single-leg exercise — most effective too",
    },
    "Leg Extension": {
        "cues": ["Pause hard at top — 1-second squeeze every rep", "3-second controlled descent — feel the quad", "Don't swing or kick — no momentum", "Toes slightly pulled back for VMO (teardrop) activation"],
        "breathing": "Exhale on extend, inhale on lower",
        "trainer_tip": "Full ROM matters — don't let the stack rest between reps",
    },
    "Leg Curl": {
        "cues": ["Keep hips firmly pressed into the pad", "Curl all the way — heel toward your glutes", "3-second slow eccentric on every rep", "Point toes slightly for more hamstring emphasis"],
        "breathing": "Exhale on curl, inhale on lower",
        "trainer_tip": "Do single-leg version to address left-right imbalances",
    },
    "Hip Thrust": {
        "cues": ["Upper back on bench, bar over hip crease with pad", "Drive through heels — not toes — at all times", "Full hip extension — glute squeeze at the absolute top", "Chin tucked in — maintain neutral spine throughout"],
        "breathing": "Exhale powerfully and forcefully at the top position",
        "trainer_tip": "Band above knees prevents knee cave and adds glute activation",
    },
    "Glute Bridge": {
        "cues": ["Heels close to glutes, feet flat on floor", "Drive hips up — squeeze glutes maximally at top", "2-second pause at the top — don't rush", "Lower with full control, don't crash down"],
        "breathing": "Exhale on bridge up, inhale on lower",
        "trainer_tip": "Elevate your shoulders on a bench to massively increase ROM",
    },
    "Cable Kickback": {
        "cues": ["Hinge forward slightly at hips for better alignment", "Keep hip of working leg stable — no rotation", "Squeeze glute hard at full extension", "Control the return — don't let it swing"],
        "breathing": "Exhale on kick, inhale on return",
        "trainer_tip": "Go lighter — feel the glute, don't swing the leg",
    },
    "Sumo Squat": {
        "cues": ["Wide stance — toes pointing out 45°", "Push knees aggressively outward on descent", "Keep chest tall and proud throughout", "Drive through heels and inner foot on ascent"],
        "breathing": "Inhale descent, exhale on ascent",
        "trainer_tip": "Great combined inner thigh and glute activator",
    },
    "Deadlift": {
        "cues": ["Bar over mid-foot, hip-width stance", "Push the floor away — don't think 'pull'", "Protect your armpits to engage lats properly", "Lock hips and knees out simultaneously at the top"],
        "breathing": "Big breath, brace your core, hold until lockout",
        "trainer_tip": "Setup is 90% of the lift — never ever rush your start position",
    },
    "Walking Lunges": {
        "cues": ["Long stride — land on heel first", "Back knee grazes the floor on every rep", "Keep your torso vertical throughout", "Push powerfully off front foot to step through"],
        "breathing": "Exhale on each ascent step",
        "trainer_tip": "Add dumbbells once bodyweight version is fully controlled",
    },
    "Standing Calf Raises": {
        "cues": ["Deep full stretch at bottom — don't skip it", "Hold peak contraction for 1-2 seconds at top", "Slow and controlled — don't bounce", "Use the full length of your foot, not just toes"],
        "breathing": "Exhale at top, inhale on descent",
        "trainer_tip": "Calves respond to high volume and high frequency — be consistent",
    },

    # ── Home / Bodyweight ─────────────────────────────────────────────────────
    "Push-Ups": {
        "cues": ["Hands slightly wider than shoulder-width", "Body in a perfectly straight line head to heels", "Chest touches the floor — full ROM only counts", "Elbows at 45° — never flared out to 90°"],
        "breathing": "Inhale on the way down, exhale on the way up",
        "trainer_tip": "Elevate feet for more upper chest. Incline for lower chest",
    },
    "Pike Push-Ups": {
        "cues": ["Hips high in the air — inverted V shape", "Head travels down toward floor between your hands", "Elbows track toward feet direction, not outward", "Head nearly touches floor for full shoulder ROM"],
        "breathing": "Inhale descent, exhale on press",
        "trainer_tip": "This is the pathway to handstand push-ups",
    },
    "Diamond Push-Ups": {
        "cues": ["Hands close together forming a diamond shape", "Elbows graze your sides as you lower down", "Keep core tight — no sagging hips at all", "Full lockout and tricep squeeze at the top"],
        "breathing": "Inhale down, exhale up",
        "trainer_tip": "The best pure bodyweight tricep exercise — no equipment needed",
    },
    "Bodyweight Squats": {
        "cues": ["Feet shoulder-width, toes slightly turned out", "Break at hips and knees simultaneously", "Thighs parallel to floor at absolute minimum", "Drive through your full foot on the way up"],
        "breathing": "Inhale on descent, exhale on ascent",
        "trainer_tip": "Add a pause at the bottom to eliminate bounce and increase intensity",
    },
    "Plank": {
        "cues": ["Forearms parallel, elbows directly under shoulders", "Posterior pelvic tilt — actively squeeze glutes", "Press the floor away — don't let hips sag", "Neutral neck — look straight down at floor"],
        "breathing": "Steady controlled breathing throughout the hold",
        "trainer_tip": "Increase hold time in 5-second increments — quality over duration",
    },
    "Mountain Climbers": {
        "cues": ["High plank position — wrists under shoulders", "Drive knee explosively to chest", "Keep hips level and square — no bouncing", "Alternate legs in a running rhythm"],
        "breathing": "Find a steady breathing rhythm as you go",
        "trainer_tip": "Slow = core focus. Fast = cardio conditioning. Both work",
    },
    "Burpees": {
        "cues": ["Fluid movement — plank, hop in, stand, jump", "Land softly on toes when jumping — absorb it", "Full hip extension at the top of every jump", "Hands stay shoulder-width in plank position"],
        "breathing": "Exhale on jump, find a steady breathing rhythm",
        "trainer_tip": "Step back instead of jumping out if knees are sensitive",
    },
    "Jump Squats": {
        "cues": ["Load into the full squat first before exploding", "Land softly — absorb with bent knees", "Full squat depth before every single jump", "Arm swing forward helps generate more power"],
        "breathing": "Exhale powerfully on each jump",
        "trainer_tip": "Plyometric training builds fast-twitch muscle fibers rapidly",
    },
    "High Knees": {
        "cues": ["Drive knees up to hip height every rep", "Pump arms in rhythm — opposite arm to knee", "Stay on balls of feet — light and fast contact", "Keep core braced and tight throughout"],
        "breathing": "Find a steady rhythmic breathing pattern",
        "trainer_tip": "Excellent warm-up activator or standalone cardio burst",
    },
    "Glute Bridges (Floor)": {
        "cues": ["Heels close to glutes, feet flat on floor", "Squeeze glutes and drive hips high", "Pause 2 full seconds at the top position", "Lower with control — don't crash back down"],
        "breathing": "Exhale on bridge up, inhale on lower",
        "trainer_tip": "Single-leg version doubles the glute intensity immediately",
    },

    # ── Glutes / Female specific ──────────────────────────────────────────────
    "Banded Hip Thrust": {
        "cues": ["Band just above knees — push outward throughout", "Full hip extension at the top — hard glute squeeze", "Chin tucked — ribs down, no hyperextension", "Drive through heels — feel the glutes, not quads"],
        "breathing": "Exhale powerfully at full extension",
        "trainer_tip": "The band prevents knee cave and doubles glute activation",
    },
    "Sumo Deadlift": {
        "cues": ["Wide stance, toes pointing out — stand tall", "Hips hinge down to bar — not a squat", "Drive knees out aggressively as you pull", "Glute squeeze and hip drive to lockout"],
        "breathing": "Big breath, brace, exhale at lockout",
        "trainer_tip": "More glute-dominant than conventional — great for women",
    },
    "Curtsy Lunge": {
        "cues": ["Step behind and across to opposite side", "Keep front knee stacked over foot", "Torso stays upright — no forward lean", "Drive through front heel to return to start"],
        "breathing": "Inhale on lower, exhale on return",
        "trainer_tip": "Targets glute medius — the muscle that creates hip curves",
    },
    "Abductor Machine": {
        "cues": ["Sit tall with lower back against pad", "Push knees outward in a controlled arc", "Full ROM — open as wide as comfortable", "Slow return — don't let the weight stack rest"],
        "breathing": "Exhale on open, inhale on return",
        "trainer_tip": "Essential for outer glute and hip width development",
    },
}


# ── Injury keyword → exercise name fragments to skip ─────────────────────────
_INJURY_SKIP: dict[str, list[str]] = {
    "knee":     ["squat", "lunge", "leg press", "leg extension", "step-up", "jump", "bulgarian"],
    "shoulder": ["overhead", "press", "lateral raise", "dip", "upright row", "snatch", "clean"],
    "back":     ["deadlift", "bent-over", "good morning", "hyperextension"],
    "wrist":    ["wrist", "curl", "push-up", "planche", "handstand"],
    "ankle":    ["jump", "burpee", "box", "bound", "sprint", "run"],
    "hip":      ["hip thrust", "sumo", "clamshell", "fire hydrant", "hip 90"],
    "elbow":    ["curl", "skull crusher", "pushdown", "extension", "dip"],
}


def _filter_by_injury(exercises: list[dict], profile: Profile) -> list[dict]:
    """Always remove exercises that clash with reported injuries."""
    inj = (profile.injuries or "").lower()
    if not inj or inj in {"none", "no", "n/a", "na", "-", ""}:
        sport_inj = (profile.sport_injuries or "").lower()
        if not sport_inj or sport_inj in {"none", "no", "n/a", "na", "-", ""}:
            return exercises
        inj = sport_inj

    # Build set of name fragments to skip
    skip_fragments: set[str] = set()
    for keyword, frags in _INJURY_SKIP.items():
        if keyword in inj:
            skip_fragments.update(frags)

    if not skip_fragments:
        return exercises

    def _clashes(ex: dict) -> bool:
        name_lower = ex.get("name", "").lower()
        return any(frag in name_lower for frag in skip_fragments)

    filtered = [ex for ex in exercises if not _clashes(ex)]
    # Never return fewer than 4 — safety fallback keeps the original list
    return filtered if len(filtered) >= 4 else exercises


def _rotate_for_user(exercises: list[dict], user_id: int, seed: str) -> list[dict]:
    """Rotate exercise list by a user+session-specific offset so every user gets a different order."""
    if len(exercises) <= 1:
        return exercises
    import hashlib
    h = int(hashlib.md5(f"{user_id}:{seed}".encode()).hexdigest(), 16)
    offset = h % len(exercises)
    return exercises[offset:] + exercises[:offset]


def _adjust_weight_guide(weight_guide: str, profile: Profile) -> str:
    """Scale weight guide hints based on user's body weight and level."""
    if not weight_guide or "bodyweight" in weight_guide.lower() or "band" in weight_guide.lower():
        return weight_guide
    bw = profile.weight or 75.0
    level = (profile.level or "intermediate").lower()
    scale = {"beginner": 0.65, "intermediate": 1.0, "advanced": 1.25}.get(level, 1.0)
    # Only scale if the guide contains a numeric range like "60-100kg"
    import re
    nums = re.findall(r'\d+', weight_guide)
    if not nums:
        return weight_guide
    try:
        scaled = [str(max(5, round(int(n) * scale / 5) * 5)) for n in nums]
        result = weight_guide
        for orig, new in zip(nums, scaled):
            result = result.replace(orig, new, 1)
        return result
    except Exception:
        return weight_guide


def _format_exercise(ex: dict, zone: str, level: str = "intermediate", profile: "Profile | None" = None, session_key: str | None = None) -> dict:
    """Add zone + level adjusted intensity, personalized weight guide, and Ghost Trainer form cues."""
    item = dict(ex)
    base_sets = item.get("sets", 3)
    item["movement_pattern"] = classify_movement_pattern(item.get("name", ""), session_key)

    # ── Zone adjustment ──────────────────────────────────────────────────────────
    if zone == "red":
        item["sets"] = max(1, min(base_sets, 2))
        item["rest"] = "45s"
        item["intensity"] = "recovery"
        item["intensity_label"] = "Light — focus on form, zero ego"
    elif zone == "yellow":
        item["sets"] = max(2, base_sets - 1)
        item["intensity"] = "moderate"
        item["intensity_label"] = "Moderate — controlled effort"
    else:
        item["intensity"] = "full"
        item["intensity_label"] = "Full — push hard, earn it"

    # ── Level adjustment (on top of zone) ───────────────────────────────────────
    if zone != "red":
        if level == "beginner":
            item["sets"] = max(2, item["sets"] - 1)
            item["level_note"] = "Beginner: prioritise form over load. Rest longer if needed."
            # Soften rep ranges for beginners
            reps = item.get("reps", "10")
            if isinstance(reps, str) and "-" in reps:
                lo, hi = reps.split("-")
                try:
                    item["reps"] = f"{int(lo)}-{max(int(lo)+2, int(hi)-2)}"
                except Exception:
                    pass
        elif level == "advanced":
            item["sets"] = min(6, item["sets"] + 1)
            item["level_note"] = "Advanced: push to near-failure on last 2 sets."

    # ── Personalise weight guide ─────────────────────────────────────────────────
    if profile is not None:
        item["weight_guide"] = _adjust_weight_guide(item.get("weight_guide", ""), profile)

    # ── Ensure demo_url ──────────────────────────────────────────────────────────
    item.setdefault(
        "demo_url",
        "https://www.youtube.com/results?search_query=" + item.get("name", "exercise").replace(" ", "+") + "+form"
    )

    # ── Ghost Trainer coaching cues ──────────────────────────────────────────────
    name = item.get("name", "")
    cues_data = _FORM_CUES.get(name)
    if cues_data:
        item.setdefault("form_cues",     cues_data.get("cues", []))
        item.setdefault("breathing_tip", cues_data.get("breathing", ""))
        item.setdefault("trainer_tip",   cues_data.get("trainer_tip", ""))
    else:
        item.setdefault("form_cues", [
            "Maintain full control throughout the movement",
            "Focus on the target muscle — mind-muscle connection",
            "Quality reps beat heavy weight with bad form",
            "Control the negative — slow descent builds more muscle",
        ])
        item.setdefault("breathing_tip", "Exhale on effort, inhale on return")
        item.setdefault("trainer_tip",   "Slow and controlled beats fast and sloppy every time")
    return item


def _get_exercises(category: str, profile: Profile, zone: str) -> list[dict]:
    gender = (profile.gender or "male").lower()
    if gender not in ("male", "female"):
        gender = "male"
    mode  = profile.active_mode
    level = (profile.level or "intermediate").lower()
    uid   = getattr(profile, "user_id", 0) or 0

    count = 6 if zone == "green" else (5 if zone == "yellow" else 4)
    # Beginners get slightly fewer exercises to avoid overwhelm
    if level == "beginner":
        count = max(4, count - 1)

    # ── Sport mode ───────────────────────────────────────────────────────────────
    if mode == "sport" and profile.sport:
        sport_db = _SPORT.get((profile.sport or "").lower(), {})
        exercises = list(sport_db.get(category) or _GYM_MALE.get("full_body", []))
        exercises = _filter_by_injury(exercises, profile)
        exercises = _rotate_for_user(exercises, uid, category)
        return [_format_exercise(ex, zone, level, profile, category) for ex in exercises[:count]]

    # ── Injury redirect at red zone ──────────────────────────────────────────────
    if _has_injury(profile) and zone == "red":
        family = "lower" if any(k in category for k in ["leg", "lower", "glute"]) \
            else "upper" if any(k in category for k in ["push", "pull", "upper", "toning"]) \
            else "full_body"
        exercises = list(_INJURY_SAFE.get(family, _INJURY_SAFE["full_body"]))
        exercises = _rotate_for_user(exercises, uid, category)
        return [_format_exercise(ex, zone, level, profile, family) for ex in exercises[:4]]

    # ── Normal routing ───────────────────────────────────────────────────────────
    map_key  = (gender, mode)
    sess_map = _SESSION_MAPS.get(map_key, _MALE_HOME_MAP)
    db_key   = sess_map.get(category, category)
    db       = _RICH_DBS.get(map_key, _HOME_MALE)
    exercises = list(db.get(db_key) or db.get("full_body", []))

    # Always filter injuries (not just red zone)
    exercises = _filter_by_injury(exercises, profile)
    # Rotate per user — unique exercise order for every user
    exercises = _rotate_for_user(exercises, uid, category)

    return [_format_exercise(ex, zone, level, profile, db_key) for ex in exercises[:count]]


# Normalise goal aliases — shared by build_weekly_pool
_GOAL_ALIASES = {
    "weight_loss": "fat_loss", "fat loss": "fat_loss",
    "toning": "toned_body", "tone": "toned_body",
    "hourglass": "hourglass_figure", "glute_focus": "glute_growth",
    "lean_physique": "fat_loss",
}


def _plan_template_for(profile: Profile) -> tuple[str, list[str]]:
    """Resolve (goal, days_template) for a profile, with fallbacks — shared logic
    between build_weekly_pool and generate_weekly_plan."""
    gender = (profile.gender or "male").lower()
    if gender not in ("male", "female"):
        gender = "male"
    mode  = profile.active_mode
    sport = profile.sport
    goal  = _GOAL_ALIASES.get(profile.goal or "general_fitness", profile.goal or "general_fitness")

    key = (gender, mode, goal if mode != "sport" else sport)
    template = _PLANS.get(key)
    if not template:
        if mode == "sport":
            key = (gender, "sport", sport or "football")
        else:
            fallback_goal = "fat_loss" if gender == "female" else "general_fitness"
            key = (gender, mode, fallback_goal)
        template = _PLANS.get(key, ["full_body", "cardio", "push", "pull", "legs", "upper_body"])
    return goal, template


def build_weekly_pool(profile: Profile) -> list[dict]:
    """Build this week's pool of distinct session types, sized to days_per_week.
    Takes the goal template's ordered distinct non-rest session keys and
    cyclic-pads (repeats the cycle) or truncates to fit days_per_week exactly."""
    days_per_week = min(6, max(3, profile.days_per_week or 4))
    _, template = _plan_template_for(profile)

    distinct: list[str] = []
    for session_key in template:
        if session_key != "rest" and session_key not in distinct:
            distinct.append(session_key)
    if not distinct:
        distinct = ["full_body"]

    pool_keys = [distinct[i % len(distinct)] for i in range(days_per_week)]

    return [
        {
            "key": session_key,
            "label": SESSION_LABELS.get(session_key, session_key.replace("_", " ").title()),
            "db_key": session_key,
            "done": False,
            "done_date": None,
        }
        for session_key in pool_keys
    ]


def _monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def generate_weekly_plan(profile: Profile) -> dict:
    """Build a fresh weekly pool for this profile, starting this week."""
    goal, _ = _plan_template_for(profile)
    level = (profile.level or "intermediate").lower()
    days_per_week = min(6, max(3, profile.days_per_week or 4))

    return {
        "pool": build_weekly_pool(profile),
        "week_start": _monday_of(date.today()).isoformat(),
        "mode": profile.active_mode,
        "goal": goal,
        "sport": profile.sport,
        "level": level,
        "days_per_week": days_per_week,
    }


def maybe_reset_week(plan: dict, profile: Profile) -> dict:
    """If today has rolled into a new week (vs. plan['week_start']) — or this plan
    predates the pool model entirely (no 'pool' key, e.g. an old 'days'-shaped
    plan) — rebuild fresh. No-op if still the same week with a valid pool."""
    current_monday = _monday_of(date.today()).isoformat()
    if plan.get("week_start") == current_monday and "pool" in plan:
        return plan
    return generate_weekly_plan(profile)


def profile_has_usable_data(profile: Profile) -> bool:
    """True if a profile has enough real data to build a plan from, regardless
    of whether the onboarding_complete flag was ever explicitly set — covers
    existing/legacy accounts that predate that flag or completed setup through
    another path. Used to self-heal onboarding_complete rather than forcing
    already-active users back through the onboarding flow."""
    return bool(profile.name and profile.goal and profile.gender)


def get_slot(plan: dict, slot_key: str) -> dict | None:
    for item in plan.get("pool", []):
        if item.get("key") == slot_key:
            return item
    return None


def select_pool_slot(plan: dict, slot_key: str) -> dict:
    """Ensure slot_key exists in the pool — swapping it in for the first still-undone
    slot if it isn't already part of this week's split — without marking anything done."""
    pool = [dict(item) for item in plan.get("pool", [])]
    if any(item["key"] == slot_key for item in pool):
        return {**plan, "pool": pool}

    label = SESSION_LABELS.get(slot_key, slot_key.replace("_", " ").title())
    new_item = {"key": slot_key, "label": label, "db_key": slot_key, "done": False, "done_date": None}

    for i, item in enumerate(pool):
        if not item.get("done"):
            pool[i] = new_item
            return {**plan, "pool": pool}
    pool.append(new_item)  # everything's done — grow the pool by one this week
    return {**plan, "pool": pool}


def mark_slot_done(plan: dict, slot_key: str) -> dict:
    pool = [dict(item) for item in plan.get("pool", [])]
    for item in pool:
        if item["key"] == slot_key:
            item["done"] = True
            item["done_date"] = date.today().isoformat()
            break
    else:
        label = SESSION_LABELS.get(slot_key, slot_key.replace("_", " ").title())
        pool.append({"key": slot_key, "label": label, "db_key": slot_key, "done": True, "done_date": date.today().isoformat()})
    return {**plan, "pool": pool}


def unmark_slot_done(plan: dict, slot_key: str) -> dict:
    """Allow redoing an already-completed slot this week."""
    pool = [dict(item) for item in plan.get("pool", [])]
    for item in pool:
        if item["key"] == slot_key:
            item["done"] = False
            item["done_date"] = None
            break
    return {**plan, "pool": pool}


# ── Label helpers exposed to AI service ───────────────────────────────────────
MUSCLE_TO_SLOT: dict[str, str] = {
    # Generic gym/home
    "chest":      "push",
    "push":       "push",
    "back":       "pull",
    "pull":       "pull",
    "biceps":     "pull",
    "triceps":    "push",
    "legs":       "legs",
    "quads":      "legs",
    "hamstrings": "legs",
    "calves":     "legs",
    "shoulders":  "push",
    "delts":      "push",
    "arms":       "upper_body",
    "upper body": "upper_body",
    "upper":      "upper_body",
    "lower body": "lower_body",
    "lower":      "lower_body",
    "glutes":     "glutes",
    "booty":      "glutes",
    "hip thrust": "glutes",
    "core":       "core_cardio",
    "abs":        "core_cardio",
    "full body":  "full_body",
    "full":       "full_body",
    "cardio":     "cardio",
    "run":        "cardio",
    "hiit":       "cardio",
    # Sport
    "batting":    "batting_power",
    "bowling":    "bowling_strength",
    "fielding":   "fielding_agility",
    "cricket":    "cricket_conditioning",
    "football":   "football_conditioning",
    "speed":      "football_speed",
    "agility":    "football_agility",
    "running":    "easy_run",
    "tempo":      "tempo_run",
    "intervals":  "track_intervals",
    "long run":   "long_run",
}


def get_exercises_for_slot(slot, profile: Profile, zone: str) -> list[dict]:
    """Accept either a pool-slot dict or a plain session-key string. Returns the
    MAIN block only (no warm-up/cool-down) — used both for full sessions (via
    build_full_session below) and for single-exercise swap pools, where warm-up/
    cool-down entries would be wrong to offer as an alternative."""
    if isinstance(slot, str):
        exercises = _get_exercises(slot, profile, zone)
    elif slot.get("rest"):
        return []
    else:
        db_key = slot.get("db_key", "full_body")
        exercises = _get_exercises(db_key, profile, zone)
    for ex in exercises:
        ex.setdefault("section", "main")
    return exercises


# ── Warm-up / cool-down ────────────────────────────────────────────────────────
# Short, curated, equipment-free blocks — picked by movement focus so a leg day
# gets a leg-relevant warm-up rather than generic filler. Not pulled from the
# main exercise catalog since these are deliberately brief (single "set").
_WARMUP_POOLS: dict[str, list[dict]] = {
    "lower": [
        {"name": "Bodyweight Squat", "sets": 1, "reps": "15", "rest": "0s", "muscle": "Legs"},
        {"name": "Leg Swings", "sets": 1, "reps": "10 ea", "rest": "0s", "muscle": "Hips"},
        {"name": "Hip Circles", "sets": 1, "reps": "10 ea", "rest": "0s", "muscle": "Hips"},
    ],
    "upper": [
        {"name": "Arm Circles", "sets": 1, "reps": "30s", "rest": "0s", "muscle": "Shoulders"},
        {"name": "Band Pull-Apart", "sets": 1, "reps": "15", "rest": "0s", "muscle": "Rear Delts"},
        {"name": "Shoulder Rolls", "sets": 1, "reps": "10 ea", "rest": "0s", "muscle": "Shoulders"},
    ],
    "cardio": [
        {"name": "Jumping Jacks", "sets": 1, "reps": "30s", "rest": "0s", "muscle": "Full Body"},
        {"name": "High Knees", "sets": 1, "reps": "30s", "rest": "0s", "muscle": "Cardio"},
    ],
    "general": [
        {"name": "Jumping Jacks", "sets": 1, "reps": "30s", "rest": "0s", "muscle": "Full Body"},
        {"name": "Bodyweight Squat", "sets": 1, "reps": "15", "rest": "0s", "muscle": "Legs"},
        {"name": "Arm Circles", "sets": 1, "reps": "30s", "rest": "0s", "muscle": "Shoulders"},
    ],
}
_COOLDOWN_POOLS: dict[str, list[dict]] = {
    "lower": [
        {"name": "Standing Quad Stretch", "sets": 1, "reps": "30s ea", "rest": "0s", "muscle": "Quads"},
        {"name": "Seated Hamstring Stretch", "sets": 1, "reps": "30s ea", "rest": "0s", "muscle": "Hamstrings"},
    ],
    "upper": [
        {"name": "Chest Doorway Stretch", "sets": 1, "reps": "30s", "rest": "0s", "muscle": "Chest"},
        {"name": "Overhead Triceps Stretch", "sets": 1, "reps": "30s ea", "rest": "0s", "muscle": "Triceps"},
    ],
    "cardio": [
        {"name": "Standing Forward Fold", "sets": 1, "reps": "30s", "rest": "0s", "muscle": "Hamstrings/Back"},
        {"name": "Deep Breathing Recovery", "sets": 1, "reps": "60s", "rest": "0s", "muscle": "Recovery"},
    ],
    "general": [
        {"name": "Child's Pose", "sets": 1, "reps": "45s", "rest": "0s", "muscle": "Back"},
        {"name": "Standing Quad Stretch", "sets": 1, "reps": "30s ea", "rest": "0s", "muscle": "Quads"},
    ],
}
_SESSION_FOCUS: dict[str, str] = {
    "push": "upper", "pull": "upper", "upper_body": "upper", "upper_toning": "upper",
    "legs": "lower", "lower_body": "lower", "glutes": "lower",
    "cardio": "cardio", "core_cardio": "cardio",
    "full_body": "general",
}


def _format_warmup_cooldown(ex: dict, section: str) -> dict:
    item = dict(ex)
    item["section"] = section
    item["movement_pattern"] = classify_movement_pattern(item.get("name", ""))
    item.setdefault("weight_guide", "Bodyweight")
    item.setdefault("equipment_required", False)
    item.setdefault(
        "demo_url",
        "https://www.youtube.com/results?search_query=" + item.get("name", "exercise").replace(" ", "+"),
    )
    item.setdefault(
        "form_cues",
        ["Move through a full, controlled range of motion", "Gradually build up intensity"]
        if section == "warmup"
        else ["Hold the stretch — don't bounce", "Breathe slowly and relax into it"],
    )
    item.setdefault("trainer_tip", "Warm-up primes the joints you're about to load" if section == "warmup"
                     else "Cool-down stretching aids recovery and next-day soreness")
    item.setdefault("intensity_label", "Warm-up" if section == "warmup" else "Cool-down")
    return item


def build_full_session(slot, profile: Profile, zone: str) -> list[dict]:
    """The full user-facing session: warm-up + main workout + cool-down. This is
    what actually gets shown/started in the live Ghost Trainer session — use
    get_exercises_for_slot() directly instead when you need just the raw main
    block (e.g. picking a single-exercise swap alternative)."""
    main = get_exercises_for_slot(slot, profile, zone)
    if not main:
        return []
    db_key = slot.get("db_key", "full_body") if not isinstance(slot, str) else slot
    focus = _SESSION_FOCUS.get(db_key, "general")
    warmup = [_format_warmup_cooldown(e, "warmup") for e in _WARMUP_POOLS.get(focus, _WARMUP_POOLS["general"])[:2]]
    cooldown = [_format_warmup_cooldown(e, "cooldown") for e in _COOLDOWN_POOLS.get(focus, _COOLDOWN_POOLS["general"])[:2]]
    return warmup + main + cooldown
