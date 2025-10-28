from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic
import os
import json
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://unit-cost-calc.vercel.app",
        "https://*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

class RecipeRequest(BaseModel):
    recipe: str
    yield_count: int = None

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
    unknown_ingredient: bool = False
    
    class Config:
        from_attributes = True

class CostResult(BaseModel):
    recipe_name: Optional[str]
    ingredients: List[Ingredient]
    total_cost: float
    yield_count: int
    unit_cost: float

def parse_recipe_with_claude(recipe_text: str) -> dict:
    """Use Claude to extract structured ingredient data from recipe text."""
    
    prompt = f"""Extract and normalize ingredients from the following recipe.
Return ONLY valid JSON (no markdown, no code blocks) with this structure:
{{
    "recipe_name": "name of recipe if mentioned",
    "ingredients": [
        {{"ingredient": "ingredient name", "quantity": number, "unit": "g|ml|item", "note": "optional clarification"}},
        ...
    ]
}}

CRITICAL CONVERSION RULES - You MUST convert all measurements:
- ALL solid ingredients MUST be in grams (g), never oz, cups, tbsp, tsp
- ALL liquid ingredients MUST be in milliliters (ml), never oz, cups, tbsp, tsp
- Items like eggs, use "item" as unit

Standard conversions:
- 1 cup flour = 120g, 1 cup sugar = 200g, 1 cup butter = 227g, 1 cup oats = 80g
- 1 oz (weight) = 28.35g
- 1 tbsp = 15ml, 1 tsp = 5ml
- 1 cup (liquid) = 240ml
- 1 fl oz = 30ml
- For protein powder scoops/servings: use 30g per scoop as default and add note: "estimated at 30g per scoop"
- For other supplement scoops: use reasonable estimates based on product type and add a note
- For items like eggs, use "item" as unit
- Standardize ingredient names (e.g., "all-purpose flour" -> "flour", "PEScience Protein Powder" -> "protein powder")
- Extract quantities as numbers only
- If no recipe name is found, set to null
- Add a "note" field when you've made an assumption about conversions

EXAMPLES:
- "2 cups flour" → {{"ingredient": "flour", "quantity": 240, "unit": "g"}}
- "8 oz butter" → {{"ingredient": "butter", "quantity": 227, "unit": "g"}}
- "1/4 cup oil" → {{"ingredient": "oil", "quantity": 60, "unit": "ml"}}
- "2 tbsp honey" → {{"ingredient": "honey", "quantity": 30, "unit": "ml"}}

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

def get_ingredient_price(ingredient_name: str, quantity: float, unit: str) -> tuple[float, Optional[PackageInfo]]:
    """
    Get ingredient pricing from our curated database.
    Returns (cost for the specific quantity used, package info).
    """
    
    # Curated ingredient database with realistic pricing
    ingredient_database = {
        "oats": {"price_per_g": 0.002, "package_size": "1kg", "package_price": 2.00},
        "peanut butter": {"price_per_g": 0.012, "package_size": "454g", "package_price": 5.49},
        "protein powder": {"price_per_g": 0.022, "package_size": "810g (27 servings)", "package_price": 45.00},
        "egg": {"price_per_item": 0.23, "package_size": "12 eggs", "package_price": 2.76},
        "chocolate chips": {"price_per_g": 0.010, "package_size": "300g", "package_price": 3.00},
        "chocolate": {"price_per_g": 0.010, "package_size": "300g", "package_price": 3.00},
        "flour": {"price_per_g": 0.001, "package_size": "2kg", "package_price": 2.00},
        "almond flour": {"price_per_g": 0.018, "package_size": "454g", "package_price": 8.00},
        "butter": {"price_per_g": 0.015, "package_size": "454g", "package_price": 6.99},
        "sugar": {"price_per_g": 0.002, "package_size": "2kg", "package_price": 4.00},
        "brown sugar": {"price_per_g": 0.003, "package_size": "1kg", "package_price": 3.00},
        "vanilla extract": {"price_per_ml": 0.50, "package_size": "60ml", "package_price": 30.00},
        "vanilla": {"price_per_ml": 0.50, "package_size": "60ml", "package_price": 30.00},
        "baking soda": {"price_per_g": 0.01, "package_size": "454g", "package_price": 4.54},
        "baking powder": {"price_per_g": 0.02, "package_size": "227g", "package_price": 4.54},
        "salt": {"price_per_g": 0.001, "package_size": "750g", "package_price": 0.75},
        "milk": {"price_per_ml": 0.001, "package_size": "1L", "package_price": 1.00},
        "vegetable oil": {"price_per_ml": 0.005, "package_size": "750ml", "package_price": 3.75},
        "oil": {"price_per_ml": 0.005, "package_size": "750ml", "package_price": 3.75},
        "honey": {"price_per_g": 0.010, "package_size": "500g", "package_price": 5.00},
        "cocoa powder": {"price_per_g": 0.018, "package_size": "250g", "package_price": 4.50},
        "cocoa": {"price_per_g": 0.018, "package_size": "250g", "package_price": 4.50},
        "nuts": {"price_per_g": 0.025, "package_size": "200g", "package_price": 5.00},
        "cinnamon": {"price_per_g": 0.05, "package_size": "50g", "package_price": 2.50},
        "applesauce": {"price_per_g": 0.003, "package_size": "650g", "package_price": 2.00},
    }
    
    # Find match in database
    ingredient_data = None
    for key, data in ingredient_database.items():
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
    
    # Default for unknown ingredients - return minimal cost and flag as unknown
    return 0, None

@app.get("/")
async def root():
    return {"message": "Unit Cost Calculator API is running"}

@app.post("/calculate-cost", response_model=CostResult)
async def calculate_cost(request: RecipeRequest):
    """
    Main endpoint to calculate recipe cost.
    1. Parse recipe with Claude
    2. Get pricing for each ingredient from database
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
            
            # Check if ingredient is unknown (cost = 0 and no package_info)
            is_unknown = (cost == 0 and package_info is None)
            
            print(f"Ingredient: {ing['ingredient']}, cost: {cost}, package_info: {package_info}, is_unknown: {is_unknown}")
            
            ingredients_with_cost.append(Ingredient(
                ingredient=ing["ingredient"],
                quantity=ing["quantity"],
                unit=ing["unit"],
                cost=cost,
                note=ing.get("note"),
                package_info=package_info,
                manually_adjusted=False,
                unknown_ingredient=is_unknown
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