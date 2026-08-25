import { useEffect, useRef } from 'react';
import { 
  Search, 
  ArrowLeftRight, 
  PackageCheck, 
  History as HistoryIcon, 
  Users, 
  ShieldCheck, 
  Activity, 
  Sparkles, 
  Stethoscope, 
  HeartPulse, 
  Building2, 
  Key, 
  ArrowRight,
  Database
} from 'lucide-react';
import AnimatedNumber from '../components/AnimatedNumber.jsx';

export default function LandingPage({ onGetStarted }) {
  // ─── Scroll Reveal Intersection Observer ──────────────────────────────────
  const revealRefs = useRef([]);
  revealRefs.current = [];

  const addToRevealRefs = (el) => {
    if (el && !revealRefs.current.includes(el)) {
      revealRefs.current.push(el);
    }
  };

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );

    revealRefs.current.forEach((el) => {
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  const features = [
    {
      Icon: Search,
      title: 'Terminology Search',
      desc: '18,500+ traditional medicine terms with 3-tier cascade: exact hash → SQL substring → BioBERT semantic search.',
      color: 'var(--primary-mint)',
      bg: 'var(--primary-mint-soft)',
    },
    {
      Icon: ArrowLeftRight,
      title: 'Dual Coding Engine',
      desc: 'Automatic AYUSH ↔ ICD-11-TM2 translation for Ayurveda, Unani, and Siddha medical standards.',
      color: 'var(--accent-blue)',
      bg: 'var(--accent-blue-soft)',
    },
    {
      Icon: PackageCheck,
      title: 'FHIR R4 Bundles',
      desc: 'Clinician-driven FHIR R4 Bundle generation linked to patient records and NHCX insurance claims.',
      color: 'var(--accent-teal)',
      bg: 'var(--accent-teal-soft)',
    },
    {
      Icon: HistoryIcon,
      title: 'Clinical Audit History',
      desc: 'Auditable patient history with NAMASTE + ICD-11 double-coded entries timestamped and role-filtered.',
      color: 'var(--accent-lavender)',
      bg: 'var(--accent-lavender-soft)',
    },
    {
      Icon: Users,
      title: 'People Directory',
      desc: 'Role-aware directory: patients connect with doctors, doctors manage patients, admins audit records.',
      color: 'var(--accent-emerald)',
      bg: 'var(--accent-emerald-soft)',
    },
    {
      Icon: ShieldCheck,
      title: 'ABHA & PBAC Security',
      desc: 'Role-based access control (PBAC) integrated with ABHA OAuth 2.0 authentication and append-only audit logging.',
      color: 'var(--primary-sage)',
      bg: 'var(--primary-sage-soft)',
    },
  ];

  const roles = [
    {
      Icon: HeartPulse,
      label: 'Patient',
      desc: 'View personal clinical records, browse registered AYUSH doctors, and track diagnosed treatment history.',
      color: 'var(--accent-blue)',
      bg: 'var(--accent-blue-soft)',
      borderColor: 'rgba(37, 99, 235, 0.2)',
    },
    {
      Icon: Stethoscope,
      label: 'Doctor',
      desc: 'Access patient records, author and submit FHIR bundles with AYUSH dual-coding, and manage consultations.',
      color: 'var(--primary-mint)',
      bg: 'var(--primary-mint-soft)',
      borderColor: 'rgba(13, 148, 136, 0.25)',
    },
    {
      Icon: Building2,
      label: 'Administrator',
      desc: 'System-wide governance: inspect all doctor-patient connections, clinical registries, and FHIR submission logs.',
      color: 'var(--accent-lavender)',
      bg: 'var(--accent-lavender-soft)',
      borderColor: 'rgba(124, 58, 237, 0.2)',
    },
  ];

  return (
    <div style={{ minHeight: '100vh', overflowX: 'hidden' }}>

      {/* ══════════════════════════════════════════════════════════════
          HERO SECTION
      ══════════════════════════════════════════════════════════════ */}
      <section style={{
        position: 'relative',
        padding: '80px 24px 70px',
        textAlign: 'center',
        background: 'radial-gradient(ellipse 90% 60% at 50% 0%, rgba(13, 148, 136, 0.07) 0%, rgba(37, 99, 235, 0.02) 50%, transparent 80%)',
        overflow: 'hidden',
      }}>

        {/* Eyebrow Label */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          background: 'var(--bg-surface)',
          border: '1px solid rgba(13, 148, 136, 0.25)',
          boxShadow: 'var(--shadow-sm)',
          borderRadius: 'var(--radius-pill)',
          padding: '6px 18px',
          marginBottom: 24,
          fontSize: '0.78rem',
          fontWeight: 700,
          color: 'var(--primary-sage)',
          letterSpacing: '0.04em',
        }}>
          <Sparkles size={14} color="var(--primary-mint)" />
          <span>MINISTRY OF AYUSH · DIGITAL HEALTH TERMINOLOGY INFRASTRUCTURE</span>
        </div>

        {/* Large Typography Headline */}
        <h1 style={{
          fontSize: 'clamp(2.5rem, 5.5vw, 4.2rem)',
          fontWeight: 800,
          lineHeight: 1.15,
          color: 'var(--text-primary)',
          letterSpacing: '-0.035em',
          maxWidth: 960,
          margin: '0 auto 22px',
        }}>
          Unified Traditional Medicine <br />
          <span style={{
            background: 'linear-gradient(135deg, #0d9488 0%, #2563eb 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}>
            Terminology &amp; Interoperability
          </span>
        </h1>

        {/* Supporting Description */}
        <p style={{
          fontSize: 'clamp(1.05rem, 1.9vw, 1.22rem)',
          color: 'var(--text-secondary)',
          maxWidth: 740,
          margin: '0 auto 38px',
          lineHeight: 1.7,
        }}>
          India's authoritative digital health microservice connecting <strong style={{ color: 'var(--text-primary)' }}>NAMASTE</strong>,{' '}
          <strong style={{ color: 'var(--text-primary)' }}>WHO ICD-11 TM2</strong>, and{' '}
          <strong style={{ color: 'var(--text-primary)' }}>FHIR R4</strong> for seamless Ayurveda, Unani, and Siddha clinical workflows.
        </p>

        {/* Primary CTA */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: 14, flexWrap: 'wrap', marginBottom: 52 }}>
          <button
            id="landing-login-btn"
            type="button"
            className="btn btn-primary btn-lg"
            onClick={onGetStarted}
            style={{
              padding: '15px 36px',
              fontSize: '1.04rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              boxShadow: '0 6px 20px rgba(13, 148, 136, 0.28)',
            }}
          >
            <Key size={18} />
            <span>Sign In to Portal</span>
            <ArrowRight size={16} />
          </button>
        </div>

        {/* Stats Strip with Premium Count-Up Animation */}
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          gap: 48,
          flexWrap: 'wrap',
          marginTop: 20,
          paddingTop: 36,
          borderTop: '1px solid var(--border-subtle)',
          maxWidth: 1000,
          margin: '0 auto',
        }}>
          <div style={{ textAlign: 'center', minWidth: 140 }}>
            <div style={{
              fontSize: '2.4rem',
              fontWeight: 800,
              color: 'var(--primary-mint)',
              lineHeight: 1.1,
            }}>
              <AnimatedNumber value={18500} suffix="+" delay={0} duration={2100} />
            </div>
            <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: 6, fontWeight: 600 }}>
              AYUSH Terms Indexed
            </div>
          </div>

          <div style={{ textAlign: 'center', minWidth: 140 }}>
            <div style={{
              fontSize: '2.4rem',
              fontWeight: 800,
              color: 'var(--primary-mint)',
              lineHeight: 1.1,
            }}>
              <AnimatedNumber value={3} suffix="-Tier" delay={120} duration={1400} />
            </div>
            <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: 6, fontWeight: 600 }}>
              Cascade Search Engine
            </div>
          </div>

          <div style={{ textAlign: 'center', minWidth: 140 }}>
            <div style={{
              fontSize: '2.4rem',
              fontWeight: 800,
              color: 'var(--primary-mint)',
              lineHeight: 1.1,
            }}>
              <AnimatedNumber value={11} prefix="ICD-" delay={240} duration={1600} />
            </div>
            <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: 6, fontWeight: 600 }}>
              TM2 &amp; SNOMED-CT Mapped
            </div>
          </div>

          <div style={{ textAlign: 'center', minWidth: 140 }}>
            <div style={{
              fontSize: '2.4rem',
              fontWeight: 800,
              color: 'var(--primary-mint)',
              lineHeight: 1.1,
            }}>
              <AnimatedNumber value={4} prefix="FHIR R" delay={360} duration={1400} />
            </div>
            <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: 6, fontWeight: 600 }}>
              NHCX Insurance Ready
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          ROLE CARDS SECTION (With Scroll-Reveal & Interactive Depth)
      ══════════════════════════════════════════════════════════════ */}
      <section 
        ref={addToRevealRefs} 
        className="scroll-reveal" 
        style={{ padding: '80px 24px', maxWidth: 1160, margin: '0 auto' }}
      >
        <div style={{ textAlign: 'center', marginBottom: 48 }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            background: 'var(--primary-mint-soft)',
            border: '1px solid rgba(13, 148, 136, 0.25)',
            borderRadius: 'var(--radius-pill)',
            padding: '5px 16px',
            marginBottom: 14,
            fontSize: '0.78rem',
            fontWeight: 700,
            color: 'var(--primary-mint)',
            letterSpacing: '0.06em',
          }}>
            <Users size={13} />
            <span>ROLE-AWARE ACCESS</span>
          </div>
          <h2 style={{ fontSize: '2.1rem', fontWeight: 800, marginBottom: 12, color: 'var(--text-primary)' }}>
            Tailored Experiences for Every Stakeholder
          </h2>
          <p style={{ color: 'var(--text-secondary)', maxWidth: 560, margin: '0 auto', fontSize: '0.96rem' }}>
            Secure Policy-Based Access Control (PBAC) providing dedicated clinical interfaces for patients, practitioners, and administrators.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 24 }}>
          {roles.map((r) => {
            const RoleIcon = r.Icon;
            return (
              <div
                key={r.label}
                className="card card-interactive"
                style={{
                  background: 'var(--bg-surface)',
                  border: `1px solid ${r.borderColor}`,
                  borderRadius: 'var(--radius-xl)',
                  padding: '32px 28px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{
                    width: 52,
                    height: 52,
                    borderRadius: 'var(--radius-md)',
                    background: r.bg,
                    color: r.color,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: 20,
                  }}>
                    <RoleIcon size={26} strokeWidth={2.2} />
                  </div>
                  <div style={{ fontWeight: 800, fontSize: '1.25rem', color: 'var(--text-primary)', marginBottom: 10 }}>
                    {r.label}
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', lineHeight: 1.65, marginBottom: 24 }}>
                    {r.desc}
                  </p>
                </div>

                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={onGetStarted}
                  style={{
                    width: '100%',
                    justifyContent: 'space-between',
                    padding: '11px 18px',
                    borderRadius: 'var(--radius-pill)',
                    fontWeight: 600,
                  }}
                >
                  <span>Sign In as {r.label}</span>
                  <ArrowRight size={15} />
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          FEATURE CAPABILITIES GRID (With Scroll Reveal)
      ══════════════════════════════════════════════════════════════ */}
      <section 
        ref={addToRevealRefs}
        className="scroll-reveal"
        style={{
          padding: '80px 24px',
          background: 'var(--bg-subtle)',
          borderTop: '1px solid var(--border)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div style={{ maxWidth: 1160, margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: 48 }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-pill)',
              padding: '5px 16px',
              marginBottom: 14,
              fontSize: '0.78rem',
              fontWeight: 700,
              color: 'var(--accent-teal)',
              letterSpacing: '0.06em',
            }}>
              <Activity size={13} />
              <span>CORE ARCHITECTURE</span>
            </div>
            <h2 style={{ fontSize: '2.1rem', fontWeight: 800, marginBottom: 12, color: 'var(--text-primary)' }}>
              Comprehensive Terminology &amp; EMR Services
            </h2>
            <p style={{ color: 'var(--text-secondary)', maxWidth: 540, margin: '0 auto' }}>
              Engineered for high performance, sub-millisecond retrieval, and strict healthcare regulatory standards.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 24 }}>
            {features.map((f) => {
              const FeatIcon = f.Icon;
              return (
                <div
                  key={f.title}
                  className="card card-interactive"
                  style={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-lg)',
                    padding: '28px',
                  }}
                >
                  <div style={{
                    width: 46,
                    height: 46,
                    borderRadius: 'var(--radius-sm)',
                    background: f.bg,
                    color: f.color,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: 18,
                  }}>
                    <FeatIcon size={22} strokeWidth={2.2} />
                  </div>
                  <div style={{ fontWeight: 700, fontSize: '1.1rem', color: 'var(--text-primary)', marginBottom: 8 }}>
                    {f.title}
                  </div>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.65 }}>
                    {f.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════
          BOTTOM CTA SECTION
      ══════════════════════════════════════════════════════════════ */}
      <section 
        ref={addToRevealRefs}
        className="scroll-reveal"
        style={{ padding: '96px 24px', textAlign: 'center' }}
      >
        <div style={{
          maxWidth: 820,
          margin: '0 auto',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-2xl)',
          padding: '56px 40px',
          boxShadow: 'var(--shadow-card)',
        }}>
          <h2 style={{ fontSize: '2.2rem', fontWeight: 800, marginBottom: 16, color: 'var(--text-primary)' }}>
            Ready to Connect to AYUSH Terminology?
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 32, maxWidth: 520, margin: '0 auto 32px', fontSize: '1rem' }}>
            Clinicians, healthcare facilities, and patients can authenticate securely to access terminology translation and clinical records.
          </p>
          <button
            id="landing-login-btn-bottom"
            type="button"
            className="btn btn-primary btn-lg"
            onClick={onGetStarted}
            style={{
              padding: '15px 44px',
              fontSize: '1.05rem',
              fontWeight: 700,
              borderRadius: 'var(--radius-pill)',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
              boxShadow: '0 6px 20px rgba(13, 148, 136, 0.3)',
            }}
          >
            <Key size={18} />
            <span>Sign In to Portal</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </section>
    </div>
  );
}
