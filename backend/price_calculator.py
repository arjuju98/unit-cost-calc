"""
Enhanced Price Calculator for Ingredient Database
Handles conversions from various units to grams/ml
"""

def convert_to_grams(amount, unit):
    """Convert various units to grams"""
    conversions = {
        'oz': 28.35,      # weight ounces to grams
        'lb': 453.592,    # pounds to grams
        'kg': 1000,       # kilograms to grams
        'g': 1,           # already grams
    }
    
    if unit.lower() in conversions:
        return amount * conversions[unit.lower()]
    else:
        raise ValueError(f"Unknown unit: {unit}. Use oz, lb, kg, or g")

def convert_to_ml(amount, unit):
    """Convert various liquid units to milliliters"""
    conversions = {
        'fl oz': 29.5735,  # fluid ounces to ml
        'floz': 29.5735,   # fluid ounces (no space)
        'cup': 240,        # cups to ml
        'tbsp': 15,        # tablespoons to ml
        'tsp': 5,          # teaspoons to ml
        'ml': 1,           # already ml
        'l': 1000,         # liters to ml
    }
    
    if unit.lower() in conversions:
        return amount * conversions[unit.lower()]
    else:
        raise ValueError(f"Unknown unit: {unit}. Use fl oz, cup, tbsp, tsp, ml, or l")

def calculate_ingredient_price(package_price, package_amount, package_unit, ingredient_type='solid'):
    """
    Calculate price per gram/ml for an ingredient
    
    Args:
        package_price: Price of the package (e.g., 5.99)
        package_amount: Amount in package (e.g., 42)
        package_unit: Unit of measurement (e.g., 'oz', 'fl oz', 'g', 'ml')
        ingredient_type: 'solid' (uses grams) or 'liquid' (uses ml)
    
    Returns:
        Dictionary with all the info needed for database
    """
    
    try:
        if ingredient_type == 'solid':
            # Convert to grams
            grams = convert_to_grams(package_amount, package_unit)
            price_per_g = package_price / grams
            
            print("\n" + "="*60)
            print(f"INGREDIENT CALCULATION (Solid)")
            print("="*60)
            print(f"Package Info: ${package_price} for {package_amount} {package_unit}")
            print(f"Converted to: {grams:.2f}g")
            print(f"Price per gram: ${price_per_g:.6f}")
            print("\n" + "-"*60)
            print("ADD TO DATABASE:")
            print("-"*60)
            print(f'"ingredient_name": {{')
            print(f'    "price_per_g": {price_per_g:.6f},')
            print(f'    "package_size": "{int(grams)}g ({package_amount} {package_unit})",')
            print(f'    "package_price": {package_price:.2f}')
            print(f'}},')
            print("="*60 + "\n")
            
            return {
                'price_per_g': price_per_g,
                'package_size_g': grams,
                'package_price': package_price
            }
            
        else:  # liquid
            # Convert to ml
            ml = convert_to_ml(package_amount, package_unit)
            price_per_ml = package_price / ml
            
            print("\n" + "="*60)
            print(f"INGREDIENT CALCULATION (Liquid)")
            print("="*60)
            print(f"Package Info: ${package_price} for {package_amount} {package_unit}")
            print(f"Converted to: {ml:.2f}ml")
            print(f"Price per ml: ${price_per_ml:.6f}")
            print("\n" + "-"*60)
            print("ADD TO DATABASE:")
            print("-"*60)
            print(f'"ingredient_name": {{')
            print(f'    "price_per_ml": {price_per_ml:.6f},')
            print(f'    "package_size": "{int(ml)}ml ({package_amount} {package_unit})",')
            print(f'    "package_price": {package_price:.2f}')
            print(f'}},')
            print("="*60 + "\n")
            
            return {
                'price_per_ml': price_per_ml,
                'package_size_ml': ml,
                'package_price': package_price
            }
            
    except ValueError as e:
        print(f"\nERROR: {e}")
        return None

# ============================================================
# EXAMPLES - Edit these with your actual ingredient data
# ============================================================

# Solid ingredients (uses grams)
calculate_ingredient_price(7.49, 14, 'fl oz', 'liquid')      # coconut oil
calculate_ingredient_price(15.49, 8, 'oz', 'solid')      # xanthan gum

# Liquid ingredients (uses ml)
# calculate_ingredient_price(4.99, 12, 'fl oz', 'liquid')  # Vanilla: $4.99 for 12 fl oz
# calculate_ingredient_price(5.49, 2, 'cup', 'liquid')     # Honey: $5.49 for 2 cups
# calculate_ingredient_price(3.99, 750, 'ml', 'liquid')    # Olive oil: $3.99 for 750ml

# print("\n" + "="*60)
# print("HOW TO USE THIS SCRIPT:")
# print("="*60)
# print("1. Edit the examples above with your ingredient data")
# print("2. Run: python3 price_calculator.py")
# print("3. Copy the 'ADD TO DATABASE' section into main.py")
# print("4. Replace 'ingredient_name' with the actual ingredient")
# print("="*60 + "\n")