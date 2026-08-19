import React from 'react';
import ShelfHeatmap from './components/ShelfHeatmap';
import AttractivenessLeaderboard from './components/AttractivenessLeaderboard';
import Recommendations from './components/Recommendations';
import RoleViewsAndAlerts from './components/RoleViewsAndAlerts';
import { Download, LayoutDashboard, LogOut, Shield } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import AuthModal from './components/Auth';

function MainDashboard() {
  const { user, logout } = useAuth();

  if (!user) return <AuthModal />;

  const handleDownloadPDF = () => {
    window.open('http://127.0.0.1:8000/api/analytics/export/pdf', '_blank');
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      {/* Top Header */}
      <header className="flex justify-between items-center mb-6 bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-blue-50 text-blue-600 rounded-lg">
            <LayoutDashboard className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Consumer Attention Mapping</h1>
            <p className="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5">
              <span>Logged as: <strong className="text-slate-700">{user.email}</strong></span>
              <span>•</span>
              <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-medium text-xs">
                <Shield className="w-3 h-3 text-blue-600" /> {user.role}
              </span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* PDF Download visible for Marketing Manager and Retail Analyst */}
          {(user.role === 'Marketing Manager' || user.role === 'Retail Analyst') && (
            <button
              onClick={handleDownloadPDF}
              className="flex items-center gap-2 bg-slate-800 hover:bg-slate-900 text-white px-4 py-2 rounded-lg text-xs font-medium transition-all shadow-sm"
            >
              <Download className="w-3.5 h-3.5" /> Export PDF Report
            </button>
          )}

          <button
            onClick={logout}
            className="flex items-center gap-1.5 border border-slate-200 hover:bg-slate-100 text-slate-600 px-3 py-2 rounded-lg text-xs font-medium transition-all"
          >
            <LogOut className="w-3.5 h-3.5" /> Logout
          </button>
        </div>
      </header>

      {/* Real-Time Alerts Banner */}
      <RoleViewsAndAlerts currentRole={user.role} />

      {/* Role Restricted Content */}
      <div className="space-y-6 mt-6">
        {/* Store Manager View */}
        {user.role === 'Store Manager' && (
          <div className="grid grid-cols-1 gap-6">
            <ShelfHeatmap />
          </div>
        )}

        {/* Retail Analyst View */}
        {user.role === 'Retail Analyst' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-start">
              <ShelfHeatmap />
              <AttractivenessLeaderboard />
            </div>
            <Recommendations />
          </div>
        )}

        {/* Marketing Manager View */}
        {user.role === 'Marketing Manager' && (
          <div className="space-y-6">
            <AttractivenessLeaderboard />
            <Recommendations />
          </div>
        )}
      </div>
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