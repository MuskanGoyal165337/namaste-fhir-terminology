import { useState } from 'react';
import { 
  Users, 
  Stethoscope, 
  HeartPulse, 
  Building2, 
  Link2, 
  ShieldCheck, 
  CheckCircle2, 
  UserCheck, 
  Phone, 
  Calendar, 
  Building, 
  Check, 
  ArrowRight, 
  AlertCircle, 
  Eye,
  Hash,
  Activity
} from 'lucide-react';

export default function PeoplePage({
  currentUser,
  doctorsList,
  patientsList,
  selectedPatient,
  selectedDoctor,
  onSelectPatient,
  onSelectDoctor
}) {
  const role = currentUser?.role || 'doctor';
  const [adminView, setAdminView] = useState('connections'); // 'connections' | 'doctors' | 'patients'

  return (
    <div className="page-container">
      {/* ── Section Heading ── */}
      <div className="section-heading">
        <div className="section-heading-icon">
          <Users size={24} />
        </div>
        <div>
          <h2>AYUSH Clinical &amp; Patient Registry</h2>
          <p>
            {role === 'patient' && 'Discover registered AYUSH practitioners and link your clinical health records.'}
            {role === 'doctor' && 'Manage patients registered under your consultation and select active patient for bundle authoring.'}
            {role === 'admin' && 'System-wide governance view of registered practitioners, patients, and clinical affiliations.'}
          </p>
        </div>
      </div>

      {/* Active User Context Banner */}
      <div className="alert alert-info" style={{ marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <UserCheck size={18} color="var(--primary-mint)" />
          <span>Active Authenticated Profile: <strong style={{ color: 'var(--text-primary)' }}>{currentUser?.name || 'Guest Practitioner'}</strong></span>
          <span className="badge badge-system" style={{ textTransform: 'capitalize' }}>
            {role}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          {selectedPatient && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.84rem' }}>
              <HeartPulse size={15} color="var(--accent-emerald)" />
              <span>Active Patient: <strong style={{ color: 'var(--accent-emerald)' }}>{selectedPatient.name}</strong> ({selectedPatient.abhaId || selectedPatient.id})</span>
            </div>
          )}
          {selectedDoctor && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.84rem' }}>
              <Stethoscope size={15} color="var(--accent-blue)" />
              <span>Connected Doctor: <strong style={{ color: 'var(--accent-blue)' }}>{selectedDoctor.name}</strong></span>
            </div>
          )}
        </div>
      </div>

      {/* ── ADMIN: Segmented View Switcher ── */}
      {role === 'admin' && (
        <div style={{ display: 'flex', gap: 10, marginBottom: 24, paddingBottom: 16, borderBottom: '1px solid var(--border-subtle)', flexWrap: 'wrap' }}>
          {[
            { id: 'connections', label: 'Doctor-Patient Connections', Icon: Link2 },
            { id: 'doctors', label: 'All Registered Doctors', Icon: Stethoscope },
            { id: 'patients', label: 'All Registered Patients', Icon: HeartPulse },
          ].map(v => {
            const TabIcon = v.Icon;
            const isActive = adminView === v.id;
            return (
              <button
                key={v.id}
                type="button"
                className={`btn ${isActive ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 7,
                  borderRadius: 'var(--radius-pill)',
                }}
                onClick={() => setAdminView(v.id)}
              >
                <TabIcon size={14} />
                <span>{v.label}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* ── PATIENT VIEW: Registered Doctors List ── */}
      {role === 'patient' && (
        <div className="card" style={{ marginBottom: 28 }}>
          <div className="card-header">
            <div className="card-title">
              <div className="card-icon-box" style={{ background: 'var(--accent-blue-soft)', color: 'var(--accent-blue)' }}>
                <Stethoscope size={18} />
              </div>
              <span>Registered AYUSH Practitioners ({doctorsList.length})</span>
            </div>
            {selectedDoctor ? (
              <div style={{
                fontSize: '0.82rem',
                color: 'var(--accent-emerald)',
                background: 'var(--accent-emerald-soft)',
                padding: '6px 14px',
                borderRadius: 'var(--radius-pill)',
                border: '1px solid rgba(5, 150, 105, 0.25)',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}>
                <CheckCircle2 size={14} />
                <span>Connected Doctor: {selectedDoctor.name} ({selectedDoctor.system})</span>
              </div>
            ) : (
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Select a doctor to associate with your health records
              </div>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))', gap: 18 }}>
            {doctorsList.map(doc => {
              const isSelectedDoc = selectedDoctor?.id === doc.id
                || currentUser?.connectedDoctorId === doc.id
                || currentUser?.connectedDoctor === doc.name;
              return (
                <DoctorCard
                  key={doc.id}
                  doc={doc}
                  isSelected={isSelectedDoc}
                  onSelect={() => onSelectDoctor(doc)}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* ── DOCTOR VIEW: Patients registered under consultation ── */}
      {role === 'doctor' && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div className="card-icon-box" style={{ background: 'var(--accent-emerald-soft)', color: 'var(--accent-emerald)' }}>
                <HeartPulse size={18} />
              </div>
              <span>Patients in Consultation with {currentUser?.name || 'Doctor'} ({patientsList.filter(p => !p.connectedDoctor || p.connectedDoctor === currentUser?.name).length})</span>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(310px, 1fr))', gap: 18 }}>
            {patientsList
              .filter(p => !p.connectedDoctor || p.connectedDoctor === currentUser?.name)
              .map(patient => (
                <PatientCard
                  key={patient.id}
                  patient={patient}
                  isSelected={selectedPatient?.id === patient.id}
                  showDoctor={false}
                  onSelect={() => onSelectPatient(patient)}
                />
              ))}
          </div>
        </div>
      )}

      {/* ── ADMIN VIEW ── */}
      {role === 'admin' && (
        <>
          {/* Connections Table */}
          {adminView === 'connections' && (
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-icon-box" style={{ background: 'var(--accent-amber-soft)', color: 'var(--accent-amber)' }}>
                    <Link2 size={18} />
                  </div>
                  <span>Doctor ↔ Patient Affiliation Directory ({patientsList.length} total patients)</span>
                </div>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table className="custom-table">
                  <thead>
                    <tr>
                      <th>Patient Name</th>
                      <th>ABHA ID</th>
                      <th>Demographics</th>
                      <th>Connected Doctor</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {patientsList.map((patient, i) => {
                      const connDoctor = doctorsList.find(d => d.name === patient.connectedDoctor || d.id === patient.connectedDoctorId);
                      const isSelected = selectedPatient?.id === patient.id;
                      return (
                        <tr key={patient.id}>
                          <td>
                            <strong style={{ color: isSelected ? 'var(--primary-mint)' : 'var(--text-primary)' }}>
                              {patient.name}
                            </strong>
                          </td>
                          <td style={{ fontFamily: 'JetBrains Mono, monospace', color: 'var(--accent-blue)', fontSize: '0.82rem' }}>
                            {patient.abhaId || patient.id}
                          </td>
                          <td style={{ color: 'var(--text-secondary)', fontSize: '0.84rem' }}>
                            {patient.gender} · {patient.dob}
                          </td>
                          <td>
                            {patient.connectedDoctor ? (
                              <div>
                                <div style={{ color: 'var(--accent-teal)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 5 }}>
                                  <Link2 size={13} />
                                  <span>{patient.connectedDoctor}</span>
                                </div>
                                {connDoctor && (
                                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                                    {connDoctor.system} · {connDoctor.hospital}
                                  </div>
                                )}
                              </div>
                            ) : (
                              <span style={{ color: 'var(--accent-amber)', fontSize: '0.82rem', fontWeight: 600 }}>
                                Unassigned
                              </span>
                            )}
                          </td>
                          <td>
                            <button
                              type="button"
                              className={`btn ${isSelected ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                              onClick={() => onSelectPatient(patient)}
                              style={{ padding: '5px 12px', fontSize: '0.78rem' }}
                            >
                              {isSelected ? (
                                <>
                                  <Check size={12} />
                                  <span>Active</span>
                                </>
                              ) : (
                                <>
                                  <Eye size={12} />
                                  <span>Select</span>
                                </>
                              )}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* All Doctors */}
          {adminView === 'doctors' && (
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-icon-box" style={{ background: 'var(--accent-blue-soft)', color: 'var(--accent-blue)' }}>
                    <Stethoscope size={18} />
                  </div>
                  <span>All Registered Practitioners ({doctorsList.length})</span>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))', gap: 18 }}>
                {doctorsList.map(doc => (
                  <DoctorCard
                    key={doc.id}
                    doc={doc}
                    isSelected={selectedDoctor?.id === doc.id}
                    onSelect={() => onSelectDoctor(doc)}
                    showPatientCount
                    patientCount={patientsList.filter(p => p.connectedDoctorId === doc.id || p.connectedDoctor === doc.name).length}
                  />
                ))}
              </div>
            </div>
          )}

          {/* All Patients */}
          {adminView === 'patients' && (
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <div className="card-icon-box" style={{ background: 'var(--accent-emerald-soft)', color: 'var(--accent-emerald)' }}>
                    <HeartPulse size={18} />
                  </div>
                  <span>All Registered Patients ({patientsList.length})</span>
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(310px, 1fr))', gap: 18 }}>
                {patientsList.map(patient => (
                  <PatientCard
                    key={patient.id}
                    patient={patient}
                    isSelected={selectedPatient?.id === patient.id}
                    showDoctor
                    onSelect={() => onSelectPatient(patient)}
                  />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function DoctorCard({ doc, isSelected, onSelect, showPatientCount, patientCount }) {
  return (
    <div
      style={{
        padding: '22px',
        borderRadius: 'var(--radius-lg)',
        background: 'var(--bg-surface)',
        border: isSelected ? '2px solid var(--primary-mint)' : '1px solid var(--border)',
        boxShadow: isSelected ? 'var(--shadow-glow-mint)' : 'var(--shadow-card)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: '14px',
        transition: 'all var(--transition)'
      }}
    >
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <strong style={{ fontSize: '1.08rem', color: isSelected ? 'var(--primary-mint)' : 'var(--text-primary)' }}>
            {doc.name}
          </strong>
          <span className="badge badge-system">{doc.system}</span>
        </div>
        <div style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div>Registration No: <strong style={{ color: 'var(--text-primary)' }}>{doc.regNo}</strong></div>
          <div>Hospital: {doc.hospital}</div>
          {showPatientCount && (
            <div style={{ marginTop: 6, color: 'var(--accent-teal)', fontWeight: 600, fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: 5 }}>
              <HeartPulse size={14} />
              <span>{patientCount} Patient{patientCount !== 1 ? 's' : ''} in Consultation</span>
            </div>
          )}
        </div>
      </div>
      <button
        type="button"
        className={`btn ${isSelected ? 'btn-primary' : 'btn-secondary'} btn-sm`}
        style={{ width: '100%', justifyContent: 'center' }}
        onClick={onSelect}
      >
        {isSelected ? (
          <>
            <Check size={14} />
            <span>Connected Doctor</span>
          </>
        ) : (
          <>
            <ArrowRight size={14} />
            <span>Select Doctor</span>
          </>
        )}
      </button>
    </div>
  );
}

function PatientCard({ patient, isSelected, onSelect, showDoctor }) {
  return (
    <div
      style={{
        padding: '22px',
        borderRadius: 'var(--radius-lg)',
        background: 'var(--bg-surface)',
        border: isSelected ? '2px solid var(--primary-mint)' : '1px solid var(--border)',
        boxShadow: isSelected ? 'var(--shadow-glow-mint)' : 'var(--shadow-card)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: '14px',
        transition: 'all var(--transition)'
      }}
    >
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <strong style={{ fontSize: '1.08rem', color: isSelected ? 'var(--primary-mint)' : 'var(--text-primary)' }}>
            {patient.name}
          </strong>
          <span className="badge badge-code">{patient.gender} · {patient.dob}</span>
        </div>
        <div style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div>ABHA ID: <strong style={{ color: 'var(--accent-blue)', fontFamily: 'JetBrains Mono, monospace' }}>{patient.abhaId || patient.id}</strong></div>
          {patient.phone && <div>Phone: {patient.phone}</div>}
          {showDoctor && (
            <div style={{ marginTop: 6, color: 'var(--accent-amber)', fontWeight: 600, fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: 5 }}>
              <Link2 size={14} />
              <span>Doctor: {patient.connectedDoctor || 'Unassigned'}</span>
            </div>
          )}
        </div>
      </div>
      <button
        type="button"
        className={`btn ${isSelected ? 'btn-primary' : 'btn-secondary'} btn-sm`}
        style={{ width: '100%', justifyContent: 'center' }}
        onClick={onSelect}
      >
        {isSelected ? (
          <>
            <CheckCircle2 size={14} />
            <span>Active Selected Patient</span>
          </>
        ) : (
          <>
            <ArrowRight size={14} />
            <span>Select for Bundle</span>
          </>
        )}
      </button>
    </div>
  );
}
