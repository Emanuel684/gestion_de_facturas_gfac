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
    features: [
      'Hasta 15 usuarios',
      'Roles administrador, contador y asistente',
      'Extracción desde PDF e imágenes',
      'Prioridad en soporte',
    ],
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

const NAV = [
  { href: '#contexto', label: 'Contexto' },
  { href: '#problema', label: 'Problema' },
  { href: '#solucion', label: 'Solución' },
  { href: '#objetivos', label: 'Objetivos' },
  { href: '#alcance', label: 'Alcance' },
  { href: '#equipo', label: 'Equipo' },
  { href: '#planes', label: 'Planes' },
];

const OBJETIVOS_ESPECIFICOS = [
  {
    title: 'Centralizar la información',
    text: 'Una única plataforma con integridad, disponibilidad y consistencia de datos para consulta y análisis.',
  },
  {
    title: 'Automatizar el ciclo de vida',
    text: 'Registro, actualización de estados y seguimiento con menos carga operativa para administración.',
  },
  {
    title: 'Apoyar la decisión',
    text: 'Reportes en tiempo real e información actualizada para una visión clara del estado de las facturas.',
  },
  {
    title: 'Alertas y cumplimiento',
    text: 'Notificaciones para facturas pendientes o próximas a vencer, mejorando flujo de caja y pagos oportunos.',
  },
];

const COMPARATIVA = [
  { name: 'SAP Concur', note: 'Gasto y cumplimiento corporativo' },
  { name: 'Zoho Expense', note: 'Ecosistema amplio, curva de adopción' },
  { name: 'Ramp / Expensify', note: 'Enfoque enterprise y gastos' },
];

