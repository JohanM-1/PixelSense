import React, { useState, useEffect } from 'react';
import { Plus, Play, Copy, Trash, Save } from 'lucide-react';
import { useDropzone } from 'react-dropzone';

const API_BASE_URL = 'http://localhost:8000';

export default function ConfigBuilder({ onRunSuite }) {
  const [suiteName, setSuiteName] = useState('New Test Suite');
  const [configs, setConfigs] = useState([
    {
      id: 1,
      name: 'Qwen Baseline',
      model: 'qwen',
      prompt: "Mover la tarea 'MVP' de la columna 'Desarrollo' a 'Completado'",
      system_prompt: "",
      image_path: "",
      allowed_actions: ['click', 'drag'],
      refinement: false,
      prompt_template: ""
    }
  ]);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [schema, setSchema] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/grounding/config-schema`)
      .then(res => res.json())
      .then(data => setSchema(data))
      .catch(err => console.error("Failed to load schema", err));
  }, []);

  const onDrop = async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      setUploadedImage(data.filename);
      // Update all configs with this image for now (simplification)
      setConfigs(prev => prev.map(c => ({ ...c, image_path: data.filename })));
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': [] },
    multiple: false
  });

  const addConfig = () => {
    const newId = Math.max(...configs.map(c => c.id)) + 1;
    setConfigs([...configs, {
      ...configs[0],
      id: newId,
      name: `Config ${newId}`,
    }]);
  };

  const updateConfig = (id, field, value) => {
    setConfigs(configs.map(c => c.id === id ? { ...c, [field]: value } : c));
  };

  const removeConfig = (id) => {
    if (configs.length > 1) {
      setConfigs(configs.filter(c => c.id !== id));
    }
  };

  const handleRun = () => {
    if (!uploadedImage) {
      alert("Please upload an image first.");
      return;
    }
    onRunSuite({
      suite_name: suiteName,
      configs: configs
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <input
            type="text"
            value={suiteName}
            onChange={(e) => setSuiteName(e.target.value)}
            className="text-2xl font-bold bg-transparent border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none px-2 py-1"
          />
        </div>
        <button
          onClick={handleRun}
          className="flex items-center space-x-2 bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg transition-colors font-medium shadow-lg shadow-green-600/20"
        >
          <Play size={20} />
          <span>Run Suite</span>
        </button>
      </div>

      {/* Image Upload */}
      <div 
        {...getRootProps()} 
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-700 hover:border-gray-400'
        }`}
      >
        <input {...getInputProps()} />
        {uploadedImage ? (
          <div className="flex flex-col items-center">
            <p className="text-green-600 font-medium mb-2">Image uploaded: {uploadedImage}</p>
            <img 
              src={`${API_BASE_URL}/uploads/${uploadedImage}`} 
              alt="Test Target" 
              className="max-h-48 rounded-lg shadow-md"
            />
          </div>
        ) : (
          <div className="text-gray-500">
            <p className="font-medium">Drag & drop a UI screenshot here</p>
            <p className="text-sm mt-1">or click to select file</p>
          </div>
        )}
      </div>

      {/* Config Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {configs.map((config, index) => (
          <div key={config.id} className="glass p-6 rounded-xl border border-gray-200 dark:border-gray-800 relative group">
            <div className="absolute top-4 right-4 flex space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <button onClick={() => removeConfig(config.id)} className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg">
                <Trash size={16} />
              </button>
            </div>

            <div className="space-y-4">
              <input
                type="text"
                value={config.name}
                onChange={(e) => updateConfig(config.id, 'name', e.target.value)}
                className="font-bold text-lg w-full bg-transparent border-b border-gray-200 dark:border-gray-700 focus:border-blue-500 outline-none pb-1"
                placeholder="Config Name"
              />

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Model</label>
                  <select
                    value={config.model}
                    onChange={(e) => updateConfig(config.id, 'model', e.target.value)}
                    className="w-full bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm"
                  >
                    {schema?.models?.map(m => (
                      <option key={m} value={m}>{m.toUpperCase()}</option>
                    ))}
                  </select>
                </div>
                <div className="flex items-end">
                   <label className="flex items-center space-x-2 cursor-pointer">
                      <input 
                        type="checkbox" 
                        checked={config.refinement}
                        onChange={(e) => updateConfig(config.id, 'refinement', e.target.checked)}
                        className="form-checkbox h-4 w-4 text-blue-600"
                      />
                      <span className="text-sm font-medium">Gemini Refinement</span>
                   </label>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase mb-1">User Prompt</label>
                <textarea
                  value={config.prompt}
                  onChange={(e) => updateConfig(config.id, 'prompt', e.target.value)}
                  className="w-full h-20 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm resize-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase mb-1">Allowed Actions</label>
                <div className="flex flex-wrap gap-2">
                  {schema?.default_actions?.map(action => (
                    <button
                      key={action}
                      onClick={() => {
                        const current = config.allowed_actions;
                        const next = current.includes(action) 
                          ? current.filter(a => a !== action)
                          : [...current, action];
                        updateConfig(config.id, 'allowed_actions', next);
                      }}
                      className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                        config.allowed_actions.includes(action)
                          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                          : 'bg-gray-100 text-gray-500 dark:bg-gray-800'
                      }`}
                    >
                      {action}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
        
        {/* Add Button */}
        <button
          onClick={addConfig}
          className="flex flex-col items-center justify-center p-6 rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-800 text-gray-400 hover:border-blue-500 hover:text-blue-500 transition-colors h-full min-h-[300px]"
        >
          <Plus size={32} />
          <span className="mt-2 font-medium">Add Configuration</span>
        </button>
      </div>
    </div>
  );
}
