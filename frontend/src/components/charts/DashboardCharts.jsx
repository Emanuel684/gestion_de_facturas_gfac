import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ComposedChart,
  Line,
} from 'recharts';
import './Charts.css';

const STATUS_KEYS = ['pendiente', 'pagada', 'vencida'];
const STATUS_COLORS = { pendiente: '#f59e0b', pagada: '#10b981', vencida: '#ef4444' };
const STATUS_LABELS = { pendiente: 'Pendiente', pagada: 'Pagada', vencida: 'Vencida' };

export function moneyFmt(n) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(Number(n));
}

export function ChartCard({ title, subtitle, children, className = '' }) {
  return (
    <section className={`chart-card ${className}`}>
      {title ? <h3 className="chart-card-title">{title}</h3> : null}
      {subtitle ? <p className="chart-card-sub">{subtitle}</p> : null}
      <div className="chart-card-body">{children}</div>
    </section>
  );
}

function EmptyChart({ message = 'Sin datos en este periodo' }) {
  return <div className="chart-empty">{message}</div>;
}

/** Torta: cantidad de facturas por estado */
export function StatusCountPieChart({ stats }) {
  const data = STATUS_KEYS.map((k) => ({
    name: STATUS_LABELS[k],
    key: k,
    value: Number(stats?.count_by_status?.[k] ?? 0),
  })).filter((d) => d.value > 0);

  if (data.length === 0) {
    return <EmptyChart />;
  }

  return (
    <ResponsiveContainer width="100%" height="100%" minHeight={260}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          innerRadius={52}
          outerRadius={88}
          paddingAngle={2}
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
        >
          {data.map((d) => (
            <Cell key={d.key} fill={STATUS_COLORS[d.key]} />
          ))}
        </Pie>
        <Tooltip formatter={(v) => [`${v} facturas`, 'Cantidad']} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

/** Torta: montos por estado */
export function StatusAmountPieChart({ stats }) {
  const data = STATUS_KEYS.map((k) => ({
    name: STATUS_LABELS[k],
    key: k,
    value: Number(stats?.amount_by_status?.[k] ?? 0),
  })).filter((d) => d.value > 0);

  if (data.length === 0) {
    return <EmptyChart />;
  }

  return (
    <ResponsiveContainer width="100%" height="100%" minHeight={260}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          innerRadius={52}
          outerRadius={88}
          paddingAngle={2}
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
        >
          {data.map((d) => (
            <Cell key={d.key} fill={STATUS_COLORS[d.key]} />
          ))}
        </Pie>
        <Tooltip formatter={(v) => [moneyFmt(v), 'Monto']} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

/** Barras: facturación mensual + línea de cantidad de documentos */
export function MonthlyBillingChart({ monthly }) {
  const rows = (monthly ?? []).map((m) => ({
    month: m.month,
    monto: Number(m.total_amount),
    docs: Number(m.invoice_count),
  }));

  if (rows.length === 0) {
    return <EmptyChart />;
  }

  return (
    <ResponsiveContainer width="100%" height="100%" minHeight={280}>
      <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
        <XAxis dataKey="month" tick={{ fontSize: 11 }} />
        <YAxis
          yAxisId="left"
          tickFormatter={(v) => (v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : `${(v / 1e3).toFixed(0)}k`)}
          tick={{ fontSize: 11 }}
        />
        <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(value, name) =>
            name === 'monto' ? [moneyFmt(value), 'Monto total'] : [value, 'Facturas']
          }
          labelFormatter={(l) => `Mes ${l}`}
        />
        <Legend />
        <Bar yAxisId="left" dataKey="monto" name="Monto total" fill="#0e7490" radius={[4, 4, 0, 0]} />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="docs"
          name="Nº facturas"
          stroke="#7c3aed"
          strokeWidth={2}
          dot={{ r: 3 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/** Histograma: facturas por tramo de monto */
export function AmountHistogramChart({ histogram }) {
  const rows = (histogram ?? []).map((h) => ({
    label: h.label,
    n: h.invoice_count,
  }));

  if (!rows.some((r) => r.n > 0)) {
    return <EmptyChart message="Sin facturas en el rango para histograma" />;
  }

  return (
    <ResponsiveContainer width="100%" height="100%" minHeight={280}>
      <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal />
        <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
        <YAxis type="category" dataKey="label" width={100} tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v) => [`${v} facturas`, 'Cantidad']} />
        <Bar dataKey="n" name="Facturas" fill="#14b8a6" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Barras horizontales: ranking de organizaciones (plataforma) */
export function TopOrganizationsBarChart({ rows, maxBars = 12 }) {
  const slice = (rows ?? []).slice(0, maxBars).map((r) => ({
    name: r.name.length > 28 ? `${r.name.slice(0, 26)}…` : r.name,
    total: Number(r.total_amount),
    slug: r.slug,
  }));

  if (slice.length === 0) {
    return <EmptyChart message="Sin datos de ranking" />;
  }

  return (
    <ResponsiveContainer width="100%" height="100%" minHeight={Math.min(420, 40 + slice.length * 36)}>
      <BarChart data={slice} layout="vertical" margin={{ left: 8, right: 24, top: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
        <XAxis
          type="number"
          tickFormatter={(v) => (v >= 1e9 ? `${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : `${(v / 1e3).toFixed(0)}k`)}
          tick={{ fontSize: 10 }}
        />
        <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(v) => [moneyFmt(v), 'Facturación']}
          labelFormatter={(_, p) => p?.[0]?.payload?.slug ?? ''}
        />
        <Bar dataKey="total" name="Total" fill="#0e7490" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Bloque estándar: rejilla de gráficos del dashboard */
export function DashboardChartsGrid({ stats }) {
  if (!stats) return null;

  return (
    <>
      <div className="chart-grid">
        <ChartCard title="Facturas por estado" subtitle="Distribución por cantidad">
          <StatusCountPieChart stats={stats} />
        </ChartCard>
        <ChartCard title="Montos por estado" subtitle="Participación por valor (COP)">
          <StatusAmountPieChart stats={stats} />
        </ChartCard>
      </div>
      <div className="chart-grid">
        <ChartCard title="Evolución mensual" subtitle="Montos y volumen de documentos" className="chart-card--tall">
          <MonthlyBillingChart monthly={stats.monthly} />
        </ChartCard>
        <ChartCard
          title="Histograma de montos"
          subtitle="Cantidad de facturas por tramo (COP)"
          className="chart-card--tall"
        >
          <AmountHistogramChart histogram={stats.histogram_by_amount} />
        </ChartCard>
      </div>
    </>
  );
}
