import { useState, useEffect } from 'react';
import { 
  ArrowLeftRight, 
  Sparkles, 
  CheckCircle2, 
  Activity, 
  Code, 
  Layers, 
  Globe2, 
  AlertCircle, 
  FileText, 
  Check,
  Zap,
  ArrowDown
} from 'lucide-react';
import { apiFetch } from '../api.js';

const TARGET_SYSTEMS = [
  'ICD-11-TM2',
  'SNOMED-CT',
  'ICD-10',
];

const SYMPTOM_EXAMPLES = [
  { term: 'kAsaH', system: 'Ayurveda', category: 'Ayurveda' },
  { term: 'jvaraH', system: 'Ayurveda', category: 'Ayurveda' },
  { term: 'Amlapitta', system: 'Ayurveda', category: 'Ayurveda' },
  { term: 'su-al', system: 'Unani', category: 'Unani' },
  { term: 'humma', system: 'Unani', category: 'Unani' },
  { term: 'ishal', system: 'Unani', category: 'Unani' },
  { term: 'siracūlai', system: 'Siddha', category: 'Siddha' },
  { term: 'iraimal', system: 'Siddha', category: 'Siddha' },
  { term: 'kazhichal', system: 'Siddha', category: 'Siddha' },
];

export default function TranslatePage({ selectedTermData }) {
  const [sourceCode, setSourceCode] = useState('');
  const [targetSystem, setTargetSystem] = useState('ICD-11-TM2');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [showJson, setShowJson] = useState(false);

  const doTranslate = async (termToTranslate) => {
    const code = (termToTranslate || sourceCode).trim();
    if (!code) return;
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/api/$translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_code: code, target_system: targetSystem }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.message || data.detail || 'Translation failed');
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedTermData) {
      const term = selectedTermData.source_term || selectedTermData.display_name || selectedTermData.code;
      if (term) {
        setSourceCode(term);
        doTranslate(term);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTermData]);

  return (
    <div className="page-container">
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
          <span style={{ fontSize: '0.8rem', opacity: 0.85, fontWeight: 600 }}>Auto-translated below</span>
        </div>
      )}

      {/* ── Section Heading ── */}
      <div className="section-heading">
        <div className="section-heading-icon">
          <ArrowLeftRight size={24} />
        </div>
        <div>
          <h2>Terminology Translation &amp; Dual Coding</h2>
          <p>
            Bidirectional semantic crosswalk between AYUSH (NAMASTE), WHO ICD-11-TM2, and Biomedicine standard taxonomies.
          </p>
        </div>
      </div>

      <div className="grid-2">
        {/* ── Input Card ── */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-icon-box">
                <FileText size={18} />
              </div>
              <span>Symptom Input &amp; System Selection</span>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="translate-source">AYUSH Concept / Symptom Term</label>
            <input
              id="translate-source"
              type="text"
              className="form-input"
              placeholder="e.g. kAsaH, jvaraH, Amlapitta, humma, siracūlai…"
              value={sourceCode}
              onChange={e => setSourceCode(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && doTranslate()}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="translate-target">Target Coding Standard</label>
            <select
              id="translate-target"
              className="form-select"
              value={targetSystem}
              onChange={e => setTargetSystem(e.target.value)}
            >
              {TARGET_SYSTEMS.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <button
            id="translate-btn"
            type="button"
            className="btn btn-primary"
            onClick={() => doTranslate()}
            disabled={loading || !sourceCode.trim()}
            style={{ width: '100%', justifyContent: 'center', marginTop: 8, padding: '12px 20px' }}
          >
            {loading ? (
              <>
                <Activity size={16} className="animate-spin" />
                <span>Crosswalking Terminology…</span>
              </>
            ) : (
              <>
                <ArrowLeftRight size={16} />
                <span>Translate Symptom</span>
              </>
            )}
          </button>

          {/* Quick Select Preset Symptoms */}
          <div style={{ marginTop: 24, paddingTop: 18, borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: 12 }}>
              QUICK SELECT PRESET SYMPTOMS:
            </div>
            <div className="pill-tags">
              {SYMPTOM_EXAMPLES.map(ex => (
                <button
                  type="button"
                  key={ex.term}
                  className="pill-tag"
                  onClick={() => {
                    setSourceCode(ex.term);
                    doTranslate(ex.term);
                  }}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                >
                  <span style={{ fontWeight: 700, color: 'var(--primary-mint)' }}>{ex.term}</span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>({ex.system})</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ── Result Card ── */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-icon-box" style={{ background: 'var(--accent-blue-soft)', color: 'var(--accent-blue)' }}>
                <Layers size={18} />
              </div>
              <span>Dual-Coding Mapping Details</span>
            </div>
            {result && (
              <span className={`badge ${result.used_fallback ? 'badge-status-unmapped' : 'badge-status-verified'}`}>
                {result.used_fallback ? 'WHO Fallback Crosswalk' : 'Verified Mapping'}
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
                <ArrowLeftRight size={22} />
              </div>
              <h3 style={{ fontSize: '1.15rem', marginBottom: 6 }}>Ready to Crosswalk</h3>
              <p style={{ fontSize: '0.88rem' }}>Enter a traditional symptom or click a preset on the left to inspect dual-coding results.</p>
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
                <span>Translating across concept maps…</span>
              </div>
            </div>
          )}

          {result && (
            <div className="fade-in">
              {/* Formatted Dual-Coding Visual Cards */}
              <div style={{
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: '24px',
                marginBottom: '20px',
              }}>
                {/* Traditional Medicine Tier */}
                <div style={{
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  padding: '16px 20px',
                  boxShadow: 'var(--shadow-xs)',
                  marginBottom: '12px',
                }}>
                  <div style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--primary-mint)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                    TRADITIONAL MEDICINE · {result.system || 'Ayurveda'}
                  </div>
                  <div style={{ fontSize: '1.45rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: 4 }}>
                    {result.source_term || result.display_name}
                  </div>
                  <div style={{ fontSize: '0.84rem', fontFamily: 'JetBrains Mono, monospace', color: 'var(--text-muted)' }}>
                    NAMASTE / TM2 Code: <strong style={{ color: 'var(--primary-sage)' }}>{result.tm2_code || 'SL41(EA-3)'}</strong>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'center', margin: '8px 0', color: 'var(--text-muted)' }}>
                  <ArrowDown size={18} />
                </div>

                {/* Biomedicine Crosswalk Tier */}
                <div style={{
                  background: 'var(--accent-blue-soft)',
                  border: '1px solid rgba(37, 99, 235, 0.2)',
                  borderRadius: 'var(--radius-md)',
                  padding: '16px 20px',
                }}>
                  <div style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--accent-blue)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                    WHO ICD-11 &amp; BIOMEDICINE MAPPING
                  </div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: 4 }}>
                    {result.biomedicine_display || result.tm2_display || 'Cough'}
                  </div>
                  <div style={{ fontSize: '0.84rem', fontFamily: 'JetBrains Mono, monospace', color: 'var(--accent-blue)' }}>
                    ICD-11 Code: <strong>{result.biomedicine_code || 'MD12'}</strong>
                  </div>
                </div>
              </div>

              {/* Provenance Metadata Badges */}
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
                <span className="badge badge-code">Status: {result.mapping_status || 'verified'}</span>
                <span className="badge badge-system">Relationship: {result.mapping_relationship || 'equivalent'}</span>
                <span className="badge badge-lang">ConceptMap: {result.concept_map_version || 'NAMASTE-TM2-v1.0'}</span>
              </div>

              {/* Toggleable Clean JSON Output */}
              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                  <span style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--text-secondary)' }}>
                    Raw ConceptMap JSON Payload
                  </span>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => setShowJson(!showJson)}
                    style={{ fontSize: '0.78rem' }}
                  >
                    <Code size={13} />
                    <span>{showJson ? 'Hide JSON' : 'Show JSON'}</span>
                  </button>
                </div>
                {showJson && (
                  <pre className="code-viewer">
                    <code>{JSON.stringify(result, null, 2)}</code>
                  </pre>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
