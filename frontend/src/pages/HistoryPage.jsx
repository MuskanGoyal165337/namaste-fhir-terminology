import { useState } from 'react';
import { 
  History as HistoryIcon, 
  Sparkles, 
  CheckCircle2, 
  Calendar, 
  User, 
  Stethoscope, 
  HeartPulse, 
  Building2, 
  ShieldCheck, 
  Layers, 
  Filter, 
  AlertCircle,
  FileCheck,
  Tag
} from 'lucide-react';

const SYSTEM_COLORS = {
  Ayurveda:    { bg: 'var(--primary-mint-soft)', border: 'rgba(13, 148, 136, 0.25)', text: 'var(--primary-mint)' },
  Unani:       { bg: 'var(--accent-blue-soft)', border: 'rgba(37, 99, 235, 0.2)', text: 'var(--accent-blue)' },
  Siddha:      { bg: 'var(--accent-lavender-soft)', border: 'rgba(124, 58, 237, 0.2)', text: 'var(--accent-lavender)' },
  AYUSH:       { bg: 'var(--accent-teal-soft)', border: 'rgba(15, 118, 110, 0.25)', text: 'var(--accent-teal)' },
};

function SystemBadge({ system }) {
  const c = SYSTEM_COLORS[system] || SYSTEM_COLORS.AYUSH;
  return (
    <span style={{
      background: c.bg,
      border: `1px solid ${c.border}`,
      color: c.text,
      borderRadius: 'var(--radius-pill)',
      padding: '3px 12px',
      fontSize: '0.75rem',
      fontWeight: 700,
      letterSpacing: '0.02em',
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4
    }}>
      <Tag size={11} />
      <span>{system}</span>
    </span>
  );
}

