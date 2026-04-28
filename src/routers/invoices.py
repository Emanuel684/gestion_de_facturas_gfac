"""
Invoices router — full CRUD with role-based access control.

Permission rules:
  - administrador role: can see ALL invoices, create/edit/delete any invoice.
  - contador role: can see all invoices, create invoices, edit invoices they created
    or are assigned to. Cannot delete.
  - asistente role: can see invoices they created or are assigned to,
    can create invoices, cannot edit status or delete.

DIAN traceability: `dian_lifecycle_status` + `invoice_events`; `document_locked` bloquea
campos fiscales salvo transiciones de estado permitidas.
"""
import io
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db import get_db
from src.dependencies import require_active_tenant_user
from src.dian.audit import build_audit_pack
from src.dian.audit_excel import audit_pack_to_xlsx_bytes, safe_audit_filename
from src.dian.events import record_invoice_event
from src.dian.validation import is_document_editing_locked, totals_match
from src.extraction import ALL_SUPPORTED_TYPES, extract_from_file
from src.models import (
    DianDocumentType,
    DianLifecycleStatus,
    Invoice,
    InvoiceAssignee,
    InvoiceEventType,
    InvoiceStatus,
    NotificationType,
    OrganizationFiscalProfile,
    User,
    UserRole,
)
from src.notifications import create_notification_for_org, create_notification_for_users
from src.schemas import (
    AssignedUser,
    InvoiceCreate,
    InvoiceEventOut,
    InvoiceOut,
    InvoicePage,
    InvoiceTraceResponse,
    InvoiceUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def _sync_document_lock(invoice: Invoice) -> None:
    unlocked = {DianLifecycleStatus.borrador, DianLifecycleStatus.rechazada_dian}
    invoice.document_locked = invoice.dian_lifecycle_status not in unlocked


def _actor_label(user: User) -> str:
    return user.username if user.username else f"usuario {user.id}"


def _invoice_to_out(invoice: Invoice) -> InvoiceOut:
    assigned = [
        AssignedUser(id=a.user.id, username=a.user.username)
        for a in invoice.assignees
        if a.user is not None and a.user.is_active
    ]
    return InvoiceOut(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        supplier=invoice.supplier,
        description=invoice.description,
        amount=invoice.amount,
        status=invoice.status,
        due_date=invoice.due_date,
        creator_id=invoice.creator_id,
        created_at=invoice.created_at,
        updated_at=invoice.updated_at,
        assigned_users=assigned,
        document_type=invoice.document_type,
        issue_date=invoice.issue_date,
        currency=invoice.currency,
        buyer_id_type=invoice.buyer_id_type,
        buyer_id_number=invoice.buyer_id_number,
        buyer_name=invoice.buyer_name,
        seller_snapshot_nit=invoice.seller_snapshot_nit,
        seller_snapshot_dv=invoice.seller_snapshot_dv,
        seller_snapshot_business_name=invoice.seller_snapshot_business_name,
        subtotal=invoice.subtotal,
        taxable_base=invoice.taxable_base,
        iva_rate=invoice.iva_rate,
        iva_amount=invoice.iva_amount,
        withholding_amount=invoice.withholding_amount,
        total_document=invoice.total_document,
        dian_lifecycle_status=invoice.dian_lifecycle_status,
        document_locked=invoice.document_locked,
    )


async def _get_invoice_or_404(invoice_id: int, org_id: int, db: AsyncSession) -> Invoice:
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.assignees).selectinload(InvoiceAssignee.user))
        .where(Invoice.id == invoice_id, Invoice.organization_id == org_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")
    return invoice


def _check_invoice_access(invoice: Invoice, user: User) -> None:
    if user.role == UserRole.administrador or user.role == UserRole.contador:
        return
    is_assigned = any(a.user_id == user.id for a in invoice.assignees)
    if invoice.creator_id != user.id and not is_assigned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")


def _check_invoice_edit(invoice: Invoice, user: User) -> None:
    if user.role == UserRole.administrador:
        return
    if user.role == UserRole.asistente:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los asistentes no pueden modificar facturas",
        )
    is_assigned = any(a.user_id == user.id for a in invoice.assignees)
    if invoice.creator_id != user.id and not is_assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el creador, asignado o un administrador puede modificar esta factura",
        )


