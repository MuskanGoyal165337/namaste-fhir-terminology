import { useState, useCallback } from 'react';
import { 
  Search, 
  Sparkles, 
  CheckCircle2, 
  Activity, 
  Filter, 
  Layers, 
  ArrowRight, 
  SlidersHorizontal, 
  Cpu, 
  Info, 
  Check, 
  AlertCircle,
  Hash,
  Globe2,
  FileText
} from 'lucide-react';
import AnimatedNumber from '../components/AnimatedNumber.jsx';

const SYSTEMS = ['', 'Ayurveda', 'Siddha', 'Unani', 'Yoga & Naturopathy'];
const LANGUAGES = ['', 'en', 'sa', 'hi', 'ta', 'ur'];

const SUGGESTED = [
  'jwara', 'vata', 'kapha', 'pitta', 'amavata', 'shirodhara',
  'pAdadAhaH', 'trisha', 'shotha', 'arshas',
];

const getMethodClass = (m) => {
  if (m === 'exact')     return 'method-exact';
  if (m === 'substring') return 'method-substring';
  return 'method-semantic';
};

function XAIBar({ tokens }) {
  if (!tokens || tokens.length === 0) return null;
  const max = Math.max(...tokens.map(t => Math.abs(t.score)));
  return (
    <div className="xai-section">
      <div className="xai-title">
        <Cpu size={14} color="var(--primary-mint)" />
        <span>XAI Token Attention Weights (BioBERT)</span>
      </div>
      <div className="xai-tokens">
        {tokens.map((t, i) => {
          const intensity = max > 0 ? Math.abs(t.score) / max : 0;
          const alpha = 0.08 + intensity * 0.4;
          return (
            <span
              key={i}
              className="xai-token"
              title={`Score: ${t.score.toFixed(3)}`}
              style={{ background: `rgba(13, 148, 136, ${alpha})` }}
            >
              {t.token}
            </span>
          );
        })}
      </div>
    </div>
  );
}

function ResultCard({ result, isSelected, onSelectTerm }) {
  const statusClass = result.mapping_status === 'verified' ? 'badge-status-verified' : 'badge-status-unmapped';

  return (
    <div
      id={`result-${result.source_term?.replace(/\s+/g, '-')}`}
      className={`result-card fade-in${isSelected ? ' selected' : ''}`}
    >
      <div className="result-header">
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <div className="result-term">{result.source_term}</div>
            {isSelected && (
              <span className="badge badge-status-verified" style={{ fontSize: '0.74rem' }}>
                <Check size={12} />
                <span>Active Selection</span>
              </span>
            )}
          </div>
          {result.display_name && result.display_name !== result.source_term && (
            <div className="result-english">{result.display_name}</div>
          )}
        </div>
        <span className={`results-method ${getMethodClass(result.match_method)}`}>
          {result.match_method} Match
        </span>
      </div>

      <div className="result-meta">
        {result.system && (
          <span className="badge badge-system">{result.system}</span>
        )}
        {result.tm2_code && (
          <span className="badge badge-code">TM2: {result.tm2_code}</span>
        )}
        {result.language && (
          <span className="badge badge-lang">{result.language}</span>
        )}
        {result.mapping_status && (
          <span className={`badge ${statusClass}`}>{result.mapping_status}</span>
        )}
      </div>

      {result.similarity != null && (
        <div className="similarity-bar-wrap">
          <span className="similarity-label">Semantic Match Score</span>
          <div className="similarity-bar">
            <div className="similarity-fill" style={{ width: `${(result.similarity * 100).toFixed(0)}%` }} />
          </div>
          <span className="similarity-value">
            <AnimatedNumber value={result.similarity * 100} suffix="%" decimals={1} duration={1400} />
          </span>
        </div>
      )}

      {/* Direct Metadata details */}
      <div style={{
        background: 'var(--bg-subtle)',
        borderRadius: 'var(--radius-sm)',
        padding: '12px 14px',
        fontSize: '0.84rem',
        marginTop: '10px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '8px',
      }}>
        {result.tm2_display && (
          <div>
            <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>TM2 Display: </span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{result.tm2_display}</span>
          </div>
        )}
        {result.mapping_relationship && (
          <div>
            <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Relationship: </span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{result.mapping_relationship}</span>
          </div>
        )}
        {result.mapping_source && (
          <div>
            <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Source Standard: </span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{result.mapping_source}</span>
          </div>
        )}
      </div>

      <XAIBar tokens={result.xai_weights} />

      {/* Select Term Button */}
      <div style={{
        marginTop: 18,
        paddingTop: 14,
        borderTop: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 10
      }}>
        <button
          type="button"
          className={`btn ${isSelected ? 'btn-primary' : 'btn-secondary'}`}
          style={{
            padding: '8px 18px',
            fontSize: '0.84rem',
            fontWeight: 700,
          }}
          onClick={() => onSelectTerm(result)}
        >
          {isSelected ? (
            <>
              <CheckCircle2 size={15} />
              <span>Selected for Translation &amp; FHIR Bundle</span>
            </>
          ) : (
            <>
              <ArrowRight size={15} />
              <span>Select as Input Term</span>
            </>
          )}
        </button>

        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          {isSelected ? 'Active context for downstream translation & bundle authoring' : 'Sets active symptom across portal'}
        </span>
      </div>
    </div>
  );
}

