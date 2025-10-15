import React, { useState } from 'react';
import { DollarSign, ChefHat, Calculator, Loader2 } from 'lucide-react';

export default function UnitCostCalculator() {
  const [recipe, setRecipe] = useState('');
  const [yield_, setYield] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

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

    try {
      // Call backend API
      const response = await fetch('http://localhost:8000/calculate-cost', {
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
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm text-gray-900">
                            {ing.ingredient}
                            <span className="text-gray-500 text-xs ml-2">
                              ({ing.quantity}{ing.unit})
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-900 text-right font-medium">
                            ${ing.cost.toFixed(2)}
                          </td>
                        </tr>
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