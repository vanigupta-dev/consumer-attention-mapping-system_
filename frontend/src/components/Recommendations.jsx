import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Lightbulb, AlertTriangle, CheckCircle2 } from 'lucide-react';

const Recommendations = () => {
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRecommendations();
  }, []);

  const fetchRecommendations = async () => {
    try {
      const response = await axios.get('http://127.0.0.1:8000/api/analytics/recommendations');
      setRecommendations(response.data);
      setLoading(false);
    } catch (err) {
      console.error('Failed to load recommendations:', err);
      setLoading(false);
    }
  };

  if (loading) return <div className="p-4">Loading optimization insights...</div>;

  return (
    <div className="bg-white p-6 rounded-xl shadow-md w-full mt-8">
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="w-6 h-6 text-amber-500" />
        <h2 className="text-xl font-bold text-gray-800">Part 1: Optimization & Action Engine</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {recommendations.map((item) => (
          <div key={item.product_id} className="border border-gray-200 rounded-lg p-4 bg-gray-50 flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="font-semibold text-gray-900">{item.product_name}</span>
                <span className={`px-2 py-0.5 text-xs font-bold rounded ${
                  item.composite_score >= 50 ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'
                }`}>
                  Score: {item.composite_score}
                </span>
              </div>
              <ul className="text-xs text-gray-600 space-y-2 mt-2">
                {item.recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Recommendations;