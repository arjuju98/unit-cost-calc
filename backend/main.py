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

class Ingredient(BaseModel):
    ingredient: str
    quantity: float
    unit: str
    cost: float

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
        {{"ingredient": "ingredient name", "quantity": number, "unit": "g|ml|item|tbsp|tsp|cup"}},
        ...
    ]
}}

Important rules:
- Convert all volume measurements to grams where possible (1 cup flour = 120g, 1 cup sugar = 200g, 1 cup butter = 227g, 1 tbsp = 15ml, 1 tsp = 5ml)
- For items like eggs, use "item" as unit
- Standardize ingredient names (e.g., "all-purpose flour" -> "flour")
- Extract quantities as numbers only
- If no recipe name is found, set to null

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

def get_ingredient_price(ingredient_name: str, quantity: float, unit: str) -> float:
    """
    Fetch ingredient pricing using Spoonacular API.
    Returns cost for the specific quantity used.
    """
    
    if not SPOONACULAR_API_KEY:
        # Fallback prices if no API key (for testing)
        fallback_prices = {
            "oats": 0.002,  # per gram
            "peanut butter": 0.012,
            "protein powder": 0.022,
            "egg": 0.23,  # per item
            "chocolate chips": 0.010,
            "flour": 0.001,
            "butter": 0.015,
            "sugar": 0.002,
            "brown sugar": 0.003,
            "vanilla extract": 0.50,  # per ml
            "baking soda": 0.01,
            "baking powder": 0.02,
            "salt": 0.001,
            "milk": 0.001,
            "vegetable oil": 0.005,
            "honey": 0.010,
            "cocoa powder": 0.018,
            "nuts": 0.025,
            "cinnamon": 0.05,
        }
        
        # Find closest match in fallback prices
        for key, price_per_unit in fallback_prices.items():
            if key in ingredient_name.lower():
                if unit == "item":
                    return price_per_unit * quantity
                else:  # assume grams or ml
                    return price_per_unit * quantity
        
        # Default fallback
        return 0.10 * quantity
    
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
            return info_data["estimatedCost"]["value"] / 100
        
        return 0.10 * quantity  # Default if no price found
        
    except Exception as e:
        print(f"Error fetching price for {ingredient_name}: {e}")
        return 0.10 * quantity  # Default fallback

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
            cost = get_ingredient_price(
                ing["ingredient"],
                ing["quantity"],
                ing["unit"]
            )
            
            ingredients_with_cost.append(Ingredient(
                ingredient=ing["ingredient"],
                quantity=ing["quantity"],
                unit=ing["unit"],
                cost=cost
            ))
            
            total_cost += cost
        
        # Step 3: Calculate unit cost
        recipe_yield = request.yield_count
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
