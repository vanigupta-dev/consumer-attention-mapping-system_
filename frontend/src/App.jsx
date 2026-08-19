import React, { useState } from 'react';
import ShelfHeatmap from './components/ShelfHeatmap';
import AttractivenessLeaderboard from './components/AttractivenessLeaderboard';
import Recommendations from './components/Recommendations';
import RoleViewsAndAlerts from './components/RoleViewsAndAlerts';
import { Download, LayoutDashboard, LogOut } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import AuthModal from './components/Auth';

function MainDashboard() {
  const { user, logout } = useAuth();
  const [role, setRole] = useState('Store Manager');

  if (!user) {
    return <AuthModal />;
  }

  const handleDownloadPDF = () => {
    window.open('http://127.0.0.1:8000/api/analytics/export/pdf', '_blank');
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      {/* Header Bar */}
      <header className="flex justify-between items-center mb-6 bg-white p-6 rounded-xl shadow-sm">
        <div className="flex items-center gap-3">
          <LayoutDashboard className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Consumer Attention Mapping Dashboard</h1>
            <p className="text-sm text-gray-500">
              User: <span className="font-semibold text-gray-700">{user.email}</span> | Active View: <span className="font-semibold text-blue-600">{role}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleDownloadPDF}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg font-medium shadow-sm transition-all text-sm"
          >
            <Download className="w-4 h-4" /> Download PDF Report
          </button>

          <button
            onClick={logout}
            className="flex items-center gap-2 bg-gray-200 hover:bg-gray-300 text-gray-800 px-4 py-2.5 rounded-lg font-medium text-sm transition-all"
          >
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </header>

      {/* Part 2: Role Switcher & Real-Time Alerts */}
      <RoleViewsAndAlerts currentRole={role} onRoleChange={setRole} />

      {/* Main Analytics Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 items-start mb-8">
        <ShelfHeatmap />
        <AttractivenessLeaderboard />
      </div>

      {/* Part 1: Optimization Recommendations Engine */}
      <Recommendations />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainDashboard />
    </AuthProvider>
  );
}