import re
import requests
from difflib import SequenceMatcher
from app.config import settings

API_KEY = settings.USDA_API_KEY

URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

FOOD_MAP = {
    "Rice": "White rice, cooked",
    "banana": "Banana, raw",
    "Apple": "Apple, raw",
    "Chapathi": "Chapati",
    "Chicken Gravy": "Chicken curry",
    "burger": "Hamburger",
    "Pizza": "Pizza",
    "Fries": "French fries",
    "Tomato": "Tomato",
    "Idli": "Idli",
    "Vada": "Vada",

    "Egg": "Egg, whole, boiled",
    "Boiled Egg": "Egg, whole, boiled",
    "Paneer": "Paneer",
    "Chicken Breast": "Chicken breast, roasted",
    "Chicken": "Chicken breast, roasted",
    "Fish": "Fish, cooked",
    "Broccoli": "Broccoli, cooked",
    "Oats": "Oats",
    "Milk": "Milk",
    "Protein Shake": "Protein shake"
}

# Case-insensitive index over FOOD_MAP so typed text ("milk", "RICE", "2 rice")
# still resolves — FOOD_MAP's own keys stay as the YOLO photo-detector's exact
# class-name casing, this is just a lookup helper on top of it.
_FOOD_MAP_LOWER = {k.lower(): v for k, v in FOOD_MAP.items()}


# ── Local nutrition table for common, frequently-logged foods ──────────────
# The USDA full-text search is a fuzzy match over a huge catalog (including
# branded/packaged products), and it only ever sees a single search string —
# so "2 banana" used to get searched literally, "curd" matched "Soybean curd"
# (tofu) instead of dahi/yogurt, and "100g rice" matched "Dirty rice" (a
# seasoned dish) because "100g rice" never matched the FOOD_MAP key "Rice".
# For the staples people actually log every day, pin down known-good values
# instead of trusting whatever the fuzzy search turns up. Values are per the
# stated serving; get_food_nutrition() scales them by the parsed quantity.
LOCAL_NUTRITION_DB = {
    "milk": {
        "name": "Milk, whole", "serving_desc": "1 glass (244g)", "serving_g": 244,
        "calories": 149, "protein": 7.7, "carbs": 11.7, "fat": 7.9, "fiber": 0.0, "sugar": 12.3,
    },
    "banana": {
        "name": "Banana, raw", "serving_desc": "1 medium (118g)", "serving_g": 118,
        "calories": 105, "protein": 1.3, "carbs": 27.0, "fat": 0.4, "fiber": 3.1, "sugar": 14.4,
    },
    "curd": {
        "name": "Curd (Dahi)", "serving_desc": "1 cup (245g)", "serving_g": 245,
        "calories": 149, "protein": 8.5, "carbs": 11.4, "fat": 8.0, "fiber": 0.0, "sugar": 11.4,
    },
    "dal": {
        "name": "Dal, cooked", "serving_desc": "1 cup (198g)", "serving_g": 198,
        "calories": 230, "protein": 18.0, "carbs": 40.0, "fat": 0.8, "fiber": 16.0, "sugar": 2.0,
    },
    "roti": {
        "name": "Roti (Chapati)", "serving_desc": "1 medium (40g)", "serving_g": 40,
        "calories": 120, "protein": 3.1, "carbs": 18.0, "fat": 3.7, "fiber": 2.2, "sugar": 0.5,
    },
    "rice": {
        "name": "Rice, white, cooked", "serving_desc": "1 cup (158g)", "serving_g": 158,
        "calories": 205, "protein": 4.3, "carbs": 44.5, "fat": 0.4, "fiber": 0.6, "sugar": 0.1,
    },
    "egg": {
        "name": "Egg, whole, boiled", "serving_desc": "1 large (50g)", "serving_g": 50,
        "calories": 78, "protein": 6.3, "carbs": 0.6, "fat": 5.3, "fiber": 0.0, "sugar": 0.6,
    },
    "chicken breast": {
        "name": "Chicken breast, cooked", "serving_desc": "100g", "serving_g": 100,
        "calories": 165, "protein": 31.0, "carbs": 0.0, "fat": 3.6, "fiber": 0.0, "sugar": 0.0,
    },
    "paneer": {
        "name": "Paneer", "serving_desc": "100g", "serving_g": 100,
        "calories": 265, "protein": 18.3, "carbs": 1.2, "fat": 20.8, "fiber": 0.0, "sugar": 1.2,
    },
    "apple": {
        "name": "Apple, raw", "serving_desc": "1 medium (182g)", "serving_g": 182,
        "calories": 95, "protein": 0.5, "carbs": 25.0, "fat": 0.3, "fiber": 4.4, "sugar": 19.0,
    },
    "oats": {
        "name": "Oats, dry", "serving_desc": "40g (1/2 cup)", "serving_g": 40,
        "calories": 150, "protein": 5.3, "carbs": 27.0, "fat": 2.6, "fiber": 4.0, "sugar": 0.4,
    },
    "bread": {
        "name": "Bread, white, slice", "serving_desc": "1 slice (28g)", "serving_g": 28,
        "calories": 75, "protein": 2.6, "carbs": 14.0, "fat": 1.0, "fiber": 0.8, "sugar": 1.5,
    },
    "idli": {
        "name": "Idli", "serving_desc": "1 piece (35g)", "serving_g": 35,
        "calories": 39, "protein": 1.3, "carbs": 8.0, "fat": 0.1, "fiber": 0.4, "sugar": 0.1,
    },
    "dosa": {
        "name": "Dosa, plain", "serving_desc": "1 piece (75g)", "serving_g": 75,
        "calories": 133, "protein": 2.7, "carbs": 18.0, "fat": 5.5, "fiber": 0.6, "sugar": 0.3,
    },
    "potato": {
        "name": "Potato, boiled", "serving_desc": "1 medium (150g)", "serving_g": 150,
        "calories": 130, "protein": 2.7, "carbs": 30.0, "fat": 0.1, "fiber": 2.4, "sugar": 1.4,
    },
    "tomato": {
        "name": "Tomato, raw", "serving_desc": "1 medium (123g)", "serving_g": 123,
        "calories": 22, "protein": 1.1, "carbs": 4.8, "fat": 0.2, "fiber": 1.5, "sugar": 3.2,
    },
    "almonds": {
        "name": "Almonds", "serving_desc": "10 almonds (12g)", "serving_g": 12,
        "calories": 70, "protein": 2.6, "carbs": 2.6, "fat": 6.0, "fiber": 1.5, "sugar": 0.5,
    },
    "peanut butter": {
        "name": "Peanut butter", "serving_desc": "1 tbsp (16g)", "serving_g": 16,
        "calories": 94, "protein": 4.0, "carbs": 3.0, "fat": 8.0, "fiber": 1.0, "sugar": 1.5,
    },
}

