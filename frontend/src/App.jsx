import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import LandingPage from './components/LandingPage';
import FileUpload from './components/FileUpload';
import ImagePreview from './components/ImagePreview';
import OcrResults from './components/OcrResults';
import ScanProgress from './components/ScanProgress';
import { AlertCircle, ArrowLeft, RefreshCw, FileCheck } from 'lucide-react';

// Generates canvas image for sample packaged commodity testing
function createSampleLabelBlob(type) {
  const canvas = document.createElement('canvas');
  canvas.width = 640;
  canvas.height = 480;
  const ctx = canvas.getContext('2d');

  // Clean white label background
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, 640, 480);

  // Border frame
  ctx.strokeStyle = '#0284c7';
  ctx.lineWidth = 3;
  ctx.strokeRect(12, 12, 616, 456);

  // Subtle header band
  ctx.fillStyle = '#f0f9ff';
  ctx.fillRect(14, 14, 612, 48);
  ctx.fillStyle = '#0369a1';
  ctx.font = 'bold 17px sans-serif';
  ctx.fillText('LEGAL METROLOGY PACKAGED COMMODITY SPECIFICATION', 28, 44);

  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 16px monospace';

  if (type === 'amul-ghee') {
    ctx.fillText('COMMODITY: AMUL PURE GHEE 1L POUCH', 28, 95);
    ctx.fillText('NET QUANTITY: 1 L (905 g)', 28, 135);
    ctx.fillText('MRP Rs. 590.00 (INCL. OF ALL TAXES)', 28, 175);
    ctx.fillText('MFG DATE: 12/04/2026', 28, 215);
    ctx.fillText('EXPIRY: 9 MONTHS FROM PACKAGING', 28, 255);
    ctx.fillText('MFG BY: GUJARAT CO-OP MILK MKT FEDERATION LTD', 28, 295);
    ctx.fillText('ANAND 388001, GUJARAT, INDIA', 28, 335);
    ctx.fillText('CONSUMER CARE: 1800-258-3333 / customercare@amul.coop', 28, 375);
    ctx.fillText('FSSAI LIC NO 10014021000001', 28, 415);
  } else if (type === 'biscuits') {
    // Advisory case: MRP without "inclusive of all taxes" clause
    ctx.fillText('PRODUCT: CRUNCHY BITES BUTTER COOKIES', 28, 95);
    ctx.fillText('NET WEIGHT: 200 g (WHEN PACKED)', 28, 135);
    ctx.fillText('MRP: Rs. 45.00', 28, 175); // Missing "inclusive of all taxes"
    ctx.fillText('BATCH NO: BB2026-09', 28, 215);
    ctx.fillText('MFG DATE: 08/2026', 28, 255);
    ctx.fillText('MFG BY: APEX FOODS PVT LTD, MUMBAI 400001', 28, 295);
    ctx.fillText('CARE: care@apexfoods.in / Tel 022-28282828', 28, 335);
    ctx.fillText('FSSAI LIC NO 10012022000111', 28, 375);
  } else if (type === 'blurry-sample') {
    // Blurry mobile photo test case (low Laplacian score, triggers Real-ESRGAN)
    ctx.filter = 'blur(4px)';
    ctx.fillText('PRODUCT: NATURE HERBAL SHAMPOO 200ML', 28, 95);
    ctx.fillText('NET QUANTITY: 200 ml', 28, 135);
    ctx.fillText('MRP Rs. 185.00 (INCL. OF ALL TAXES)', 28, 175);
    ctx.fillText('MFG DATE: 07/2026', 28, 215);
    ctx.fillText('MFG BY: AYUR CARE LABS, HARIDWAR 249401', 28, 295);
    ctx.fillText('CARE: 1800-444-555 / support@ayurcare.in', 28, 375);
    ctx.filter = 'none';
  } else {
    // Non-food case: Detergent
    ctx.fillText('COMMODITY: ULTRA CLEAN LAUNDRY POWDER', 28, 95);
    ctx.fillText('NET QUANTITY: 1.0 kg', 28, 135);
    ctx.fillText('MRP Rs. 140.00 (INCL. OF ALL TAXES)', 28, 175);
    ctx.fillText('MONTH & YEAR OF PACK: 08/2026', 28, 215);
    ctx.fillText('GENERIC NAME: SYNTHETIC DETERGENT POWDER', 28, 255);
    ctx.fillText('MANUFACTURED BY: HINDUSTAN HOMECARE LTD', 28, 295);
    ctx.fillText('NEW DELHI 110001, INDIA', 28, 335);
    ctx.fillText('FEEDBACK HELPLINE: 1800-111-222 / help@clean.in', 28, 375);
  }

  return new Promise((resolve) => {
    canvas.toBlob((blob) => {
      const file = new File([blob], `${type}-sample-label.png`, { type: 'image/png' });
      resolve({ file, dataUrl: canvas.toDataURL('image/png') });
    }, 'image/png');
  });
}

