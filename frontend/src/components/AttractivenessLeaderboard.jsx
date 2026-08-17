import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Trophy, TrendingUp, AlertTriangle } from 'lucide-react';

const AttractivenessLeaderboard = () => {
  const [products, setProducts] = useState([]);

  useEffect(() => {
    axios.get('http://127.0.0.1:8000/api/analytics/product-attractiveness')
      .then(res => setProducts(res.data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="bg-white p-6 rounded-xl shadow-md mt-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
          <Trophy className="text-yellow-500" /> Product Attractiveness Index
        </h2>
        <span className="text-xs bg-blue-100 text-blue-800 px-3 py-1 rounded-full font-semibold">
          Weighted Multi-Metric
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b bg-gray-50 text-xs font-semibold text-gray-600 uppercase">
              <th className="p-3">Rank</th>
              <th className="p-3">Product / Display</th>
              <th className="p-3">Gaze Duration</th>
              <th className="p-3">Interactions</th>
              <th className="p-3">Pickup Rate</th>
              <th className="p-3">Composite Score</th>
            </tr>
          </thead>
          <tbody className="divide-y text-sm">
            {products.map((item) => (
              <tr key={item.zone_id} className="hover:bg-gray-50">
                <td className="p-3 font-bold text-gray-700">#{item.rank}</td>
                <td className="p-3 font-medium text-gray-900">{item.product_name}</td>
                <td className="p-3 text-gray-600">{item.raw_attention_sec}s</td>
                <td className="p-3 text-gray-600">{item.raw_interactions}</td>
                <td className="p-3 text-gray-600">{(item.pickup_rate * 100).toFixed(0)}%</td>
                <td className="p-3">
                  <span className={`px-2 py-1 rounded-md text-xs font-bold ${
                    item.attractiveness_score >= 60 ? 'bg-green-100 text-green-800' :
                    item.attractiveness_score >= 30 ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {item.attractiveness_score} / 100
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AttractivenessLeaderboard;