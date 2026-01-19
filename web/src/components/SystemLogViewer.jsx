import React, { useEffect, useState, useRef } from 'react';
import { Terminal, X, Minimize2, Maximize2 } from 'lucide-react';

export default function SystemLogViewer({ mode = 'floating' }) {
  const [logs, setLogs] = useState([]);
  const [isOpen, setIsOpen] = useState(false); // Collapsed by default
  const endRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    // Connect to system logs websocket
    const ws = new WebSocket('ws://localhost:8000/api/v1/ws/logs');
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('Connected to system logs');
    };

    ws.onmessage = (event) => {
      const message = event.data;
      setLogs(prev => [...prev.slice(-200), message]); // Keep last 200 logs
      
      // Auto-open on model loading events (only in floating mode)
      if (mode === 'floating' && (message.includes("Loading model") || message.includes("Downloading"))) {
        setIsOpen(true);
      }
    };

    return () => {
      ws.close();
    };
  }, [mode]);

  useEffect(() => {
    if (isOpen || mode === 'embedded') {
      endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, isOpen, mode]);

  if (mode === 'embedded') {
    return (
      <div className="w-full h-[calc(100vh-8rem)] bg-black/90 text-white rounded-xl shadow-2xl overflow-hidden flex flex-col font-mono text-sm border border-gray-700">
        <div className="flex items-center justify-between p-4 bg-gray-800/50 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <Terminal size={18} className="text-green-400" />
            <span className="font-semibold text-lg">System Logs</span>
          </div>
          <button onClick={() => setLogs([])} className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs transition-colors">
            Clear Logs
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-1 font-mono">
          {logs.length === 0 && <div className="text-gray-500 italic">Waiting for logs...</div>}
          {logs.map((log, i) => (
            <div key={i} className="break-words leading-relaxed border-b border-white/5 pb-1 mb-1 last:border-0">
              <span className="text-gray-500 mr-3 select-none">[{new Date().toLocaleTimeString()}]</span>
              <span className={log.includes("ERROR") ? "text-red-400 font-bold" : (log.includes("INFO") ? "text-blue-300" : "text-gray-300")}>
                  {log}
              </span>
            </div>
          ))}
          <div ref={endRef} />
        </div>
      </div>
    );
  }

  if (!isOpen) {
    // Minimized state (floating button)
    return (
        <button 
            onClick={() => setIsOpen(true)}
            className="fixed bottom-4 right-4 z-50 bg-black/80 dark:bg-white/10 text-white p-3 rounded-full shadow-lg hover:scale-105 transition-transform"
            title="Show System Logs"
        >
            <Terminal size={20} />
        </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 w-96 max-w-[calc(100vw-2rem)] bg-black/90 text-white rounded-xl shadow-2xl overflow-hidden flex flex-col font-mono text-xs border border-gray-700">
      <div className="flex items-center justify-between p-3 bg-gray-800/50 border-b border-gray-700">
        <div className="flex items-center gap-2">
            <Terminal size={14} className="text-green-400" />
            <span className="font-semibold">System Logs</span>
        </div>
        <div className="flex items-center gap-2">
            <button onClick={() => setLogs([])} className="hover:text-red-400 text-[10px]">Clear</button>
            <button onClick={() => setIsOpen(false)} className="hover:text-gray-300">
                <Minimize2 size={14} />
            </button>
        </div>
      </div>
      
      <div className="h-64 overflow-y-auto p-3 space-y-1">
        {logs.length === 0 && <div className="text-gray-500 italic">Waiting for logs...</div>}
        {logs.map((log, i) => (
          <div key={i} className="break-words leading-tight">
            <span className="text-gray-500 mr-2">[{new Date().toLocaleTimeString()}]</span>
            <span className={log.includes("ERROR") ? "text-red-400" : (log.includes("INFO") ? "text-blue-300" : "text-gray-300")}>
                {log}
            </span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}
