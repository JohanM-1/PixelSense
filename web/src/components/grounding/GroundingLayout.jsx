import React, { useState } from 'react';
import ConfigBuilder from './ConfigBuilder';
import ComparisonView from './ComparisonView';

const API_BASE_URL = 'http://localhost:8000';

export default function GroundingLayout() {
  const [view, setView] = useState('config'); // config, running, results
  const [currentSuiteId, setCurrentSuiteId] = useState(null);
  const [suiteResults, setSuiteResults] = useState(null);

  const handleRunSuite = async (suiteConfig) => {
    setView('running');
    setSuiteResults(null); // Clear previous

    try {
      const response = await fetch(`${API_BASE_URL}/grounding/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(suiteConfig)
      });
      
      const data = await response.json();
      setCurrentSuiteId(data.suite_id);

      // Poll for results or fetch immediately since our backend is sync for now
      // In a real async backend, we would poll here.
      // Fetch details
      const detailsRes = await fetch(`${API_BASE_URL}/grounding/runs/${data.suite_id}`);
      const detailsData = await detailsRes.json();
      
      setSuiteResults(detailsData.configs);
      setView('results');
    } catch (error) {
      console.error("Execution failed", error);
      alert("Execution failed. Check console.");
      setView('config');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4 mb-6">
        <button 
          onClick={() => setView('config')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            view === 'config' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
          }`}
        >
          Configuration
        </button>
        {currentSuiteId && (
          <button 
            onClick={() => setView('results')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              view === 'results' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'
            }`}
          >
            Latest Results
          </button>
        )}
      </div>

      {view === 'config' && (
        <ConfigBuilder onRunSuite={handleRunSuite} />
      )}

      {(view === 'results' || view === 'running') && (
        <ComparisonView suiteId={currentSuiteId} suiteData={suiteResults} />
      )}
    </div>
  );
}
