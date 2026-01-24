import React, { useState } from 'react';
import { Play, Save, CheckCircle, Tag, Loader, Edit2, X } from 'lucide-react';
import VideoUploader from '../VideoUploader';
import AnnotationCanvas from './AnnotationCanvas';

const API_BASE = 'http://localhost:8000/api/v1';

export default function LabelingWorkspace() {
  const [step, setStep] = useState('upload'); // upload, labeling
  const [jobId, setJobId] = useState(null);
  const [frames, setFrames] = useState([]); // List of image URLs
  const [labels, setLabels] = useState({}); // { frame_filename: [ {x,y,w,h,label} ] }
  const [loading, setLoading] = useState(false);
  const [selectedFrame, setSelectedFrame] = useState(null); // URL of frame being edited

  const handleUploadComplete = async (filename) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/labeling/init`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, num_frames: 100 })
      });
      if (!res.ok) throw new Error('Init failed');
      const data = await res.json();
      setJobId(data.job_id);
      setFrames(data.frames);
      setStep('labeling');
    } catch (err) {
      console.error(err);
      alert("Failed to initialize labeling job");
    } finally {
      setLoading(false);
    }
  };

  const openLabelModal = (frameUrl) => {
    setSelectedFrame(frameUrl);
  };

  const handleAnnotationSave = (annotations) => {
    const filename = selectedFrame.split('/').pop();
    setLabels(prev => ({ ...prev, [filename]: annotations }));
    setSelectedFrame(null);
  };

  const runAutoLabel = async (testSingle = false) => {
    const labeledCount = Object.keys(labels).length;
    if (labeledCount < 1) {
        alert("Please label at least 1 frame as an example first.");
        return;
    }

    setLoading(true);
    try {
      const allFrameNames = frames.map(url => url.split('/').pop());
      // Targets are all frames NOT in labels
      let targets = allFrameNames.filter(fname => !labels[fname]);
      let isRelabeling = false;
        
      if (targets.length === 0) {
          if (testSingle) {
              // Pick the last frame to re-test, but ensure we have at least one OTHER frame as example
              const lastFrame = allFrameNames[allFrameNames.length - 1];
              targets = [lastFrame];
              isRelabeling = true;
              
              const potentialExamples = labeledCount - (labels[lastFrame] ? 1 : 0);
              if (potentialExamples < 1) {
                  alert("Cannot re-test: You need at least one other labeled frame to serve as an example.");
                  setLoading(false);
                  return;
              }
          } else {
             alert("All frames are already labeled!");
             setLoading(false);
             return;
          }
      }

      if (testSingle && !isRelabeling) {
          // Just take the first target for testing
          targets = [targets[0]];
      }

      // Prepare examples: All labeled frames EXCEPT the ones we are about to predict
      const examples = Object.entries(labels)
        .filter(([frame, _]) => !targets.includes(frame))
        .map(([frame, boxes]) => ({ frame, boxes }));

      const res = await fetch(`${API_BASE}/labeling/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, examples, targets })
      });
      if (!res.ok) throw new Error('Prediction failed');
      const data = await res.json();
      
      const newLabels = { ...labels };
      data.predictions.forEach(p => {
        newLabels[p.frame] = p.boxes;
      });
      setLabels(newLabels);
      if (testSingle) {
          const testedFrame = data.predictions[0]?.frame;
          const testedFrameUrl = frames.find(url => url.endsWith(testedFrame));
          if (testedFrameUrl) {
             openLabelModal(testedFrameUrl);
          }
      } else {
          alert(`Auto-labeled ${data.predictions.length} frames!`);
      }
    } catch (err) {
      console.error(err);
      alert("Auto-labeling failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const saveDataset = async () => {
    setLoading(true);
    try {
      const labelList = Object.entries(labels).map(([frame, boxes]) => ({ frame, boxes }));
      const res = await fetch(`${API_BASE}/labeling/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, labels: labelList })
      });
      if (!res.ok) throw new Error('Save failed');
      alert("Dataset saved successfully!");
    } catch (err) {
      console.error(err);
      alert("Failed to save");
    } finally {
      setLoading(false);
    }
  };

  const getLabelSummary = (url) => {
      const fname = url.split('/').pop();
      const boxes = labels[fname];
      if (!boxes || boxes.length === 0) return null;
      return `${boxes.length} box(es)`;
  };

  return (
    <div className="p-6 h-full overflow-auto">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">AI Labeling Assistant</h1>
          <p className="text-gray-500">Extract frames, label a few, and let AI do the rest.</p>
        </div>
        {step === 'labeling' && (
            <div className="flex gap-2">
                <button 
                    onClick={() => runAutoLabel(true)}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
                    title="Test on 1 frame first"
                >
                    {loading ? <Loader className="animate-spin" size={18} /> : <Play size={18} />}
                    Test (1 Frame)
                </button>
                <button 
                    onClick={() => runAutoLabel(false)}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg disabled:opacity-50"
                >
                    {loading ? <Loader className="animate-spin" size={18} /> : <Play size={18} />}
                    Auto-Label Remaining
                </button>
                <button 
                    onClick={saveDataset}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg disabled:opacity-50"
                >
                    <Save size={18} />
                    Save Dataset
                </button>
            </div>
        )}
      </div>

      {step === 'upload' && (
        <div className="max-w-2xl mx-auto mt-10">
            {loading ? (
                <div className="text-center py-20">
                    <Loader className="animate-spin mx-auto text-blue-500 mb-4" size={48} />
                    <p className="text-lg text-gray-600">Extracting frames from video...</p>
                </div>
            ) : (
                <VideoUploader onUploadComplete={handleUploadComplete} />
            )}
        </div>
      )}

      {step === 'labeling' && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {frames.map((url, idx) => {
                const summary = getLabelSummary(url);
                return (
                    <div 
                        key={idx} 
                        className={`relative group rounded-lg overflow-hidden border-2 cursor-pointer transition-all
                            ${summary ? 'border-green-500' : 'border-gray-200 dark:border-gray-700 hover:border-blue-400'}
                        `}
                        onClick={() => openLabelModal(url)}
                    >
                        <img 
                            src={`http://localhost:8000${url}`} 
                            alt={`Frame ${idx}`} 
                            className="w-full h-32 object-cover"
                        />
                        <div className="absolute top-1 right-1">
                            {summary && <div className="bg-green-500 text-white p-1 rounded-full"><CheckCircle size={14} /></div>}
                        </div>
                        {summary && (
                            <div className="absolute bottom-0 left-0 right-0 bg-black/70 text-white text-xs p-1 text-center truncate">
                                {summary}
                            </div>
                        )}
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
                    </div>
                );
            })}
        </div>
      )}

      {/* Labeling Modal */}
      {selectedFrame && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-white dark:bg-gray-800 rounded-2xl max-w-5xl w-full h-[80vh] shadow-2xl overflow-hidden flex flex-col">
                <div className="p-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-900">
                    <h3 className="text-lg font-bold">Annotate Frame</h3>
                    <button onClick={() => setSelectedFrame(null)} className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full"><X size={20} /></button>
                </div>
                
                <div className="flex-1 p-6 overflow-hidden bg-gray-100 dark:bg-gray-900/50">
                    <AnnotationCanvas 
                        image={`http://localhost:8000${selectedFrame}`}
                        onSave={handleAnnotationSave}
                    />
                </div>
            </div>
        </div>
      )}
    </div>
  );
}
