"""
Figuras tipo dashboard (matplotlib, backend Agg) para incrustar en PDF y Excel.
"""
from __future__ import annotations

import io
from decimal import Decimal
from typing import Any

# Sin GUI (Docker / servidor)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import ticker

from src.schemas import DashboardStatsOut

_STATUS_LABELS = ("Pendiente", "Pagada", "Vencida")
_STATUS_KEYS = ("pendiente", "pagada", "vencida")
_COLORS = ("#f59e0b", "#10b981", "#ef4444")


def _num(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


def dashboard_figure_png(stats: DashboardStatsOut | dict[str, Any]) -> bytes:
    """
    Una figura 2x2 alineada con el dashboard web: tortas por estado, barras mensuales, histograma.
    """
    if isinstance(stats, DashboardStatsOut):
        d = stats.model_dump(mode="python")
    else:
        d = stats

    fig, axes = plt.subplots(2, 2, figsize=(11.5, 9.2))
    fig.patch.set_facecolor("#ffffff")
    plt.rcParams["font.family"] = "DejaVu Sans"

    # --- (0,0) Torta: cantidad por estado ---
    ax = axes[0, 0]
    counts = d.get("count_by_status") or {}
    sizes = [_num(counts.get(k, 0)) for k in _STATUS_KEYS]
    total_c = sum(sizes)
    if total_c > 0:
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=_STATUS_LABELS,
            autopct=lambda pct: f"{pct:.0f}%" if pct > 5 else "",
            colors=_COLORS,
            startangle=90,
        )
        for t in autotexts:
            t.set_fontsize(9)
        ax.set_title("Facturas por estado (cantidad)", fontsize=11, fontweight="bold")
    else:
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", fontsize=12, color="#6b7280")
        ax.set_axis_off()
        ax.set_title("Facturas por estado (cantidad)", fontsize=11, fontweight="bold")

    # --- (0,1) Torta: montos por estado ---
    ax = axes[0, 1]
    amounts = d.get("amount_by_status") or {}
    amts = [_num(amounts.get(k, 0)) for k in _STATUS_KEYS]
    total_a = sum(amts)
    if total_a > 0:
        ax.pie(
            amts,
            labels=_STATUS_LABELS,
            autopct=lambda pct: f"{pct:.0f}%" if pct > 4 else "",
            colors=_COLORS,
            startangle=90,
        )
        ax.set_title("Montos por estado (COP)", fontsize=11, fontweight="bold")
    else:
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", fontsize=12, color="#6b7280")
        ax.set_axis_off()
        ax.set_title("Montos por estado (COP)", fontsize=11, fontweight="bold")

    # --- (1,0) Barras: facturación mensual ---
    ax = axes[1, 0]
    monthly = d.get("monthly") or []
    if monthly:
        months = [m.get("month", "") for m in monthly]
        montos = [_num(m.get("total_amount")) for m in monthly]
        x = range(len(months))
        ax.bar(x, montos, color="#0e7490", edgecolor="#0c6577", linewidth=0.5)
        ax.set_xticks(list(x))
        ax.set_xticklabels(months, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("COP (millones)", fontsize=9)
        ax.ticklabel_format(style="plain", axis="y")
        # Escala legible en millones
        if max(montos, default=0) >= 1e6:
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{y / 1e6:.1f}M"))
        ax.set_title("Facturación mensual (total)", fontsize=11, fontweight="bold")
        ax.grid(axis="y", alpha=0.3)
    else:
        ax.text(0.5, 0.5, "Sin series mensuales", ha="center", va="center", fontsize=11, color="#6b7280")
        ax.set_axis_off()
        ax.set_title("Facturación mensual (total)", fontsize=11, fontweight="bold")

    # --- (1,1) Histograma horizontal: tramos de monto ---
    ax = axes[1, 1]
    hist = d.get("histogram_by_amount") or []
    if hist and any(_num(h.get("invoice_count", 0)) for h in hist):
        labels = [str(h.get("label", "")) for h in hist]
        vals = [int(h.get("invoice_count", 0) or 0) for h in hist]
        y = range(len(labels))
        ax.barh(list(y), vals, color="#14b8a6", edgecolor="#0d9488", linewidth=0.5)
        ax.set_yticks(list(y))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("Nº facturas", fontsize=9)
        ax.set_title("Histograma por tramo de monto", fontsize=11, fontweight="bold")
        ax.grid(axis="x", alpha=0.3)
        ax.invert_yaxis()
    else:
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center", fontsize=12, color="#6b7280")
        ax.set_axis_off()
        ax.set_title("Histograma por tramo de monto", fontsize=11, fontweight="bold")

    fig.suptitle("Resumen gráfico (mismos datos que el dashboard)", fontsize=13, fontweight="bold", y=0.98)
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
