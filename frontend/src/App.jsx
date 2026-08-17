import React from 'react';
import ShelfHeatmap from './components/ShelfHeatmap';
import AttractivenessLeaderboard from './components/AttractivenessLeaderboard';
import { Download, LayoutDashboard } from 'lucide-react';

function App() {
  const handleDownloadPDF = () => {
    window.open('http://127.0.0.1:8000/api/analytics/export/pdf', '_blank');
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      {/* Header Bar */}
      <header className="flex justify-between items-center mb-8 bg-white p-6 rounded-xl shadow-sm">
        <div className="flex items-center gap-3">
          <LayoutDashboard className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Consumer Attention Mapping Dashboard</h1>
            <p className="text-sm text-gray-500">Real-time shelf analytics and consumer behavior tracking</p>
          </div>
        </div>

        <button
          onClick={handleDownloadPDF}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg font-medium shadow-sm transition-all"
        >
          <Download className="w-4 h-4" /> Download PDF Report
        </button>
      </header>

      {/* Main Grid View */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <ShelfHeatmap />
        <AttractivenessLeaderboard />
      </div>
    </div>
  );
}

export default App;