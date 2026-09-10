import React, { useState, useEffect, useRef } from 'react';
import { Camera, RefreshCw, Check, AlertCircle, FlipHorizontal, ArrowLeft, Upload } from 'lucide-react';

export default function CameraCapture({ onPhotoCaptured, onFallbackToUpload }) {
  const [stream, setStream] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [cameraError, setCameraError] = useState(null);
  const [capturedPreview, setCapturedPreview] = useState(null);
  const [capturedBlob, setCapturedBlob] = useState(null);
  const [facingMode, setFacingMode] = useState('environment'); // Prefer rear camera on mobile
  const [availableCamerasCount, setAvailableCamerasCount] = useState(0);

  const videoRef = useRef(null);
  const streamRef = useRef(null);

  // Stop camera tracks helper
  const stopStream = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setStream(null);
  };

  // Start camera stream
  const startCamera = async (facing = facingMode) => {
    setIsLoading(true);
    setCameraError(null);
    stopStream();

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraError('Live camera capture is not supported in this browser. Please use the Upload Photo option.');
      setIsLoading(false);
      return;
    }

    try {
      // Check available cameras to see if camera flipping is applicable
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter((d) => d.kind === 'videoinput');
        setAvailableCamerasCount(videoDevices.length);
      } catch (e) {
        // Enumerate devices not strictly required
      }

      const constraints = {
        video: {
          facingMode: { ideal: facing },
          width: { ideal: 1920, min: 640 },
          height: { ideal: 1080, min: 480 },
        },
        audio: false,
      };

      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = mediaStream;
      setStream(mediaStream);

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err) {
      console.warn('Camera access error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCameraError('Camera access was denied. Please allow camera permissions in your browser bar, or switch to Upload Photo.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCameraError('No camera found on this device. Please use the Upload Photo option.');
      } else if (err.name === 'NotReadableError') {
        setCameraError('Camera is currently in use by another application. Please close other apps and try again.');
      } else {
        setCameraError(err.message || 'Failed to initialize camera. Please use the Upload Photo option.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    startCamera(facingMode);
    return () => {
      stopStream();
    };
  }, [facingMode]);

  // Flip between front and rear cameras
  const toggleFacingMode = () => {
    setFacingMode((prev) => (prev === 'environment' ? 'user' : 'environment'));
  };

  // Capture current video frame
  const handleCapture = () => {
    if (!videoRef.current) return;

    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        const dataUrl = canvas.toDataURL('image/jpeg', 0.95);
        setCapturedBlob(blob);
        setCapturedPreview(dataUrl);
        // Stop stream while reviewing
        stopStream();
      },
      'image/jpeg',
      0.95
    );
  };

  // Discard and retake
  const handleRetake = () => {
    setCapturedPreview(null);
    setCapturedBlob(null);
    startCamera(facingMode);
  };

  // Confirm photo and pass to parent
  const handleConfirmPhoto = () => {
    if (!capturedBlob) return;

    const filename = `label-capture-${Date.now()}.jpg`;
    const file = new File([capturedBlob], filename, { type: 'image/jpeg' });
    stopStream();
    onPhotoCaptured(file);
  };

  return (
    <div className="camera-capture-container">
      {/* 1. Camera Error State / Graceful Denial */}
      {cameraError ? (
        <div className="camera-error-card">
          <div className="camera-error-icon-box">
            <AlertCircle size={28} className="camera-error-glyph" />
          </div>
          <h3 className="camera-error-title">Camera Unavailable</h3>
          <p className="camera-error-message">{cameraError}</p>
          <div className="camera-error-actions">
            <button
              type="button"
              className="btn btn-camera-secondary"
              onClick={() => startCamera(facingMode)}
            >
              <RefreshCw size={15} />
              <span>Try Again</span>
            </button>
            <button
              type="button"
              className="btn btn-camera-primary"
              onClick={onFallbackToUpload}
            >
              <Upload size={15} />
              <span>Switch to Upload Photo</span>
            </button>
          </div>
        </div>
      ) : capturedPreview ? (
        /* 2. Review Captured Snapshot */
        <div className="camera-review-view">
          <div className="camera-preview-wrapper">
            <img
              src={capturedPreview}
              alt="Captured commodity label"
              className="camera-captured-image"
            />
            <div className="camera-review-badge">
              <span>Photo Captured</span>
            </div>
          </div>

          <div className="camera-review-controls">
            <button
              type="button"
              className="btn btn-camera-retake"
              onClick={handleRetake}
            >
              <RefreshCw size={16} />
              <span>Retake Photo</span>
            </button>

            <button
              type="button"
              className="btn btn-camera-confirm"
              onClick={handleConfirmPhoto}
            >
              <Check size={16} />
              <span>Use This Photo</span>
            </button>
          </div>
        </div>
      ) : (
        /* 3. Live Camera Viewfinder */
        <div className="camera-viewfinder-wrapper">
          <div className="camera-viewport">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="camera-video-element"
              onLoadedMetadata={() => {
                if (videoRef.current) {
                  videoRef.current.play().catch(() => {});
                }
              }}
            />

            {/* Viewfinder Target Framing Guides */}
            <div className="camera-framing-overlay">
              <div className="framing-corner top-left"></div>
              <div className="framing-corner top-right"></div>
              <div className="framing-corner bottom-left"></div>
              <div className="framing-corner bottom-right"></div>
              <div className="framing-instruction">
                Align packaged commodity label within frame
              </div>
            </div>

            {isLoading && (
              <div className="camera-loading-overlay">
                <div className="clean-spinner"></div>
                <span>Starting camera...</span>
              </div>
            )}
          </div>

          {/* Shutter / Controls Bar */}
          <div className="camera-shutter-bar">
            {availableCamerasCount > 1 && (
              <button
                type="button"
                className="btn-camera-util"
                onClick={toggleFacingMode}
                title="Switch Camera"
                disabled={isLoading}
              >
                <FlipHorizontal size={18} />
              </button>
            )}

            <button
              type="button"
              className="camera-shutter-btn"
              onClick={handleCapture}
              disabled={isLoading}
              title="Capture Label"
            >
              <div className="shutter-inner-ring">
                <div className="shutter-center-dot"></div>
              </div>
            </button>

            {availableCamerasCount > 1 && <div className="camera-util-spacer"></div>}
          </div>
        </div>
      )}
    </div>
  );
}