export default function App() {
  const [currentView, setCurrentView] = useState('home'); // 'home' | 'scanner'
  const [selectedFile, setSelectedFile] = useState(null);
  const [imageSrc, setImageSrc] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [ocrResult, setOcrResult] = useState(null);
  const [hoveredLineId, setHoveredLineId] = useState(null);
  const [scanError, setScanError] = useState(null);
  const [backendStatus, setBackendStatus] = useState({ online: false, engine: null, version: null });

  // Periodically check backend health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/api/v1/health');
        if (res.ok) {
          const data = await res.json();
          setBackendStatus({ online: true, engine: data.ocr_engine, version: data.version });
        } else {
          setBackendStatus({ online: false, engine: null, version: null });
        }
      } catch (err) {
        setBackendStatus({ online: false, engine: null, version: null });
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setOcrResult(null);
    setScanError(null);

    const reader = new FileReader();
    reader.onload = (e) => setImageSrc(e.target.result);
    reader.readAsDataURL(file);
  };

  const handleSampleSelect = async (sampleType) => {
    const { file, dataUrl } = await createSampleLabelBlob(sampleType);
    setSelectedFile(file);
    setImageSrc(dataUrl);
    setOcrResult(null);
    setScanError(null);
  };

  const handleScan = async () => {
    if (!selectedFile) return;

    setIsScanning(true);
    setScanError(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch('/api/v1/scan', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error (${response.status})`);
      }

      const data = await response.json();
      setOcrResult(data);
    } catch (err) {
      console.error('Scan error:', err);
      setScanError(err.message || 'Failed to scan image. Ensure backend is running.');
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <div className="app-shell">
      <Header
        currentView={currentView}
        onNavigate={setCurrentView}
      />

      <main className="shell-body">
        {currentView === 'home' ? (
          <LandingPage
            onStartScan={() => setCurrentView('scanner')}
          />
        ) : (
          <div className="scanner-container">
            <div className="scanner-top-bar">
              <button
                className="btn btn-back-link"
                onClick={() => setCurrentView('home')}
              >
                <ArrowLeft size={16} />
                <span>Return to Overview</span>
              </button>
            </div>

            <div className="scanner-layout-grid">
              {/* Left Column: Image Upload & Visual Label Preview */}
              <div className="scanner-left-col">
                <FileUpload
                  onFileSelect={handleFileSelect}
                  onScan={handleScan}
                  isScanning={isScanning}
                  selectedFile={selectedFile}
                  onSampleSelect={handleSampleSelect}
                />

                {scanError && (
                  <div className="clean-alert-error">
                    <AlertCircle size={18} />
                    <span><strong>Scan failed:</strong> {scanError}</span>
                  </div>
                )}

                {imageSrc && (
                  <ImagePreview
                    imageSrc={imageSrc}
                    ocrResult={ocrResult}
                    hoveredLineId={hoveredLineId}
                    onHoverLine={setHoveredLineId}
                  />
                )}
              </div>

              {/* Right Column: Statutory Compliance Results Card (Hero) */}
              <div className="scanner-right-col">
                {isScanning ? (
                  <ScanProgress isScanning={isScanning} />
                ) : ocrResult ? (
                  <OcrResults ocrResult={ocrResult} />
                ) : (
                  <div className="empty-audit-card">
                    <div className="empty-card-icon-box">
                      <FileCheck size={32} className={isScanning ? 'pulse-spin' : ''} />
                    </div>
                    <h3>{isScanning ? 'Pre-Screening Mandatory Declarations...' : 'No Label Scanned Yet'}</h3>
                    <p>
                      {isScanning
                        ? 'Running OCR text detection and validating declarations against Legal Metrology Rules, 2011.'
                        : 'Upload a packaged commodity label image or pick a pre-configured sample to perform AI-assisted compliance pre-screening.'}
                    </p>

                    <div className="audit-checklist-preview">
                      <div className="checklist-preview-item">✓ Rule 6(1)(a) Manufacturer & Postal Address</div>
                      <div className="checklist-preview-item">✓ Rule 6(1)(b) Net Quantity in Standard Metric Units</div>
                      <div className="checklist-preview-item">✓ Rule 6(1)(e) MRP & "Inclusive of all taxes"</div>
                      <div className="checklist-preview-item">✓ Rule 6(1)(d) Month & Year of Manufacture</div>
                      <div className="checklist-preview-item">✓ Rule 6(1)(f) Consumer Care Helpline & Email</div>
                      <div className="checklist-preview-item">✓ FSSAI Statutory License Number Verification</div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
