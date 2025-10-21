import React, { useState } from 'react';
import { DollarSign, ChefHat, Calculator, Loader2, Edit2, Check, X, Info } from 'lucide-react';

export default function UnitCostCalculator() {
  const [recipe, setRecipe] = useState('');
  const [yield_, setYield] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [editingIndex, setEditingIndex] = useState(null);
  const [editPackageSize, setEditPackageSize] = useState('');
  const [editPackagePrice, setEditPackagePrice] = useState('');
  const [expandedIndex, setExpandedIndex] = useState(null);

  const exampleRecipe = `Chocolate Chip Protein Cookies

- 60g oats
- 30g peanut butter
- 20g protein powder
- 1 egg
- 10g chocolate chips

Yields: 6 cookies`;

  const handleCalculate = async () => {
    if (!recipe.trim()) {
      setError('Please enter a recipe');
      return;
    }
    if (!yield_.trim()) {
      setError('Please enter the yield (number of items)');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);
    setEditingIndex(null);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/calculate-cost`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          recipe: recipe,
          yield_count: parseInt(yield_)
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to calculate cost');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const parsePackageSize = (sizeStr) => {
    // Extract numeric value from package size string like "454g" or "1kg"
    const match = sizeStr.match(/(\d+(?:\.\d+)?)\s*(g|kg|ml|L|item)/i);
    if (!match) return null;
    
    let value = parseFloat(match[1]);
    const unit = match[2].toLowerCase();
    
    // Convert to base units (grams/ml)
    if (unit === 'kg') value *= 1000;
    if (unit === 'l') value *= 1000;
    
    return { value, unit: unit === 'item' ? 'item' : (unit === 'ml' || unit === 'l' ? 'ml' : 'g') };
  };

  const startEdit = (index) => {
    const ing = result.ingredients[index];
    if (ing.package_info) {
      // Extract just the numeric part and unit from package size
      const parsed = parsePackageSize(ing.package_info.size);
      if (parsed) {
        setEditPackageSize(parsed.value.toString());
      } else {
        setEditPackageSize('');
      }
      setEditPackagePrice(ing.package_info.price.toFixed(2));
    }
    setEditingIndex(index);
  };

  const cancelEdit = () => {
    setEditingIndex(null);
    setEditPackageSize('');
    setEditPackagePrice('');
  };

  const saveEdit = (index) => {
    const packageSize = parseFloat(editPackageSize);
    const packagePrice = parseFloat(editPackagePrice);
    
    if (isNaN(packageSize) || packageSize <= 0) {
      alert('Please enter a valid package size');
      return;
    }
    if (isNaN(packagePrice) || packagePrice < 0) {
      alert('Please enter a valid package price');
      return;
    }

    const ing = result.ingredients[index];
    
    // Calculate new cost per unit
    const newCostPerUnit = packagePrice / packageSize;
    
    // Calculate new ingredient cost based on quantity used
    const newIngredientCost = newCostPerUnit * ing.quantity;
    
    // Determine display unit
    const displayUnit = ing.unit === 'ml' ? 'ml' : (ing.unit === 'item' ? 'item' : 'g');
    
    // Update the ingredient
    const updatedIngredients = [...result.ingredients];
    updatedIngredients[index] = {
      ...ing,
      cost: newIngredientCost,
      manually_adjusted: true,
      package_info: {
        size: `${packageSize}${displayUnit}`,
        price: packagePrice,
        cost_per_unit: newCostPerUnit,
        unit: displayUnit
      }
    };

    // Recalculate totals
    const newTotalCost = updatedIngredients.reduce((sum, ing) => sum + ing.cost, 0);
    const newUnitCost = newTotalCost / result.yield_count;

    setResult({
      ...result,
      ingredients: updatedIngredients,
      total_cost: newTotalCost,
      unit_cost: newUnitCost
    });

    setEditingIndex(null);
    setEditPackageSize('');
    setEditPackagePrice('');
  };

  const toggleExpanded = (index) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  const loadExample = () => {
    setRecipe(exampleRecipe);
    setYield('6');
    setError('');
    setResult(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-amber-50 to-yellow-50">
      <div className="max-w-5xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="flex items-center justify-center gap-3 mb-4">
            <ChefHat className="w-12 h-12 text-orange-600" />
            <h1 className="text-4xl font-bold text-gray-900">Unit Cost Calculator</h1>
          </div>
          <p className="text-lg text-gray-600">
            Calculate the cost per unit for your baked goods automatically
          </p>
        </div>

        {/* Main Content */}
        <div className="grid md:grid-cols-2 gap-8">
          {/* Input Section */}
          <div className="bg-white rounded-2xl shadow-lg p-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-semibold text-gray-800">Recipe Input</h2>
              <button
                onClick={loadExample}
                className="text-sm text-orange-600 hover:text-orange-700 font-medium"
              >
                Load Example
              </button>
            </div>

            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Recipe
                </label>
                <textarea
                  value={recipe}
                  onChange={(e) => setRecipe(e.target.value)}
                  placeholder="Paste your recipe here...&#10;&#10;Example:&#10;Chocolate Chip Cookies&#10;- 200g flour&#10;- 100g butter&#10;- 50g sugar&#10;- 1 egg&#10;- 50g chocolate chips"
                  className="w-full h-64 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent resize-none text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Yield (number of items)
                </label>
                <input
                  type="number"
                  value={yield_}
                  onChange={(e) => setYield(e.target.value)}
                  placeholder="e.g., 12"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                />
              </div>

              <button
                onClick={handleCalculate}
                disabled={loading}
                className="w-full bg-orange-600 hover:bg-orange-700 disabled:bg-gray-400 text-white font-semibold py-4 rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Calculating...
                  </>
                ) : (
                  <>
                    <Calculator className="w-5 h-5" />
                    Calculate Cost
                  </>
                )}
              </button>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              )}
            </div>
          </div>

          {/* Results Section */}
          <div className="bg-white rounded-2xl shadow-lg p-8">
            <h2 className="text-2xl font-semibold text-gray-800 mb-6">Cost Breakdown</h2>

            {!result && !loading && (
              <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                <DollarSign className="w-16 h-16 mb-4" />
                <p className="text-center">
                  Enter your recipe and click Calculate Cost to see the breakdown
                </p>
              </div>
            )}

            {loading && (
              <div className="flex flex-col items-center justify-center h-64">
                <Loader2 className="w-12 h-12 text-orange-600 animate-spin mb-4" />
                <p className="text-gray-600">Analyzing recipe and fetching prices...</p>
              </div>
            )}

            {result && (
              <div className="space-y-6">
                {/* Recipe Name */}
                {result.recipe_name && (
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900">{result.recipe_name}</h3>
                  </div>
                )}

                {/* Instructions */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
                  <div className="flex items-start gap-2">
                    <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-medium">Adjust pricing to match your purchases</p>
                      <p className="text-xs mt-1">Click "show details" then edit the package size and price you actually paid.</p>
                    </div>
                  </div>
                </div>

                {/* Ingredients Table */}
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                          Ingredient
                        </th>
                        <th className="px-4 py-3 text-right text-xs font-medium text-gray-700 uppercase">
                          Cost
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {result.ingredients?.map((ing, idx) => (
                        <React.Fragment key={idx}>
                          <tr className="hover:bg-gray-50">
                            <td className="px-4 py-3">
                              <div className="text-sm text-gray-900 font-medium">
                                {ing.ingredient}
                                {ing.manually_adjusted && (
                                  <span className="ml-2 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                                    Edited
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-gray-500 mt-1">
                                {ing.quantity}{ing.unit}
                                {ing.package_info && (
                                  <button
                                    onClick={() => toggleExpanded(idx)}
                                    className="ml-2 text-blue-600 hover:text-blue-700 underline"
                                  >
                                    {expandedIndex === idx ? 'hide details' : 'show details'}
                                  </button>
                                )}
                              </div>
                              {ing.note && (
                                <div className="text-xs text-blue-600 mt-1.5 flex items-start gap-1 bg-blue-50 px-2 py-1 rounded">
                                  <span>💡</span>
                                  <span>{ing.note}</span>
                                </div>
                              )}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <span className="text-sm text-gray-900 font-medium">
                                ${ing.cost.toFixed(2)}
                              </span>
                            </td>
                          </tr>
                          {expandedIndex === idx && ing.package_info && (
                            <tr className="bg-gray-50">
                              <td colSpan="2" className="px-4 py-3">
                                {editingIndex === idx ? (
                                  <div className="space-y-3">
                                    <div className="text-sm font-medium text-gray-700 mb-2">
                                      Edit Package Details
                                    </div>
                                    <div className="grid grid-cols-2 gap-3">
                                      <div>
                                        <label className="block text-xs text-gray-600 mb-1">
                                          Package Size ({ing.package_info.unit})
                                        </label>
                                        <input
                                          type="number"
                                          step="0.1"
                                          value={editPackageSize}
                                          onChange={(e) => setEditPackageSize(e.target.value)}
                                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-orange-500"
                                          placeholder="e.g., 1000"
                                        />
                                      </div>
                                      <div>
                                        <label className="block text-xs text-gray-600 mb-1">
                                          Package Price ($)
                                        </label>
                                        <input
                                          type="number"
                                          step="0.01"
                                          value={editPackagePrice}
                                          onChange={(e) => setEditPackagePrice(e.target.value)}
                                          className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-orange-500"
                                          placeholder="e.g., 12.00"
                                        />
                                      </div>
                                    </div>
                                    <div className="flex items-center gap-2 pt-2">
                                      <button
                                        onClick={() => saveEdit(idx)}
                                        className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                                      >
                                        <Check className="w-4 h-4" />
                                        Save
                                      </button>
                                      <button
                                        onClick={cancelEdit}
                                        className="flex items-center gap-1 px-3 py-1.5 bg-gray-300 text-gray-700 text-sm rounded hover:bg-gray-400"
                                      >
                                        <X className="w-4 h-4" />
                                        Cancel
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  <div className="text-xs text-gray-600 space-y-1">
                                    <div className="flex justify-between items-center">
                                      <div>
                                        <div className="font-medium text-gray-700 mb-1">Pricing Details:</div>
                                        <div>Package Size: {ing.package_info.size}</div>
                                        <div>Package Price: ${ing.package_info.price.toFixed(2)}</div>
                                        <div>Cost per {ing.package_info.unit}: ${ing.package_info.cost_per_unit.toFixed(4)}</div>
                                      </div>
                                      <button
                                        onClick={() => startEdit(idx)}
                                        className="flex items-center gap-1 px-3 py-1.5 bg-orange-100 text-orange-700 text-sm rounded hover:bg-orange-200"
                                      >
                                        <Edit2 className="w-3 h-3" />
                                        Edit
                                      </button>
                                    </div>
                                  </div>
                                )}
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Totals */}
                <div className="space-y-3 pt-4 border-t-2 border-gray-200">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700 font-medium">Total Recipe Cost:</span>
                    <span className="text-2xl font-bold text-gray-900">
                      ${result.total_cost?.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-700 font-medium">Yield:</span>
                    <span className="text-lg text-gray-900">
                      {result.yield_count} {result.yield_count === 1 ? 'item' : 'items'}
                    </span>
                  </div>
                  <div className="bg-orange-50 rounded-lg p-4 mt-4">
                    <div className="flex justify-between items-center">
                      <span className="text-orange-900 font-semibold text-lg">
                        Unit Cost:
                      </span>
                      <span className="text-3xl font-bold text-orange-600">
                        ${result.unit_cost?.toFixed(2)}
                      </span>
                    </div>
                    <p className="text-orange-700 text-sm mt-1">per item</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="text-center mt-12 text-gray-500 text-sm">
          <p>Built for home bakers and small bakery owners</p>
        </div>
      </div>
    </div>
  );
}