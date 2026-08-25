import { useState, useEffect } from 'react';
import { 
  Key, 
  Lock, 
  User, 
  Stethoscope, 
  HeartPulse, 
  Building2, 
  ShieldCheck, 
  CheckCircle2, 
  AlertCircle, 
  UserPlus, 
  LogIn, 
  LogOut, 
  Info, 
  Phone, 
  Calendar, 
  Sparkles,
  ArrowRight,
  ShieldAlert
} from 'lucide-react';

const SEED_USERS = [
  // Seed Patients
  {
    role: 'patient',
    id: '14-8829-1029-3381',
    name: 'Rahul Verma',
    abhaId: '14-8829-1029-3381',
    gender: 'Male',
    dob: '1994-05-12',
    phone: '+91 98765 43210',
    password: 'password123',
    connectedDoctor: 'Dr. Rajesh Sharma',
    connectedDoctorId: 'AYU-10492',
  },
  {
    role: 'patient',
    id: '14-7731-2048-9921',
    name: 'Ananya Iyer',
    abhaId: '14-7731-2048-9921',
    gender: 'Female',
    dob: '1988-11-24',
    phone: '+91 91234 56789',
    password: 'password123',
    connectedDoctor: 'Dr. Fatima Khan',
    connectedDoctorId: 'UNA-20183',
  },
  {
    role: 'patient',
    id: '14-9082-3310-4417',
    name: 'Mohan Das',
    abhaId: '14-9082-3310-4417',
    gender: 'Male',
    dob: '1972-03-08',
    phone: '+91 87654 32100',
    password: 'password123',
    connectedDoctor: 'Dr. Rajesh Sharma',
    connectedDoctorId: 'AYU-10492',
  },
  {
    role: 'patient',
    id: '14-5534-7790-2281',
    name: 'Sunita Reddy',
    abhaId: '14-5534-7790-2281',
    gender: 'Female',
    dob: '2001-07-19',
    phone: '+91 77889 90011',
    password: 'password123',
    connectedDoctor: 'Dr. Santhosh Kumar',
    connectedDoctorId: 'SID-30741',
  },
  // Seed Doctors
  {
    role: 'doctor',
    id: 'AYU-10492',
    name: 'Dr. Rajesh Sharma',
    regNo: 'AYU-10492',
    system: 'Ayurveda',
    hospital: 'All India Institute of Ayurveda (AIIA)',
    password: 'password123'
  },
  {
    role: 'doctor',
    id: 'UNA-20183',
    name: 'Dr. Fatima Khan',
    regNo: 'UNA-20183',
    system: 'Unani',
    hospital: 'National Institute of Unani Medicine (NIUM)',
    password: 'password123'
  },
  {
    role: 'doctor',
    id: 'SID-30741',
    name: 'Dr. Santhosh Kumar',
    regNo: 'SID-30741',
    system: 'Siddha',
    hospital: 'National Institute of Siddha (NIS)',
    password: 'password123'
  },
  // Seed Admins
  {
    role: 'admin',
    id: 'ADM-001',
    name: 'Dr. Anshul Admin',
    staffId: 'ADM-001',
    department: 'Ministry of Ayush EMR IT Cell',
    password: 'admin123'
  }
];

