"""
Extracción estructurada de facturas con Google Gemini (multimodal).

Requiere GEMINI_API_KEY. Si falla o no está configurada, el flujo en extraction.py
usa el extractor por regex sobre el texto OCR.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from src.config import settings

logger = logging.getLogger(__name__)

# Límite conservador para inline_data (Gemini ~20MB; dejamos margen)
MAX_INLINE_BYTES = 7 * 1024 * 1024

# Esquema de respuesta para generateContent (tipos en MAYÚSCULAS según API Gemini)
_GEMINI_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "invoice_number": {
            "type": "STRING",
            "description": "Número de factura o consecutivo visible en el documento.",
        },
        "supplier": {
            "type": "STRING",
            "description": "Nombre o razón social del proveedor/emisor/vendedor (no el comprador).",
        },
        "description": {
            "type": "STRING",
            "description": "Resumen breve del concepto o línea principal si es claro.",
            "nullable": True,
        },
        "amount": {
            "type": "NUMBER",
            "description": "Total a pagar o total del documento en moneda local (número decimal, sin símbolos).",
        },
        "currency": {
            "type": "STRING",
            "description": "Código ISO de moneda, ej. COP, USD.",
            "nullable": True,
        },
        "due_date": {
            "type": "STRING",
            "description": "Fecha de vencimiento en ISO 8601 si aparece; si no, null.",
            "nullable": True,
        },
        "issue_date": {
            "type": "STRING",
            "description": "Fecha de emisión/expedición en ISO 8601 si aparece.",
            "nullable": True,
        },
        "document_type": {
            "type": "STRING",
            "description": "Uno de: factura_venta, nota_credito, nota_debito según el documento.",
            "nullable": True,
        },
        "buyer_id_type": {
            "type": "STRING",
            "description": "Tipo de identificación del comprador (ej. NIT, CC, CE) si aparece.",
            "nullable": True,
        },
        "buyer_id_number": {
            "type": "STRING",
            "description": "Número de identificación del comprador sin puntos ni espacios.",
            "nullable": True,
        },
        "buyer_name": {
            "type": "STRING",
            "description": "Nombre o razón social del comprador/adquiriente si aparece.",
            "nullable": True,
        },
        "subtotal": {"type": "NUMBER", "description": "Subtotal antes de impuestos si aparece.", "nullable": True},
        "taxable_base": {"type": "NUMBER", "description": "Base gravable si aparece.", "nullable": True},
        "iva_rate": {
            "type": "NUMBER",
            "description": "Tasa IVA como decimal (ej. 0.19 para 19%).",
            "nullable": True,
        },
        "iva_amount": {"type": "NUMBER", "description": "Valor IVA si aparece.", "nullable": True},
        "withholding_amount": {
            "type": "NUMBER",
            "description": "Retenciones u otros descuentos si aparece.",
            "nullable": True,
        },
        "total_document": {
            "type": "NUMBER",
            "description": "Total del documento si difiere del total a pagar.",
            "nullable": True,
        },
    },
    "required": ["invoice_number", "supplier", "amount"],
}


def _system_instruction() -> str:
    return """Eres un experto en facturas comerciales y tributarias en Colombia y Latinoamérica.
Analiza el documento (imagen, PDF o texto) y extrae datos para un sistema ERP de gestión de facturas.

