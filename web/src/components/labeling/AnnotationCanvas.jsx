import React, { useState, useRef } from "react";
import { Crosshair, Check, Trash2, Tag as TagIcon } from "lucide-react";

export default function AnnotationCanvas({ image, initialBoxes = [], onSave }) {
  const [boxes, setBoxes] = useState(initialBoxes);

  // Sync state if props change (e.g. when opening modal with new data)
  React.useEffect(() => {
    setBoxes(initialBoxes);
  }, [initialBoxes]);
  const [currentBox, setCurrentBox] = useState(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPos, setStartPos] = useState(null);
  const [activeBoxIndex, setActiveBoxIndex] = useState(null);
  const [currentLabel, setCurrentLabel] = useState("");

  const containerRef = useRef(null);
  const canvasRect = useRef(null);

  const getRelativeCoords = (e, rectOverride = null) => {
    const rect = rectOverride || containerRef.current?.getBoundingClientRect();
    if (!rect || !rect.width || !rect.height) return null;

    const x = ((e.clientX - rect.left) / rect.width) * 1000;
    const y = ((e.clientY - rect.top) / rect.height) * 1000;

    return {
      x: Math.max(0, Math.min(1000, x)),
      y: Math.max(0, Math.min(1000, y)),
    };
  };

  const handleMouseDown = (e) => {
    if (e.button !== 0) return;

    if (activeBoxIndex !== null) {
      setActiveBoxIndex(null);
      setCurrentLabel("");
      return;
    }

    const rect = containerRef.current?.getBoundingClientRect();
    canvasRect.current = rect;

    const coords = getRelativeCoords(e, rect);
    if (!coords) return;

    setStartPos(coords);
    setIsDrawing(true);
    setCurrentBox({ x: coords.x, y: coords.y, w: 0, h: 0 });
  };

  const handleMouseMove = (e) => {
    if (!isDrawing || !startPos) return;
    if (e.buttons !== 1) return handleMouseUp();

    const coords = getRelativeCoords(e, canvasRect.current);
    if (!coords) return;

    setCurrentBox({
      x: Math.min(coords.x, startPos.x),
      y: Math.min(coords.y, startPos.y),
      w: Math.abs(coords.x - startPos.x),
      h: Math.abs(coords.y - startPos.y),
    });
  };

  const handleMouseUp = () => {
    if (!isDrawing || !currentBox) {
      resetDrawing();
      return;
    }

    setIsDrawing(false);

    if (currentBox.w > 10 && currentBox.h > 10) {
      setBoxes((prev) => {
        const next = [...prev, { ...currentBox, label: "" }];
        setActiveBoxIndex(next.length - 1);
        return next;
      });
    }

    resetDrawing();
  };

  const resetDrawing = () => {
    setCurrentBox(null);
    setStartPos(null);
    setIsDrawing(false);
    canvasRect.current = null;
  };

  const handleLabelSubmit = () => {
    if (activeBoxIndex === null) return;

    setBoxes((prev) =>
      prev.map((b, i) =>
        i === activeBoxIndex ? { ...b, label: currentLabel } : b
      )
    );

    setActiveBoxIndex(null);
    setCurrentLabel("");
  };

  const deleteBox = (index, e) => {
    e.stopPropagation();
    setBoxes((prev) => prev.filter((_, i) => i !== index));
    if (index === activeBoxIndex) {
      setActiveBoxIndex(null);
      setCurrentLabel("");
    } else if (index < activeBoxIndex) {
      setActiveBoxIndex(activeBoxIndex - 1);
    }
  };

  return (
    <div className="flex flex-col h-full select-none">
      <div
        className="relative flex-1 border rounded-lg"
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <img
          src={image}
          className="w-full h-full object-contain pointer-events-none rounded-lg"
          draggable={false}
        />

        {boxes.map((box, i) => (
          <div
            key={i}
            className={`absolute border-2 z-20 group ${
              activeBoxIndex === i ? "border-yellow-400 bg-yellow-400/20" : "border-green-500"
            }`}
            style={{
              left: `${box.x / 10}%`,
              top: `${box.y / 10}%`,
              width: `${box.w / 10}%`,
              height: `${box.h / 10}%`,
            }}
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation();
              setActiveBoxIndex(i);
              setCurrentLabel(box.label);
            }}
          >
            {box.label && (
              <div className="absolute -top-6 bg-green-500 text-white text-xs px-1 rounded">
                {box.label}
              </div>
            )}

            <button
              onClick={(e) => deleteBox(i, e)}
              className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100"
            >
              <Trash2 size={12} />
            </button>
          </div>
        ))}

        {currentBox && (
          <div
            className="absolute border-2 border-blue-500 bg-blue-500/20 z-20"
            style={{
              left: `${currentBox.x / 10}%`,
              top: `${currentBox.y / 10}%`,
              width: `${currentBox.w / 10}%`,
              height: `${currentBox.h / 10}%`,
            }}
          />
        )}
      </div>

      <div className="mt-4 flex gap-3 items-center">
        {activeBoxIndex !== null && (
          <>
            <input
              value={currentLabel}
              onChange={(e) => setCurrentLabel(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLabelSubmit()}
              placeholder="Label..."
              className="flex-1 p-2 border rounded select-text"
              autoFocus
            />
            <button onClick={handleLabelSubmit} className="px-4 py-2 bg-yellow-500 text-white rounded">
              Set
            </button>
          </>
        )}

        <button
          onClick={() => onSave(boxes)}
          className="ml-auto px-6 py-2 bg-blue-600 text-white rounded font-bold flex items-center gap-2"
        >
          <Check size={18} />
          Save
        </button>
      </div>
    </div>
  );
}