export default function LoginPage({ currentUser, onLoginSuccess, onLogout, onRegisterUser }) {
  const [selectedRole, setSelectedRole] = useState('doctor'); // 'patient' | 'doctor' | 'admin'
  const [mode, setMode] = useState('signin'); // 'signin' | 'signup'

  // Patient Fields
  const [patientAbha, setPatientAbha] = useState('');
  const [patientPass, setPatientPass] = useState('');
  const [patientName, setPatientName] = useState('');
  const [patientGender, setPatientGender] = useState('Male');
  const [patientDob, setPatientDob] = useState('');
  const [patientPhone, setPatientPhone] = useState('');

  // Doctor Fields
  const [docRegNo, setDocRegNo] = useState('');
  const [docPass, setDocPass] = useState('');
  const [docName, setDocName] = useState('');
  const [docSystem, setDocSystem] = useState('Ayurveda');
  const [docHospital, setDocHospital] = useState('');

  // Admin Fields
  const [adminId, setAdminId] = useState('');
  const [adminPass, setAdminPass] = useState('');
  const [adminName, setAdminName] = useState('');
  const [adminDept, setAdminDept] = useState('');
  const [adminKey, setAdminKey] = useState('');

  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Initialize localStorage with seeds if not present
  useEffect(() => {
    try {
      if (!localStorage.getItem('ayush_users')) {
        localStorage.setItem('ayush_users', JSON.stringify(SEED_USERS));
      }
    } catch (e) {
      console.error('LocalStorage is not available:', e);
    }
  }, []);

  const getStoredUsers = () => {
    try {
      const stored = localStorage.getItem('ayush_users');
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      console.error(e);
    }
    return SEED_USERS;
  };

  const saveUsers = (usersList) => {
    try {
      localStorage.setItem('ayush_users', JSON.stringify(usersList));
    } catch (e) {
      console.error(e);
    }
  };

  const clearForm = () => {
    setPatientAbha('');
    setPatientPass('');
    setPatientName('');
    setPatientDob('');
    setPatientPhone('');
    setDocRegNo('');
    setDocPass('');
    setDocName('');
    setDocHospital('');
    setAdminId('');
    setAdminPass('');
    setAdminName('');
    setAdminDept('');
    setAdminKey('');
  };

  const handleRoleSelect = (role) => {
    setSelectedRole(role);
    setError(null);
    setSuccessMsg(null);
    clearForm();
  };

  const handleModeSelect = (selectedMode) => {
    setMode(selectedMode);
    setError(null);
    setSuccessMsg(null);
    clearForm();
  };

  const fillQuickCredentials = (role, id, pass) => {
    setSelectedRole(role);
    setMode('signin');
    setError(null);
    setSuccessMsg(null);
    clearForm();
    if (role === 'patient') {
      setPatientAbha(id);
      setPatientPass(pass);
    } else if (role === 'doctor') {
      setDocRegNo(id);
      setDocPass(pass);
    } else if (role === 'admin') {
      setAdminId(id);
      setAdminPass(pass);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    const users = getStoredUsers();
    let userData = null;

    if (mode === 'signin') {
      if (selectedRole === 'patient') {
        const abha = patientAbha.trim();
        if (!abha) {
          setError('ABHA Health ID is required.');
          return;
        }
        const user = users.find(u => u.role === 'patient' && (u.id === abha || u.abhaId === abha));
        if (!user) {
          setError('Account with this ABHA Health ID not found. Please Sign Up first.');
          return;
        }
        if (user.password !== patientPass) {
          setError('Incorrect password.');
          return;
        }
        userData = user;
      } else if (selectedRole === 'doctor') {
        const reg = docRegNo.trim();
        if (!reg) {
          setError('AYUSH Registration Number is required.');
          return;
        }
        const user = users.find(u => u.role === 'doctor' && (u.id === reg || u.regNo === reg));
        if (!user) {
          setError('Account with this Registration Number not found. Please Sign Up first.');
          return;
        }
        if (user.password !== docPass) {
          setError('Incorrect password.');
          return;
        }
        userData = user;
      } else if (selectedRole === 'admin') {
        const aid = adminId.trim();
        if (!aid) {
          setError('Admin Staff ID is required.');
          return;
        }
        const user = users.find(u => u.role === 'admin' && (u.id === aid || u.staffId === aid));
        if (!user) {
          setError('Admin account with this Staff ID not found.');
          return;
        }
        if (user.password !== adminPass) {
          setError('Incorrect password.');
          return;
        }
        userData = user;
      }

      if (userData) {
        onLoginSuccess(userData);
      }
    } else {
      // mode === 'signup'
      if (selectedRole === 'patient') {
        const abha = patientAbha.trim();
        const name = patientName.trim();
        const pass = patientPass;

        if (!name || !abha || !pass) {
          setError('Full Name, ABHA ID, and Password are required.');
          return;
        }

        // Validate ABHA Format
        const rawAbha = abha.replace(/-/g, '');
        if (rawAbha.length !== 14 || isNaN(rawAbha)) {
          setError('ABHA Health ID must be exactly 14 digits.');
          return;
        }

        const exists = users.some(u => u.role === 'patient' && (u.id === abha || u.abhaId === abha));
        if (exists) {
          setError('A patient account with this ABHA Health ID already exists.');
          return;
        }

        userData = {
          role: 'patient',
          id: abha,
          name: name,
          abhaId: abha,
          gender: patientGender,
          dob: patientDob || 'N/A',
          phone: patientPhone || 'N/A',
          password: pass,
          connectedDoctor: null
        };
      } else if (selectedRole === 'doctor') {
        const reg = docRegNo.trim();
        const name = docName.trim();
        const pass = docPass;

        if (!name || !reg || !pass) {
          setError('Doctor Name, Registration Number, and Password are required.');
          return;
        }

        const exists = users.some(u => u.role === 'doctor' && (u.id === reg || u.regNo === reg));
        if (exists) {
          setError('A doctor account with this Registration Number already exists.');
          return;
        }

        userData = {
          role: 'doctor',
          id: reg,
          name: name,
          regNo: reg,
          system: docSystem,
          hospital: docHospital || 'AYUSH Clinic',
          password: pass
        };
      } else if (selectedRole === 'admin') {
        const aid = adminId.trim();
        const name = adminName.trim();
        const pass = adminPass;
        const key = adminKey.trim();

        if (!name || !aid || !pass || !key) {
          setError('Full Name, Staff ID, Security Access Key, and Password are required.');
          return;
        }

        if (key !== 'AYUSH-SEC-2026') {
          setError('Invalid Admin Security Access Key.');
          return;
        }

        const exists = users.some(u => u.role === 'admin' && (u.id === aid || u.staffId === aid));
        if (exists) {
          setError('An administrator account with this Staff ID already exists.');
          return;
        }

        userData = {
          role: 'admin',
          id: aid,
          name: name,
          staffId: aid,
          department: adminDept || 'Ministry of Ayush EMR IT Cell',
          password: pass
        };
      }

      if (userData) {
        const newUsers = [...users, userData];
        saveUsers(newUsers);

        if (onRegisterUser) {
          onRegisterUser(userData);
        }

        setSuccessMsg('Account created successfully! Logging you in...');
        setTimeout(() => {
          onLoginSuccess(userData);
        }, 1000);
      }
    }
  };

  return (
    <div style={{ minHeight: '100vh', padding: '40px 24px 80px' }}>
      <div style={{ maxWidth: 840, margin: '0 auto' }}>
        {/* Header Title */}
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            background: 'var(--primary-mint-soft)',
            border: '1px solid rgba(13, 148, 136, 0.25)',
            borderRadius: 'var(--radius-pill)',
            padding: '5px 16px',
            marginBottom: 16,
            fontSize: '0.78rem',
            fontWeight: 700,
            color: 'var(--primary-mint)',
            letterSpacing: '0.04em',
          }}>
            <ShieldCheck size={14} />
            <span>SECURE PBAC AUTHENTICATION GATEWAY</span>
          </div>

          <h1 style={{ fontSize: '2.5rem', fontWeight: 800, marginBottom: 12, color: 'var(--text-primary)' }}>
            AYUSH EMR Portal Sign In
          </h1>
          <p style={{ color: 'var(--text-secondary)', maxWidth: 580, margin: '0 auto', fontSize: '0.96rem' }}>
            Access policy-protected clinical terminology search, dual-coding crosswalks, and transactional FHIR R4 Bundle workflows.
          </p>
        </div>

        {/* ── Active User Card (if logged in) ── */}
        {currentUser ? (
          <div className="card fade-in" style={{ border: '2px solid var(--primary-mint)', background: 'var(--bg-surface)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span className="badge badge-status-verified" style={{ fontSize: '0.78rem' }}>
                    <CheckCircle2 size={13} />
                    <span>Currently Authenticated</span>
                  </span>
                  <span className="badge badge-system" style={{ textTransform: 'capitalize' }}>
                    {currentUser.role}
                  </span>
                </div>
                <h3 style={{ fontSize: '1.35rem', color: 'var(--text-primary)', margin: 0 }}>
                  {currentUser.name}
                </h3>
                <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                  {currentUser.role === 'patient' && `ABHA ID: ${currentUser.abhaId || currentUser.id}`}
                  {currentUser.role === 'doctor' && `Registration No: ${currentUser.regNo || currentUser.id} · ${currentUser.system || 'Ayurveda'} (${currentUser.hospital || 'Hospital'})`}
                  {currentUser.role === 'admin' && `Staff ID: ${currentUser.staffId || currentUser.id} · ${currentUser.department || 'AYUSH EMR Cell'}`}
                </p>
              </div>

              <button
                type="button"
                className="btn btn-secondary"
                style={{
                  color: 'var(--accent-rose)',
                  borderColor: 'rgba(225, 29, 72, 0.3)',
                  background: 'var(--accent-rose-soft)'
                }}
                onClick={onLogout}
              >
                <LogOut size={15} />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        ) : (
          /* ── Authentication Card ── */
          <div className="card fade-in" style={{ padding: '36px', borderRadius: 'var(--radius-xl)' }}>
            {/* Role Segment Selector */}
            <div style={{ marginBottom: 28 }}>
              <div style={{ fontSize: '0.84rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: 12, letterSpacing: '0.04em' }}>
                SELECT PORTAL ROLE:
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14 }}>
                <button
                  type="button"
                  style={{
                    padding: '18px',
                    borderRadius: 'var(--radius-md)',
                    background: selectedRole === 'patient' ? 'var(--accent-blue-soft)' : 'var(--bg-surface)',
                    border: selectedRole === 'patient' ? '2px solid var(--accent-blue)' : '1px solid var(--border)',
                    boxShadow: selectedRole === 'patient' ? 'var(--shadow-glow-blue)' : 'var(--shadow-xs)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 8,
                    textAlign: 'center',
                    transition: 'all var(--transition)'
                  }}
                  onClick={() => handleRoleSelect('patient')}
                >
                  <div style={{
                    width: 42,
                    height: 42,
                    borderRadius: 'var(--radius-sm)',
                    background: selectedRole === 'patient' ? 'var(--accent-blue)' : 'var(--accent-blue-soft)',
                    color: selectedRole === 'patient' ? '#ffffff' : 'var(--accent-blue)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <HeartPulse size={22} />
                  </div>
                  <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>Patient Access</strong>
                  <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>ABHA &amp; Health Records</span>
                </button>

                <button
                  type="button"
                  style={{
                    padding: '18px',
                    borderRadius: 'var(--radius-md)',
                    background: selectedRole === 'doctor' ? 'var(--primary-mint-soft)' : 'var(--bg-surface)',
                    border: selectedRole === 'doctor' ? '2px solid var(--primary-mint)' : '1px solid var(--border)',
                    boxShadow: selectedRole === 'doctor' ? 'var(--shadow-glow-mint)' : 'var(--shadow-xs)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 8,
                    textAlign: 'center',
                    transition: 'all var(--transition)'
                  }}
                  onClick={() => handleRoleSelect('doctor')}
                >
                  <div style={{
                    width: 42,
                    height: 42,
                    borderRadius: 'var(--radius-sm)',
                    background: selectedRole === 'doctor' ? 'var(--primary-mint)' : 'var(--primary-mint-soft)',
                    color: selectedRole === 'doctor' ? '#ffffff' : 'var(--primary-mint)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <Stethoscope size={22} />
                  </div>
                  <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>Doctor / Clinician</strong>
                  <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>Dual Coding &amp; Bundles</span>
                </button>

                <button
                  type="button"
                  style={{
                    padding: '18px',
                    borderRadius: 'var(--radius-md)',
                    background: selectedRole === 'admin' ? 'var(--accent-lavender-soft)' : 'var(--bg-surface)',
                    border: selectedRole === 'admin' ? '2px solid var(--accent-lavender)' : '1px solid var(--border)',
                    boxShadow: selectedRole === 'admin' ? '0 0 20px rgba(124, 58, 237, 0.15)' : 'var(--shadow-xs)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 8,
                    textAlign: 'center',
                    transition: 'all var(--transition)'
                  }}
                  onClick={() => handleRoleSelect('admin')}
                >
                  <div style={{
                    width: 42,
                    height: 42,
                    borderRadius: 'var(--radius-sm)',
                    background: selectedRole === 'admin' ? 'var(--accent-lavender)' : 'var(--accent-lavender-soft)',
                    color: selectedRole === 'admin' ? '#ffffff' : 'var(--accent-lavender)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <Building2 size={22} />
                  </div>
                  <strong style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>Administrator</strong>
                  <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>Governance &amp; Audit</span>
                </button>
              </div>
            </div>

            {/* Mode Switch: Sign In vs Sign Up */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginBottom: 28, padding: 4, background: 'var(--bg-subtle)', borderRadius: 'var(--radius-pill)', maxWidth: 360, margin: '0 auto 28px' }}>
              <button
                type="button"
                className={`btn btn-sm ${mode === 'signin' ? 'btn-primary' : 'btn-ghost'}`}
                style={{ flex: 1, borderRadius: 'var(--radius-pill)', padding: '7px 16px' }}
                onClick={() => handleModeSelect('signin')}
              >
                <LogIn size={14} />
                <span>Sign In</span>
              </button>
              <button
                type="button"
                className={`btn btn-sm ${mode === 'signup' ? 'btn-primary' : 'btn-ghost'}`}
                style={{ flex: 1, borderRadius: 'var(--radius-pill)', padding: '7px 16px' }}
                onClick={() => handleModeSelect('signup')}
              >
                <UserPlus size={14} />
                <span>Create Account</span>
              </button>
            </div>

            {error && (
              <div className="alert alert-error">
                <AlertCircle size={18} />
                <div>{error}</div>
              </div>
            )}

            {successMsg && (
              <div className="alert alert-success">
                <CheckCircle2 size={18} />
                <div>{successMsg}</div>
              </div>
            )}

            {/* Form Fields according to Role & Mode */}
            <form onSubmit={handleSubmit}>
              {/* ── PATIENT FORM ── */}
              {selectedRole === 'patient' && (
                <div>
                  {mode === 'signup' && (
                    <div className="form-group">
                      <label className="form-label" htmlFor="patient-name">Full Patient Name *</label>
                      <input id="patient-name" type="text" className="form-input" required
                        value={patientName} onChange={e => setPatientName(e.target.value)} placeholder="e.g. Rahul Verma" />
                    </div>
                  )}

                  <div className="form-group">
                    <label className="form-label" htmlFor="patient-abha">ABHA Health ID (14 Digits) *</label>
                    <input id="patient-abha" type="text" className="form-input" required
                      value={patientAbha} onChange={e => setPatientAbha(e.target.value)} placeholder="e.g. 14-8829-1029-3381" />
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>
                      Ayushman Bharat Health Account ID (14 digits)
                    </span>
                  </div>

                  {mode === 'signup' && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                      <div className="form-group">
                        <label className="form-label" htmlFor="patient-gender">Gender</label>
                        <select id="patient-gender" className="form-select" value={patientGender} onChange={e => setPatientGender(e.target.value)}>
                          <option value="Male">Male</option>
                          <option value="Female">Female</option>
                          <option value="Other">Other</option>
                        </select>
                      </div>

                      <div className="form-group">
                        <label className="form-label" htmlFor="patient-dob">Date of Birth</label>
                        <input id="patient-dob" type="date" className="form-input" value={patientDob} onChange={e => setPatientDob(e.target.value)} />
                      </div>
                    </div>
                  )}

                  {mode === 'signup' && (
                    <div className="form-group">
                      <label className="form-label" htmlFor="patient-phone">Mobile Phone Number</label>
                      <input id="patient-phone" type="text" className="form-input"
                        value={patientPhone} onChange={e => setPatientPhone(e.target.value)} placeholder="e.g. +91 98765 43210" />
                    </div>
                  )}

                  <div className="form-group">
                    <label className="form-label" htmlFor="patient-pass">Security Password *</label>
                    <input id="patient-pass" type="password" className="form-input" required
                      value={patientPass} onChange={e => setPatientPass(e.target.value)} placeholder="••••••••" />
                  </div>
                </div>
              )}

              {/* ── DOCTOR FORM ── */}
              {selectedRole === 'doctor' && (
                <div>
                  {mode === 'signup' && (
                    <div className="form-group">
                      <label className="form-label" htmlFor="doc-name">Doctor Full Name *</label>
                      <input id="doc-name" type="text" className="form-input" required
                        value={docName} onChange={e => setDocName(e.target.value)} placeholder="e.g. Dr. Rajesh Sharma" />
                    </div>
                  )}

                  <div className="form-group">
                    <label className="form-label" htmlFor="doc-reg">AYUSH Registration / License Number *</label>
                    <input id="doc-reg" type="text" className="form-input" required
                      value={docRegNo} onChange={e => setDocRegNo(e.target.value)} placeholder="e.g. AYU-10492, UNA-20183, SID-30741" />
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>
                      State or National AYUSH Council Registration Number
                    </span>
                  </div>

                  {mode === 'signup' && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                      <div className="form-group">
                        <label className="form-label" htmlFor="doc-system">System of Traditional Medicine</label>
                        <select id="doc-system" className="form-select" value={docSystem} onChange={e => setDocSystem(e.target.value)}>
                          <option value="Ayurveda">Ayurveda</option>
                          <option value="Unani">Unani</option>
                          <option value="Siddha">Siddha</option>
                          <option value="Yoga & Naturopathy">Yoga &amp; Naturopathy</option>
                        </select>
                      </div>

                      <div className="form-group">
                        <label className="form-label" htmlFor="doc-hosp">Affiliated Hospital / Clinical Institute</label>
                        <input id="doc-hosp" type="text" className="form-input"
                          value={docHospital} onChange={e => setDocHospital(e.target.value)} placeholder="e.g. AIIA New Delhi" />
                      </div>
                    </div>
                  )}

                  <div className="form-group">
                    <label className="form-label" htmlFor="doc-pass">Security Password *</label>
                    <input id="doc-pass" type="password" className="form-input" required
                      value={docPass} onChange={e => setDocPass(e.target.value)} placeholder="••••••••" />
                  </div>
                </div>
              )}

              {/* ── ADMIN FORM ── */}
              {selectedRole === 'admin' && (
                <div>
                  {mode === 'signup' && (
                    <div className="form-group">
                      <label className="form-label" htmlFor="admin-name">Administrator Full Name *</label>
                      <input id="admin-name" type="text" className="form-input" required
                        value={adminName} onChange={e => setAdminName(e.target.value)} placeholder="e.g. Dr. Anshul Admin" />
                    </div>
                  )}

                  <div className="form-group">
                    <label className="form-label" htmlFor="admin-id">Admin Staff ID *</label>
                    <input id="admin-id" type="text" className="form-input" required
                      value={adminId} onChange={e => setAdminId(e.target.value)} placeholder="e.g. ADM-001" />
                  </div>

                  {mode === 'signup' && (
                    <div className="form-group">
                      <label className="form-label" htmlFor="admin-dept">Department</label>
                      <input id="admin-dept" type="text" className="form-input"
                        value={adminDept} onChange={e => setAdminDept(e.target.value)} placeholder="e.g. Ministry of Ayush EMR IT Cell" />
                    </div>
                  )}

                  {mode === 'signup' && (
                    <div className="form-group">
                      <label className="form-label" htmlFor="admin-key">Admin Security Access Key *</label>
                      <input id="admin-key" type="password" className="form-input" required
                        value={adminKey} onChange={e => setAdminKey(e.target.value)} placeholder="Enter AYUSH-SEC-2026" />
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>
                        Required for elevated privileges (Key: <strong>AYUSH-SEC-2026</strong>)
                      </span>
                    </div>
                  )}

                  <div className="form-group">
                    <label className="form-label" htmlFor="admin-pass">Security Password *</label>
                    <input id="admin-pass" type="password" className="form-input" required
                      value={adminPass} onChange={e => setAdminPass(e.target.value)} placeholder="••••••••" />
                  </div>
                </div>
              )}

              <button
                type="submit"
                className="btn btn-primary btn-lg"
                style={{ width: '100%', marginTop: 20, padding: '13px 24px', fontSize: '1rem' }}
              >
                {mode === 'signin' ? (
                  <>
                    <Key size={16} />
                    <span>Sign In as {selectedRole.toUpperCase()}</span>
                  </>
                ) : (
                  <>
                    <UserPlus size={16} />
                    <span>Register {selectedRole.toUpperCase()} Profile</span>
                  </>
                )}
              </button>
            </form>

            {/* Quick Access Helper */}
            {mode === 'signin' && (
              <div style={{
                marginTop: 28,
                padding: '18px 20px',
                background: 'var(--bg-subtle)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
                fontSize: '0.84rem',
              }}>
                <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10, color: 'var(--primary-sage)' }}>
                  <Info size={15} />
                  <span>Pre-seeded Clinical Test Credentials (Click to Autofill):</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
                  <button
                    type="button"
                    onClick={() => fillQuickCredentials('patient', '14-8829-1029-3381', 'password123')}
                    style={{
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border)',
                      padding: '10px 14px',
                      borderRadius: 'var(--radius-sm)',
                      textAlign: 'left',
                      cursor: 'pointer',
                      boxShadow: 'var(--shadow-xs)'
                    }}
                  >
                    <div style={{ fontWeight: 700, color: 'var(--accent-blue)', fontSize: '0.82rem' }}>Patient: Rahul Verma</div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>ABHA: 14-8829-1029-3381</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => fillQuickCredentials('doctor', 'AYU-10492', 'password123')}
                    style={{
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border)',
                      padding: '10px 14px',
                      borderRadius: 'var(--radius-sm)',
                      textAlign: 'left',
                      cursor: 'pointer',
                      boxShadow: 'var(--shadow-xs)'
                    }}
                  >
                    <div style={{ fontWeight: 700, color: 'var(--primary-mint)', fontSize: '0.82rem' }}>Doctor: Dr. Rajesh Sharma</div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Reg: AYU-10492 (Ayurveda)</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => fillQuickCredentials('admin', 'ADM-001', 'admin123')}
                    style={{
                      background: 'var(--bg-surface)',
                      border: '1px solid var(--border)',
                      padding: '10px 14px',
                      borderRadius: 'var(--radius-sm)',
                      textAlign: 'left',
                      cursor: 'pointer',
                      boxShadow: 'var(--shadow-xs)'
                    }}
                  >
                    <div style={{ fontWeight: 700, color: 'var(--accent-lavender)', fontSize: '0.82rem' }}>Admin: Dr. Anshul Admin</div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Staff ID: ADM-001</div>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
