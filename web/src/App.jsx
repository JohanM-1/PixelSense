import React, { useState } from 'react';
import Layout from './components/Layout';
import ConfigPanel from './components/ConfigPanel';
import AnalysisView from './components/AnalysisView';
import SystemLogViewer from './components/SystemLogViewer';
import GroundingLayout from './components/grounding/GroundingLayout';
import { ThemeProvider } from './context/ThemeContext';

function AppContent() {
  const [activeTab, setActiveTab] = useState('analysis');
  
  // State lifted from AnalysisView to preserve progress
  const [analysisState, setAnalysisState] = useState({
    step: 'upload',
    filename: null,
    roi: null,
    logs: [],
    isAnalyzing: false,
    result: null
  });

  return (
    <Layout activeTab={activeTab} onTabChange={setActiveTab}>
      <div className={activeTab === 'analysis' ? 'block' : 'hidden'}>
        <AnalysisView state={analysisState} setState={setAnalysisState} />
      </div>
      <div className={activeTab === 'grounding' ? 'block' : 'hidden'}>
        <GroundingLayout />
      </div>
      <div className={activeTab === 'settings' ? 'block' : 'hidden'}>
        <ConfigPanel />
      </div>
      <div className={activeTab === 'logs' ? 'block' : 'hidden'}>
        <SystemLogViewer mode="embedded" />
      </div>
      {activeTab !== 'logs' && <SystemLogViewer />}
    </Layout>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
