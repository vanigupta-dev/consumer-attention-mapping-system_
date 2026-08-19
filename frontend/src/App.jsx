import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import AuthModal from './components/Auth';
import {
  Download, LayoutDashboard, LogOut, Shield, Sliders, Eye, AlertTriangle,
  Clock, TrendingUp, ShoppingBag, Sparkles, Users
} from 'lucide-react';

const HOURLY_DATA = [
  { hour: '09:00 AM', footfall: 42, avgDwell: '12s', attentionScore: 64 },
  { hour: '11:00 AM', footfall: 118, avgDwell: '28s', attentionScore: 88 },
  { hour: '01:00 PM', footfall: 95, avgDwell: '19s', attentionScore: 72 },
  { hour: '03:00 PM', footfall: 140, avgDwell: '34s', attentionScore: 94 },
  { hour: '05:00 PM', footfall: 185, avgDwell: '41s', attentionScore: 98 },
  { hour: '07:00 PM', footfall: 110, avgDwell: '22s', attentionScore: 79 },
];

const PRODUCTS_ANALYTICS = [
  { id: 1, name: 'Wireless Headphones', category: 'Electronics', gazeCount: 412, dwellAvg: '24.1s', attractiveness: 98, shelfZone: 'Eye Level', action: 'Increase Stock (+20 units)' },
  { id: 2, name: 'Luxury Chronograph Watch', category: 'Accessories', gazeCount: 342, dwellAvg: '18.4s', attractiveness: 94, shelfZone: 'Eye Level', action: 'Cross-sell with Leather Belts' },
  { id: 3, name: 'Organic Cold-Pressed Juice', category: 'Beverages', gazeCount: 289, dwellAvg: '8.2s', attractiveness: 78, shelfZone: 'Touch Level', action: 'Move closer to Checkout' },
  { id: 4, name: 'Artisanal Dark Chocolate', category: 'Confectionery', gazeCount: 156, dwellAvg: '5.1s', attractiveness: 52, shelfZone: 'Knee Level', action: 'Relocate to Eye Level' },
];

