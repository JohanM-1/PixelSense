import React, { useEffect, useRef } from 'react';
import { Terminal, Check, AlertTriangle, Clock } from 'lucide-react';

export default function LogViewer({ logs }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="glass-panel flex flex-col h-[500px] text-gray-900 dark:text-gray-100 transition-colors duration-300">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <h3 className="font-semibold flex items-center gap-2 text-gray-900 dark:text-gray-100">
          <Terminal size={18} />
          <span>Analysis Logs</span>
        </h3>
        <span className="text-xs text-gray-500 dark:text-gray-400">{logs.length} entries</span>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-sm">
        {logs.length === 0 && (
          <div className="text-gray-500 dark:text-gray-400 text-center mt-20">
            Waiting for analysis to start...
          </div>
        )}
        
        {logs.map((log, idx) => (
          <LogItem key={idx} log={log} />
        ))}
        <div ref={endRef} />
      </div>
    </div>
  );
}

function LogItem({ log }) {
  if (log.type === 'info') {
    return (
      <div className="text-blue-600 dark:text-blue-400 flex gap-2">
        <span className="opacity-50">ℹ</span>
        <span>{log.message}</span>
      </div>
    );
  }

  if (log.type === 'status') {
    return (
      <div className="text-gray-600 dark:text-gray-400 italic flex gap-2">
        <span className="opacity-50">…</span>
        <span>{log.message}</span>
      </div>
    );
  }

  if (log.type === 'segment_start') {
    return (
      <div className="border-t border-gray-100 dark:border-gray-800 pt-2 mt-2">
        <div className="flex items-center gap-2 text-gray-900 dark:text-gray-100 font-bold">
          <Clock size={14} />
          <span>Processing Segment {log.segment_index + 1}/{log.total_segments}</span>
          <span className="text-xs font-normal opacity-60">({log.start.toFixed(1)}s - {log.end.toFixed(1)}s)</span>
        </div>
      </div>
    );
  }

  if (log.type === 'segment_complete') {
    const events = log.result.events || [];
    return (
      <div className="pl-4 border-l-2 border-green-500/30 space-y-1">
        <div className="text-green-600 dark:text-green-400 flex items-center gap-2">
          <Check size={14} />
          <span>Segment Complete: {events.length} events found</span>
        </div>
        {events.length > 0 && (
          <div className="text-xs text-gray-900 dark:text-gray-100 bg-gray-50 dark:bg-gray-800/50 p-2 rounded">
            {events.map((e, i) => (
              <div key={i} className="truncate">
                • {e.timestamp} - {e.action} ({e.skill_used?.key || 'No Key'})
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (log.type === 'error') {
    return (
      <div className="text-red-600 bg-red-50 dark:bg-red-900/20 p-2 rounded flex items-start gap-2">
        <AlertTriangle size={16} className="mt-0.5" />
        <span>{log.message}</span>
      </div>
    );
  }

  return <div className="text-gray-500 dark:text-gray-400">{JSON.stringify(log)}</div>;
}