export default function SearchPage({ selectedTermData, onSelectTerm }) {
  const [query, setQuery]       = useState('');
  const [system, setSystem]     = useState('');
  const [lang, setLang]         = useState('');
  const [limit, setLimit]       = useState(10);
  const [loading, setLoading]   = useState(false);
  const [results, setResults]   = useState(null);
  const [error, setError]       = useState(null);

  const doSearch = useCallback(async (q) => {
    const term = (q ?? query).trim();
    if (!term) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const params = new URLSearchParams({ q: term, limit });
      if (system) params.set('system', system);
      if (lang)   params.set('lang', lang);
      const res = await fetch(`/api/$expand?${params}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail?.message || data.detail || 'Search failed');
      setResults(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [query, system, lang, limit]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') doSearch();
  };

  return (
    <div className="page-container">
      {/* ── Heading ── */}
      <div className="section-heading">
        <div className="section-heading-icon">
          <Search size={24} />
        </div>
        <div>
          <h2>Traditional Medicine Terminology Search</h2>
          <p>
            Explore 18,500+ AYUSH concepts with 3-tier cascade: Exact Hash → SQL Substring → BioBERT Semantic Search.
          </p>
        </div>
      </div>

      {/* ── Search Hero Box ── */}
      <div className="search-hero-box">
        <div className="search-input-wrap">
          <Search size={20} className="search-icon-left" />
          <input
            id="search-input"
            type="text"
            className="search-input-field"
            placeholder="Search symptoms, diseases, formulations (e.g. jwara, vata, amavata, pAdadAhaH)..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            autoComplete="off"
          />
          <button
            id="search-btn"
            type="button"
            className="btn btn-primary"
            onClick={() => doSearch()}
            disabled={loading || !query.trim()}
            style={{
              position: 'absolute',
              right: 8,
              padding: '10px 24px',
              borderRadius: 'var(--radius-pill)',
            }}
          >
            {loading ? 'Searching…' : 'Search Term'}
          </button>
        </div>

        {/* Filter Controls */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          marginTop: 18,
          flexWrap: 'wrap',
          paddingTop: 14,
          borderTop: '1px solid var(--border-subtle)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-muted)', fontSize: '0.84rem', fontWeight: 600 }}>
            <SlidersHorizontal size={14} />
            <span>Filters:</span>
          </div>

          <select
            id="filter-system"
            className="form-select"
            style={{ width: 'auto', padding: '6px 12px', fontSize: '0.84rem' }}
            value={system}
            onChange={e => setSystem(e.target.value)}
          >
            <option value="">All AYUSH Systems</option>
            {SYSTEMS.filter(Boolean).map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <select
            id="filter-lang"
            className="form-select"
            style={{ width: 'auto', padding: '6px 12px', fontSize: '0.84rem' }}
            value={lang}
            onChange={e => setLang(e.target.value)}
          >
            <option value="">All Languages</option>
            {LANGUAGES.filter(Boolean).map(l => (
              <option key={l} value={l}>{l.toUpperCase()}</option>
            ))}
          </select>

          <select
            id="filter-limit"
            className="form-select"
            style={{ width: 'auto', padding: '6px 12px', fontSize: '0.84rem' }}
            value={limit}
            onChange={e => setLimit(Number(e.target.value))}
          >
            {[5, 10, 20, 50].map(n => (
              <option key={n} value={n}>Top {n} Results</option>
            ))}
          </select>
        </div>

        {/* Suggested Pills */}
        {!results && (
          <div style={{ marginTop: 20 }}>
            <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8, letterSpacing: '0.04em' }}>
              SUGGESTED CLINICAL CONCEPTS:
            </div>
            <div className="pill-tags">
              {SUGGESTED.map(s => (
                <button
                  type="button"
                  key={s}
                  className="pill-tag"
                  onClick={() => { setQuery(s); doSearch(s); }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Error Banner ── */}
      {error && (
        <div className="alert alert-error">
          <AlertCircle size={18} />
          <div>{error}</div>
        </div>
      )}

      {/* ── Loading Spinner ── */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 10,
            background: 'var(--bg-surface)',
            padding: '12px 24px',
            borderRadius: 'var(--radius-pill)',
            border: '1px solid var(--border)',
            boxShadow: 'var(--shadow-sm)',
            color: 'var(--primary-mint)',
            fontWeight: 600,
            fontSize: '0.9rem'
          }}>
            <Activity size={18} className="animate-spin" />
            <span>Executing 3-tier cascade search…</span>
          </div>
        </div>
      )}

      {/* ── Search Results List ── */}
      {results && (
        <div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 20,
            flexWrap: 'wrap',
            gap: 10
          }}>
            <div style={{ fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
              Found <strong style={{ color: 'var(--text-primary)' }}>{results.total}</strong> results for{' '}
              <em style={{ color: 'var(--primary-mint)', fontWeight: 600 }}>"{results.query}"</em>
              {results.system_filter ? ` in ${results.system_filter}` : ''}
            </div>

            {results.results[0] && (
              <span className={`results-method ${getMethodClass(results.results[0].match_method)}`}>
                Top Match: {results.results[0].match_method}
              </span>
            )}
          </div>

          {results.total === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
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
                <Search size={22} />
              </div>
              <h3 style={{ fontSize: '1.15rem', marginBottom: 6 }}>No Terminology Matches Found</h3>
              <p style={{ fontSize: '0.88rem' }}>Please try a broader clinical term or adjust the system filters.</p>
            </div>
          ) : (
            results.results.map((r, i) => {
              const uniqueId = r._id || `result-${i}-${r.source_term}-${r.tm2_code || r.code || i}`;
              const itemWithId = { ...r, _id: uniqueId };
              const isSelected = Boolean(
                selectedTermData &&
                (selectedTermData._id === uniqueId ||
                 (selectedTermData.source_term === r.source_term &&
                  selectedTermData.tm2_code === r.tm2_code &&
                  selectedTermData.display_name === r.display_name))
              );

              return (
                <ResultCard
                  key={uniqueId}
                  result={itemWithId}
                  isSelected={isSelected}
                  onSelectTerm={onSelectTerm}
                />
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
