import React, { useState, useRef, useEffect } from 'react';
import { Crosshair, Check } from 'lucide-react';

export default function ROISelector({ filename, onConfirm }) {
  const [imageSrc, setImageSrc] = useState(null);
  const [selection, setSelection] = useState(null); // {x, y, w, h} in percentage or px relative to view? Px relative to view is easier for drawing.
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  
  const imgRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (filename) {
      setImageSrc(`http://localhost:8000/api/v1/video/${filename}/frame?timestamp=1.0`); // Get frame at 1s to ensure content
    }
  }, [filename]);

  const getCoords = (e) => {
    const rect = containerRef.current.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    };
  };

  const handleMouseDown = (e) => {
    e.preventDefault();
    const coords = getCoords(e);
    setStartPos(coords);
    setIsDrawing(true);
    setSelection({ x: coords.x, y: coords.y, w: 0, h: 0 });
  };

  const handleMouseMove = (e) => {
    if (!isDrawing) return;
    const coords = getCoords(e);
    
    const x = Math.min(coords.x, startPos.x);
    const y = Math.min(coords.y, startPos.y);
    const w = Math.abs(coords.x - startPos.x);
    const h = Math.abs(coords.y - startPos.y);

    setSelection({ x, y, w, h });
  };

  const handleMouseUp = () => {
    setIsDrawing(false);
  };

  const handleConfirm = () => {
    if (!selection || !imgRef.current) return;

    // Convert view coordinates to original image coordinates
    const scaleX = imgRef.current.naturalWidth / imgRef.current.clientWidth;
    const scaleY = imgRef.current.naturalHeight / imgRef.current.clientHeight;

    const roi = {
      x: Math.round(selection.x * scaleX),
      y: Math.round(selection.y * scaleY),
      w: Math.round(selection.w * scaleX),
      h: Math.round(selection.h * scaleY)
    };

    onConfirm(roi);
  };

  if (!imageSrc) return <div className="p-10 text-center text-gray-500">Loading frame...</div>;

  return (
    <div className="glass-panel p-6 space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Crosshair size={20} />
          <span>Select Focus Area (HUD)</span>
        </h3>
        <div className="space-x-2">
            <button 
                onClick={() => setSelection(null)}
                className="text-sm text-gray-500 hover:text-gray-700 px-3 py-1"
            >
                Reset
            </button>
            <button 
                onClick={handleConfirm}
                disabled={!selection}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
                <Check size={16} />
                Confirm Selection
            </button>
        </div>
      </div>

      <div className="relative overflow-hidden rounded-lg bg-black/5 border border-gray-200 dark:border-gray-700 select-none" ref={containerRef}>
        <img 
            ref={imgRef}
            src={imageSrc} 
            alt="Video Frame" 
            className="w-full h-auto block pointer-events-none"
            draggable={false}
        />
        
        {/* Overlay for drawing */}
        <div 
            className="absolute inset-0 cursor-crosshair z-10"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
        />

        {/* Selection Box */}
        {selection && (
            <div 
                className="absolute border-2 border-blue-500 bg-blue-500/20 pointer-events-none z-20"
                style={{
                    left: selection.x,
                    top: selection.y,
                    width: selection.w,
                    height: selection.h
                }}
            />
        )}
      </div>
      <p className="text-sm text-gray-500 text-center">
        Click and drag to highlight the area where skills/cooldowns are displayed.
      </p>
    </div>
  );
}