function MainDashboard() {
  const { user, logout } = useAuth();
  const [gazeThreshold, setGazeThreshold] = useState(2.0);
  const [dwellThreshold, setDwellThreshold] = useState(10);
  const [selectedHour, setSelectedHour] = useState('All Day');

  const activeRole = user?.role || 'Guest';

  const handleDownloadPDF = async () => {
    try {
      if (!user?.role) {
        alert("No user role detected. Please log out and log back in.");
        return;
      }

      const response = await fetch(`http://127.0.0.1:8000/api/analytics/export/pdf?role=${encodeURIComponent(user.role)}`);
      if (!response.ok) throw new Error('Failed to generate PDF on server');

      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/pdf')) {
        alert('Backend returned invalid document format.');
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const formattedRole = user.role.replace(/\s+/g, '_');
      link.download = `${formattedRole}_Report.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      window.print();
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6 font-sans">
      {/* HEADER */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center bg-slate-800 border border-slate-700 p-5 rounded-2xl mb-6 gap-4 shadow-lg">
        <div className="flex items-center gap-3.5">
          <div className="p-3 bg-blue-600/20 text-blue-400 rounded-xl">
            <LayoutDashboard className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white">Consumer Attention Mapping</h1>
              <span className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full">Active Portal</span>
            </div>
            <p className="text-xs text-slate-400 flex items-center gap-2 mt-1">
              <span>Account: <strong className="text-slate-200">{user?.email}</strong></span>
              <span>•</span>
              <span className="inline-flex items-center gap-1 text-blue-400 font-medium">
                <Shield className="w-3.5 h-3.5" /> {activeRole}
              </span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* EXPORT BUTTON & PREVIEW TOOLTIP */}
          <div className="flex flex-col items-end gap-1">
            <button
              onClick={handleDownloadPDF}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-xl text-xs font-semibold shadow-lg shadow-blue-600/20 cursor-pointer transition-all"
            >
              <Download className="w-4 h-4" /> Export {activeRole} PDF Report
            </button>
            <span className="text-[10px] text-slate-400">
              Generating tailored table for {activeRole}
            </span>
          </div>

          <button
            onClick={logout}
            className="flex items-center gap-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 px-3.5 py-2 rounded-xl text-xs font-medium cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5" /> Logout
          </button>
        </div>
      </header>

      {/* FILTER CONTROLS */}
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-5 mb-6">
        <div className="flex items-center gap-2 mb-3 text-xs font-semibold text-slate-400 uppercase">
          <Sliders className="w-4 h-4 text-blue-400" />
          <span>Real-time Threshold & Spatial Parameters</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-900 p-3.5 rounded-xl border border-slate-700">
            <div className="flex justify-between items-center text-xs mb-2">
              <span className="text-slate-300">Min Gaze Threshold</span>
              <span className="text-blue-400 font-mono font-bold">{gazeThreshold}s</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="10.0"
              step="0.5"
              value={gazeThreshold}
              onChange={(e) => setGazeThreshold(parseFloat(e.target.value))}
              className="w-full accent-blue-500 bg-slate-700 h-1.5 rounded-lg cursor-pointer"
            />
          </div>

          <div className="bg-slate-900 p-3.5 rounded-xl border border-slate-700">
            <div className="flex justify-between items-center text-xs mb-2">
              <span className="text-slate-300">Dwell Time Threshold</span>
              <span className="text-emerald-400 font-mono font-bold">{dwellThreshold}s</span>
            </div>
            <input
              type="range"
              min="5"
              max="60"
              step="5"
              value={dwellThreshold}
              onChange={(e) => setDwellThreshold(parseInt(e.target.value))}
              className="w-full accent-emerald-500 bg-slate-700 h-1.5 rounded-lg cursor-pointer"
            />
          </div>

          <div className="bg-slate-900 p-3.5 rounded-xl border border-slate-700">
            <label className="block text-xs text-slate-300 mb-1.5">Hourly Window Selection</label>
            <select
              value={selectedHour}
              onChange={(e) => setSelectedHour(e.target.value)}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg text-xs text-slate-200 px-3 py-1.5 focus:outline-none"
            >
              <option value="All Day">All Day Aggregated</option>
              {HOURLY_DATA.map((h, i) => (
                <option key={i} value={h.hour}>{h.hour} Peak Window</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* PDF REPORT DATA PREVIEW CARD */}
      <div className="bg-slate-800 border border-slate-700 rounded-2xl p-5 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Download className="w-4 h-4 text-blue-400" /> Dedicated PDF Export Dataset for {activeRole}
          </h3>
          <span className="text-[11px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2.5 py-0.5 rounded-full font-medium">
            Auto-Generated in Report
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {activeRole === 'Store Manager' && (
            <>
              <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
                <p className="font-bold text-white mb-1">Floor Spatial Heatmaps</p>
                <p className="text-[11px] text-slate-400">Ranks Zone A/B/C performance to optimize immediate floor layouts.</p>
              </div>
              <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
                <p className="font-bold text-white mb-1">Inventory & Misplacement Alerts</p>
                <p className="text-[11px] text-slate-400">Triggers restocking priorities for high-gaze, low-stock items.</p>
              </div>
              <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
                <p className="font-bold text-white mb-1">Hourly Dwell & Footfall Log</p>
                <p className="text-[11px] text-slate-400">Assists staff scheduling during peak 3 PM – 5 PM traffic windows.</p>
              </div>
            </>
          )}

          {activeRole === 'Retail Analyst' && (
            <>
              <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
                <p className="font-bold text-white mb-1">Attractiveness & Conversion Matrix</p>
                <p className="text-[11px] text-slate-400">Informs long-term shelf space allocation based on gaze duration.</p>
              </div>
              <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
                <p className="font-bold text-white mb-1">Planogram ROI & Eye-Level Stats</p>
                <p className="text-[11px] text-slate-400">Validates product placement efficiency across premium shelf tiers.</p>
              </div>
              <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
                <p className="font-bold text-white mb-1">Cross-Merchandising Lifts</p>
                <p className="text-[11px] text-slate-400">Identifies high-converting product pairings (+88% co-gaze lift).</p>
              </div>
            </>
          )}

          {activeRole === 'Marketing Manager' && (
            <>
              <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
                <p className="font-bold text-white mb-1">A/B Visual Saliency Comparison</p>
                <p className="text-[11px] text-slate-400">Measures visual campaign effectiveness between Display A and B.</p>
              </div>
              <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
                <p className="font-bold text-white mb-1">Demographic Attention Scores</p>
                <p className="text-[11px] text-slate-400">Aligns visual display content with target buyer age demographics.</p>
              </div>
              <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
                <p className="font-bold text-white mb-1">Promo Engagement Rates</p>
                <p className="text-[11px] text-slate-400">Calculates banner conversion metrics and average gaze duration.</p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* 1. STORE MANAGER DASHBOARD MODULE */}
      {activeRole === 'Store Manager' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-slate-800 border border-slate-700 rounded-2xl p-6">
              <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
                <Eye className="w-5 h-5 text-blue-400" /> Floor Shelf Spatial Heatmap
              </h2>
              <div className="grid grid-cols-3 gap-4 h-48">
                <div className="bg-rose-950/40 border border-rose-500/50 rounded-xl p-4 flex flex-col justify-between">
                  <div>
                    <span className="text-[10px] text-rose-400 font-bold uppercase">Zone A (Eye Level)</span>
                    <p className="text-xl font-extrabold text-white mt-1">94% Attention</p>
                  </div>
                  <span className="text-[11px] text-rose-300">High Footfall Density</span>
                </div>
                <div className="bg-amber-950/40 border border-amber-500/50 rounded-xl p-4 flex flex-col justify-between">
                  <div>
                    <span className="text-[10px] text-amber-400 font-bold uppercase">Zone B (Touch Level)</span>
                    <p className="text-xl font-extrabold text-white mt-1">62% Attention</p>
                  </div>
                  <span className="text-[11px] text-amber-300">Moderate Engagement</span>
                </div>
                <div className="bg-slate-900 border border-slate-700 rounded-xl p-4 flex flex-col justify-between">
                  <div>
                    <span className="text-[10px] text-slate-400 font-bold uppercase">Zone C (Bottom Tier)</span>
                    <p className="text-xl font-extrabold text-white mt-1">18% Attention</p>
                  </div>
                  <span className="text-[11px] text-slate-500">Low Visual Interaction</span>
                </div>
              </div>
            </div>

            <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6">
              <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-400" /> Operational & Restock Alerts
              </h2>
              <div className="space-y-3">
                <div className="p-3 bg-amber-500/10 border-l-4 border-amber-500 text-amber-200 text-xs rounded-xl">
                  <p className="font-semibold">Wireless Headphones Low Stock</p>
                  <p className="text-[11px] text-amber-300/80 mt-0.5">High gaze duration (24.1s) but stock level under 5 units.</p>
                </div>
                <div className="p-3 bg-blue-500/10 border-l-4 border-blue-500 text-blue-200 text-xs rounded-xl">
                  <p className="font-semibold">Misplaced Display Item</p>
                  <p className="text-[11px] text-blue-300/80 mt-0.5">Dark Chocolate registered 40+ gazes in Electronics section.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6">
            <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-emerald-400" /> Hourly Store Dwell & Traffic Metrics
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
              {HOURLY_DATA.map((h, i) => (
                <div key={i} className="bg-slate-900 border border-slate-700 p-4 rounded-xl text-center">
                  <span className="text-xs text-slate-400 block mb-1">{h.hour}</span>
                  <p className="text-lg font-bold text-white">{h.footfall} <span className="text-[10px] text-slate-400 font-normal">visitors</span></p>
                  <span className="text-[11px] text-emerald-400 font-medium block mt-1">{h.avgDwell} dwell</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 2. RETAIL ANALYST DASHBOARD MODULE */}
      {activeRole === 'Retail Analyst' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-slate-800 border border-slate-700 rounded-2xl p-6">
              <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-400" /> Product Attractiveness & Conversion Matrix
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-900 uppercase text-[10px] text-slate-400">
                    <tr>
                      <th className="p-3">Product Name</th>
                      <th className="p-3">Shelf Placement</th>
                      <th className="p-3">Gaze Count</th>
                      <th className="p-3">Attractiveness Score</th>
                      <th className="p-3">Recommended Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {PRODUCTS_ANALYTICS.map((p) => (
                      <tr key={p.id}>
                        <td className="p-3 font-medium text-white">{p.name}</td>
                        <td className="p-3">{p.shelfZone}</td>
                        <td className="p-3 font-mono">{p.gazeCount}</td>
                        <td className="p-3 font-bold text-blue-400">{p.attractiveness} / 100</td>
                        <td className="p-3 text-emerald-400 font-semibold">{p.action}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6">
              <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
                <ShoppingBag className="w-5 h-5 text-purple-400" /> Cross-Merchandising Insights
              </h2>
              <div className="space-y-4">
                <div className="bg-slate-900 p-3.5 rounded-xl border border-slate-700">
                  <div className="flex justify-between items-center text-xs mb-1">
                    <span className="font-semibold text-white">Watch + Leather Belts</span>
                    <span className="text-purple-400 font-bold">88% Lift</span>
                  </div>
                  <p className="text-[11px] text-slate-400">High co-gaze overlap during 03:00 PM peak hours.</p>
                </div>
                <div className="bg-slate-900 p-3.5 rounded-xl border border-slate-700">
                  <div className="flex justify-between items-center text-xs mb-1">
                    <span className="font-semibold text-white">Juice + Energy Snacks</span>
                    <span className="text-purple-400 font-bold">64% Lift</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Placing snacks next to beverages increases juice checkout by 18%.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3. MARKETING MANAGER DASHBOARD MODULE */}
      {activeRole === 'Marketing Manager' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 bg-slate-800 border border-slate-700 rounded-2xl p-6">
              <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-400" /> Marketing Display A/B Saliency Test
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-slate-900 p-5 rounded-xl border border-slate-700">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400 font-bold uppercase">Display Variant A (Neon Header)</span>
                    <span className="text-xs text-emerald-400 font-bold">+24% Attention</span>
                  </div>
                  <p className="text-3xl font-extrabold text-white mt-2">78.4%</p>
                  <p className="text-[11px] text-slate-400 mt-2">Average gaze duration: 18.2s per visitor.</p>
                </div>

                <div className="bg-slate-900 p-5 rounded-xl border border-slate-700">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-slate-400 font-bold uppercase">Display Variant B (Standard)</span>
                    <span className="text-xs text-rose-400 font-bold">-8% Attention</span>
                  </div>
                  <p className="text-3xl font-extrabold text-white mt-2">52.1%</p>
                  <p className="text-[11px] text-slate-400 mt-2">Average gaze duration: 9.4s per visitor.</p>
                </div>
              </div>
            </div>

            <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6">
              <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-400" /> Demographics Attention Score
              </h2>
              <div className="space-y-3">
                <div className="bg-slate-900 p-3 rounded-xl border border-slate-700 flex justify-between items-center">
                  <span className="text-xs text-slate-300">Age 18 - 28 (Tech Display)</span>
                  <span className="text-xs font-bold text-blue-400">92 Score</span>
                </div>
                <div className="bg-slate-900 p-3 rounded-xl border border-slate-700 flex justify-between items-center">
                  <span className="text-xs text-slate-300">Age 29 - 45 (Watch Display)</span>
                  <span className="text-xs font-bold text-emerald-400">88 Score</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function AppContent() {
  const { user } = useAuth();
  if (!user) return <AuthModal />;
  return <MainDashboard />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}