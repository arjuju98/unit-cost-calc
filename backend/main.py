from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic
import os
import json
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys - you'll need to set these as environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

class RecipeRequest(BaseModel):
    recipe: str
    yield_count: int = None

    class Config:
        # Allow both 'yield' and 'yield_count' as field names
        populate_by_name = True
        json_schema_extra = {
            "examples": [
                {
                    "recipe": "Sample recipe text",
                    "yield": 6
                }
            ]
        }

class PackageInfo(BaseModel):
    size: str
    price: float
    cost_per_unit: float
    unit: str

class Ingredient(BaseModel):
    ingredient: str
    quantity: float
    unit: str
    cost: float
    note: Optional[str] = None
    package_info: Optional[PackageInfo] = None
    manually_adjusted: bool = False

class CostResult(BaseModel):
    recipe_name: Optional[str]
    ingredients: List[Ingredient]
    total_cost: float
    yield_count: int
    unit_cost: float

def parse_recipe_with_claude(recipe_text: str) -> Dict:
    """Use Claude to extract structured ingredient data from recipe text."""
    
    prompt = f"""Extract and normalize ingredients from the following recipe.
Return ONLY valid JSON (no markdown, no code blocks) with this structure:
{{
    "recipe_name": "name of recipe if mentioned",
    "ingredients": [
        {{"ingredient": "ingredient name", "quantity": number, "unit": "g|ml|item|tbsp|tsp|cup", "note": "optional clarification"}},
        ...
    ]
}}

Important rules:
- Convert all volume measurements to grams where possible (1 cup flour = 120g, 1 cup sugar = 200g, 1 cup butter = 227g, 1 tbsp = 15ml, 1 tsp = 5ml)
- For protein powder scoops/servings: use 30g per scoop as default and add note: "estimated at 30g per scoop"
- For other supplement scoops: use reasonable estimates based on product type and add a note
- For items like eggs, use "item" as unit
- Standardize ingredient names (e.g., "all-purpose flour" -> "flour", "PEScience Protein Powder" -> "protein powder")
- Extract quantities as numbers only
- If no recipe name is found, set to null
- Add a "note" field when you've made an assumption about conversions

Recipe:
{recipe_text}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    response_text = message.content[0].text.strip()
    
    # Remove markdown code blocks if present
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
        response_text = response_text.strip()
    
    return json.loads(response_text)

def get_ingredient_price(ingredient_name: str, quantity: float, unit: str) -> tuple[float, PackageInfo]:
    """
    Fetch ingredient pricing using Spoonacular API.
    Returns (cost for the specific quantity used, package info).
    """
    
    if not SPOONACULAR_API_KEY:
        # Fallback prices if no API key (for testing)
        fallback_data = {
            "oats": {"price_per_g": 0.002, "package_size": "1kg", "package_price": 2.00},
            "peanut butter": {"price_per_g": 0.012, "package_size": "454g", "package_price": 5.49},
            "protein powder": {"price_per_g": 0.022, "package_size": "810g (27 servings)", "package_price": 45.00},
            "egg": {"price_per_item": 0.23, "package_size": "12 eggs", "package_price": 2.76},
            "chocolate chips": {"price_per_g": 0.010, "package_size": "300g", "package_price": 3.00},
            "flour": {"price_per_g": 0.001, "package_size": "2kg", "package_price": 2.00},
            "butter": {"price_per_g": 0.015, "package_size": "454g", "package_price": 6.99},
            "sugar": {"price_per_g": 0.002, "package_size": "2kg", "package_price": 4.00},
            "brown sugar": {"price_per_g": 0.003, "package_size": "1kg", "package_price": 3.00},
            "vanilla extract": {"price_per_ml": 0.50, "package_size": "60ml", "package_price": 30.00},
            "baking soda": {"price_per_g": 0.01, "package_size": "454g", "package_price": 4.54},
            "baking powder": {"price_per_g": 0.02, "package_size": "227g", "package_price": 4.54},
            "salt": {"price_per_g": 0.001, "package_size": "750g", "package_price": 0.75},
            "milk": {"price_per_ml": 0.001, "package_size": "1L", "package_price": 1.00},
            "vegetable oil": {"price_per_ml": 0.005, "package_size": "750ml", "package_price": 3.75},
            "honey": {"price_per_g": 0.010, "package_size": "500g", "package_price": 5.00},
            "cocoa powder": {"price_per_g": 0.018, "package_size": "250g", "package_price": 4.50},
            "nuts": {"price_per_g": 0.025, "package_size": "200g", "package_price": 5.00},
            "cinnamon": {"price_per_g": 0.05, "package_size": "50g", "package_price": 2.50},
        }
        
        # Find closest match in fallback prices
        ingredient_data = None
        for key, data in fallback_data.items():
            if key in ingredient_name.lower():
                ingredient_data = data
                break
        
        if ingredient_data:
            if unit == "item":
                cost = ingredient_data.get("price_per_item", 0.23) * quantity
                package_info = PackageInfo(
                    size=ingredient_data["package_size"],
                    price=ingredient_data["package_price"],
                    cost_per_unit=ingredient_data.get("price_per_item", 0.23),
                    unit="item"
                )
            else:  # assume grams or ml
                price_key = "price_per_ml" if unit == "ml" else "price_per_g"
                cost_per_unit = ingredient_data.get(price_key, 0.01)
                cost = cost_per_unit * quantity
                package_info = PackageInfo(
                    size=ingredient_data["package_size"],
                    price=ingredient_data["package_price"],
                    cost_per_unit=cost_per_unit,
                    unit=unit
                )
            return cost, package_info
        
        # Default fallback - more reasonable estimates
        if unit == "item":
            cost = 0.25 * quantity  # $0.25 per item (like an egg)
        else:  # grams or ml
            cost = 0.01 * quantity  # $0.01 per gram/ml
        
        package_info = PackageInfo(
            size="Unknown",
            price=10.00,
            cost_per_unit=0.01 if unit != "item" else 0.25,
            unit=unit
        )
        return cost, package_info
    
    try:
        # Spoonacular ingredient search
        search_url = f"https://api.spoonacular.com/food/ingredients/search"
        search_params = {
            "apiKey": SPOONACULAR_API_KEY,
            "query": ingredient_name,
            "number": 1
        }
        
        search_response = requests.get(search_url, params=search_params)
        search_data = search_response.json()
        
        if not search_data.get("results"):
            return 0.10 * quantity  # Default estimate
        
        ingredient_id = search_data["results"][0]["id"]
        
        # Get ingredient information including price
        info_url = f"https://api.spoonacular.com/food/ingredients/{ingredient_id}/information"
        info_params = {
            "apiKey": SPOONACULAR_API_KEY,
            "amount": quantity,
            "unit": unit
        }
        
        info_response = requests.get(info_url, params=info_params)
        info_data = info_response.json()
        
        # Extract price estimate
        if "estimatedCost" in info_data:
            # Spoonacular returns cost in cents
            cost = info_data["estimatedCost"]["value"] / 100
            package_info = PackageInfo(
                size="Estimated",
                price=cost,
                cost_per_unit=cost / quantity if quantity > 0 else 0,
                unit=unit
            )
            return cost, package_info
        
        default_cost = 0.01 * quantity if unit != "item" else 0.25 * quantity
        package_info = PackageInfo(
            size="Unknown",
            price=10.00,
            cost_per_unit=0.01 if unit != "item" else 0.25,
            unit=unit
        )
        return default_cost, package_info
        
    except Exception as e:
        print(f"Error fetching price for {ingredient_name}: {e}")
        default_cost = 0.01 * quantity if unit != "item" else 0.25 * quantity
        package_info = PackageInfo(
            size="Unknown",
            price=10.00,
            cost_per_unit=0.01 if unit != "item" else 0.25,
            unit=unit
        )
        return default_cost, package_info

@app.get("/")
async def root():
    return {"message": "Unit Cost Calculator API is running"}

@app.post("/calculate-cost", response_model=CostResult)
async def calculate_cost(request: RecipeRequest):
    """
    Main endpoint to calculate recipe cost.
    1. Parse recipe with Claude
    2. Fetch pricing for each ingredient
    3. Calculate total and unit cost
    """
    
    try:
        # Debug logging
        print(f"Received request: recipe length={len(request.recipe)}, yield_count={request.yield_count}")
        # Step 1: Parse recipe
        parsed_data = parse_recipe_with_claude(request.recipe)
        
        recipe_name = parsed_data.get("recipe_name")
        ingredients_data = parsed_data.get("ingredients", [])
        
        if not ingredients_data:
            raise HTTPException(status_code=400, detail="No ingredients found in recipe")
        
        # Step 2: Get pricing for each ingredient
        ingredients_with_cost = []
        total_cost = 0
        
        for ing in ingredients_data:
            cost, package_info = get_ingredient_price(
                ing["ingredient"],
                ing["quantity"],
                ing["unit"]
            )
            
            ingredients_with_cost.append(Ingredient(
                ingredient=ing["ingredient"],
                quantity=ing["quantity"],
                unit=ing["unit"],
                cost=cost,
                note=ing.get("note"),
                package_info=package_info
            ))
            
            total_cost += cost
        
        # Step 3: Calculate unit cost
        recipe_yield = request.yield_count
        print(f"Recipe yield value: {recipe_yield}, type: {type(recipe_yield)}")
        if not recipe_yield or recipe_yield <= 0:
            raise HTTPException(status_code=400, detail="Yield must be a positive number")
        
        unit_cost = total_cost / recipe_yield
        
        return CostResult(
            recipe_name=recipe_name,
            ingredients=ingredients_with_cost,
            total_cost=total_cost,
            yield_count=recipe_yield,
            unit_cost=unit_cost
        )
        
    except json.JSONDecodeError as e:
        print(f"JSON DECODE ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to parse recipe: {str(e)}")
    except Exception as e:
        print(f"GENERAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error calculating cost: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)