export default function HistoryPage({
  currentUser,
  selectedPatient,
  selectedDoctor,
  clinicalHistory
}) {
  const role = currentUser?.role || 'patient';
  const [filterSystem, setFilterSystem] = useState('All');

  // Filter history records by role
  let filteredHistory = clinicalHistory.filter(item => {
    if (role === 'patient') {
      return item.patientId === currentUser?.id
        || item.patientName === currentUser?.name
        || item.patientAbha === currentUser?.abhaId;
    }
    if (role === 'doctor') {
      if (!selectedPatient) return false;
      return item.patientId === selectedPatient?.id
        || item.patientName === selectedPatient?.name
        || item.patientAbha === selectedPatient?.abhaId;
    }
    if (role === 'admin') {
      if (selectedPatient) {
        return item.patientId === selectedPatient?.id
          || item.patientName === selectedPatient?.name
          || item.patientAbha === selectedPatient?.abhaId;
      }
      if (selectedDoctor) {
        return item.submittedBy === selectedDoctor?.name;
      }
      return true; // Admin with no filter → show all
    }
    return true;
  });

  // Further filter by system
  if (filterSystem !== 'All') {
    filteredHistory = filteredHistory.filter(item => item.system === filterSystem);
  }

  const systems = ['All', ...Array.from(new Set(clinicalHistory.map(h => h.system).filter(Boolean)))];

  return (
    <div className="page-container">
      {/* ── Heading ── */}
      <div className="section-heading">
        <div className="section-heading-icon">
          <HistoryIcon size={24} />
        </div>
        <div>
          <h2>Clinical Condition History &amp; Audit Log</h2>
          <p>
            Historical longitudinal record of double-coded AYUSH diagnoses and validated FHIR R4 condition bundles.
          </p>
        </div>
      </div>

      {/* Context Alert */}
      <div className="alert alert-info" style={{ marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <User size={16} />
          <span>Active User: <strong style={{ color: 'var(--text-primary)' }}>{currentUser?.name || 'Guest'}</strong></span>
          <span className="badge badge-system" style={{ textTransform: 'capitalize' }}>{role}</span>
        </div>
        <div style={{ fontSize: '0.84rem' }}>
          {role === 'patient' && <span>Personal Clinical Record History</span>}
          {role === 'doctor' && (
            selectedPatient ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <HeartPulse size={15} color="var(--accent-emerald)" />
                <span>Patient History: <strong style={{ color: 'var(--accent-emerald)' }}>{selectedPatient.name}</strong></span>
              </span>
            ) : (
              <span style={{ color: 'var(--accent-amber)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                <AlertCircle size={15} />
                <span>No Patient Selected. Select a patient from the People directory.</span>
              </span>
            )
          )}
          {role === 'admin' && (
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldCheck size={15} color="var(--accent-blue)" />
              <span>
                Administrative Audit
                {selectedPatient && <> · Patient: <strong style={{ color: 'var(--accent-emerald)' }}>{selectedPatient.name}</strong></>}
                {selectedDoctor && !selectedPatient && <> · Doctor: <strong style={{ color: 'var(--accent-blue)' }}>{selectedDoctor.name}</strong></>}
                {!selectedPatient && !selectedDoctor && <> · System-Wide Entries</>}
              </span>
            </span>
          )}
        </div>
      </div>

      {/* System Filter Tabs */}
      {(filteredHistory.length > 0 || filterSystem !== 'All') && (
        <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.84rem', color: 'var(--text-muted)', marginRight: 6, fontWeight: 600 }}>
            <Filter size={14} />
            <span>Filter by System:</span>
          </div>
          {systems.map(sys => (
            <button
              key={sys}
              type="button"
              onClick={() => setFilterSystem(sys)}
              className={`pill-tag ${filterSystem === sys ? 'active' : ''}`}
            >
              {sys}
            </button>
          ))}
          <span style={{ marginLeft: 'auto', fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: 600 }}>
            {filteredHistory.length} Record{filteredHistory.length !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      {/* History Cards List */}
      {filteredHistory.length === 0 ? (
        <div className="card" style={{ padding: '48px 24px', textAlign: 'center' }}>
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
            <HistoryIcon size={22} />
          </div>
          <h3 style={{ fontSize: '1.2rem', marginBottom: 6 }}>No Clinical Records Found</h3>
          <p style={{ fontSize: '0.9rem', maxWidth: 460, margin: '0 auto' }}>
            {role === 'doctor' && !selectedPatient
              ? 'Please select an active patient from the People tab to view their clinical history.'
              : filterSystem !== 'All'
              ? `No records found under the ${filterSystem} system.`
              : 'No FHIR bundles or double-coded conditions have been submitted for this record yet.'}
          </p>
        </div>
      ) : (
        filteredHistory.map((entry, idx) => (
          <div
            key={entry.id || idx}
            className="card fade-in"
            style={{
              marginBottom: 18,
              padding: 0,
              overflow: 'hidden'
            }}
          >
            {/* Top Accent Strip */}
            <div style={{
              height: 4,
              background: (SYSTEM_COLORS[entry.system] || SYSTEM_COLORS.AYUSH).text,
              opacity: 0.8
            }} />

            <div style={{ padding: '24px' }}>
              {/* Header Row */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                    <h3 style={{ fontSize: '1.28rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                      {entry.term}
                    </h3>
                    <SystemBadge system={entry.system || 'AYUSH'} />
                  </div>

                  {/* AYUSH TM2 Code Tag */}
                  <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      {entry.system || 'AYUSH'} Code:
                    </span>
                    <span style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontWeight: 700,
                      fontSize: '0.88rem',
                      color: 'var(--primary-sage)',
                      background: 'var(--primary-sage-soft)',
                      padding: '2px 10px',
                      borderRadius: 'var(--radius-pill)',
                      border: '1px solid rgba(64, 109, 98, 0.2)'
                    }}>
                      {entry.tm2Code}
                    </span>
                  </div>
                </div>

                {/* Right Metadata */}
                <div style={{ textAlign: 'right', fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end', color: 'var(--text-muted)' }}>
                    <Calendar size={14} />
                    <span>Diagnosed Date:</span>
                    <strong style={{ color: 'var(--text-primary)' }}>{entry.addedDate}</strong>
                  </div>
                  {entry.patientName && (
                    <div style={{ marginTop: 4 }}>
                      Patient: <strong style={{ color: 'var(--accent-emerald)' }}>{entry.patientName}</strong>
                    </div>
                  )}
                  {entry.submittedBy && (
                    <div style={{ marginTop: 2, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      Authoring Practitioner: {entry.submittedBy}
                    </div>
                  )}
                </div>
              </div>

              {/* ICD-11 Dual-Coding Section */}
              <div style={{
                marginTop: 18,
                paddingTop: 16,
                borderTop: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 12
              }}>
                <div>
                  <div style={{ fontSize: '0.74rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
                    WHO ICD-11 &amp; BIOMEDICINE EQUIVALENT
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                    <strong style={{ fontSize: '1.05rem', color: 'var(--text-primary)' }}>
                      {entry.icdDisplay}
                    </strong>
                    <span style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontWeight: 700,
                      fontSize: '0.82rem',
                      color: 'var(--accent-blue)',
                      background: 'var(--accent-blue-soft)',
                      padding: '2px 10px',
                      borderRadius: 'var(--radius-pill)',
                      border: '1px solid rgba(37, 99, 235, 0.2)'
                    }}>
                      ICD-11: {entry.icdCode}
                    </span>
                  </div>
                </div>

                {/* Double-Coding Verified Chip */}
                <div style={{
                  fontSize: '0.76rem',
                  background: 'var(--accent-emerald-soft)',
                  border: '1px solid rgba(5, 150, 105, 0.25)',
                  color: 'var(--accent-emerald)',
                  borderRadius: 'var(--radius-pill)',
                  padding: '5px 14px',
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}>
                  <CheckCircle2 size={13} />
                  <span>Double-Coded · NAMASTE + ICD-11</span>
                </div>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