export default function LandingPage() {
  return (
    <div className="landing">
      <header className="landing-header" role="banner">
        <div className="landing-header-inner">
          <a href="#top" className="landing-brand">
            <svg width="36" height="36" viewBox="0 0 40 40" fill="none" aria-hidden>
              <rect width="40" height="40" rx="10" fill="#0e7490" />
              <path d="M10 14h20M10 20h20M10 26h14" stroke="white" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
            <span>SGF</span>
          </a>
          <nav className="landing-nav" aria-label="Secciones">
            {NAV.map((item) => (
              <a key={item.href} href={item.href} className="landing-nav-link">
                {item.label}
              </a>
            ))}
          </nav>
          <div className="landing-header-cta">
            <Link to="/login" className="btn btn-landing-outline">
              Iniciar sesión
            </Link>
            <Link to="/signup" className="btn btn-landing-primary">
              Crear cuenta
            </Link>
          </div>
        </div>
      </header>

      <main id="top">
        <section className="landing-hero" aria-labelledby="hero-title">
          <div className="landing-hero-badge">Universidad Pontificia Bolivariana · Proyecto Aplicado en TIC I · 2026</div>
          <h1 id="hero-title">
            Sistema web de gestión de facturas para{' '}
            <span className="landing-hero-accent">pequeñas y medianas empresas</span>
          </h1>
          <p className="landing-lead">
            Centralice facturas, automatice seguimiento y tome decisiones con información confiable. Una plataforma
            ligera, pensada para equipos administrativos y contables que necesitan orden sin complejidad innecesaria.
          </p>
          <div className="landing-hero-actions">
            <Link to="/signup" className="btn btn-landing-primary btn-landing-lg">
              Entrar a la plataforma
            </Link>
            <Link to="/login" className="btn btn-landing-ghost btn-landing-lg">
              Ya tengo cuenta
            </Link>
            <a href="#planes" className="btn btn-landing-outline btn-landing-lg">
              Ver planes
            </a>
          </div>
          <ul className="landing-stats" aria-label="Impacto esperado del proyecto">
            <li>
              <strong>−30%</strong>
              <span>tiempo en gestión de facturas (meta)</span>
            </li>
            <li>
              <strong>−25%</strong>
              <span>errores humanos (meta)</span>
            </li>
            <li>
              <strong>100%</strong>
              <span>trazabilidad y control en un solo lugar</span>
            </li>
          </ul>
        </section>

        <section id="contexto" className="landing-section landing-section-alt">
          <div className="landing-container">
            <p className="landing-kicker">Introducción</p>
            <h2 className="landing-section-title">Contexto y transformación digital</h2>
            <div className="landing-prose-grid">
              <div className="landing-prose">
                <p>
                  La transformación digital es un pilar para la sostenibilidad y competitividad de las organizaciones.
                  Las TIC permiten optimizar procesos, reducir costos y fortalecer decisiones basadas en datos confiables.
                </p>
                <p>
                  En <strong>PYMES</strong>, adoptar soluciones tecnológicas no es solo ventaja competitiva: es necesidad
                  estratégica. Muchas operan con recursos limitados y procesos manuales, lo que aumenta errores e
                  ineficiencia.
                </p>
              </div>
              <aside className="landing-highlight-card">
                <h3>Situación actual frecuente</h3>
                <p>
                  Hojas de cálculo, correos y PDF dispersos dificultan la trazabilidad, generan duplicidad y impiden una
                  visión clara y en tiempo real del estado financiero: señal de <strong>baja madurez digital</strong> y
                  necesidad de un sistema centralizado.
                </p>
              </aside>
            </div>
          </div>
        </section>

        <section id="problema" className="landing-section">
          <div className="landing-container landing-container-narrow">
            <p className="landing-kicker">Problema</p>
            <h2 className="landing-section-title">Qué estamos resolviendo</h2>
            <p className="landing-section-lead">
              Las PYMES presentan una gestión ineficiente de facturas por la ausencia de sistemas centralizados y
              automatizados, lo que genera cuellos de botella, errores y dificultades para el control financiero.
            </p>
            <ul className="landing-checklist">
              <li>Registro manual y duplicidad de información</li>
              <li>Pérdida de documentos y retrasos en pagos</li>
              <li>Riesgo de incumplimiento de obligaciones legales y fiscales</li>
              <li>Alta carga operativa para administración y contabilidad</li>
              <li>Poca visibilidad de facturas vencidas y flujo de caja</li>
            </ul>
          </div>
        </section>

        <section id="solucion" className="landing-section landing-section-alt">
          <div className="landing-container">
            <p className="landing-kicker">Justificación</p>
            <h2 className="landing-section-title">Por qué importa y en qué nos diferenciamos</h2>
            <p className="landing-section-lead landing-section-lead-center">
              Digitalizar la gestión de facturas mejora trazabilidad, reduce errores y libera tiempo del personal
              administrativo. El impacto esperado incluye mayor productividad y fortalecimiento de la cultura digital.
            </p>
            <div className="landing-compare">
              <div>
                <h3 className="landing-subtitle">Referentes en el mercado</h3>
                <p className="landing-muted">
                  Existen soluciones robustas orientadas a grandes volúmenes o presupuestos elevados:
                </p>
                <ul className="landing-compare-list">
                  {COMPARATIVA.map((c) => (
                    <li key={c.name}>
                      <strong>{c.name}</strong>
                      <span>{c.note}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="landing-differential">
                <h3 className="landing-subtitle">Diferencial SGF</h3>
                <p>
                  Aplicación web <strong>ligera y escalable</strong>, centrada en el usuario y diseñada para necesidades
                  reales de PYMES: <strong>usabilidad, simplicidad y eficiencia operativa</strong>, sin la complejidad ni
                  el costo típico de suites corporativas.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section id="objetivos" className="landing-section">
          <div className="landing-container">
            <p className="landing-kicker">Objetivos</p>
            <h2 className="landing-section-title">Hacia dónde apunta el proyecto</h2>
            <div className="landing-objective-general">
              <h3>Objetivo general</h3>
              <p>
                Desarrollar una aplicación web que permita <strong>centralizar, automatizar y controlar</strong> la
                facturación en PYMES mediante tecnologías modernas, contribuyendo a la transformación digital y a la
                eficiencia organizacional, reduciendo tareas manuales y el riesgo de error.
              </p>
            </div>
            <div className="landing-cards-grid">
              {OBJETIVOS_ESPECIFICOS.map((o) => (
                <article key={o.title} className="landing-card">
                  <h4>{o.title}</h4>
                  <p>{o.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section landing-section-alt">
          <div className="landing-container">
            <p className="landing-kicker">Contexto organizacional</p>
            <h2 className="landing-section-title">Para quién está pensado</h2>
            <div className="landing-two-col">
              <div className="landing-card landing-card-flat">
                <h3>Organización</h3>
                <p>
                  PYMES con áreas administrativas y financieras responsables de facturas y pagos: equipos que necesitan
                  orden, roles claros y seguimiento sin depender de carpetas sueltas.
                </p>
              </div>
              <div className="landing-card landing-card-flat">
                <h3>Usuarios</h3>
                <p>
                  Personal <strong>administrativo, contable y gerencial</strong> que requiere información confiable para la
                  operación diaria y decisiones estratégicas.
                </p>
              </div>
            </div>
            <p className="landing-muted landing-centered">
              Hoy, muchos procesos siguen siendo manuales o en herramientas no integradas: digitación repetitiva,
              múltiples archivos y baja trazabilidad, con riesgo de error y dependencia del conocimiento tácito del
              personal.
            </p>
          </div>
        </section>

        <section id="alcance" className="landing-section">
          <div className="landing-container">
            <p className="landing-kicker">Alcance</p>
            <h2 className="landing-section-title">Qué incluye el proyecto</h2>
            <div className="landing-scope-grid">
              <article className="landing-scope-card landing-scope-in">
                <h3>Incluye</h3>
                <ul>
                  <li>Registro y seguimiento de facturas</li>
                  <li>Control de estados</li>
                  <li>Reportes básicos</li>
                  <li>Base para notificaciones y alertas</li>
                </ul>
              </article>
              <article className="landing-scope-card landing-scope-out">
                <h3>No incluye (en esta etapa)</h3>
                <ul>
                  <li>Integraciones avanzadas con contabilidad externa</li>
                  <li>Facturación electrónica certificada</li>
                  <li>Módulos financieros avanzados</li>
                </ul>
              </article>
              <article className="landing-scope-card landing-scope-deliver">
                <h3>Entrega académica</h3>
                <p>
                  Al cierre del semestre: <strong>PMV funcional</strong>, documentación técnica, manual de usuario y
                  demostración del sistema.
                </p>
              </article>
            </div>
          </div>
        </section>

        <section className="landing-section landing-tech">
          <div className="landing-container">
            <p className="landing-kicker">Solución TIC</p>
            <h2 className="landing-section-title">Arquitectura del prototipo</h2>
            <p className="landing-section-lead landing-section-lead-center">
              Sistema cliente-servidor: interfaz en <strong>React</strong>, backend en <strong>Python</strong> con API
              REST, pensado para evolucionar de forma ordenada.
            </p>
            <ul className="landing-tech-list">
              <li>
                <span className="landing-tech-label">Frontend</span>
                React — experiencia de usuario clara y responsive
              </li>
              <li>
                <span className="landing-tech-label">Backend</span>
                Python — servicios REST y lógica de negocio
              </li>
              <li>
                <span className="landing-tech-label">Funcionalidades</span>
                Registro, consulta de estado, reportes y base para alertas automáticas
              </li>
            </ul>
          </div>
        </section>

        <section id="equipo" className="landing-section landing-section-alt">
          <div className="landing-container">
            <p className="landing-kicker">Equipo y proyecto académico</p>
            <h2 className="landing-section-title">Quienes construyen SGF</h2>
            <p className="landing-academic-meta">
              <strong>Universidad Pontificia Bolivariana</strong> · Ingeniería de Sistemas e Informática · Proyecto
              Aplicado en TIC I
              <br />
              Docente: <strong>Yuri Marcela Escobar</strong>
            </p>
            <div className="landing-team-grid">
              <article className="landing-team-card landing-team-lead">
                <h3>Emanuel Acevedo M</h3>
                <p className="landing-team-role">Líder de proyecto</p>
                <p className="landing-team-desc">
                  Coordinación general, arquitectura tecnológica y supervisión del desarrollo.
                </p>
              </article>
              <article className="landing-team-card">
                <h3>Nicolás Agudelo</h3>
                <p className="landing-team-role">Integrante</p>
                <p className="landing-team-desc">Desarrollo, pruebas y documentación.</p>
              </article>
              <article className="landing-team-card">
                <h3>John Rayo</h3>
                <p className="landing-team-role">Integrante</p>
                <p className="landing-team-desc">Desarrollo, pruebas y documentación.</p>
              </article>
              <article className="landing-team-card">
                <h3>Juan José Ospina</h3>
                <p className="landing-team-role">Integrante</p>
                <p className="landing-team-desc">Desarrollo, pruebas y documentación.</p>
              </article>
            </div>
            <p className="landing-muted landing-centered landing-team-roles-note">
              Roles de desarrollo: frontend (React), backend (Python), análisis de requerimientos, pruebas y documentación.
            </p>
          </div>
        </section>

        <section id="planes" className="landing-section landing-plans">
          <div className="landing-container">
            <h2 className="landing-section-title">Planes y precios</h2>
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
                    to={`/signup?plan=${p.key}`}
                    className={p.highlight ? 'btn btn-landing-primary btn-plan' : 'btn btn-landing-outline btn-plan'}
                  >
                    {p.cta}
                  </Link>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-cta-final">
          <div className="landing-container landing-cta-inner">
            <h2>¿Listo para ordenar su facturación?</h2>
            <p>Cree una cuenta o inicie sesión para acceder al panel de su organización.</p>
            <div className="landing-hero-actions">
              <Link to="/signup" className="btn btn-landing-primary btn-landing-lg">
                Crear cuenta gratuita
              </Link>
              <Link to="/login" className="btn btn-landing-ghost btn-landing-lg">
                Iniciar sesión
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="landing-footer" role="contentinfo">
        <div className="landing-footer-inner">
          <div className="landing-footer-brand">
            <span className="landing-footer-logo">SGF</span>
            <span>Sistema de Gestión de Facturas · Demo / proyecto académico UPB 2026</span>
          </div>
          <div className="landing-footer-links">
            <a href="#contexto">Información del proyecto</a>
            <Link to="/login">Acceso</Link>
            <Link to="/signup">Registro</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
