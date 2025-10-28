def calculate_price_per_unit(package_price, package_size, unit="g"):
    """
    Quick calculator for ingredient prices
    """
    price_per_unit = package_price / package_size
    print(f"\nPackage: ${package_price} for {package_size}{unit}")
    print(f"Price per {unit}: ${price_per_unit:.4f}")
    print(f'\nAdd to database:')
    print(f'"price_per_{unit}": {price_per_unit:.4f},')
    print("-" * 50)
    return price_per_unit

# Run your calculations here:
calculate_price_per_unit(8.99, 454, "g")  # Example: Almond flour
calculate_price_per_unit(5.49, 750, "ml")  # Example: Vanilla extract