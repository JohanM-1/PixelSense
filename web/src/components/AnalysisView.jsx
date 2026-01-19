import React, { useState, useRef } from 'react';
import { Play, RotateCcw } from 'lucide-react';
import VideoUploader from './VideoUploader';
import ROISelector from './ROISelector';
import LogViewer from './LogViewer';

export default function AnalysisView({ state, setState }) {
  const { step, filename, roi, logs, isAnalyzing, result } = state;
  const wsRef = useRef(null);

  const updateState = (updates) => {
    setState(prev => ({ ...prev, ...updates }));
  };

  const handleUploadComplete = (file) => {
    updateState({ filename: file, step: 'roi' });
  };

  const handleROIConfirm = (selectedRoi) => {
    updateState({ roi: selectedRoi });
  };

  const startAnalysis = () => {
    updateState({ 
        step: 'analysis', 
        logs: [], 
        isAnalyzing: true, 
        result: null 
    });

    const ws = new WebSocket('ws://localhost:8000/api/v1/ws/analyze');
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({
        filename,
        roi
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'complete') {
        setState(prev => ({ 
            ...prev, 
            isAnalyzing: false, 
            result: data.result 
        }));
        ws.close();
      } else {
        setState(prev => ({ ...prev, logs: [...prev.logs, data] }));
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setState(prev => ({ 
          ...prev, 
          logs: [...prev.logs, { type: 'error', message: "Connection error" }],
          isAnalyzing: false 
      }));
    };
    
    ws.onclose = () => {
        setState(prev => ({ ...prev, isAnalyzing: false }));
    };
  };

  const reset = () => {
    updateState({
        step: 'upload',
        filename: null,
        roi: null,
        logs: [],
        result: null
    });
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header / Status */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-black dark:text-white">New Analysis</h2>
          <p className="text-black/60 dark:text-gray-400">Upload gameplay footage to extract events.</p>
        </div>
        {filename && (
          <button onClick={reset} className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-red-500 transition-colors">
            <RotateCcw size={16} /> Start Over
          </button>
        )}
      </div>

      {/* Step 1: Upload */}
      {step === 'upload' && (
        <VideoUploader onUploadComplete={handleUploadComplete} />
      )}

      {/* Step 2: ROI & Prep */}
      {step === 'roi' && (
        <div className="space-y-6">
          <ROISelector filename={filename} onConfirm={handleROIConfirm} />
          
          <div className="flex justify-end">
            <button 
              onClick={startAnalysis}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-semibold shadow-lg shadow-blue-500/30 flex items-center gap-2 transition-transform hover:scale-105 active:scale-95"
            >
              <Play fill="currentColor" />
              <span>Start Analysis</span>
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Analysis Logs */}
      {step === 'analysis' && (
        <div className="flex flex-col lg:grid lg:grid-cols-3 gap-6">
          <div className="order-2 lg:order-1 lg:col-span-2">
            <LogViewer logs={logs} />
          </div>
          <div className="order-1 lg:order-2 space-y-6">
             {/* Status Card */}
             <div className="glass-panel p-6">
                <h3 className="font-semibold mb-4 text-black dark:text-white">Status</h3>
                <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${isAnalyzing ? 'bg-green-500 animate-pulse' : (result ? 'bg-green-500' : 'bg-gray-300')}`} />
                    <span className="text-black dark:text-gray-200">
                        {isAnalyzing ? 'Analyzing Video...' : (result ? 'Analysis Complete' : 'Waiting for Start')}
                    </span>
                </div>
             </div>

             {/* Result Preview (Simple) */}
             {result && (
                 <div className="glass-panel p-6 bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-800">
                     <h3 className="font-semibold text-green-700 dark:text-green-400 mb-2">Analysis Complete!</h3>
                     <p className="text-sm text-black/70 dark:text-gray-400">
                         Processed {result.metrics?.processed_segments} segments.
                     </p>
                     
                     {/* JSON Preview Block */}
                     <div className="mt-4 mb-4 bg-white dark:bg-black/40 p-3 rounded-lg border border-green-100 dark:border-green-900/30 max-h-60 overflow-y-auto">
                        <pre className="text-xs font-mono text-black dark:text-green-300 whitespace-pre-wrap">
                            {JSON.stringify(result, null, 2)}
                        </pre>
                     </div>

                     <div className="mt-4">
                         <a 
                            href={`data:text/json;charset=utf-8,${encodeURIComponent(JSON.stringify(result, null, 2))}`}
                            download="analysis_result.json"
                            className="text-blue-600 hover:underline text-sm font-medium"
                         >
                             Download Full JSON Report
                         </a>
                     </div>
                 </div>
             )}
          </div>
        </div>
      )}
    </div>
  );
}
