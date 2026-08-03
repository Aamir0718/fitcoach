from app.services.nutrition_service import get_food_nutrition
from app.config import settings

API_KEY = settings.USDA_API_KEY
print(API_KEY)
print(get_food_nutrition("Rice"))