import { useState, useEffect } from 'react';
import { 
  PackageCheck, 
  Sparkles, 
  CheckCircle2, 
  Activity, 
  FileText, 
  Layers, 
  AlertCircle, 
  ShieldCheck, 
  Check, 
  XCircle, 
  Send, 
  RefreshCw, 
  UserCheck, 
  Stethoscope, 
  HeartPulse,
  Code,
  ShieldAlert
} from 'lucide-react';
import AnimatedNumber from '../components/AnimatedNumber.jsx';
import { apiFetch } from '../api.js';

const MOCK_TOKEN = 'test-mock-token';

const PRESET_SYMPTOMS = [
  { term: 'hikkA (hidhmA)', system: 'Ayurveda', tm2: 'SM74(EA-2)', icd11: 'MD12', icd11_disp: 'Cough' },
  { term: 'kAsaH',          system: 'Ayurveda', tm2: 'SL41(EA-3)', icd11: 'MD12', icd11_disp: 'Cough' },
  { term: 'jvaraH',         system: 'Ayurveda', tm2: 'SP51(EC-3)', icd11: 'MG26', icd11_disp: 'Fever of unknown origin' },
  { term: 'Amlapitta',      system: 'Ayurveda', tm2: 'DA01',       icd11: 'DA22', icd11_disp: 'Dyspepsia' },
  { term: 'su-al',          system: 'Unani',    tm2: 'UE-01',      icd11: 'MD12', icd11_disp: 'Cough' },
  { term: 'humma',          system: 'Unani',    tm2: 'UE-02',      icd11: 'MG26', icd11_disp: 'Fever' },
  { term: 'ishal',          system: 'Unani',    tm2: 'UE-03',      icd11: 'DD91', icd11_disp: 'Diarrhoea' },
  { term: 'siracūlai',      system: 'Siddha',   tm2: 'SE-01',      icd11: 'MB46', icd11_disp: 'Headache' },
  { term: 'iraimal',        system: 'Siddha',   tm2: 'SE-02',      icd11: 'CA23', icd11_disp: 'Asthma' },
  { term: 'kazhichal',      system: 'Siddha',   tm2: 'SE-03',      icd11: 'DD91', icd11_disp: 'Diarrhoea' },
];

function generateBundleForSymptom(term, system = 'Ayurveda', tm2Code = 'SM74(EA-2)', icdCode = 'MD12', icdDisp = 'Cough', patientRef = 'Patient/example') {
  return {
    resourceType: 'Bundle',
    type: 'transaction',
    entry: [
      {
        resource: {
          resourceType: 'Condition',
          code: {
            coding: [
              {
                system: 'http://namaste.ayush.gov.in',
                code: tm2Code,
                display: term
              },
              {
                system: 'http://id.who.int/icd/release/11/mms',
                code: icdCode,
                display: icdDisp
              }
            ],
            text: `${term} (${system} - ${icdDisp})`
          },
          subject: { reference: patientRef }
        }
      }
    ]
  };
}

