import React, { useState, useRef, useEffect } from 'react';
import { Eye, EyeOff } from 'lucide-react';

export default function ImagePreview({ imageSrc, ocrResult, hoveredLineId, onHoverLine }) {
  const [showBoxes, setShowBoxes] = useState(true);
  const [naturalDimensions, setNaturalDimensions] = useState({ width: 0, height: 0 });
  const [displayedDimensions, setDisplayedDimensions] = useState({ width: 0, height: 0 });
  const imageRef = useRef(null);

  const handleImageLoad = (e) => {
    const { naturalWidth, naturalHeight, clientWidth, clientHeight } = e.target;
    setNaturalDimensions({ width: naturalWidth, height: naturalHeight });
    setDisplayedDimensions({ width: clientWidth, height: clientHeight });
  };

  useEffect(() => {
    const updateSize = () => {
      if (imageRef.current) {
        setDisplayedDimensions({
          width: imageRef.current.clientWidth,
          height: imageRef.current.clientHeight
        });
      }
    };
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  const scaleX = naturalDimensions.width > 0 ? displayedDimensions.width / naturalDimensions.width : 1;
  const scaleY = naturalDimensions.height > 0 ? displayedDimensions.height / naturalDimensions.height : 1;

  return (
    <div className="preview-container-clean">
      <div className="preview-header-clean">
        <span className="preview-title-text">Label Visual Detection</span>
        {ocrResult && (
          <div className="preview-controls-clean">
            <button
              className={`toggle-box-btn ${showBoxes ? 'toggle-box-active' : ''}`}
              onClick={() => setShowBoxes(!showBoxes)}
              title="Toggle bounding boxes overlay"
            >
              {showBoxes ? <Eye size={14} /> : <EyeOff size={14} />}
              <span>{showBoxes ? 'Hide Highlight Boxes' : 'Show Highlight Boxes'}</span>
            </button>
          </div>
        )}
      </div>

      <div className="image-viewport">
        <div className="image-wrapper-relative">
          <img
            ref={imageRef}
            src={imageSrc}
            alt="Packaged Commodity Label Preview"
            className="clean-source-img"
            onLoad={handleImageLoad}
          />

          {showBoxes && ocrResult && ocrResult.lines && displayedDimensions.width > 0 && (
            <svg
              className="clean-svg-overlay"
              width={displayedDimensions.width}
              height={displayedDimensions.height}
              viewBox={`0 0 ${displayedDimensions.width} ${displayedDimensions.height}`}
            >
              {ocrResult.lines.map((line) => {
                const pointsString = line.box
                  .map(([x, y]) => `${x * scaleX},${y * scaleY}`)
                  .join(' ');

                const isHovered = hoveredLineId === line.id;
                // Soft blue for normal outline, soft brown for hovered outline
                const strokeColor = isHovered ? '#8d5b4c' : '#0284c7';

                return (
                  <g
                    key={line.id}
                    className="clean-polygon-group"
                    onMouseEnter={() => onHoverLine && onHoverLine(line.id)}
                    onMouseLeave={() => onHoverLine && onHoverLine(null)}
                  >
                    <polygon
                      points={pointsString}
                      fill={isHovered ? 'rgba(141, 91, 76, 0.15)' : 'rgba(2, 132, 199, 0.08)'}
                      stroke={strokeColor}
                      strokeWidth={isHovered ? 2.5 : 1.5}
                    />
                  </g>
                );
              })}
            </svg>
          )}
        </div>
      </div>
    </div>
  );
}
