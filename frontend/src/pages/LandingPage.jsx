import { Link } from 'react-router-dom';
import './LandingPage.css';

const PLANS = [
  {
    tier: 'Básico',
    key: 'basico',
    price: '$29.000',
    period: '/mes',
    desc: 'Ideal para freelancers y microempresas que inician su control de facturas.',
    features: ['Hasta 3 usuarios', 'Facturas ilimitadas en su organización', 'Soporte por correo'],
    cta: 'Empezar',
    highlight: false,
  },
  {
    tier: 'Profesional',
    key: 'profesional',
    price: '$79.000',
    period: '/mes',
    desc: 'Equipos contables y PYMES que necesitan roles y asignaciones.',
    features: ['Hasta 15 usuarios', 'Roles administrador, contador y asistente', 'Extracción desde PDF e imágenes', 'Prioridad en soporte'],
    cta: 'Elegir Profesional',
    highlight: true,
  },
  {
    tier: 'Empresarial',
    key: 'empresarial',
    price: 'A medida',
    period: '',
    desc: 'Múltiples organizaciones y requisitos de integración o cumplimiento.',
    features: ['Usuarios y volumen a medida', 'Administración central de organizaciones', 'SLA y acompañamiento'],
    cta: 'Contactar ventas',
    highlight: false,
  },
];

export default function LandingPage() {
  return (
    <div className="landing">
      <header className="landing-header">
        <div className="landing-brand">
          <svg width="36" height="36" viewBox="0 0 40 40" fill="none" aria-hidden>
            <rect width="40" height="40" rx="10" fill="#0e7490" />
            <path d="M10 14h20M10 20h20M10 26h14" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
          <span>SGF</span>
        </div>
        <Link to="/login" className="btn btn-landing-outline">
          Iniciar sesión
        </Link>
      </header>

      <section className="landing-hero">
        <h1>Gestión de facturas para equipos que crecen</h1>
        <p className="landing-lead">
          Centralice facturas por organización, defina roles y mantenga a su contabilidad al día.
          Cada cliente trabaja en su propio espacio aislado y seguro.
        </p>
        <div className="landing-hero-actions">
          <a href="#planes" className="btn btn-landing-primary">
            Ver planes
          </a>
          <Link to="/login" className="btn btn-landing-ghost">
            Acceder a mi cuenta
          </Link>
        </div>
      </section>

      <section id="planes" className="landing-plans">
        <h2>Planes y precios</h2>
        <p className="landing-plans-sub">Elija el nivel que mejor se adapte a su organización.</p>
        <div className="landing-grid">
          {PLANS.map((p) => (
            <article key={p.key} className={`plan-card${p.highlight ? ' plan-card-highlight' : ''}`}>
              {p.highlight && <span className="plan-badge">Popular</span>}
              <h3>{p.tier}</h3>
              <p className="plan-desc">{p.desc}</p>
              <div className="plan-price">
                <strong>{p.price}</strong>
                <span>{p.period}</span>
              </div>
              <ul className="plan-features">
                {p.features.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
              <Link
                to="/login"
                className={p.highlight ? 'btn btn-landing-primary btn-plan' : 'btn btn-landing-outline btn-plan'}
              >
                {p.cta}
              </Link>
            </article>
          ))}
        </div>
      </section>

      <footer className="landing-footer">
        <p>SGF — Sistema de Gestión de Facturas · Proyecto académico / demo</p>
      </footer>
    </div>
  );
}
