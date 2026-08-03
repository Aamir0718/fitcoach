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

    search_name = FOOD_MAP.get(food_name, food_name)

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
    print("\nSelected USDA Food:", food["description"])
    print("\nAvailable nutrients:")

    for nutrient in food.get("foodNutrients", []):
        print(
            nutrient.get("nutrientName"),
            "=",
            nutrient.get("value")
        )
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

    return {
        "name": food["description"],
        "quantity": "1 serving",
        "calories": round(nutrients["calories"], 2),
        "protein": round(nutrients["protein"], 2),
        "carbs": round(nutrients["carbs"], 2),
        "fat": round(nutrients["fat"], 2),
        "fiber": round(nutrients["fiber"], 2),
        "sugar": round(nutrients["sugar"], 2)
    }