import React from 'react';
import PackTrueLogo from './PackTrueLogo';
import { ArrowRight, ShieldCheck, Scale, FileCheck2, AlertTriangle, Building2, Calendar, PhoneCall, DollarSign } from 'lucide-react';

export default function LandingPage({ onStartScan }) {
  const mandatoryFields = [
    {
      icon: <Building2 size={20} />,
      title: 'Manufacturer & Packer Details',
      rule: 'Rule 6(1)(a)',
      desc: 'Name and complete postal address including locality, state, and 6-digit PIN code.'
    },
    {
      icon: <Scale size={20} />,
      title: 'Net Quantity Declaration',
      rule: 'Rule 6(1)(b) & Rule 12',
      desc: 'Standard metric SI units (g, kg, ml, l, N) with statutory prefix and minimum font height.'
    },
    {
      icon: <DollarSign size={20} />,
      title: 'Maximum Retail Price (MRP)',
      rule: 'Rule 6(1)(e)',
      desc: 'Accurate currency declaration strictly with the mandatory "inclusive of all taxes" clause.'
    },
    {
      icon: <Calendar size={20} />,
      title: 'Month & Year of Manufacture',
      rule: 'Rule 6(1)(d)',
      desc: 'Unambiguous manufacturing, packaging, or import date displayed in standardized formats.'
    },
    {
      icon: <PhoneCall size={20} />,
      title: 'Consumer Care Grievance Details',
      rule: 'Rule 6(1)(f)',
      desc: 'Designated helpline telephone number and email address for consumer redressal.'
    },
    {
      icon: <FileCheck2 size={20} />,
      title: 'FSSAI License / Regulatory Registration',
      rule: 'FSS Regulations / DoCA Norms',
      desc: '14-digit statutory food safety license verification for pre-packaged edible items.'
    }
  ];

  return (
    <div className="landing-container">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-badge">
          <ShieldCheck size={16} />
          <span>Packaged Commodities Compliance Audit</span>
        </div>

        {/* Clickable Brand Logo & Wordmark */}
        <div
          className="hero-logo-container"
          onClick={onStartScan}
          title="Click to start compliance scan"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onStartScan()}
        >
          <PackTrueLogo size={64} className="hero-logo-svg" />
          <h1 className="hero-title">
            PackTrue
          </h1>
        </div>

        <p className="hero-tagline">
          Accurate label compliance checks, no false alarms.
        </p>

        <p className="hero-description">
          Automated statutory compliance auditing for packaged commodity labels under the Legal Metrology (Packaged Commodities) Rules, 2011.
        </p>

        <div className="hero-actions">
          <button className="btn btn-hero" onClick={onStartScan}>
            <span>Start Compliance Scan</span>
            <ArrowRight size={18} />
          </button>
        </div>
      </section>

      {/* 3-Tier Preliminary Assessment Framework */}
      <section className="tier-overview-section">
        <div className="section-header-centered">
          <span className="section-kicker">Statutory Assessment Framework</span>
          <h2>3-Tier Legal Metrology Classification</h2>
          <p>
            Eliminates false positives by evaluating declarations in structured statutory context rather than raw text matching.
          </p>
        </div>

        <div className="tiers-grid">
          <div className="tier-card tier-card-compliant">
            <div className="tier-pill-wrapper">
              <span className="tier-pill tier-pill-green">Compliant</span>
            </div>
            <h3>Statutory Standards Met</h3>
            <p>
              Mandatory declaration is present, correctly formatted, and adheres to Legal Metrology 2011 guidelines.
            </p>
          </div>

          <div className="tier-card tier-card-advisory">
            <div className="tier-pill-wrapper">
              <span className="tier-pill tier-pill-advisory">Compliant — Packaging Advisory</span>
            </div>
            <h3>Minor Packaging Observation</h3>
            <p>
              Field is present and technically legal, but has an advisory note (e.g. omitted "inclusive of all taxes" clause, single contact channel, or ambiguous date prefix).
            </p>
          </div>

          <div className="tier-card tier-card-violation">
            <div className="tier-pill-wrapper">
              <span className="tier-pill tier-pill-red">Non-Compliant</span>
            </div>
            <h3>Statutory Violation / Missing</h3>
            <p>
              Mandatory statutory declaration is missing entirely or in clear violation of Legal Metrology Rule 6.
            </p>
          </div>
        </div>
      </section>

      {/* Mandatory Scope of Audit */}
      <section className="scope-section">
        <div className="section-header-centered">
          <span className="section-kicker">Automated Verification Scope</span>
          <h2>Mandatory Declarations Checked</h2>
        </div>

        <div className="scope-grid">
          {mandatoryFields.map((field, idx) => (
            <div key={idx} className="scope-card">
              <div className="scope-icon-box">{field.icon}</div>
              <div className="scope-card-content">
                <span className="scope-rule-tag">{field.rule}</span>
                <h4>{field.title}</h4>
                <p>{field.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Call to Action Footer Band */}
      <section className="cta-band">
        <div className="cta-content">
          <h3>Ready to inspect a packaged commodity label?</h3>
          <p>Upload a clear photo or packaging artwork to generate an instant statutory compliance report.</p>
        </div>
        <button className="btn btn-hero" onClick={onStartScan}>
          <span>Open Scanner Tool</span>
          <ArrowRight size={18} />
        </button>
      </section>
    </div>
  );
}
