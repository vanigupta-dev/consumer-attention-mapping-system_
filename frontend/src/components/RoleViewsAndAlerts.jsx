import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { AlertTriangle, UserCheck, ShieldAlert, TrendingUp, ShoppingBag } from 'lucide-react';

const RoleViewsAndAlerts = ({ currentRole, onRoleChange }) => {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/analytics/alerts');
      setAlerts(res.data.alerts || []);
    } catch (err) {
      console.error('Failed to load alerts:', err);
    }
  };

  return (
    <div className="space-y-4 mb-6">
      {/* Dynamic Alerts Banner */}
      {alerts.length > 0 && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg shadow-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-600 shrink-0" />
            <h3 className="font-bold text-red-800 text-sm">System Alert: Low Performing Displays Detected</h3>
          </div>
          <div className="mt-2 text-xs text-red-700 space-y-1">
            {alerts.map((a) => (
              <p key={a.product_id}>
                ⚠️ <span className="font-semibold">{a.product_name}</span>: Score is {a.score} (Threshold: 30.0)
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Role View Selector */}
      <div className="flex justify-between items-center bg-white p-4 rounded-xl shadow-sm border border-gray-100">
        <div className="flex items-center gap-2">
          <UserCheck className="w-5 h-5 text-blue-600" />
          <span className="text-sm font-semibold text-gray-700">Select Role View:</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => onRoleChange('Store Manager')}
            className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              currentRole === 'Store Manager'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Store Manager
          </button>
          <button
            onClick={() => onRoleChange('Retail Analyst')}
            className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              currentRole === 'Retail Analyst'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Retail Analyst
          </button>
          <button
            onClick={() => onRoleChange('Marketing Manager')}
            className={`px-4 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              currentRole === 'Marketing Manager'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Marketing Manager
          </button>
        </div>
      </div>
    </div>
  );
};

export default RoleViewsAndAlerts;