import React, { useState, useRef } from 'react';
import CameraCapture from './CameraCapture';
import { Upload, Camera, FileImage, AlertCircle, ArrowRight, Image as ImageIcon } from 'lucide-react';

export default function FileUpload({ onFileSelect, onScan, isScanning, selectedFile, onSampleSelect }) {
  const [activeMode, setActiveMode] = useState('upload'); // 'upload' | 'camera'
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const validateAndSetFile = (file) => {
    setErrorMessage('');
    if (!file) return;

    const validTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp', 'image/tiff'];
    if (!validTypes.includes(file.type) && !file.name.match(/\.(jpg|jpeg|png|webp|bmp|tiff)$/i)) {
      setErrorMessage('Please upload a valid image file (JPEG, PNG, WEBP, BMP, or TIFF).');
      return;
    }

    if (file.size > 15 * 1024 * 1024) {
      setErrorMessage('File size exceeds the 15MB limit.');
      return;
    }

    onFileSelect(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  return (
    <div className="custom-upload-card">
      <div className="card-header-clean">
        <div>
          <h2 className="card-title-clean">Commodity Label Image</h2>
          <p className="card-desc-clean">Capture a photograph or upload packaging artwork of the label</p>
        </div>
      </div>

      {/* Mode Selector Tabs: Take Photo vs Upload Photo */}
      <div className="upload-mode-nav">
        <button
          type="button"
          className={`upload-tab-btn ${activeMode === 'camera' ? 'active' : ''}`}
          onClick={() => setActiveMode('camera')}
        >
          <Camera size={16} />
          <span>Take Photo</span>
        </button>
        <button
          type="button"
          className={`upload-tab-btn ${activeMode === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveMode('upload')}
        >
          <Upload size={16} />
          <span>Upload Photo</span>
        </button>
      </div>

      {/* Dynamic Upload / Camera Body */}
      {activeMode === 'camera' ? (
        <CameraCapture
          onPhotoCaptured={(file) => {
            validateAndSetFile(file);
          }}
          onFallbackToUpload={() => setActiveMode('upload')}
        />
      ) : (
        /* Bespoke custom dropzone (solid tactile border, clean off-white / light blue styling) */
        <div
          className={`custom-dropzone ${isDragOver ? 'custom-dropzone-dragover' : ''} ${selectedFile ? 'custom-dropzone-loaded' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current && fileInputRef.current.click()}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleInputChange}
            accept="image/jpeg,image/png,image/webp,image/bmp,image/tiff"
            style={{ display: 'none' }}
          />

          <div className="dropzone-tactile-surface">
            <div className="dropzone-icon-box">
              <Upload size={22} className="dropzone-glyph" />
            </div>
            <div className="dropzone-text-group">
              <span className="dropzone-main-heading">
                {selectedFile ? 'Replace selected label image' : 'Select or drop label image'}
              </span>
              <span className="dropzone-sub-caption">
                Direct photo or high-res packaging render (JPG, PNG, WEBP up to 15 MB)
              </span>
            </div>
          </div>
        </div>
      )}

      {errorMessage && (
        <div className="clean-alert-error">
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {selectedFile && (
        <div className="staged-file-card">
          <div className="staged-file-meta">
            <FileImage size={20} className="staged-file-icon" />
            <div className="staged-file-text">
              <span className="staged-filename">{selectedFile.name}</span>
              <span className="staged-filesize">{(selectedFile.size / 1024).toFixed(1)} KB</span>
            </div>
          </div>

          <button
            className="btn btn-scan-action"
            onClick={onScan}
            disabled={isScanning}
          >
            {isScanning ? (
              <>
                <div className="clean-spinner"></div>
                <span>Auditing Declarations...</span>
              </>
            ) : (
              <>
                <span>Run Compliance Audit</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </div>
      )}

      {/* Preloaded Sample Commodities */}
      <div className="sample-commodity-drawer">
        <span className="sample-drawer-title">Test with pre-configured commodity labels:</span>
        <div className="sample-pills-row">
          <button
            type="button"
            className="sample-pill-btn"
            onClick={() => onSampleSelect('amul-ghee')}
            disabled={isScanning}
          >
            <span className="pill-dot"></span>
            <span>Amul Ghee (Compliant Label)</span>
          </button>
          <button
            type="button"
            className="sample-pill-btn"
            onClick={() => onSampleSelect('biscuits')}
            disabled={isScanning}
          >
            <span className="pill-dot"></span>
            <span>Butter Cookies (Advisory MRP)</span>
          </button>
          <button
            type="button"
            className="sample-pill-btn"
            onClick={() => onSampleSelect('detergent')}
            disabled={isScanning}
          >
            <span className="pill-dot"></span>
            <span>Detergent 1kg (Non-Food Item)</span>
          </button>
          <button
            type="button"
            className="sample-pill-btn"
            onClick={() => onSampleSelect('blurry-sample')}
            disabled={isScanning}
          >
            <span className="pill-dot pill-dot-amber"></span>
            <span>Blurry Label Capture (Tests Real-ESRGAN Deblur)</span>
          </button>
        </div>
      </div>
    </div>
  );
}
