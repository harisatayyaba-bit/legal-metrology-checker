import React, { useState } from 'react';
import ComplianceCard from './ComplianceCard';
import { ChevronDown, ChevronUp, Copy, Check, Terminal, FileCheck, Sparkles, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function OcrResults({ ocrResult }) {
  const [showRawText, setShowRawText] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!ocrResult) return null;

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const quality = ocrResult.image_quality;

  return (
    <div className="results-wrapper-clean">
      {/* Image Quality Pre-processing Status Banner */}
      {quality && (
        <div className={`image-quality-banner ${quality.enhancement_applied ? 'quality-banner-enhanced' : 'quality-banner-good'}`}>
          <div className="quality-banner-content">
            {quality.enhancement_applied ? (
              <Sparkles size={18} className="quality-icon quality-icon-enhanced" />
            ) : (
              <CheckCircle2 size={18} className="quality-icon quality-icon-good" />
            )}
            <div className="quality-text-group">
              <span className="quality-main-status">
                Image quality: <strong>{quality.quality_status}</strong>
              </span>
              <span className="quality-meta-subtext">
                Laplacian blur score: <code>{quality.blur_score}</code> (Quality threshold: {quality.quality_threshold})
                {quality.enhancement_applied && ` • Deblurred via ${quality.enhancement_method}`}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 1. Primary Hero Section: Statutory Compliance Results Card */}
      {ocrResult.compliance ? (
        <ComplianceCard
          compliance={ocrResult.compliance}
          scanId={ocrResult.scan_id}
          imageQuality={ocrResult.image_quality}
          averageConfidence={ocrResult.average_confidence}
          requiresHumanReview={ocrResult.requires_human_review}
        />
      ) : (
        <div className="clean-alert-info">
          <span>Compliance assessment in progress...</span>
        </div>
      )}

      {/* 2. Secondary Collapsed Section: Raw Extracted OCR Text */}
      <div className="raw-text-accordion">
        <button
          type="button"
          className="accordion-header-btn"
          onClick={() => setShowRawText(!showRawText)}
        >
          <div className="accordion-title-left">
            <Terminal size={16} className="accordion-icon" />
            <span className="accordion-title-text">
              View Raw Extracted Text ({ocrResult.lines ? ocrResult.lines.length : 0} lines detected)
            </span>
          </div>
          <div className="accordion-arrow">
            {showRawText ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </div>
        </button>

        {showRawText && (
          <div className="accordion-body">
            <div className="accordion-action-bar">
              <span className="ocr-meta-tag">OCR Engine: {ocrResult.ocr_engine} • Latency: {ocrResult.processing_time_ms} ms</span>
              <button
                className="btn btn-copy-clean"
                onClick={() => handleCopy(ocrResult.raw_text)}
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                <span>{copied ? 'Copied' : 'Copy Text'}</span>
              </button>
            </div>
            <pre className="raw-text-content">{ocrResult.raw_text}</pre>
          </div>
        )}
      </div>
    </div>
  );
}
