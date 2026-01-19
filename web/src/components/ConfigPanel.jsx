import React, { useState, useEffect } from 'react';
import { Save, RefreshCw, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';

export default function ConfigPanel() {
  const [config, setConfig] = useState({
    system_prompt: '',
    user_prompt: '',
    detail: 'medium',
    model_name: '',
    available_models: [],
    assistant: {
        provider: 'gemini',
        api_key: 'AIzaSyD2IVLNXYGVisQ78T1PaRyI0G2NpSszva0',
        base_url: 'https://generativelanguage.googleapis.com/v1beta/openai/',
        model: 'gemini-3-flash-preview'
    }
  });
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [refining, setRefining] = useState(null); // 'system' or 'user' or null
  const [showAssistant, setShowAssistant] = useState(false);

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/config');
      const data = await res.json();
      setConfig(prev => ({...prev, ...data})); // Merge to keep defaults if missing
    } catch (err) {
      console.error("Failed to fetch config", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch('http://localhost:8000/api/v1/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      // Could show toast here
    } catch (err) {
      console.error("Failed to save config", err);
    } finally {
      setSaving(false);
    }
  };

  const handleRefine = async (type) => {
    if (!config.assistant?.api_key) {
        alert("Please configure the AI Assistant API Key first.");
        setShowAssistant(true);
        return;
    }
    
    setRefining(type);
    try {
        const prompt = type === 'system' ? config.system_prompt : config.user_prompt;
        const res = await fetch('http://localhost:8000/api/v1/tools/refine-prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, type })
        });
        
        if (!res.ok) throw new Error(await res.text());
        
        const data = await res.json();
        if (type === 'system') {
            setConfig(prev => ({...prev, system_prompt: data.refined_prompt}));
        } else {
            setConfig(prev => ({...prev, user_prompt: data.refined_prompt}));
        }
    } catch (err) {
        console.error("Failed to refine prompt", err);
        alert("Failed to refine prompt: " + err.message);
    } finally {
        setRefining(null);
    }
  };

  return (
    <div className="glass-panel p-4 md:p-6 space-y-6 text-gray-900 dark:text-gray-100 transition-colors duration-300">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 md:gap-0">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">Configuration</h2>
        <div className="flex space-x-2 w-full md:w-auto">
          <button 
            onClick={fetchConfig}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-gray-600 dark:text-gray-400"
          >
            <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
          </button>
          <button 
            onClick={handleSave}
            disabled={saving}
            className="flex-1 md:flex-none justify-center flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
          >
            <Save size={18} />
            <span>{saving ? 'Saving...' : 'Save Changes'}</span>
          </button>
        </div>
      </div>

      {/* AI Assistant Configuration */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
        <button 
            onClick={() => setShowAssistant(!showAssistant)}
            className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
            <div className="flex items-center gap-2 font-semibold">
                <Sparkles size={18} className="text-purple-500" />
                <span>AI Assistant Settings (Prompt Editor)</span>
            </div>
            {showAssistant ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
        
        {showAssistant && (
            <div className="p-4 space-y-4 bg-white dark:bg-gray-900/50">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">Provider</label>
                        <select 
                            value={config.assistant?.provider || 'gemini'}
                            onChange={(e) => setConfig({...config, assistant: {...config.assistant, provider: e.target.value}})}
                            className="w-full p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-purple-500 outline-none"
                        >
                            <option value="gemini">Google Gemini</option>
                            <option value="openai">OpenAI / Kilo Code / Compatible</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">Model Name</label>
                        <input 
                            type="text"
                            value={config.assistant?.model || 'gemini-1.5-flash-8b'}
                            onChange={(e) => setConfig({...config, assistant: {...config.assistant, model: e.target.value}})}
                            className="w-full p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-purple-500 outline-none"
                            placeholder="e.g. gemini-1.5-flash-8b"
                        />
                    </div>
                </div>
                <div>
                    <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">API Key</label>
                    <input 
                        type="password"
                        value={config.assistant?.api_key || ''}
                        onChange={(e) => setConfig({...config, assistant: {...config.assistant, api_key: e.target.value}})}
                        className="w-full p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-purple-500 outline-none"
                        placeholder="Enter your API Key"
                    />
                </div>
                <div>
                    <label className="block text-sm font-medium mb-1 text-gray-700 dark:text-gray-300">Base URL (Optional)</label>
                    <input 
                        type="text"
                        value={config.assistant?.base_url || ''}
                        onChange={(e) => setConfig({...config, assistant: {...config.assistant, base_url: e.target.value}})}
                        className="w-full p-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-purple-500 outline-none"
                        placeholder="https://generativelanguage.googleapis.com/v1beta/openai/"
                    />
                </div>
            </div>
        )}
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2 text-gray-900 dark:text-gray-300">Vision Model (Analysis)</label>
          <select 
            value={config.model_name || ''}
            onChange={(e) => setConfig({...config, model_name: e.target.value})}
            className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/50 focus:ring-2 focus:ring-blue-500 outline-none transition-all text-gray-900 dark:text-gray-100 appearance-none"
            style={{ backgroundImage: 'none' }}
          >
            {config.available_models && config.available_models.map((model) => (
                <option key={model.id} value={model.id} className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
                    {model.name} {model.type.includes('api') ? '(Cloud API)' : '(Local GPU)'}
                </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {config.model_name && config.model_name.includes('api') 
                ? "Uses external API. Requires API Key in Assistant Settings." 
                : "Runs locally. Requires CUDA GPU with sufficient VRAM."}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2 text-gray-900 dark:text-gray-300">Analysis Detail Level</label>
          <select 
            value={config.detail}
            onChange={(e) => setConfig({...config, detail: e.target.value})}
            className="w-full p-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/50 focus:ring-2 focus:ring-blue-500 outline-none transition-all text-gray-900 dark:text-gray-100 appearance-none"
            style={{ backgroundImage: 'none' }}
          >
            <option value="low" className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">Low (Fast)</option>
            <option value="medium" className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">Medium (Balanced)</option>
            <option value="high" className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">High (Detailed)</option>
            <option value="max" className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">Max (Frame-by-Frame)</option>
          </select>
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-300">System Prompt</label>
            <button 
                onClick={() => handleRefine('system')}
                disabled={refining === 'system'}
                className="flex items-center gap-1 text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded-md hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors"
                title="Refine with AI Assistant"
            >
                <Sparkles size={12} className={refining === 'system' ? "animate-spin" : ""} />
                {refining === 'system' ? 'Refining...' : 'Refine with AI'}
            </button>
          </div>
          <textarea 
            value={config.system_prompt}
            onChange={(e) => setConfig({...config, system_prompt: e.target.value})}
            className="w-full h-64 p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/50 font-mono text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all resize-y text-gray-900 dark:text-gray-100"
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="block text-sm font-medium text-gray-900 dark:text-gray-300">User Prompt Template</label>
            <button 
                onClick={() => handleRefine('user')}
                disabled={refining === 'user'}
                className="flex items-center gap-1 text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded-md hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors"
                title="Refine with AI Assistant"
            >
                <Sparkles size={12} className={refining === 'user' ? "animate-spin" : ""} />
                {refining === 'user' ? 'Refining...' : 'Refine with AI'}
            </button>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">The instruction sent for each segment. Use {'{start_time}'} and {'{end_time}'} placeholders.</p>
          <textarea 
            value={config.user_prompt}
            onChange={(e) => setConfig({...config, user_prompt: e.target.value})}
            className="w-full h-24 p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/50 font-mono text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all resize-y text-gray-900 dark:text-gray-100"
          />
        </div>
      </div>
    </div>
  );
}