def _check_invoice_delete(invoice: Invoice, user: User) -> None:
    if user.role != UserRole.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede eliminar facturas",
        )


def _locked_field_update_attempt(payload: InvoiceUpdate) -> bool:
    return any(
        [
            payload.invoice_number is not None,
            payload.supplier is not None,
            payload.description is not None,
            payload.amount is not None,
            payload.document_type is not None,
            payload.issue_date is not None,
            payload.currency is not None,
            payload.buyer_id_type is not None,
            payload.buyer_id_number is not None,
            payload.buyer_name is not None,
            payload.subtotal is not None,
            payload.taxable_base is not None,
            payload.iva_rate is not None,
            payload.iva_amount is not None,
            payload.withholding_amount is not None,
            payload.total_document is not None,
        ]
    )


def _resolve_monetary_fields_create(payload: InvoiceCreate, base_amount: Decimal) -> dict:
    """Deriva subtotales/IVA/total coherente con el monto interno si no se envían."""
    subtotal = payload.subtotal
    taxable_base = payload.taxable_base
    iva_rate = payload.iva_rate
    iva_amount = payload.iva_amount
    wh = payload.withholding_amount
    total_doc = payload.total_document

    if subtotal is None and total_doc is None and iva_rate is None and iva_amount is None:
        return {
            "subtotal": base_amount,
            "taxable_base": base_amount,
            "iva_rate": Decimal("0"),
            "iva_amount": Decimal("0"),
            "withholding_amount": wh,
            "total_document": base_amount,
        }

    sub = subtotal if subtotal is not None else base_amount
    rate = iva_rate if iva_rate is not None else Decimal("0")
    iva = iva_amount if iva_amount is not None else (sub * rate).quantize(Decimal("0.01"))
    tax_base = taxable_base if taxable_base is not None else sub
    w = wh or Decimal("0")
    total = total_doc if total_doc is not None else (sub + iva - w).quantize(Decimal("0.01"))
    return {
        "subtotal": sub,
        "taxable_base": tax_base,
        "iva_rate": rate,
        "iva_amount": iva,
        "withholding_amount": wh,
        "total_document": total,
    }


def _resolve_monetary_fields_update(invoice: Invoice, payload: InvoiceUpdate) -> dict:
    """Fusiona montos DIAN existentes con el payload parcial."""
    amt = payload.amount if payload.amount is not None else invoice.amount
    sub = payload.subtotal if payload.subtotal is not None else invoice.subtotal
    if sub is None:
        sub = amt
    taxable_base = payload.taxable_base if payload.taxable_base is not None else invoice.taxable_base
    if taxable_base is None:
        taxable_base = sub
    rate = payload.iva_rate if payload.iva_rate is not None else invoice.iva_rate
    if rate is None:
        rate = Decimal("0")
    wh = payload.withholding_amount if payload.withholding_amount is not None else invoice.withholding_amount
    iva = payload.iva_amount if payload.iva_amount is not None else invoice.iva_amount
    if iva is None:
        iva = (sub * rate).quantize(Decimal("0.01"))
    w = wh or Decimal("0")
    total = payload.total_document if payload.total_document is not None else invoice.total_document
    if total is None:
        total = (sub + iva - w).quantize(Decimal("0.01"))
    return {
        "subtotal": sub,
        "taxable_base": taxable_base,
        "iva_rate": rate,
        "iva_amount": iva,
        "withholding_amount": wh,
        "total_document": total,
    }


