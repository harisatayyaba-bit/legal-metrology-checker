import React, { useState, useEffect } from 'react';
import { Eye, FileSearch, ShieldCheck, CheckCircle2 } from 'lucide-react';

export default function ScanProgress({ isScanning }) {
  const [currentStep, setCurrentStep] = useState(1);

  const steps = [
    {
      id: 1,
      name: 'Checking image quality',
      subtext: 'Variance of Laplacian blur score & deblur evaluation',
      icon: Eye,
    },
    {
      id: 2,
      name: 'Extracting text',
      subtext: 'PaddleOCR line segmentation & character recognition',
      icon: FileSearch,
    },
    {
      id: 3,
      name: 'Checking compliance',
      subtext: 'Validating mandatory declarations per Legal Metrology Rules, 2011',
      icon: ShieldCheck,
    },
  ];

  useEffect(() => {
    if (!isScanning) {
      setCurrentStep(1);
      return;
    }

    setCurrentStep(1);
    // Smooth timed progression across the 3 sequential pipeline stages
    const timer1 = setTimeout(() => {
      setCurrentStep(2);
    }, 1100);

    const timer2 = setTimeout(() => {
      setCurrentStep(3);
    }, 2400);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, [isScanning]);

  return (
    <div className="scan-progress-card">
      <div className="progress-header">
        <div className="progress-badge-pill">
          <span className="pill-dot pill-dot-pulse"></span>
          <span>Pre-Screening in Progress</span>
        </div>
        <h3 className="progress-title">Analyzing Packaged Commodity Label</h3>
        <p className="progress-subtitle">
          Automated multi-stage statutory pre-screening under Legal Metrology 2011 norms.
        </p>
      </div>

      <div className="progress-stepper">
        {steps.map((step, idx) => {
          const StepIcon = step.icon;
          const isCompleted = currentStep > step.id;
          const isActive = currentStep === step.id;

          return (
            <div
              key={step.id}
              className={`stepper-item ${isCompleted ? 'step-completed' : ''} ${isActive ? 'step-active' : ''}`}
            >
              <div className="step-indicator-col">
                <div className="step-circle">
                  {isCompleted ? (
                    <CheckCircle2 size={18} className="step-check-icon" />
                  ) : (
                    <StepIcon size={18} className="step-glyph-icon" />
                  )}
                  {isActive && <div className="step-halo-pulse"></div>}
                </div>
                {idx < steps.length - 1 && (
                  <div className={`step-connector-line ${isCompleted ? 'line-completed' : ''}`}></div>
                )}
              </div>

              <div className="step-content-col">
                <div className="step-title-row">
                  <span className="step-name">{step.name}</span>
                  {isActive && <span className="step-running-tag">Processing...</span>}
                  {isCompleted && <span className="step-done-tag">Complete</span>}
                </div>
                <span className="step-desc">{step.subtext}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
