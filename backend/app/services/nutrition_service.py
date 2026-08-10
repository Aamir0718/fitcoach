import re
import logging
from difflib import SequenceMatcher

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

API_KEY = settings.USDA_API_KEY

URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

FOOD_MAP = {
    "rice": "White rice, cooked",
    "banana": "Banana, raw",
    "apple": "Apple, raw",
    "chapathi": "Chapati",
    "chicken gravy": "Chicken curry",
    "burger": "Hamburger",
    "pizza": "Pizza",
    "fries": "French fries",
    "tomato": "Tomato",
    "idli": "Idli",
    "vada": "Vada",
    "egg": "Egg, whole, boiled",
    "boiled egg": "Egg, whole, boiled",
    "paneer": "Paneer",
    "chicken breast": "Chicken breast, roasted",
    "chicken": "Chicken breast, roasted",
    "fish": "Fish, cooked",
    "broccoli": "Broccoli, cooked",
    "oats": "Oats",
    "milk": "Milk",
    "protein shake": "Protein shake",
}

# USDA's search results report nutrients per 100g of the food (true for the
# Foundation/SR Legacy entries our FOOD_MAP maps onto). Every quantity below is
# ultimately converted to grams so nutrients can be scaled off that 100g baseline
# instead of being handed back unscaled and mislabeled "1 serving".
DEFAULT_GRAMS = 100

# grams per unit for foods that get logged by count ("2 bananas", "3 idlis")
PIECE_WEIGHTS = {
    "banana": 118,
    "apple": 182,
    "egg": 50,
    "boiled egg": 50,
    "chapathi": 40,
    "chapati": 40,
    "roti": 40,
    "idli": 35,
    "vada": 45,
    "paneer": 100,
    "burger": 250,
    "pizza": 250,
    "fries": 100,
    "tomato": 123,
    "protein shake": 300,
    "milk": 240,
    "oats": 40,
}

NUM_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "half": 0.5, "couple": 2, "few": 3,
}

# unit -> grams; unit -> None means "count-based", resolved via PIECE_WEIGHTS instead
UNIT_GRAMS = {
    "g": 1, "gm": 1, "gms": 1, "gram": 1, "grams": 1,
    "kg": 1000, "kgs": 1000,
    "ml": 1, "l": 1000, "ltr": 1000, "litre": 1000, "liter": 1000,
    "cup": 158, "cups": 158,
    "bowl": 200, "bowls": 200,
    "tbsp": 15, "tablespoon": 15, "tablespoons": 15,
    "tsp": 5, "teaspoon": 5, "teaspoons": 5,
    "slice": 30, "slices": 30,
    "plate": 250, "plates": 250,
    "glass": 240, "glasses": 240,
    "piece": None, "pieces": None, "pc": None, "pcs": None,
}

_SPLIT_RE = re.compile(r"\s*(?:,|\band\b|\bwith\b|\+)\s*", re.IGNORECASE)
_FUSED_QTY_RE = re.compile(r"^(\d+(?:\.\d+)?)([a-zA-Z]+)")
# units written glued to the number ("200g"), vs. word units that read better
# with a space ("2 cups")
_COMPACT_UNITS = {"g", "gm", "gms", "gram", "grams", "kg", "kgs", "ml", "l", "ltr", "litre", "liter"}


def split_food_items(description: str) -> list[str]:
    """Split a free-text meal ("2 eggs and a bowl of oats") into separate food
    phrases so each one gets looked up and scaled on its own instead of the
    whole sentence being thrown at USDA as a single (unmatchable) query."""
    parts = [p.strip() for p in _SPLIT_RE.split(description or "") if p.strip()]
    return parts or ([description] if description else [])


def _to_number(token: str):
    token = token.lower().strip(".,")
    if token in NUM_WORDS:
        return NUM_WORDS[token]
    try:
        return float(token)
    except ValueError:
        return None


def _fmt(n: float) -> str:
    return f"{n:g}"


def parse_food_item(text: str) -> tuple[str, float, str]:
    """
    Parse one food phrase into (food_name, grams, display_quantity).

    Handles "200g rice", "2 bananas", "a bowl of oats", "3 idlis", etc.
    Falls back to a plain 100g/"1 serving" reading when no quantity is stated,
    so a bare "chicken" still behaves like before.
    """
    text = (text or "").strip()
    if not text:
        return text, DEFAULT_GRAMS, "1 serving"

    # "200g rice" -> "200 g rice" so it tokenizes cleanly
    text = _FUSED_QTY_RE.sub(r"\1 \2", text)
    tokens = text.split()

    num = _to_number(tokens[0])
    if num is None or num <= 0:
        return text, DEFAULT_GRAMS, "1 serving"

    rest = tokens[1:]
    if rest and rest[0].lower() == "of":
        rest = rest[1:]

    unit = None
    if rest and rest[0].lower().rstrip(".,") in UNIT_GRAMS:
        unit = rest[0].lower().rstrip(".,")
        rest = rest[1:]
        if rest and rest[0].lower() == "of":
            rest = rest[1:]

    food = " ".join(rest).strip() or text
    food_lower = food.lower()
    # Crude singularization ("bananas" -> "banana") so plural phrasing still
    # matches FOOD_MAP/PIECE_WEIGHTS and the USDA query — skip when the
    # plural-looking word is itself a known food (e.g. "oats", "fries").
    if food_lower.endswith("s") and food_lower not in PIECE_WEIGHTS and len(food_lower) > 3:
        food_lookup = food_lower[:-1]
    else:
        food_lookup = food_lower

    if unit and UNIT_GRAMS.get(unit) is not None:
        grams = num * UNIT_GRAMS[unit]
        sep = "" if unit in _COMPACT_UNITS else " "
        display = f"{_fmt(num)}{sep}{unit} {food}"
    else:
        piece_weight = PIECE_WEIGHTS.get(food_lookup, DEFAULT_GRAMS)
        grams = num * piece_weight
        display = f"{_fmt(num)} x {food}"

    return food_lookup, round(grams, 1), display


def similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def get_best_food(search_name, foods):

    # 1. Exact match
    for food in foods:
        if food["description"].lower() == search_name.lower():
            return food

    # 2. Contains match
    for food in foods:
        if search_name.lower() in food["description"].lower():
            return food

    # 3. Highest similarity
    best = foods[0]
    best_score = 0

    for food in foods:
        score = similarity(search_name, food["description"])
        if score > best_score:
            best_score = score
            best = food

    return best


# In-memory cache of per-100g nutrient profiles, keyed by search term. The USDA
# API round-trip is the slow part of every /nutrition/analyze call and the same
# handful of foods (rice, chicken, eggs...) get looked up over and over, so this
# avoids re-hitting USDA for something we already resolved this process's lifetime.
_food_cache: dict[str, dict | None] = {}
_CACHE_LIMIT = 300


async def _fetch_food_base(search_name: str) -> dict | None:
    cache_key = search_name.lower()
    if cache_key in _food_cache:
        return _food_cache[cache_key]

    params = {"query": search_name, "pageSize": 10, "api_key": API_KEY}

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(URL, params=params)
    except httpx.RequestError as e:
        logger.warning(f"USDA request failed for '{search_name}': {e}")
        return None

    if response.status_code != 200:
        logger.warning(f"USDA API returned {response.status_code} for '{search_name}'")
        return None

    data = response.json()

    if not data.get("foods"):
        if len(_food_cache) >= _CACHE_LIMIT:
            _food_cache.pop(next(iter(_food_cache)))
        _food_cache[cache_key] = None
        return None

    food = get_best_food(search_name, data["foods"])
    logger.debug(f"Selected USDA food for '{search_name}': {food['description']}")

    nutrients = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0, "sugar": 0}

    for nutrient in food.get("foodNutrients", []):
        name = nutrient.get("nutrientName", "")
        value = nutrient.get("value", 0) or 0
        unit = (nutrient.get("unitName") or "").upper()

        if name == "Energy":
            # USDA lists Energy twice per food — once in KCAL, once in kJ.
            # Without filtering by unit, whichever happened to come last in the
            # list would win, sometimes overwriting the correct kcal figure
            # with the kJ one (~4.18x too high) — that was the source of the
            # wildly inflated calorie counts.
            if unit == "KCAL":
                nutrients["calories"] = value
        elif name == "Protein":
            nutrients["protein"] = value
        elif name == "Carbohydrate, by difference":
            nutrients["carbs"] = value
        elif name == "Total lipid (fat)":
            nutrients["fat"] = value
        elif name == "Fiber, total dietary":
            nutrients["fiber"] = value
        elif name == "Total Sugars":
            nutrients["sugar"] = value

    base = {"name": food["description"], "per_100g": nutrients}

    if len(_food_cache) >= _CACHE_LIMIT:
        _food_cache.pop(next(iter(_food_cache)))
    _food_cache[cache_key] = base
    return base


async def get_food_nutrition(food_name: str, grams: float = DEFAULT_GRAMS, display_quantity: str | None = None):
    """
    Look up a food's nutrition, scaled to the amount actually eaten.

    USDA reports values per 100g, so `grams` (usually parsed from the user's
    quantity via parse_food_item, e.g. "2 bananas" -> ~236g) is used to scale
    every nutrient proportionally instead of returning the raw per-100g figures
    labeled as a generic "1 serving" regardless of how much was eaten.
    """
    search_name = FOOD_MAP.get(food_name.lower(), food_name)

    base = await _fetch_food_base(search_name)
    if base is None:
        return None

    factor = max(grams, 0) / 100.0
    n = base["per_100g"]

    return {
        "name": base["name"],
        "quantity": display_quantity or f"{_fmt(grams)}g",
        "calories": round(n["calories"] * factor, 1),
        "protein": round(n["protein"] * factor, 1),
        "carbs": round(n["carbs"] * factor, 1),
        "fat": round(n["fat"] * factor, 1),
        "fiber": round(n["fiber"] * factor, 1),
        "sugar": round(n["sugar"] * factor, 1),
    }
