import { useState, useEffect } from 'react';
import { apiFetch } from '../api.js';

const MOCK_TOKEN = 'test-mock-token';

const SYSTEM_COLORS = {
  Ayurveda:           '#6384ff',
  Siddha:             '#a855f7',
  Unani:              '#22d3ee',
  Homeopathy:         '#f59e0b',
  'Yoga & Naturopathy': '#10b981',
};

const SYSTEM_COLOR_LIST = ['#6384ff', '#a855f7', '#22d3ee', '#f59e0b', '#10b981', '#f43f5e'];

function MorbidityChart({ items }) {
  if (!items?.length) return null;
  const max = Math.max(...items.map(i => i.count));
  return (
    <div className="bar-chart">
      {items.slice(0, 12).map((item, i) => (
        <div key={i} className="bar-item">
          <div className="bar-label" title={item.term}>{item.term}</div>
          <div className="bar-track">
            <div
              className="bar-fill"
              style={{
                width: max > 0 ? `${(item.count / max) * 100}%` : '0%',
                background: SYSTEM_COLORS[item.system] || '#6384ff',
              }}
            />
          </div>
          <div className="bar-count">{item.count}</div>
        </div>
      ))}
    </div>
  );
}

function SystemDonut({ systems }) {
  if (!systems) return null;
  const entries = Object.entries(systems);
  const total   = entries.reduce((s, [, v]) => s + v, 0);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {entries.map(([sys, count], i) => {
        const pct = total > 0 ? (count / total) * 100 : 0;
        const color = SYSTEM_COLORS[sys] || SYSTEM_COLOR_LIST[i % SYSTEM_COLOR_LIST.length];
        return (
          <div key={sys} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: color, flexShrink: 0 }} />
            <span style={{ flex: 1, fontSize: '0.88rem', color: 'var(--text-secondary)' }}>{sys}</span>
            <div className="bar-track" style={{ width: 100 }}>
              <div className="bar-fill" style={{ width: `${pct}%`, background: color }} />
            </div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', width: 40, textAlign: 'right' }}>{count}</span>
          </div>
        );
      })}
      <div style={{ marginTop: 8, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
        Total records: {total.toLocaleString()}
      </div>
    </div>
  );
}

function TrendChart({ trends }) {
  if (!trends?.length) return null;
  const max = Math.max(...trends.map(t => t.total_encounters));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {trends.map((day, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ width: 70, fontSize: '0.75rem', color: 'var(--text-muted)', flexShrink: 0 }}>{day.date}</span>
          <div className="bar-track" style={{ flex: 1 }}>
            <div
              className="bar-fill"
              style={{ width: max > 0 ? `${(day.total_encounters / max) * 100}%` : '0%', background: 'var(--gradient-hero)' }}
            />
          </div>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', width: 32, textAlign: 'right' }}>{day.total_encounters}</span>
        </div>
      ))}
    </div>
  );
}