# ── List ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=InvoicePage)
async def list_invoices(
    status_filter: Annotated[InvoiceStatus | None, Query(alias="status")] = None,
    supplier_filter: Annotated[str | None, Query(alias="supplier")] = None,
    page: Annotated[int, Query(ge=0)] = 0,
    page_size: Annotated[int, Query(ge=1, le=100, alias="page_size")] = 10,
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> InvoicePage:
    org_id = current_user.organization_id
    query = select(Invoice).options(
        selectinload(Invoice.assignees).selectinload(InvoiceAssignee.user)
    )
    query = query.where(Invoice.organization_id == org_id)

    if current_user.role == UserRole.asistente:
        assigned_subq = select(InvoiceAssignee.invoice_id).where(
            InvoiceAssignee.user_id == current_user.id
        )
        query = query.where(
            or_(Invoice.creator_id == current_user.id, Invoice.id.in_(assigned_subq))
        )

    if status_filter:
        query = query.where(Invoice.status == status_filter)

    if supplier_filter:
        query = query.where(Invoice.supplier.ilike(f"%{supplier_filter}%"))

    query = query.order_by(Invoice.created_at.desc()).offset(page * page_size).limit(page_size + 1)
    result = await db.execute(query)
    rows = result.scalars().all()

    has_next = len(rows) > page_size
    items = rows[:page_size]

    return InvoicePage(
        items=[_invoice_to_out(inv) for inv in items],
        has_next=has_next,
        page=page,
        page_size=page_size,
    )


# ── Upload & Extract ─────────────────────────────────────────────────────────

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


def _detect_mime(file_bytes: bytes, filename: str, declared: str) -> str:
    if file_bytes.startswith(b"%PDF"):
        return "application/pdf"
    if file_bytes[:2] == b"PK" and filename.lower().endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    try:
        from PIL import Image

        with Image.open(io.BytesIO(file_bytes)) as img:
            img_map = {
                "JPEG": "image/jpeg",
                "PNG": "image/png",
                "WEBP": "image/webp",
                "BMP": "image/bmp",
                "TIFF": "image/tiff",
            }
            if img.format in img_map:
                return img_map[img.format]
    except Exception:
        pass
    return declared


@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_invoice_document(
    file: UploadFile = File(...),
    current_user: User = Depends(require_active_tenant_user),
) -> dict:
    content_type = file.content_type or ""
    filename = file.filename or "unknown"

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo excede el tamaño máximo de {MAX_UPLOAD_SIZE // (1024*1024)} MB.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo está vacío.",
        )

    content_type = _detect_mime(file_bytes, filename, content_type)
    if content_type not in ALL_SUPPORTED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Tipo de archivo no soportado: {content_type}. "
                "Formatos aceptados: imágenes (JPEG, PNG), PDF, DOCX."
            ),
        )

    try:
        extracted = extract_from_file(file_bytes, content_type, filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(e),
        )
    except RuntimeError as e:
        logger.error("Extraction library missing: %s", e)
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e),
        )
    except Exception:
        logger.exception("Unexpected error extracting data from %s", filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al procesar el archivo. Intente con otro documento.",
        )

    logger.info(
        "User id=%d uploaded %s — extracted fields: %s",
        current_user.id, filename, list(extracted.keys()),
    )

    has_core = bool(extracted.get("invoice_number") or extracted.get("amount"))
    if extracted.get("extraction_method") == "gemini" and has_core:
        msg = "Datos extraídos con Gemini; revise y confirme los campos."
    elif has_core:
        msg = "Datos extraídos exitosamente."
    else:
        msg = "Archivo procesado; revise los datos extraídos."

    return {
        "message": msg,
        "extracted": extracted,
        "filename": filename,
    }


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceOut:
    org_id = current_user.organization_id
    existing = await db.execute(
        select(Invoice).where(
            Invoice.organization_id == org_id,
            Invoice.invoice_number == payload.invoice_number,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una factura con número '{payload.invoice_number}'",
        )

    now = datetime.now(timezone.utc)
    issue_dt = payload.issue_date or now
    doc_type = payload.document_type or DianDocumentType.factura_venta
    currency = (payload.currency or "COP").strip().upper()
    dian_st = payload.dian_lifecycle_status or DianLifecycleStatus.borrador

    fp_result = await db.execute(
        select(OrganizationFiscalProfile).where(OrganizationFiscalProfile.organization_id == org_id)
    )
    fp = fp_result.scalar_one_or_none()
    seller_nit = fp.nit if fp else None
    seller_dv = fp.dv if fp else None
    seller_bn = fp.business_name if fp else None

    monetary = _resolve_monetary_fields_create(payload, payload.amount)
    subtotal = monetary.get("subtotal", payload.amount)
    taxable_base = monetary.get("taxable_base", payload.amount)
    iva_rate = monetary.get("iva_rate", Decimal("0"))
    iva_amount = monetary.get("iva_amount", Decimal("0"))
    wh = monetary.get("withholding_amount")
    total_doc = monetary.get("total_document", payload.amount)

    if subtotal is not None and iva_amount is not None and total_doc is not None:
        if not totals_match(subtotal, iva_amount, wh, total_doc):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Los totales (subtotal + IVA - retenciones) no coinciden con el total del documento",
            )

    invoice = Invoice(
        organization_id=org_id,
        invoice_number=payload.invoice_number,
        supplier=payload.supplier,
        description=payload.description,
        amount=payload.amount,
        status=payload.status,
        due_date=payload.due_date,
        creator_id=current_user.id,
        document_type=doc_type,
        issue_date=issue_dt,
        currency=currency,
        buyer_id_type=payload.buyer_id_type,
        buyer_id_number=payload.buyer_id_number,
        buyer_name=payload.buyer_name,
        seller_snapshot_nit=seller_nit,
        seller_snapshot_dv=seller_dv,
        seller_snapshot_business_name=seller_bn,
        subtotal=subtotal,
        taxable_base=taxable_base,
        iva_rate=iva_rate,
        iva_amount=iva_amount,
        withholding_amount=wh,
        total_document=total_doc,
        dian_lifecycle_status=dian_st,
    )
    _sync_document_lock(invoice)
    db.add(invoice)
    await db.flush()

    for uid in set(payload.assigned_user_ids):
        u = await db.get(User, uid)
        if not u or u.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Usuario con id={uid} no encontrado en la organización",
            )
        if not u.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Usuario con id={uid} está deshabilitado",
            )
        db.add(InvoiceAssignee(invoice_id=invoice.id, user_id=uid))

    await create_notification_for_org(
        db,
        organization_id=org_id,
        exclude_user_id=current_user.id,
        notification_type=NotificationType.invoice_created,
        title="Nueva factura registrada",
        message=f"{_actor_label(current_user)} creó la factura {invoice.invoice_number}.",
        invoice_id=invoice.id,
        payload={"invoice_number": invoice.invoice_number},
    )
    assigned_user_ids = {
        uid for uid in set(payload.assigned_user_ids) if uid != current_user.id
    }
    if assigned_user_ids:
        await create_notification_for_users(
            db,
            organization_id=org_id,
            user_ids=assigned_user_ids,
            notification_type=NotificationType.invoice_assigned,
            title="Factura asignada",
            message=f"Se le asignó la factura {invoice.invoice_number}.",
            invoice_id=invoice.id,
            payload={"invoice_number": invoice.invoice_number},
        )

    await record_invoice_event(
        db,
        invoice=invoice,
        event_type=InvoiceEventType.created,
        actor=current_user,
        payload={"invoice_number": invoice.invoice_number},
    )
    await db.commit()

    invoice = await _get_invoice_or_404(invoice.id, org_id, db)
    logger.info("Invoice id=%d created by user id=%d", invoice.id, current_user.id)
    return _invoice_to_out(invoice)