# Aliases (Indian-English spellings, plurals, synonyms) → LOCAL_NUTRITION_DB key.
_ALIASES = {
    "banana": "banana", "bananas": "banana",
    "milk": "milk",
    "curd": "curd", "dahi": "curd", "yogurt": "curd", "yoghurt": "curd", "curds": "curd",
    "dal": "dal", "daal": "dal", "dhal": "dal", "lentils": "dal", "lentil": "dal",
    "roti": "roti", "rotis": "roti", "chapati": "roti", "chapathi": "roti",
    "chappati": "roti", "chapatis": "roti", "phulka": "roti",
    "rice": "rice",
    "egg": "egg", "eggs": "egg", "boiled egg": "egg",
    "chicken breast": "chicken breast", "chicken": "chicken breast",
    "paneer": "paneer", "cottage cheese": "paneer",
    "apple": "apple", "apples": "apple",
    "oats": "oats", "oatmeal": "oats",
    "bread": "bread",
    "idli": "idli", "idlis": "idli",
    "dosa": "dosa", "dosas": "dosa",
    "potato": "potato", "potatoes": "potato",
    "tomato": "tomato", "tomatoes": "tomato",
    "almonds": "almonds", "almond": "almonds",
    "peanut butter": "peanut butter",
}

# Spelled-out / fractional quantities ("a banana", "half a roti", "two eggs").
_NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "half": 0.5, "couple": 2, "few": 3,
}
_UNIT_WORDS = {
    "cup", "cups", "glass", "glasses", "piece", "pieces", "slice", "slices",
    "bowl", "bowls", "plate", "plates", "serving", "servings", "tbsp",
    "tablespoon", "tablespoons", "tsp", "teaspoon", "teaspoons", "of", "g",
    "gm", "gms", "gram", "grams", "ml",
}