export default function BundlePage({ selectedTermData, currentUser, selectedPatient, onAddToHistory }) {
  const [selectedSymptom, setSelectedSymptom] = useState('');
  const [symptomsInput, setSymptomsInput] = useState('');
  const [suggestedCode, setSugg] = useState('');
  const [correctedCode, setCorr] = useState('');
  const [bundleJson, setBundleJson] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  const [lastSubmitted, setLastSubmitted] = useState(null);
  const [currentSymbolObj, setCurrentSymptomObj] = useState(null);

  const applySymptom = (sym) => {
    setSelectedSymptom(sym.term);
    setSymptomsInput(sym.term);
    setSugg(sym.tm2);
    setCurrentSymptomObj(sym);
    const patRef = selectedPatient
      ? `Patient/${selectedPatient.abhaId || selectedPatient.id}`
      : 'Patient/example';
    const bundle = generateBundleForSymptom(sym.term, sym.system, sym.tm2, sym.icd11, sym.icd11_disp, patRef);
    setBundleJson(JSON.stringify(bundle, null, 2));
  };

  useEffect(() => {
    if (selectedTermData) {
      const term = selectedTermData.source_term || selectedTermData.display_name || selectedTermData.code || 'Symptom';
      const system = selectedTermData.system || 'Ayurveda';
      const tm2 = selectedTermData.tm2_code || selectedTermData.code || 'SM74(EA-2)';
      const icd11 = selectedTermData.biomedicine_code || 'MD12';
      const icd11_disp = selectedTermData.biomedicine_display || selectedTermData.tm2_display || selectedTermData.display_name || 'Clinical Condition';
      applySymptom({ term, system, tm2, icd11, icd11_disp });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTermData]);

  const handleCustomSymptomChange = (text) => {
    setSymptomsInput(text);
    const match = PRESET_SYMPTOMS.find(s => s.term.toLowerCase() === text.trim().toLowerCase());
    if (match) {
      applySymptom(match);
    } else {
      setCurrentSymptomObj(null);
      const patRef = selectedPatient ? `Patient/${selectedPatient.abhaId || selectedPatient.id}` : 'Patient/example';
      const bundle = generateBundleForSymptom(text || 'symptom', 'AYUSH', 'AAC-01', 'MD12', text || 'Clinical Condition', patRef);
      setBundleJson(JSON.stringify(bundle, null, 2));
    }
  };

  const doSubmit = async () => {
    if (!selectedPatient) {
      setError('Please select a patient from the People tab before submitting a FHIR Bundle.');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setSubmitted(false);

    let bundle;
    try {
      bundle = JSON.parse(bundleJson);
    } catch {
      setError('Invalid JSON format in bundle editor.');
      setLoading(false);
      return;
    }

    try {
      const body = { bundle };
      if (symptomsInput) body.input_symptoms = symptomsInput;
      if (suggestedCode) body.suggested_code = suggestedCode;
      if (correctedCode) body.corrected_code = correctedCode;

      const res = await apiFetch('/api/Bundle', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${MOCK_TOKEN}`,
        },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        let errMsg = 'Bundle submission failed.';
        if (typeof detail === 'string') {
          errMsg = detail;
        } else if (detail?.message) {
          errMsg = detail.message;
        } else if (detail?.error === 'icd11_rule_violation') {
          errMsg = `Validation: ${detail.message || 'ICD-11 rule violation.'} ${detail.corrected_suggestion ? `(Suggestion: ${detail.corrected_suggestion})` : ''}`;
        } else if (detail?.error === 'pbac_denied') {
          errMsg = `Access Denied: ${detail.reason || 'Insufficient role permissions.'}`;
        } else if (detail) {
          errMsg = JSON.stringify(detail);
        }
        throw new Error(errMsg);
      }
      setResult(data);

      // Add to history
      const now = new Date();
      const dateStr = now.toISOString().split('T')[0];
      const sym = currentSymbolObj || {
        term: symptomsInput || 'Clinical Condition',
        system: 'Ayurveda',
        tm2: suggestedCode || 'AAC-01',
        icd11: 'MD12',
        icd11_disp: 'Clinical Condition',
      };

      const historyEntry = {
        id: `h-${Date.now()}`,
        patientId: selectedPatient.id,
        patientName: selectedPatient.name,
        patientAbha: selectedPatient.abhaId || selectedPatient.id,
        submittedBy: currentUser?.name || 'Unknown Doctor',
        term: sym.term,
        system: sym.system,
        tm2Code: sym.tm2,
        icdCode: sym.icd11,
        icdDisplay: sym.icd11_disp,
        addedDate: dateStr,
      };

      if (onAddToHistory) onAddToHistory(historyEntry);
      setLastSubmitted(historyEntry);
      setSubmitted(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Role Guard
  if (!currentUser || (currentUser.role !== 'doctor' && currentUser.role !== 'admin')) {
    return (
      <div className="page-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 460 }}>
        <div className="card fade-in" style={{ textAlign: 'center', maxWidth: 480, padding: '48px 36px', borderRadius: 'var(--radius-xl)' }}>
          <div style={{
            width: 60,
            height: 60,
            borderRadius: 'var(--radius-lg)',
            background: 'var(--accent-rose-soft)',
            color: 'var(--accent-rose)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px'
          }}>
            <ShieldAlert size={28} />
          </div>
          <h3 style={{ fontSize: '1.4rem', marginBottom: 12 }}>Access Restricted</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem' }}>
            FHIR R4 Bundle submission is restricted to registered <strong>Doctors</strong> and <strong>Administrators</strong>.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Patient context banner */}
      {selectedPatient ? (
        <div className="alert alert-info" style={{ marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <HeartPulse size={18} color="var(--primary-mint)" />
            <span>Target Patient: <strong style={{ color: 'var(--text-primary)' }}>{selectedPatient.name}</strong></span>
            <span className="badge badge-code">ABHA: {selectedPatient.abhaId || selectedPatient.id}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.84rem' }}>
            <Stethoscope size={14} color="var(--primary-sage)" />
            <span>Practitioner: <strong>{currentUser?.name}</strong></span>
          </div>
        </div>
      ) : (
        <div className="alert alert-warning" style={{ marginBottom: 24 }}>
          <AlertCircle size={18} />
          <div>
            <strong>No active patient selected.</strong> Please open the <strong>People</strong> tab and select a patient before submitting a bundle.
          </div>
        </div>
      )}

      {/* Selected Term Banner */}
      {selectedTermData && (
        <div className="alert alert-info" style={{ marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <Sparkles size={16} />
            <span>Active Term from Search: <strong style={{ color: 'var(--text-primary)' }}>{selectedTermData.source_term || selectedTermData.display_name}</strong></span>
            {selectedTermData.system && (
              <span className="badge badge-system">{selectedTermData.system}</span>
            )}
            {selectedTermData.tm2_code && (
              <span className="badge badge-code">TM2: {selectedTermData.tm2_code}</span>
            )}
          </div>
          <span style={{ fontSize: '0.8rem', opacity: 0.85, fontWeight: 600 }}>FHIR Bundle Configured</span>
        </div>
      )}

      {/* Submission Success Alert */}
      {submitted && lastSubmitted && (
        <div className="alert alert-success" style={{ marginBottom: 24 }}>
          <CheckCircle2 size={20} />
          <div>
            <strong>FHIR R4 Bundle successfully created &amp; logged to patient history!</strong>
            <div style={{ fontSize: '0.82rem', marginTop: 4, color: '#065f46' }}>
              Condition: <strong>{lastSubmitted.term}</strong> · ICD-11: <strong>{lastSubmitted.icdCode}</strong> ({lastSubmitted.icdDisplay}) · Patient: {lastSubmitted.patientName}
            </div>
          </div>
        </div>
      )}

      {/* Section Heading */}
      <div className="section-heading">
        <div className="section-heading-icon">
          <PackageCheck size={24} />
        </div>
        <div>
          <h2>FHIR R4 Clinical Bundle Authoring Studio</h2>
          <p>
            Standardize and submit dual-coded Ayurveda, Unani, or Siddha diagnostic entries as transactional FHIR R4 Bundles.
          </p>
        </div>
      </div>

      {/* Symptom Selection Card */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <div className="card-title">
            <div className="card-icon-box">
              <FileText size={18} />
            </div>
            <span>Clinical Symptom / Diagnosis Selection</span>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="bundle-symptom-input">Input AYUSH Diagnostic Concept</label>
          <input
            id="bundle-symptom-input"
            type="text"
            className="form-input"
            placeholder="e.g. hikkA (hidhmA), kAsaH, jvaraH, Amlapitta, humma, siracūlai…"
            value={symptomsInput}
            onChange={e => handleCustomSymptomChange(e.target.value)}
          />
        </div>

        <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: 12 }}>
          PRESET CLINICAL CONDITIONS:
        </div>
        <div className="pill-tags">
          {PRESET_SYMPTOMS.map(sym => (
            <button
              key={sym.term}
              type="button"
              className={`pill-tag ${selectedSymptom === sym.term ? 'active' : ''}`}
              onClick={() => applySymptom(sym)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
            >
              <span>{sym.term}</span>
              <span style={{ fontSize: '0.72rem', opacity: 0.8 }}>({sym.system})</span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid-2">
        {/* Bundle JSON Editor */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-icon-box" style={{ background: 'var(--accent-blue-soft)', color: 'var(--accent-blue)' }}>
                <Code size={18} />
              </div>
              <span>FHIR R4 Bundle Specification</span>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => handleCustomSymptomChange(symptomsInput)}
            >
              <RefreshCw size={13} />
              <span>Regenerate</span>
            </button>
          </div>

          <textarea
            id="bundle-editor"
            className="form-textarea"
            style={{ minHeight: 280, fontSize: '0.82rem', lineHeight: 1.55 }}
            placeholder="Select a symptom above to generate the standardized FHIR R4 Bundle payload..."
            value={bundleJson}
            onChange={e => setBundleJson(e.target.value)}
            spellCheck={false}
          />

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginTop: 18 }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" htmlFor="suggested-code">AYUSH / TM2 Code</label>
              <input 
                id="suggested-code" 
                type="text" 
                className="form-input"
                placeholder="e.g. SM74(EA-2)"
                value={suggestedCode} 
                onChange={e => setSugg(e.target.value)} 
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" htmlFor="corrected-code">Corrected Code (Optional)</label>
              <input 
                id="corrected-code" 
                type="text" 
                className="form-input"
                placeholder="e.g. EA-3.2"
                value={correctedCode} 
                onChange={e => setCorr(e.target.value)} 
              />
            </div>
          </div>

          <button
            id="bundle-submit-btn"
            type="button"
            className="btn btn-primary btn-lg"
            onClick={doSubmit}
            disabled={loading || !selectedPatient}
            style={{
              width: '100%',
              justifyContent: 'center',
              marginTop: 20,
              padding: '13px 20px',
            }}
          >
            {loading ? (
              <>
                <Activity size={16} className="animate-spin" />
                <span>Validating &amp; Submitting to NHCX…</span>
              </>
            ) : !selectedPatient ? (
              <>
                <AlertCircle size={16} />
                <span>Select a Patient to Submit</span>
              </>
            ) : (
              <>
                <Send size={16} />
                <span>Submit FHIR Bundle to Patient History</span>
              </>
            )}
          </button>
        </div>

        {/* Submission Receipt / Response */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-icon-box" style={{ background: 'var(--accent-emerald-soft)', color: 'var(--accent-emerald)' }}>
                <CheckCircle2 size={18} />
              </div>
              <span>Submission Receipt &amp; Validation</span>
            </div>
            {result && (
              <span className="badge badge-status-verified">
                {result.bundle_id ? `ID: ${result.bundle_id.slice(0, 8)}…` : 'Persisted'}
              </span>
            )}
          </div>

          {error && (
            <div className="alert alert-error">
              <AlertCircle size={18} />
              <div>{error}</div>
            </div>
          )}

          {!result && !error && !loading && (
            <div style={{ textAlign: 'center', padding: '48px 24px' }}>
              <div style={{
                width: 48,
                height: 48,
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-subtle)',
                color: 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px'
              }}>
                <PackageCheck size={22} />
              </div>
              <h3 style={{ fontSize: '1.15rem', marginBottom: 6 }}>Ready for Submission</h3>
              <p style={{ fontSize: '0.88rem' }}>Verify the payload in the editor and submit to execute schema validation and record creation.</p>
            </div>
          )}

          {loading && (
            <div style={{ textAlign: 'center', padding: '60px 0' }}>
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 10,
                background: 'var(--bg-subtle)',
                padding: '12px 24px',
                borderRadius: 'var(--radius-pill)',
                color: 'var(--primary-mint)',
                fontWeight: 600,
                fontSize: '0.9rem'
              }}>
                <Activity size={18} className="animate-spin" />
                <span>Executing FHIR R4 validation rules…</span>
              </div>
            </div>
          )}

          {result && (
            <div className="fade-in">
              {/* Validation Pipeline Summary */}
              {result.validation && (
                <div style={{ marginBottom: 18 }}>
                  <div style={{ fontWeight: 700, marginBottom: 8, color: 'var(--text-secondary)', fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Schema Validation Pipeline
                  </div>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '12px 16px',
                    background: result.validation.valid ? 'var(--accent-emerald-soft)' : 'var(--accent-rose-soft)',
                    border: `1px solid ${result.validation.valid ? 'rgba(5, 150, 105, 0.25)' : 'rgba(225, 29, 72, 0.25)'}`,
                    borderRadius: 'var(--radius-md)',
                  }}>
                    {result.validation.valid ? (
                      <CheckCircle2 size={20} color="var(--accent-emerald)" />
                    ) : (
                      <XCircle size={20} color="var(--accent-rose)" />
                    )}
                    <div>
                      <div style={{ fontSize: '0.92rem', fontWeight: 700, color: result.validation.valid ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                        {result.validation.valid ? 'FHIR R4 & ICD-11 TM2 Validation Passed' : 'Validation Error Encountered'}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                        {result.validation.message || 'All dual codings adhere strictly to National Health Standards.'}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* NHCX Claim Readiness */}
              {result.claimReadiness && (
                <div style={{ marginBottom: 20 }}>
                  <div style={{ fontWeight: 700, marginBottom: 8, color: 'var(--text-secondary)', fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    NHCX Insurance Claim Readiness
                  </div>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '12px 16px',
                    background: result.claimReadiness.claimReadiness ? 'var(--accent-blue-soft)' : 'var(--accent-amber-soft)',
                    border: `1px solid ${result.claimReadiness.claimReadiness ? 'rgba(37, 99, 235, 0.2)' : 'rgba(217, 119, 6, 0.25)'}`,
                    borderRadius: 'var(--radius-md)',
                  }}>
                    <ShieldCheck size={20} color={result.claimReadiness.claimReadiness ? 'var(--accent-blue)' : 'var(--accent-amber)'} />
                    <div>
                      <div style={{ fontSize: '0.92rem', fontWeight: 700, color: result.claimReadiness.claimReadiness ? 'var(--accent-blue)' : 'var(--accent-amber)' }}>
                        {result.claimReadiness.claimReadiness ? 'Approved for NHCX Auto-Claim Adjudication' : 'Manual Audit Recommended'}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                        Confidence Index: <strong>
                          <AnimatedNumber value={result.claimReadiness.claimReadinessScore * 100} suffix="%" duration={1200} />
                        </strong>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 8 }}>
                Server Response Payload:
              </div>
              <pre className="code-viewer">
                <code>{JSON.stringify(result, null, 2)}</code>
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