function ProbabilityTable({ rows }) {
  if (!rows?.length) return null;
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="data-table">
        <thead>
          <tr>
            <th>Traditional Pattern</th>
            <th>System</th>
            <th>Biomedical Diagnosis</th>
            <th>P(biomedical|traditional)</th>
            <th>Count</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{row.traditional_pattern}</td>
              <td>
                <span className="badge badge-system">{row.traditional_system}</span>
              </td>
              <td>{row.biomedical_diagnosis}</td>
              <td>
                <span style={{ color: row.conditional_probability > 0.7 ? 'var(--accent-green)' : 'var(--accent-amber)', fontWeight: 700 }}>
                  {(row.conditional_probability * 100).toFixed(1)}%
                </span>
              </td>
              <td style={{ color: 'var(--text-muted)' }}>{row.joint_count}/{row.pattern_total_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function useAnalytics(endpoint) {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);

  useEffect(() => {
    setLoading(true);
    apiFetch(`/api/analytics/${endpoint}`, {
      headers: { Authorization: `Bearer ${MOCK_TOKEN}` },
    })
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [endpoint]);

  return { data, loading, error };
}

export default function AnalyticsPage() {
  const morbidity  = useAnalytics('morbidity-frequency');
  const districts  = useAnalytics('district-aggregates');
  const probs      = useAnalytics('probability-table');
  const trends     = useAnalytics('encounter-trends');

  const Spinner = () => (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
      <div className="loading-spinner" />
    </div>
  );

  return (
    <div className="page-container">
      <div className="section-heading">
        <div className="section-heading-icon" style={{ background: 'rgba(168,85,247,0.1)' }}>📊</div>
        <div>
          <h2>Ministry Analytics Dashboard</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginTop: 4 }}>
            De-identified aggregate public health analytics — morbidity frequency, district breakdowns, 
            encounter trends, and biomedical probability tables.
          </p>
        </div>
      </div>

      {/* ── Stats Strip ── */}
      <div className="stats-grid" style={{ marginBottom: 28 }}>
        <div className="stat-card">
          <div className="stat-value">
            {morbidity.data ? morbidity.data.total_records.toLocaleString() : '—'}
          </div>
          <div className="stat-label">Total Terminology Records</div>
          <div className="stat-trend">↑ NAMASTE 2024-v1</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {morbidity.data ? Object.keys(morbidity.data.systems).length : '—'}
          </div>
          <div className="stat-label">AYUSH Systems Covered</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {trends.data ? trends.data.days_tracked : '—'}
          </div>
          <div className="stat-label">Days Tracked</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {districts.data ? districts.data.total_districts : '—'}
          </div>
          <div className="stat-label">Districts with Data</div>
        </div>
      </div>

      {/* ── Row 1: Morbidity + System Distribution ── */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-icon" style={{ background: 'rgba(99,132,255,0.1)' }}>📈</div>
              Top Conditions by Frequency
            </div>
            {morbidity.data?.is_demo && (
              <span className="badge badge-status-unmapped">Demo</span>
            )}
          </div>
          {morbidity.loading ? <Spinner /> :
           morbidity.error ? <div className="alert alert-error">⚠️ {morbidity.error}</div> :
           <MorbidityChart items={morbidity.data?.top_conditions} />}
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-icon" style={{ background: 'rgba(168,85,247,0.1)' }}>🥧</div>
              Records by AYUSH System
            </div>
          </div>
          {morbidity.loading ? <Spinner /> :
           morbidity.error ? <div className="alert alert-error">⚠️ {morbidity.error}</div> :
           <SystemDonut systems={morbidity.data?.systems} />}
        </div>
      </div>

      {/* ── Row 2: Encounter Trends ── */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <div className="card-title">
            <div className="card-icon" style={{ background: 'rgba(34,211,238,0.1)' }}>📅</div>
            30-Day Encounter Trends
          </div>
          {trends.data?.is_demo && (
            <span className="badge badge-status-unmapped">Demo</span>
          )}
        </div>
        {trends.loading ? <Spinner /> :
         trends.error ? <div className="alert alert-error">⚠️ {trends.error}</div> :
         <TrendChart trends={trends.data?.trends} />}
      </div>

      {/* ── Row 3: Probability Table ── */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <div className="card-title">
            <div className="card-icon" style={{ background: 'rgba(245,158,11,0.1)' }}>🎯</div>
            P(Biomedical | Traditional) Probability Table
          </div>
          {probs.data?.is_demo && (
            <span className="badge badge-status-unmapped">Demo</span>
          )}
        </div>
        {probs.data?.formula && (
          <div className="alert alert-info" style={{ marginBottom: 16 }}>
            📐 {probs.data.formula}
          </div>
        )}
        {probs.loading ? <Spinner /> :
         probs.error ? <div className="alert alert-error">⚠️ {probs.error}</div> :
         <ProbabilityTable rows={probs.data?.rows} />}
      </div>

      {/* ── Row 4: District Table ── */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <div className="card-icon" style={{ background: 'rgba(244,63,94,0.1)' }}>🗺️</div>
            District Aggregates
          </div>
          {districts.data?.is_demo && (
            <span className="badge badge-status-unmapped">Demo</span>
          )}
        </div>
        {districts.loading ? <Spinner /> :
         districts.error ? <div className="alert alert-error">⚠️ {districts.error}</div> : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>State</th>
                  <th>District</th>
                  <th>Total Encounters</th>
                  <th>Top System</th>
                  <th>Top Condition</th>
                </tr>
              </thead>
              <tbody>
                {districts.data?.aggregates?.map((row, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{row.state}</td>
                    <td>{row.district}</td>
                    <td style={{ color: 'var(--accent-blue)', fontWeight: 600 }}>{row.total_encounters}</td>
                    <td>
                      <span className="badge badge-system">{row.top_system}</span>
                    </td>
                    <td style={{ fontFamily: 'Courier New, monospace', fontSize: '0.8rem' }}>{row.top_condition}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