def _parse_quantity(text: str) -> tuple[float, str, float | None]:
    """Pull a leading quantity off free-typed text, returning (count, food_name, grams).
    'grams' is set instead of 'count' when the text gave an explicit weight —
    e.g. '2 banana' -> (2.0, 'banana', None), '100g rice' -> (1.0, 'rice', 100.0),
    'a bowl of dal' -> (1.0, 'dal', None)."""
    t = text.strip().lower()

    # "100g rice" / "250ml milk" — explicit weight, converted to a fraction of
    # the known serving size by the caller rather than treated as a count.
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(g|gm|gms|gram|grams|ml)\s+(.*)$", t)
    if m:
        return 1.0, m.group(3).strip(), float(m.group(1))

    m = re.match(r"^(\d+(?:\.\d+)?|\d+/\d+|[a-z]+)\s+(.*)$", t)
    if not m:
        return 1.0, t, None

    qty_raw, rest = m.groups()
    qty = None
    if qty_raw in _NUMBER_WORDS:
        qty = float(_NUMBER_WORDS[qty_raw])
    elif "/" in qty_raw:
        n, d = qty_raw.split("/", 1)
        try:
            qty = float(n) / float(d)
        except (ValueError, ZeroDivisionError):
            qty = None
    else:
        try:
            qty = float(qty_raw)
        except ValueError:
            qty = None

    if qty is None:
        # Leading word wasn't a quantity at all (e.g. "fried rice") — keep
        # the whole original text as the food name.
        return 1.0, t, None

    # Drop a filler unit word right after the quantity ("2 cups rice" -> "rice").
    rest = rest.strip()
    first_word = rest.split(" ", 1)[0] if rest else ""
    if first_word in _UNIT_WORDS:
        rest = rest[len(first_word):].strip()
        if rest.startswith("of "):
            rest = rest[3:].strip()

    return qty, (rest or t), None


def _normalize_food_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _lookup_local(normalized: str) -> dict | None:
    if not normalized:
        return None
    if normalized in _ALIASES:
        return LOCAL_NUTRITION_DB[_ALIASES[normalized]]
    # Singular fallback ("bananas" -> "banana") for anything not already aliased.
    if normalized.endswith("s") and normalized[:-1] in _ALIASES:
        return LOCAL_NUTRITION_DB[_ALIASES[normalized[:-1]]]
    # Last word match for short phrases like "glass milk" / "boiled egg".
    last_word = normalized.split(" ")[-1]
    if last_word in _ALIASES:
        return LOCAL_NUTRITION_DB[_ALIASES[last_word]]
    return None


def _resolve_quantity(count: float, grams: float | None, serving_g: float) -> float:
    """Turn a parsed (count, grams) pair into a multiplier on the per-serving
    values, converting an explicit weight ('100g rice') into a fraction of
    the known serving size instead of treating it as '1 serving'."""
    if grams is not None and serving_g:
        return grams / serving_g
    return count


def _scale(nutrition: dict, qty: float) -> dict:
    # "2 x 1 medium (118g)" reads oddly — drop a leading "1 " from the serving
    # description so a multiplied serving reads "2 x medium (118g)" instead.
    desc = nutrition["serving_desc"]
    desc_no_count = re.sub(r"^1\s+", "", desc)
    qty_label = round(qty, 2)
    quantity = desc if qty == 1 else f"{qty_label:g} x {desc_no_count}"
    return {
        "name": nutrition["name"],
        "quantity": quantity,
        "calories": round(nutrition["calories"] * qty, 2),
        "protein": round(nutrition["protein"] * qty, 2),
        "carbs": round(nutrition["carbs"] * qty, 2),
        "fat": round(nutrition["fat"] * qty, 2),
        "fiber": round(nutrition["fiber"] * qty, 2),
        "sugar": round(nutrition["sugar"] * qty, 2),
    }


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


def get_food_nutrition(food_name: str):
    count, rest, grams = _parse_quantity(food_name)
    normalized = _normalize_food_name(rest)

    # 1. Curated local table — reliable values for the foods people log most.
    local = _lookup_local(normalized)
    if local:
        return _scale(local, _resolve_quantity(count, grams, local["serving_g"]))

    # 2. USDA FoodData Central — search on the cleaned food name (quantity/unit
    # words stripped), not the raw typed text, so "100g rice" actually matches
    # the "Rice" entry instead of being searched as the literal string.
    search_name = (
        _FOOD_MAP_LOWER.get(normalized)
        or _FOOD_MAP_LOWER.get(normalized.rstrip("s"))
        or FOOD_MAP.get(rest)
        or rest
    )

    params = {
        "query": search_name,
        "pageSize": 10,
        "api_key": API_KEY
    }

    response = requests.get(URL, params=params)

    if response.status_code != 200:
        return None

    data = response.json()

    if not data.get("foods"):
        return None

    food = get_best_food(search_name, data["foods"])

    nutrients = {
        "calories": 0,
        "protein": 0,
        "carbs": 0,
        "fat": 0,
        "fiber": 0,
        "sugar": 0
    }

    for nutrient in food.get("foodNutrients", []):

        name = nutrient.get("nutrientName", "")
        value = nutrient.get("value", 0)

        if name == "Energy":
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

    # USDA foodNutrients values are per 100g.
    return _scale({
        "name": food["description"],
        "serving_desc": "100g serving",
        **nutrients,
    }, _resolve_quantity(count, grams, 100))
