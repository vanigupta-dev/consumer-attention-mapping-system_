import React, { useEffect, useState } from 'react';
import Plot from 'react-plotly.js';
import axios from 'axios';

const ShelfHeatmap = () => {
  const [heatmapData, setHeatmapData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHeatmap();
    const interval = setInterval(fetchHeatmap, 5000); // Auto-refresh every 5s
    return () => clearInterval(interval);
  }, []);

  const fetchHeatmap = async () => {
    try {
      const response = await axios.get('http://127.0.0.1:8000/api/analytics/heatmap');
      setHeatmapData(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching shelf heatmap:', error);
      setLoading(false);
    }
  };

  if (loading) return <div className="p-4">Loading Shelf Heatmap...</div>;
  if (!heatmapData) return <div className="p-4 text-red-500">Failed to load heatmap data.</div>;

  return (
    <div className="bg-white p-6 rounded-xl shadow-md">
      <h2 className="text-xl font-bold mb-2 text-gray-800">Shelf Attention Heatmap</h2>
      <p className="text-sm text-gray-500 mb-4">
        Average dwell duration (seconds) across a 5x8 shelf grid position.
      </p>

      <Plot
        data={[
          {
            z: heatmapData.heatmap_matrix,
            type: 'heatmap',
            colorscale: 'YlOrRd', // Yellow -> Orange -> Red per mentor spec[cite: 2]
            hoverongaps: false,
            colorbar: {
              title: 'Dwell (s)',
              titleside: 'right'
            }
          }
        ]}
        layout={{
          width: 700,
          height: 400,
          title: 'Shelf Dwell Time Density',
          xaxis: { title: 'Shelf Column (Left to Right)' },
          yaxis: { title: 'Shelf Row (Top to Bottom)', autorange: 'reversed' }
        }}
        config={{ responsive: true, displayModeBar: false }}
      />
    </div>
  );
};

export default ShelfHeatmap;