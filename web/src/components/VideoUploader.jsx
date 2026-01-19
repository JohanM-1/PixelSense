import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, FileVideo, CheckCircle, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';

export default function VideoUploader({ onUploadComplete }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setUploading(true);
    setProgress(0);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', 'http://localhost:8000/api/v1/upload', true);

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percentComplete = (event.loaded / event.total) * 100;
          setProgress(percentComplete);
        }
      };

      xhr.onload = () => {
        if (xhr.status === 200) {
          const data = JSON.parse(xhr.responseText);
          setUploading(false);
          onUploadComplete(data.filename);
        } else {
          setError('Upload failed: ' + xhr.statusText);
          setUploading(false);
        }
      };

      xhr.onerror = () => {
        setError('Network error during upload');
        setUploading(false);
      };

      xhr.send(formData);
    } catch (err) {
      console.error(err);
      setError('Upload failed');
      setUploading(false);
    }
  }, [onUploadComplete]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    accept: {'video/*': ['.mp4', '.mov', '.avi', '.mkv']},
    maxFiles: 1
  });

  return (
    <div 
      {...getRootProps()} 
      className={`glass-panel p-10 text-center cursor-pointer border-2 border-dashed transition-all duration-300 group
        ${isDragActive ? 'border-blue-500 bg-blue-50/50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-700 hover:border-blue-400'}
      `}
    >
      <input {...getInputProps()} />
      
      <div className="flex flex-col items-center justify-center space-y-4">
        <div className={`p-4 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-500 transition-transform duration-300 ${isDragActive ? 'scale-110' : ''}`}>
          {uploading ? (
            <motion.div 
              animate={{ rotate: 360 }}
              transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
            >
              <RefreshCw size={32} />
            </motion.div>
          ) : (
            <UploadCloud size={32} />
          )}
        </div>

        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {uploading ? 'Uploading Video...' : 'Upload Game Footage'}
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Drag & drop or click to select
          </p>
        </div>

        {error && (
          <div className="flex items-center space-x-2 text-red-500 text-sm mt-2">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
}

// Helper icon since I forgot to import it above
function RefreshCw({ size, className }) {
  return (
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className={className}
    >
      <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
      <path d="M21 3v5h-5" />
      <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
      <path d="M8 16H3v5" />
    </svg>
  )
}