# ── Trace & audit (before /{invoice_id} single segment handlers if any) ─────

@router.get("/{invoice_id}/trace", response_model=InvoiceTraceResponse)
async def get_invoice_trace(
    invoice_id: int,
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceTraceResponse:
    from src.models import InvoiceEvent

    invoice = await _get_invoice_or_404(invoice_id, current_user.organization_id, db)
    _check_invoice_access(invoice, current_user)
    r = await db.execute(
        select(InvoiceEvent)
        .where(
            InvoiceEvent.invoice_id == invoice_id,
            InvoiceEvent.organization_id == current_user.organization_id,
        )
        .order_by(InvoiceEvent.created_at.asc())
    )
    events = r.scalars().all()
    return InvoiceTraceResponse(
        invoice=_invoice_to_out(invoice),
        events=[InvoiceEventOut.model_validate(e) for e in events],
    )


@router.get("/{invoice_id}/audit-pack")
async def get_invoice_audit_pack(
    invoice_id: int,
    export_format: Annotated[Literal["json", "xlsx"], Query(alias="format")] = "json",
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
):
    from src.models import InvoiceEvent

    invoice = await _get_invoice_or_404(invoice_id, current_user.organization_id, db)
    _check_invoice_access(invoice, current_user)

    r_ev = await db.execute(
        select(InvoiceEvent)
        .where(
            InvoiceEvent.invoice_id == invoice_id,
            InvoiceEvent.organization_id == current_user.organization_id,
        )
        .order_by(InvoiceEvent.created_at.asc())
    )
    events = r_ev.scalars().all()

    r_fp = await db.execute(
        select(OrganizationFiscalProfile).where(
            OrganizationFiscalProfile.organization_id == current_user.organization_id
        )
    )
    fp = r_fp.scalar_one_or_none()

    pack = build_audit_pack(
        invoice,
        list(events),
        fp,
        datetime.now(timezone.utc),
    )
    await record_invoice_event(
        db,
        invoice=invoice,
        event_type=InvoiceEventType.export_generated,
        actor=current_user,
        payload={"format": export_format},
    )
    await db.commit()
    if export_format == "json":
        return JSONResponse(content=pack)

    xlsx_bytes = audit_pack_to_xlsx_bytes(pack)
    fname = safe_audit_filename(invoice.invoice_number)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="paquete-auditoria-{fname}.xlsx"'},
    )


