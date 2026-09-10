import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  ChevronsDown,
  ChevronsUp,
  FileDown,
  FileEdit,
  FileText,
  ShieldAlert
} from 'lucide-react';

export default function ComplianceCard({ compliance, scanId, imageQuality, averageConfidence, requiresHumanReview }) {
  if (!compliance) return null;

  // Scan-level review signal based on blur score, enhancement, or low extraction certainty
  const isLowConfidence = Boolean(
    requiresHumanReview ||
    imageQuality?.enhancement_applied ||
    imageQuality?.is_blurry ||
    (averageConfidence !== undefined && averageConfidence < 0.70)
  );

  // Track expanded state for each declaration field
  const allFieldIds = compliance.fields ? compliance.fields.map((f) => f.field_id) : [];
  const [expandedFields, setExpandedFields] = useState(() => new Set(allFieldIds));

  // Report download states
  const [isExporting, setIsExporting] = useState(null); // 'pdf' | 'docx' | null
  const [exportError, setExportError] = useState(null);

  const toggleField = (fieldId) => {
    setExpandedFields((prev) => {
      const next = new Set(prev);
      if (next.has(fieldId)) {
        next.delete(fieldId);
      } else {
        next.add(fieldId);
      }
      return next;
    });
  };

  const allExpanded = allFieldIds.length > 0 && allFieldIds.every((id) => expandedFields.has(id));

  const toggleAll = () => {
    if (allExpanded) {
      setExpandedFields(new Set());
    } else {
      setExpandedFields(new Set(allFieldIds));
    }
  };

  const handleDownloadReport = async (format) => {
    if (!scanId) {
      setExportError('Scan ID not available for this session. Please perform a fresh scan.');
      return;
    }

    setIsExporting(format);
    setExportError(null);

    try {
      const res = await fetch(`/api/v1/report/${scanId}?format=${format}`);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to generate report (${res.status})`);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `packtrue_compliance_report_${scanId}.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Report export error:', err);
      setExportError(err.message || 'Failed to download report');
    } finally {
      setIsExporting(null);
    }
  };

  const getOverallVerdictTheme = (verdict) => {
    switch (verdict) {
      case 'Compliant':
        return {
          bannerClass: 'verdict-banner-compliant',
          badgeClass: 'verdict-badge-compliant',
          icon: <CheckCircle2 size={24} className="verdict-icon" />
        };
      case 'Compliant — Packaging Advisory':
        return {
          bannerClass: 'verdict-banner-advisory',
          badgeClass: 'verdict-badge-advisory',
          icon: <AlertTriangle size={24} className="verdict-icon" />
        };
      case 'Non-Compliant':
      default:
        return {
          bannerClass: 'verdict-banner-violation',
          badgeClass: 'verdict-badge-violation',
          icon: <AlertCircle size={24} className="verdict-icon" />
        };
    }
  };

  const getAssessmentTitle = (verdict) => {
    switch (verdict) {
      case 'Compliant':
        return 'Compliant';
      case 'Compliant — Packaging Advisory':
        return 'Packaging Advisories Flagged';
      case 'Non-Compliant':
      default:
        return 'Potential Violations Flagged';
    }
  };

  const getFieldBadgeClass = (verdict) => {
    switch (verdict) {
      case 'Compliant':
        return 'field-badge-compliant';
      case 'Compliant — Packaging Advisory':
        return 'field-badge-advisory';
      case 'Non-Compliant':
      default:
        return 'field-badge-violation';
    }
  };

  const theme = getOverallVerdictTheme(compliance.overall_verdict);

  return (
    <div className="compliance-results-card">
      {/* Automated Pre-Screening Legal Notice */}
      <div className="screening-disclaimer-banner">
        <ShieldAlert size={16} className="disclaimer-icon" />
        <span>
          This is an automated pre-screening tool. Findings are not a legal determination and require confirmation by an authorized Legal Metrology officer before any enforcement action.
        </span>
      </div>

      {/* Scan-Level Confidence Warning Banner (Conditional on blur score / certainty) */}
      {isLowConfidence && (
        <div className="confidence-review-banner">
          <AlertTriangle size={20} className="confidence-review-icon" />
          <div className="confidence-review-text">
            <span className="confidence-review-title">⚠ Low Confidence — Human Review Recommended</span>
            <span className="confidence-review-sub">
              Image quality was degraded or enhancement was applied during pre-screening. Findings require officer confirmation before enforcement action.
            </span>
          </div>
        </div>
      )}

      {/* Overall Assessment Banner */}
      <div className={`overall-verdict-banner ${theme.bannerClass}`}>
        <div className="banner-left">
          {theme.icon}
          <div>
            <div className="banner-kicker">Legal Metrology Preliminary Assessment</div>
            <h2 className="banner-verdict-title">{getAssessmentTitle(compliance.overall_verdict)}</h2>
            <p className="banner-summary">{compliance.summary}</p>
          </div>
        </div>

        <div className="verdict-stats-group">
          <div className="stat-chip stat-passed">
            <span className="stat-count">{compliance.passed_checks}</span>
            <span className="stat-label">Passed</span>
          </div>
          {compliance.advisory_checks > 0 && (
            <div className="stat-chip stat-advisory">
              <span className="stat-count">{compliance.advisory_checks}</span>
              <span className="stat-label">Advisories</span>
            </div>
          )}
          {compliance.failed_checks > 0 && (
            <div className="stat-chip stat-failed">
              <span className="stat-count">{compliance.failed_checks}</span>
              <span className="stat-label">Potential Violations</span>
            </div>
          )}
        </div>
      </div>

      {/* Report Export Action Bar */}
      <div className="report-export-bar">
        <div className="report-export-info">
          <FileText size={18} className="report-export-icon" />
          <div className="report-export-labels">
            <span className="report-export-heading">Statutory Compliance Pre-Screening Report</span>
            <span className="report-export-sub">
              Includes original label image evidence, pre-screening checklist, and officer verification block
            </span>
          </div>
        </div>

        <div className="report-export-buttons">
          <button
            type="button"
            className="btn btn-export-pdf"
            onClick={() => handleDownloadReport('pdf')}
            disabled={isExporting !== null}
            title="Download PDF report with evidence attachment"
          >
            {isExporting === 'pdf' ? (
              <>
                <div className="clean-spinner"></div>
                <span>Generating PDF...</span>
              </>
            ) : (
              <>
                <FileDown size={16} />
                <span>Download Report (PDF)</span>
              </>
            )}
          </button>

          <button
            type="button"
            className="btn btn-export-docx"
            onClick={() => handleDownloadReport('docx')}
            disabled={isExporting !== null}
            title="Export editable Word document with officer notes section"
          >
            {isExporting === 'docx' ? (
              <>
                <div className="clean-spinner"></div>
                <span>Generating DOCX...</span>
              </>
            ) : (
              <>
                <FileEdit size={16} />
                <span>Export Word (.docx)</span>
              </>
            )}
          </button>
        </div>
      </div>

      {exportError && (
        <div className="clean-alert-error" style={{ marginBottom: '1.25rem' }}>
          <AlertCircle size={16} />
          <span>{exportError}</span>
        </div>
      )}

      {/* Structured Declarations Checklist */}
      <div className="fields-checklist">
        <div className="checklist-header">
          <div className="checklist-title-group">
            <h3>Mandatory Packaging Declarations Pre-Screening</h3>
            <span className="checklist-subtitle">Pre-screened per Legal Metrology (Packaged Commodities) Rules, 2011 • Pending Officer Confirmation</span>
          </div>

          <button
            type="button"
            className="btn-collapse-toggle"
            onClick={toggleAll}
            title={allExpanded ? 'Collapse all declaration cards' : 'Expand all declaration cards'}
          >
            {allExpanded ? (
              <>
                <ChevronsUp size={15} />
                <span>Collapse All</span>
              </>
            ) : (
              <>
                <ChevronsDown size={15} />
                <span>Expand All</span>
              </>
            )}
          </button>
        </div>

        <div className="fields-list">
          {compliance.fields.map((field) => {
            const badgeClass = getFieldBadgeClass(field.verdict);
            const isExpanded = expandedFields.has(field.field_id);

            return (
              <div
                key={field.field_id}
                className={`field-card ${field.verdict === 'Non-Compliant' ? 'field-card-failed' : ''} ${field.verdict === 'Compliant — Packaging Advisory' ? 'field-card-advisory' : ''}`}
              >
                {/* Clickable Header for Collapsing Detail */}
                <div
                  className="field-card-top clickable"
                  onClick={() => toggleField(field.field_id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && toggleField(field.field_id)}
                >
                  <div className="field-title-area">
                    <h4 className="field-name">{field.field_name}</h4>
                    <span className="field-rule-ref">{field.rule_reference}</span>
                  </div>

                  <div className="field-top-right">
                    <span className={`field-verdict-badge ${badgeClass}`}>
                      {field.verdict}
                    </span>
                    <button
                      type="button"
                      className="field-chevron-btn"
                      aria-label={isExpanded ? 'Collapse section' : 'Expand section'}
                    >
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </div>
                </div>

                {/* Collapsible Details Body */}
                {isExpanded && (
                  <div className="field-collapse-body">
                    <div className="field-value-row">
                      <span className="value-label">Extracted Value:</span>
                      <div className="value-box">
                        <code>{field.extracted_value || 'None detected'}</code>
                      </div>
                    </div>

                    <div className="field-reason-row">
                      <span className="reason-bullet">•</span>
                      <p className="field-reason-text">{field.reason}</p>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