Reglas:
- Identifica al PROVEEDOR/EMISOR (quien vende o presta el servicio), no al comprador, en el campo supplier.
- amount: el total a pagar o total de la factura (número decimal puro, sin símbolo $ ni texto).
- Moneda: si no está clara, asume COP para documentos colombianos.
- Fechas: responde en ISO 8601 (ej. 2026-03-15 o 2026-03-15T00:00:00Z). Si solo hay día/mes/año inferido, usa solo la fecha.
- document_type: factura_venta (por defecto), nota_credito o nota_debito si el documento es explícitamente ese tipo.
- NIT/ID: sin puntos ni espacios en buyer_id_number.
- Si un campo no aparece o es ilegible, omítelo o usa null; no inventes números de factura."""


def _normalize_iso_date(s: str | None) -> str | None:
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    # Ya ISO
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError:
        pass
    # DD/MM/YYYY
    m = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})$", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            dt = datetime(y, mo, d, tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            return None
    return None


def _num(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v) if not isinstance(v, bool) else None
    if isinstance(v, str):
        s = v.strip().replace(" ", "").replace("$", "")
        if not s:
            return None
        try:
            if "," in s and "." in s:
                if s.rfind(",") > s.rfind("."):
                    s = s.replace(".", "").replace(",", ".")
                else:
                    s = s.replace(",", "")
            elif "," in s and s.count(",") == 1 and re.search(r",\d{1,2}$", s):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
            d = Decimal(s)
            return float(d)
        except (InvalidOperation, ValueError):
            return None
    return None


def _normalize_gemini_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """Convierte la respuesta del modelo a tipos compatibles con el frontend / API."""
    out: dict[str, Any] = {}

    if raw.get("invoice_number"):
        out["invoice_number"] = str(raw["invoice_number"]).strip()[:120]
    if raw.get("supplier"):
        out["supplier"] = str(raw["supplier"]).strip()[:255]

    desc = raw.get("description")
    if desc:
        out["description"] = str(desc).strip()[:500]

    amt = _num(raw.get("amount"))
    if amt is not None and amt > 0:
        out["amount"] = amt

    cur = raw.get("currency")
    if cur:
        out["currency"] = str(cur).strip().upper()[:8]

    for key in ("due_date", "issue_date"):
        iso = _normalize_iso_date(raw.get(key))
        if iso:
            out[key] = iso

    dt = raw.get("document_type")
    if dt in ("factura_venta", "nota_credito", "nota_debito"):
        out["document_type"] = dt

    if raw.get("buyer_id_type"):
        out["buyer_id_type"] = str(raw["buyer_id_type"]).strip()[:20]
    if raw.get("buyer_id_number"):
        out["buyer_id_number"] = re.sub(r"[\s.]", "", str(raw["buyer_id_number"]))[:32]
    if raw.get("buyer_name"):
        out["buyer_name"] = str(raw["buyer_name"]).strip()[:255]

    for fk in ("subtotal", "taxable_base", "iva_rate", "iva_amount", "withholding_amount", "total_document"):
        n = _num(raw.get(fk))
        if n is not None:
            out[fk] = n

    return out


def _parse_response_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)


def extract_with_gemini(
    file_bytes: bytes,
    content_type: str,
    filename: str,
    doc_plain_text: str,
) -> dict[str, Any]:
    """
    Llama a Gemini y devuelve un dict normalizado o {} si falla.
    doc_plain_text: texto ya extraído (OCR/docx) para modo texto o refuerzo.
    """
    api_key = (settings.gemini_api_key or "").strip()
    if not api_key:
        return {}

    if len(file_bytes) > MAX_INLINE_BYTES:
        logger.warning("Archivo demasiado grande para Gemini inline (%s bytes)", len(file_bytes))
        return {}

    model = (settings.gemini_model or "gemini-2.0-flash").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    ct = content_type or "application/octet-stream"
    docx = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    user_parts: list[dict[str, Any]] = []
    if ct == docx or filename.lower().endswith(".docx"):
        user_parts.append(
            {
                "text": (
                    "Extrae los datos del siguiente texto de un documento Word (factura o similar):\n\n"
                    "---\n"
                    f"{doc_plain_text[:48000]}"
                )
            }
        )
    else:
        b64 = base64.standard_b64encode(file_bytes).decode("ascii")
        if ct.startswith("image/") or ct == "application/pdf":
            mime = ct
        elif ct == "application/octet-stream":
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            mime = {
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "png": "image/png",
                "webp": "image/webp",
                "bmp": "image/bmp",
                "tiff": "image/tiff",
                "tif": "image/tiff",
                "pdf": "application/pdf",
            }.get(ext, "image/jpeg")
        else:
            mime = "image/jpeg"
        user_parts.append({"inline_data": {"mime_type": mime, "data": b64}})
        if doc_plain_text.strip():
            user_parts.append(
                {
                    "text": (
                        "Texto reconocido por OCR (puede ayudar si la imagen es borrosa):\n"
                        f"{doc_plain_text[:12000]}"
                    )
                }
            )

    payload = {
        "systemInstruction": {"parts": [{"text": _system_instruction()}]},
        "contents": [{"role": "user", "parts": user_parts}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
            "responseSchema": _GEMINI_SCHEMA,
        },
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            r = client.post(url, params={"key": api_key}, json=payload)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        logger.warning("Gemini HTTP error: %s %s", e.response.status_code, e.response.text[:500])
        return {}
    except Exception as e:
        logger.warning("Gemini request failed: %s", e)
        return {}

    try:
        candidates = data.get("candidates") or []
        if not candidates:
            logger.warning("Gemini: sin candidates: %s", str(data)[:400])
            return {}
        parts_out = candidates[0].get("content", {}).get("parts") or []
        if not parts_out:
            return {}
        text = parts_out[0].get("text") or ""
        raw = _parse_response_json(text)
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning("Gemini: no se pudo parsear JSON: %s", e)
        return {}

    normalized = _normalize_gemini_dict(raw)
    if not normalized.get("invoice_number") and not normalized.get("amount"):
        logger.info("Gemini devolvió datos sin número ni monto usable")
        return {}

    return normalized