# ── Overdue ───────────────────────────────────────────────────────────────────

@router.get("/overdue", response_model=list[InvoiceOut])
async def list_overdue_invoices(
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> list[InvoiceOut]:
    now = datetime.now(timezone.utc)
    org_id = current_user.organization_id
    query = (
        select(Invoice)
        .options(selectinload(Invoice.assignees).selectinload(InvoiceAssignee.user))
        .where(
            Invoice.organization_id == org_id,
            Invoice.status == InvoiceStatus.pendiente,
            Invoice.due_date.is_not(None),
            Invoice.due_date < now,
        )
        .order_by(Invoice.due_date.asc())
    )

    if current_user.role == UserRole.asistente:
        assigned_subq = select(InvoiceAssignee.invoice_id).where(
            InvoiceAssignee.user_id == current_user.id
        )
        query = query.where(
            or_(Invoice.creator_id == current_user.id, Invoice.id.in_(assigned_subq))
        )

    result = await db.execute(query)
    invoices = result.scalars().unique().all()
    return [_invoice_to_out(inv) for inv in invoices]


@router.get("/due-soon", response_model=list[InvoiceOut])
async def list_due_soon_invoices(
    days: Annotated[int, Query(ge=1, le=30)] = 7,
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> list[InvoiceOut]:
    now = datetime.now(timezone.utc)
    due_until = now + timedelta(days=days)
    org_id = current_user.organization_id
    query = (
        select(Invoice)
        .options(selectinload(Invoice.assignees).selectinload(InvoiceAssignee.user))
        .where(
            Invoice.organization_id == org_id,
            Invoice.status == InvoiceStatus.pendiente,
            Invoice.due_date.is_not(None),
            Invoice.due_date >= now,
            Invoice.due_date <= due_until,
        )
        .order_by(Invoice.due_date.asc())
    )

    if current_user.role == UserRole.asistente:
        assigned_subq = select(InvoiceAssignee.invoice_id).where(
            InvoiceAssignee.user_id == current_user.id
        )
        query = query.where(
            or_(Invoice.creator_id == current_user.id, Invoice.id.in_(assigned_subq))
        )

    result = await db.execute(query)
    invoices = result.scalars().unique().all()
    return [_invoice_to_out(inv) for inv in invoices]


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: int,
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceOut:
    invoice = await _get_invoice_or_404(invoice_id, current_user.organization_id, db)
    _check_invoice_access(invoice, current_user)
    return _invoice_to_out(invoice)


# ── Update ────────────────────────────────────────────────────────────────────

@router.put("/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceOut:
    org_id = current_user.organization_id
    invoice = await _get_invoice_or_404(invoice_id, org_id, db)
    _check_invoice_edit(invoice, current_user)

    locked = is_document_editing_locked(invoice.dian_lifecycle_status, invoice.document_locked)
    if locked and _locked_field_update_attempt(payload):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Documento bloqueado para edición fiscal; solo puede cambiar estado de cobro, asignaciones o estado DIAN permitido",
        )

    old_dian = invoice.dian_lifecycle_status
    old_status = invoice.status
    old_assigned_user_ids = {a.user_id for a in invoice.assignees}

    if payload.invoice_number is not None:
        existing = await db.execute(
            select(Invoice).where(
                Invoice.organization_id == org_id,
                Invoice.invoice_number == payload.invoice_number,
                Invoice.id != invoice_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una factura con número '{payload.invoice_number}'",
            )
        invoice.invoice_number = payload.invoice_number

    if payload.supplier is not None:
        invoice.supplier = payload.supplier
    if payload.description is not None:
        invoice.description = payload.description
    if payload.amount is not None:
        invoice.amount = payload.amount
    if payload.status is not None:
        invoice.status = payload.status
    if payload.due_date is not None:
        invoice.due_date = payload.due_date

    if payload.document_type is not None:
        invoice.document_type = payload.document_type
    if payload.issue_date is not None:
        invoice.issue_date = payload.issue_date
    if payload.currency is not None:
        invoice.currency = payload.currency.strip().upper()
    if payload.buyer_id_type is not None:
        invoice.buyer_id_type = payload.buyer_id_type
    if payload.buyer_id_number is not None:
        invoice.buyer_id_number = payload.buyer_id_number
    if payload.buyer_name is not None:
        invoice.buyer_name = payload.buyer_name

    amt = invoice.amount
    if any(
        x is not None
        for x in (
            payload.subtotal,
            payload.taxable_base,
            payload.iva_rate,
            payload.iva_amount,
            payload.withholding_amount,
            payload.total_document,
        )
    ):
        monetary = _resolve_monetary_fields_update(invoice, payload)
        invoice.subtotal = monetary["subtotal"]
        invoice.taxable_base = monetary["taxable_base"]
        invoice.iva_rate = monetary["iva_rate"]
        invoice.iva_amount = monetary["iva_amount"]
        invoice.withholding_amount = monetary["withholding_amount"]
        invoice.total_document = monetary["total_document"]

    if invoice.subtotal is not None and invoice.iva_amount is not None and invoice.total_document is not None:
        if not totals_match(
            invoice.subtotal,
            invoice.iva_amount,
            invoice.withholding_amount,
            invoice.total_document,
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Los totales no son coherentes",
            )

    if payload.dian_lifecycle_status is not None:
        invoice.dian_lifecycle_status = payload.dian_lifecycle_status
        _sync_document_lock(invoice)
        if old_dian != invoice.dian_lifecycle_status:
            await record_invoice_event(
                db,
                invoice=invoice,
                event_type=InvoiceEventType.status_changed,
                actor=current_user,
                payload={"from": old_dian.value, "to": invoice.dian_lifecycle_status.value},
            )

    if payload.assigned_user_ids is not None:
        existing_user_ids = old_assigned_user_ids
        new_user_ids = set(payload.assigned_user_ids)

        to_remove = existing_user_ids - new_user_ids
        for a in list(invoice.assignees):
            if a.user_id in to_remove:
                await db.delete(a)

        to_add = new_user_ids - existing_user_ids
        for uid in to_add:
            u = await db.get(User, uid)
            if not u or u.organization_id != org_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Usuario con id={uid} no encontrado en la organización",
                )
            if not u.is_active:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Usuario con id={uid} está deshabilitado",
                )
            db.add(InvoiceAssignee(invoice_id=invoice.id, user_id=uid))

    changed_fields = [k for k, v in payload.model_dump(exclude_unset=True).items() if v is not None]
    status_changed = payload.status is not None and old_status != invoice.status
    if status_changed:
        await create_notification_for_org(
            db,
            organization_id=org_id,
            exclude_user_id=current_user.id,
            notification_type=NotificationType.invoice_status_changed,
            title="Estado de factura actualizado",
            message=(
                f"{_actor_label(current_user)} cambió la factura {invoice.invoice_number} "
                f"de {old_status.value} a {invoice.status.value}."
            ),
            invoice_id=invoice.id,
            payload={
                "invoice_number": invoice.invoice_number,
                "from_status": old_status.value,
                "to_status": invoice.status.value,
            },
        )

    if payload.assigned_user_ids is not None:
        new_assigned_user_ids = set(payload.assigned_user_ids)
        added_user_ids = new_assigned_user_ids - old_assigned_user_ids
        removed_user_ids = old_assigned_user_ids - new_assigned_user_ids
        if added_user_ids:
            await create_notification_for_users(
                db,
                organization_id=org_id,
                user_ids=added_user_ids,
                notification_type=NotificationType.invoice_assigned,
                title="Factura asignada",
                message=f"{_actor_label(current_user)} le asignó la factura {invoice.invoice_number}.",
                invoice_id=invoice.id,
                payload={"invoice_number": invoice.invoice_number},
            )
        if removed_user_ids:
            await create_notification_for_users(
                db,
                organization_id=org_id,
                user_ids=removed_user_ids,
                notification_type=NotificationType.invoice_unassigned,
                title="Factura desasignada",
                message=f"{_actor_label(current_user)} le quitó la factura {invoice.invoice_number}.",
                invoice_id=invoice.id,
                payload={"invoice_number": invoice.invoice_number},
            )

    non_assignment_or_status_update = any(
        field not in {"status", "assigned_user_ids"} for field in changed_fields
    )
    if non_assignment_or_status_update:
        await create_notification_for_org(
            db,
            organization_id=org_id,
            exclude_user_id=current_user.id,
            notification_type=NotificationType.invoice_updated,
            title="Factura actualizada",
            message=f"{_actor_label(current_user)} actualizó la factura {invoice.invoice_number}.",
            invoice_id=invoice.id,
            payload={"invoice_number": invoice.invoice_number, "fields": changed_fields},
        )

    await record_invoice_event(
        db,
        invoice=invoice,
        event_type=InvoiceEventType.updated,
        actor=current_user,
        payload={"fields": changed_fields},
    )
    await db.commit()
    invoice = await _get_invoice_or_404(invoice_id, org_id, db)
    logger.info("Invoice id=%d updated by user id=%d", invoice.id, current_user.id)
    return _invoice_to_out(invoice)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    current_user: User = Depends(require_active_tenant_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    invoice = await _get_invoice_or_404(invoice_id, current_user.organization_id, db)
    _check_invoice_delete(invoice, current_user)
    await db.delete(invoice)
    await db.commit()
    logger.info("Invoice id=%d deleted by user id=%d", invoice_id, current_user.id)
