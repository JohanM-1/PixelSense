import React, { useState } from 'react';
import { CheckCircle, XCircle, Clock, ArrowRight, X } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

export default function ComparisonView({ suiteId, suiteData }) {
  const [selectedImage, setSelectedImage] = useState(null);

  if (!suiteData) return (
    <div className="flex flex-col items-center justify-center h-64 text-gray-500">
      <Clock className="animate-spin mb-4" size={32} />
      <p>Running test suite...</p>
    </div>
  );

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Results: {suiteId}</h2>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
        {suiteData.map((result, index) => (
          <div key={index} className="glass rounded-xl overflow-hidden border border-gray-200 dark:border-gray-800 flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-lg">{result.config_name}</h3>
                <span className="text-xs font-mono text-gray-500 uppercase">{result.model}</span>
              </div>
              <div className={`px-2 py-1 rounded text-xs font-bold ${
                result.status === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              }`}>
                {result.status.toUpperCase()}
              </div>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4 flex-1">
              {/* Image Result */}
              {result.image_url && (
                <div className="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 bg-black/5 relative group">
                  <img 
                    src={`${API_BASE_URL}${result.image_url}`} 
                    alt="Result" 
                    className="w-full object-contain cursor-pointer"
                    onClick={() => setSelectedImage(`${API_BASE_URL}${result.image_url}`)}
                  />
                  <button
                    onClick={() => setSelectedImage(`${API_BASE_URL}${result.image_url}`)}
                    className="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    View Full
                  </button>
                </div>
              )}

              {/* Actions List */}
              <div>
                <h4 className="text-sm font-semibold mb-2 text-gray-600 dark:text-gray-400 uppercase">Generated Actions</h4>
                <div className="space-y-2">
                  {result.actions?.map((action, i) => (
                    <div key={i} className="bg-gray-50 dark:bg-gray-800 p-3 rounded-lg border border-gray-100 dark:border-gray-700 text-sm">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 px-1.5 py-0.5 rounded text-xs font-bold uppercase">
                          {action.action}
                        </span>
                        {action.description && <span className="text-gray-600 dark:text-gray-300">{action.description}</span>}
                      </div>
                      <div className="font-mono text-xs text-gray-500">
                        {action.bbox ? `BBox: [${action.bbox.join(', ')}]` : ''}
                        {action.start_bbox ? `Start: [${action.start_bbox.join(', ')}]` : ''}
                        {action.end_bbox ? ` ➝ End: [${action.end_bbox.join(', ')}]` : ''}
                      </div>
                    </div>
                  ))}
                  {(!result.actions || result.actions.length === 0) && (
                    <p className="text-sm text-gray-400 italic">No actions generated.</p>
                  )}
                </div>
              </div>
            </div>

            {/* Raw JSON Toggle */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50">
               <details>
                 <summary className="text-xs font-mono cursor-pointer text-gray-500 hover:text-blue-500">View Raw Response</summary>
                 <pre className="mt-2 text-xs overflow-x-auto p-2 bg-gray-100 dark:bg-black rounded text-gray-700 dark:text-gray-300">
                   {result.raw_response}
                 </pre>
               </details>
            </div>
          </div>
        ))}
      </div>

      {/* Image Modal */}
      {selectedImage && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setSelectedImage(null)}
        >
          <div className="relative max-w-7xl max-h-[90vh] w-full h-full flex items-center justify-center">
            <img 
              src={selectedImage} 
              alt="Full view" 
              className="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
            />
            <button 
              onClick={() => setSelectedImage(null)}
              className="absolute top-4 right-4 bg-white/10 hover:bg-white/20 text-white p-2 rounded-full transition-colors"
            >
              <X size={24} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
