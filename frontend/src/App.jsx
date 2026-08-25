import { useState, useEffect } from 'react';
import { 
  Home, 
  Users, 
  History as HistoryIcon, 
  Search, 
  ArrowLeftRight, 
  Package, 
  ShieldCheck, 
  Activity, 
  LogOut, 
  Key, 
  Lock, 
  Stethoscope, 
  HeartPulse, 
  Sparkles,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import SearchPage from './pages/SearchPage.jsx';
import BundlePage from './pages/BundlePage.jsx';
import TranslatePage from './pages/TranslatePage.jsx';
import LoginPage from './pages/LoginPage.jsx';
import PeoplePage from './pages/PeoplePage.jsx';
import HistoryPage from './pages/HistoryPage.jsx';
import LandingPage from './pages/LandingPage.jsx';

// ─── Mock Data ───────────────────────────────────────────────────────────────
const MOCK_DOCTORS = [
  {
    id: 'AYU-10492',
    name: 'Dr. Rajesh Sharma',
    regNo: 'AYU-10492',
    system: 'Ayurveda',
    hospital: 'All India Institute of Ayurveda (AIIA)',
  },
  {
    id: 'UNA-20183',
    name: 'Dr. Fatima Khan',
    regNo: 'UNA-20183',
    system: 'Unani',
    hospital: 'National Institute of Unani Medicine (NIUM)',
  },
  {
    id: 'SID-30741',
    name: 'Dr. Santhosh Kumar',
    regNo: 'SID-30741',
    system: 'Siddha',
    hospital: 'National Institute of Siddha (NIS)',
  },
];

const MOCK_PATIENTS = [
  {
    id: '14-8829-1029-3381',
    name: 'Rahul Verma',
    abhaId: '14-8829-1029-3381',
    gender: 'Male',
    dob: '1994-05-12',
    phone: '+91 98765 43210',
    connectedDoctor: 'Dr. Rajesh Sharma',
    connectedDoctorId: 'AYU-10492',
  },
  {
    id: '14-7731-2048-9921',
    name: 'Ananya Iyer',
    abhaId: '14-7731-2048-9921',
    gender: 'Female',
    dob: '1988-11-24',
    phone: '+91 91234 56789',
    connectedDoctor: 'Dr. Fatima Khan',
    connectedDoctorId: 'UNA-20183',
  },
  {
    id: '14-9082-3310-4417',
    name: 'Mohan Das',
    abhaId: '14-9082-3310-4417',
    gender: 'Male',
    dob: '1972-03-08',
    phone: '+91 87654 32100',
    connectedDoctor: 'Dr. Rajesh Sharma',
    connectedDoctorId: 'AYU-10492',
  },
  {
    id: '14-5534-7790-2281',
    name: 'Sunita Reddy',
    abhaId: '14-5534-7790-2281',
    gender: 'Female',
    dob: '2001-07-19',
    phone: '+91 77889 90011',
    connectedDoctor: 'Dr. Santhosh Kumar',
    connectedDoctorId: 'SID-30741',
  },
];

const SEED_HISTORY = [
  {
    id: 'h-001',
    patientId: '14-8829-1029-3381',
    patientName: 'Rahul Verma',
    patientAbha: '14-8829-1029-3381',
    submittedBy: 'Dr. Rajesh Sharma',
    term: 'hikkA (hidhmA)',
    system: 'Ayurveda',
    tm2Code: 'SM74(EA-2)',
    icdCode: 'MD12',
    icdDisplay: 'Cough',
    addedDate: '2026-08-10',
  },
  {
    id: 'h-002',
    patientId: '14-8829-1029-3381',
    patientName: 'Rahul Verma',
    patientAbha: '14-8829-1029-3381',
    submittedBy: 'Dr. Rajesh Sharma',
    term: 'jvaraH',
    system: 'Ayurveda',
    tm2Code: 'SP51(EC-3)',
    icdCode: 'MG26',
    icdDisplay: 'Fever of unknown origin',
    addedDate: '2026-08-12',
  },
  {
    id: 'h-003',
    patientId: '14-7731-2048-9921',
    patientName: 'Ananya Iyer',
    patientAbha: '14-7731-2048-9921',
    submittedBy: 'Dr. Fatima Khan',
    term: 'su-al',
    system: 'Unani',
    tm2Code: 'UE-01',
    icdCode: 'MD12',
    icdDisplay: 'Cough',
    addedDate: '2026-08-11',
  },
];

// ─── Tab Definitions (Using Lucide Icons, No Emojis) ─────────────────────────
const ALL_TABS = [
  { id: 'home',      label: 'Home',              Icon: Home,           roles: ['*'], showWhenAuthed: false },
  { id: 'people',    label: 'People',            Icon: Users,          roles: ['patient', 'doctor', 'admin'], showWhenAuthed: true },
  { id: 'history',   label: 'History',           Icon: HistoryIcon,    roles: ['patient', 'doctor', 'admin'], showWhenAuthed: true },
  { id: 'search',    label: 'Terminology',       Icon: Search,         roles: ['*'], showWhenAuthed: true  },
  { id: 'translate', label: 'Translate',         Icon: ArrowLeftRight, roles: ['*'], showWhenAuthed: true  },
  { id: 'bundle',    label: 'FHIR Bundle',       Icon: Package,        roles: ['doctor', 'admin'], showWhenAuthed: true },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [healthStatus, setHealthStatus] = useState(null);
  const [selectedTermData, setSelectedTermData] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [navScrolled, setNavScrolled] = useState(false);

  // Helper to load registered users from localStorage and combine with Mock lists
  const getStoredUsers = () => {
    try {
      const stored = localStorage.getItem('ayush_users');
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {
      console.error("Failed to parse stored users:", e);
    }
    return [];
  };

  const getInitialPatients = () => {
    const stored = getStoredUsers();
    const storedPatients = stored.filter(u => u.role === 'patient');
    const combined = [...MOCK_PATIENTS];
    storedPatients.forEach(sp => {
      const existingIdx = combined.findIndex(p => p.id === sp.id || p.abhaId === sp.abhaId);
      if (existingIdx >= 0) {
        combined[existingIdx] = {
          ...combined[existingIdx],
          connectedDoctor: sp.connectedDoctor !== undefined ? sp.connectedDoctor : combined[existingIdx].connectedDoctor,
          connectedDoctorId: sp.connectedDoctorId !== undefined ? sp.connectedDoctorId : combined[existingIdx].connectedDoctorId,
        };
      } else {
        combined.push({
          id: sp.id,
          name: sp.name,
          abhaId: sp.abhaId || sp.id,
          gender: sp.gender || 'Unknown',
          dob: sp.dob || 'N/A',
          phone: sp.phone || '',
          connectedDoctor: sp.connectedDoctor || null,
          connectedDoctorId: sp.connectedDoctorId || null,
        });
      }
    });
    return combined;
  };

  const getInitialDoctors = () => {
    const stored = getStoredUsers();
    const storedDoctors = stored.filter(u => u.role === 'doctor');
    const combined = [...MOCK_DOCTORS];
    storedDoctors.forEach(sd => {
      if (!combined.some(d => d.id === sd.id)) {
        combined.push({
          id: sd.id,
          name: sd.name,
          regNo: sd.regNo || sd.id,
          system: sd.system || 'Ayurveda',
          hospital: sd.hospital || 'Hospital'
        });
      }
    });
    return combined;
  };

  const [doctorsList, setDoctorsList] = useState(getInitialDoctors);
  const [patientsList, setPatientsList] = useState(getInitialPatients);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [selectedDoctor, setSelectedDoctor] = useState(null);
  const [clinicalHistory, setClinicalHistory] = useState(SEED_HISTORY);

  useEffect(() => {
    const handleScroll = () => {
      setNavScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    fetch('/health')
      .then(r => r.json())
      .then(d => setHealthStatus(d))
      .catch(() => setHealthStatus({ status: 'error' }));

    // ── Load Clinical History from DB ──
    fetch('/api/history')
      .then(r => r.ok ? r.json() : [])
      .then(historyData => {
        if (Array.isArray(historyData) && historyData.length > 0) {
          setClinicalHistory(historyData);
        }
      })
      .catch(e => console.error("Error fetching history from DB:", e));

    // ── Load Doctor-Patient Connections from DB ──
    fetch('/api/connections')
      .then(r => r.ok ? r.json() : [])
      .then(connectionsData => {
        if (Array.isArray(connectionsData) && connectionsData.length > 0) {
          setPatientsList(prev => prev.map(p => {
            const found = connectionsData.find(c => c.patientId === p.id || c.patientId === p.abhaId);
            if (found && found.doctorName) {
              return {
                ...p,
                connectedDoctor: found.doctorName,
                connectedDoctorId: found.doctorId,
              };
            }
            return p;
          }));
        }
      })
      .catch(e => console.error("Error fetching connections from DB:", e));
  }, []);

  // Doctor selection handler that persists patient's doctor selection to database and localStorage
  const handleSelectDoctor = (doc) => {
    setSelectedDoctor(doc);

    // If active user is a patient, save doctor connection permanently in DB
    if (currentUser && currentUser.role === 'patient') {
      const docName = doc ? doc.name : null;
      const docId = doc ? doc.id : null;
      const docSys = doc ? doc.system : null;

      // Update currentUser
      const updatedUser = {
        ...currentUser,
        connectedDoctor: docName,
        connectedDoctorId: docId,
      };
      setCurrentUser(updatedUser);

      // Update patientsList state
      setPatientsList(prev => prev.map(p => {
        if (p.id === currentUser.id || p.abhaId === currentUser.abhaId || p.name === currentUser.name) {
          return {
            ...p,
            connectedDoctor: docName,
            connectedDoctorId: docId,
          };
        }
        return p;
      }));

      // ── Persist connection permanently in database ──
      fetch('/api/connections', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patientId: currentUser.id || currentUser.abhaId,
          patientName: currentUser.name,
          patientAbha: currentUser.abhaId || currentUser.id,
          doctorId: docId,
          doctorName: docName,
          system: docSys,
        })
      }).catch(err => console.error("Failed to persist connection to DB:", err));

      // Update localStorage stored users list
      try {
        const stored = localStorage.getItem('ayush_users');
        let users = stored ? JSON.parse(stored) : [];
        let found = false;
        users = users.map(u => {
          if (u.role === 'patient' && (u.id === currentUser.id || u.abhaId === currentUser.abhaId || u.name === currentUser.name)) {
            found = true;
            return {
              ...u,
              connectedDoctor: docName,
              connectedDoctorId: docId,
            };
          }
          return u;
        });
        if (!found) {
          users.push({
            ...currentUser,
            connectedDoctor: docName,
            connectedDoctorId: docId,
          });
        }
        localStorage.setItem('ayush_users', JSON.stringify(users));
      } catch (e) {
        console.error("Failed to persist doctor selection to localStorage:", e);
      }
    }
  };

  const handleLoginSuccess = (userData) => {
    setCurrentUser(userData);
    if (userData.role === 'patient') {
      const patient = patientsList.find(
        p => p.abhaId === userData.abhaId || p.id === userData.id || p.name === userData.name
      ) || userData;

      setSelectedPatient(patient);

      // Automatically select saved connected doctor if present
      const docName = patient.connectedDoctor || userData.connectedDoctor;
      const docId = patient.connectedDoctorId || userData.connectedDoctorId;
      if (docId || docName) {
        const doc = doctorsList.find(d => d.id === docId || d.name === docName);
        if (doc) setSelectedDoctor(doc);
      }
    }
    if (userData.role === 'doctor') {
      const doc = doctorsList.find(
        d => d.regNo === userData.regNo || d.id === userData.id
      );
      if (doc) setSelectedDoctor(doc);
    }
    setActiveTab('people');
  };

  const handleLogout = () => {
    setCurrentUser(null);
    setSelectedPatient(null);
    setSelectedDoctor(null);
    setActiveTab('home');
  };

  const handleAddToHistory = (entry) => {
    setClinicalHistory(prev => [entry, ...prev]);

    // ── Persist history entry permanently in database ──
    fetch('/api/history', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: entry.id,
        patientId: entry.patientId,
        patientName: entry.patientName,
        patientAbha: entry.patientAbha,
        submittedBy: entry.submittedBy,
        term: entry.term,
        system: entry.system,
        tm2Code: entry.tm2Code,
        icdCode: entry.icdCode,
        icdDisplay: entry.icdDisplay,
        addedDate: entry.addedDate,
      })
    }).catch(err => console.error("Failed to persist history item to DB:", err));
  };

  const handleRegisterUser = (userData) => {
    if (userData.role === 'patient') {
      const exists = patientsList.find(p => p.id === userData.id);
      if (!exists) {
        setPatientsList(prev => [...prev, {
          id: userData.id,
          name: userData.name,
          abhaId: userData.abhaId || userData.id,
          gender: userData.gender || 'Unknown',
          dob: userData.dob || 'N/A',
          phone: userData.phone || '',
          connectedDoctor: null,
          connectedDoctorId: null,
        }]);
      }
    } else if (userData.role === 'doctor') {
      const exists = doctorsList.find(d => d.id === userData.id);
      if (!exists) {
        setDoctorsList(prev => [...prev, {
          id: userData.id,
          name: userData.name,
          regNo: userData.regNo || userData.id,
          system: userData.system || 'Ayurveda',
          hospital: userData.hospital || 'Hospital',
        }]);
      }
    }
  };

  const isHealthy = healthStatus?.status === 'healthy';

  // Compute visible tabs
  const visibleTabs = ALL_TABS.filter(tab => {
    if (!currentUser) {
      // Show only home when not logged in
      return tab.id === 'home';
    }
    // Logged in: hide home tab, show everything role-appropriate
    if (tab.id === 'home') return false;
    if (tab.roles.includes('*')) return true;
    return tab.roles.includes(currentUser.role);
  });

  const getRoleIcon = () => {
    if (currentUser?.role === 'patient') return <HeartPulse size={14} className="role-icon" />;
    if (currentUser?.role === 'doctor') return <Stethoscope size={14} className="role-icon" />;
    return <ShieldCheck size={14} className="role-icon" />;
  };

  return (
    <div className="app-wrapper">
      {/* ── Navbar ── */}
      <nav className={`navbar${navScrolled ? ' scrolled' : ''}`}>
        {/* Brand — clicking takes home or dashboard */}
        <button
          type="button"
          className="navbar-brand"
          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
          onClick={() => setActiveTab(currentUser ? 'people' : 'home')}
        >
          <div className="brand-icon">
            <Activity size={20} strokeWidth={2.5} />
          </div>
          <div className="brand-text">
            <span className="brand-name">AYUSH EMR</span>
            <span className="brand-sub">Terminology Portal</span>
          </div>
        </button>

        {/* Nav Tabs */}
        <div className="nav-tabs">
          {visibleTabs.map(tab => {
            const TabIcon = tab.Icon;
            return (
              <button
                key={tab.id}
                type="button"
                id={`nav-tab-${tab.id}`}
                className={`nav-tab${activeTab === tab.id ? ' active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <TabIcon size={16} strokeWidth={2} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Right: user pill + health status */}
        <div className="nav-right">
          {currentUser ? (
            <div style={{
              fontSize: '0.82rem',
              background: 'var(--primary-mint-soft)',
              border: '1px solid rgba(13, 148, 136, 0.25)',
              borderRadius: 'var(--radius-pill)',
              padding: '5px 14px',
              color: 'var(--primary-sage)',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              boxShadow: 'var(--shadow-xs)'
            }}>
              {getRoleIcon()}
              <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{currentUser.name}</span>
              <span style={{ 
                fontSize: '0.72rem', 
                background: 'rgba(13, 148, 136, 0.15)', 
                padding: '2px 8px', 
                borderRadius: 'var(--radius-pill)', 
                textTransform: 'capitalize',
                fontWeight: 600,
                color: 'var(--primary-mint)'
              }}>
                {currentUser.role}
              </span>
              <button
                type="button"
                onClick={handleLogout}
                title="Sign Out"
                style={{
                  marginLeft: 4,
                  background: 'var(--accent-rose-soft)',
                  border: '1px solid rgba(225, 29, 72, 0.25)',
                  borderRadius: 'var(--radius-pill)',
                  color: 'var(--accent-rose)',
                  fontSize: '0.74rem',
                  fontWeight: 700,
                  padding: '3px 9px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  transition: 'all var(--transition-fast)'
                }}
              >
                <LogOut size={12} />
                <span>Sign Out</span>
              </button>
            </div>
          ) : (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => setActiveTab('login')}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Key size={14} />
              <span>Sign In</span>
            </button>
          )}

          <div className={`health-badge${isHealthy === false ? ' error' : ''}`}>
            <div className="health-dot" />
            <span>
              {healthStatus == null ? 'Connecting…'
                : isHealthy ? `API Active (v${healthStatus.version})`
                : 'API Offline'}
            </span>
          </div>
        </div>
      </nav>

      {/* ── Page Content ── */}
      <main className="main-content">

        {/* Home / Landing */}
        <div style={{ display: activeTab === 'home' ? 'block' : 'none' }}>
          <LandingPage onGetStarted={() => setActiveTab('login')} />
        </div>

        {/* Login */}
        <div style={{ display: activeTab === 'login' ? 'block' : 'none' }}>
          <LoginPage
            currentUser={currentUser}
            onLoginSuccess={handleLoginSuccess}
            onLogout={handleLogout}
            onRegisterUser={handleRegisterUser}
          />
        </div>

        {/* People – auth required */}
        <div style={{ display: activeTab === 'people' ? 'block' : 'none' }}>
          {currentUser ? (
            <PeoplePage
              currentUser={currentUser}
              doctorsList={doctorsList}
              patientsList={patientsList}
              selectedPatient={selectedPatient}
              selectedDoctor={selectedDoctor}
              onSelectPatient={setSelectedPatient}
              onSelectDoctor={handleSelectDoctor}
            />
          ) : (
            <AuthGuard onGoToLogin={() => setActiveTab('login')} />
          )}
        </div>

        {/* History – auth required */}
        <div style={{ display: activeTab === 'history' ? 'block' : 'none' }}>
          {currentUser ? (
            <HistoryPage
              currentUser={currentUser}
              selectedPatient={selectedPatient}
              selectedDoctor={selectedDoctor}
              clinicalHistory={clinicalHistory}
            />
          ) : (
            <AuthGuard onGoToLogin={() => setActiveTab('login')} />
          )}
        </div>

        {/* Terminology Search */}
        <div style={{ display: activeTab === 'search' ? 'block' : 'none' }}>
          <SearchPage
            selectedTermData={selectedTermData}
            onSelectTerm={setSelectedTermData}
          />
        </div>

        {/* Translate */}
        <div style={{ display: activeTab === 'translate' ? 'block' : 'none' }}>
          <TranslatePage selectedTermData={selectedTermData} />
        </div>

        {/* FHIR Bundle – doctor/admin only */}
        <div style={{ display: activeTab === 'bundle' ? 'block' : 'none' }}>
          {currentUser && (currentUser.role === 'doctor' || currentUser.role === 'admin') ? (
            <BundlePage
              selectedTermData={selectedTermData}
              currentUser={currentUser}
              selectedPatient={selectedPatient}
              onAddToHistory={handleAddToHistory}
            />
          ) : (
            <AuthGuard
              onGoToLogin={() => setActiveTab('login')}
              message="FHIR Bundle submission is restricted to Doctors and Administrators."
            />
          )}
        </div>
      </main>

      {/* ── Footer ── */}
      <footer style={{
        background: 'var(--bg-surface)',
        borderTop: '1px solid var(--border)',
        padding: '24px 32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 16,
        fontSize: '0.84rem',
        color: 'var(--text-secondary)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 24,
            height: 24,
            borderRadius: 6,
            background: 'var(--primary-mint-soft)',
            color: 'var(--primary-mint)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Activity size={14} />
          </div>
          <span>AYUSH EMR Terminology Microservice · NAMASTE / ICD-11-TM2 / SNOMED-CT / NHCX</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <a href="/docs" target="_blank" rel="noreferrer" style={{ color: 'var(--primary-mint)', textDecoration: 'none', fontWeight: 600 }}>API Documentation</a>
          <span style={{ color: 'var(--border)' }}>|</span>
          <a href="/health" target="_blank" rel="noreferrer" style={{ color: 'var(--text-secondary)', textDecoration: 'none' }}>Health Check</a>
          <span style={{ color: 'var(--border)' }}>|</span>
          <span>Engine: {healthStatus?.database?.engine ?? 'PostgreSQL'} · v{healthStatus?.version ?? '1.0.0'}</span>
        </div>
      </footer>
    </div>
  );
}

// ─── Auth Guard ───────────────────────────────────────────────────────────────
function AuthGuard({ onGoToLogin, message }) {
  return (
    <div className="page-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 460 }}>
      <div className="card fade-in" style={{ textAlign: 'center', maxWidth: 480, padding: '48px 36px', borderRadius: 'var(--radius-xl)' }}>
        <div style={{
          width: 64,
          height: 64,
          borderRadius: 'var(--radius-lg)',
          background: 'var(--accent-amber-soft)',
          color: 'var(--accent-amber)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 20px',
          boxShadow: 'var(--shadow-sm)'
        }}>
          <Lock size={30} strokeWidth={2.2} />
        </div>
        <h3 style={{ fontSize: '1.45rem', marginBottom: 12, color: 'var(--text-primary)' }}>Authentication Required</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 28, lineHeight: 1.6, fontSize: '0.92rem' }}>
          {message || 'Please sign in to securely access clinical directory, medical history, and terminology bundles.'}
        </p>
        <button
          type="button"
          className="btn btn-primary btn-lg"
          style={{ padding: '12px 32px', fontSize: '0.95rem' }}
          onClick={onGoToLogin}
        >
          <Key size={16} />
          <span>Sign In to Continue</span>
        </button>
      </div>
    </div>
  );
}
