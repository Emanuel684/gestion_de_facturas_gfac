"""
Invoices router — full CRUD with role-based access control.

Permission rules:
  - administrador role: can see ALL invoices, create/edit/delete any invoice.
  - contador role: can see all invoices, create invoices, edit invoices they created
    or are assigned to. Cannot delete.
  - asistente role: can see invoices they created or are assigned to,
    can create invoices, cannot edit status or delete.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db import get_db
from src.dependencies import get_current_user
from src.extraction import ALL_SUPPORTED_TYPES, extract_from_file
from src.models import Invoice, InvoiceAssignee, InvoiceStatus, User, UserRole
from src.schemas import AssignedUser, InvoiceCreate, InvoiceOut, InvoicePage, InvoiceUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/invoices", tags=["invoices"])


def _invoice_to_out(invoice: Invoice) -> InvoiceOut:
    assigned = [AssignedUser(id=a.user.id, username=a.user.username) for a in invoice.assignees]
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
    )


async def _get_invoice_or_404(invoice_id: int, db: AsyncSession) -> Invoice:
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.assignees).selectinload(InvoiceAssignee.user))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")
    return invoice


def _check_invoice_access(invoice: Invoice, user: User) -> None:
    """Raise 403 if user does not have read access to this invoice."""
    if user.role == UserRole.administrador or user.role == UserRole.contador:
        return  # admin and contador can see all invoices
    # asistente can only see invoices they created or are assigned to
    is_assigned = any(a.user_id == user.id for a in invoice.assignees)
    if invoice.creator_id != user.id and not is_assigned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")


def _check_invoice_edit(invoice: Invoice, user: User) -> None:
    """Raise 403 if user cannot edit this invoice."""
    if user.role == UserRole.administrador:
        return
    if user.role == UserRole.asistente:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los asistentes no pueden modificar facturas",
        )
    # contador can only edit invoices they created or are assigned to
    is_assigned = any(a.user_id == user.id for a in invoice.assignees)
    if invoice.creator_id != user.id and not is_assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el creador, asignado o un administrador puede modificar esta factura",
        )


def _check_invoice_delete(invoice: Invoice, user: User) -> None:
    """Raise 403 if user cannot delete this invoice. Only administrador can delete."""
    if user.role != UserRole.administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un administrador puede eliminar facturas",
        )


# ── List ─────────────────────────────────────────────────────────────────────

# ── List ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=InvoicePage)
async def list_invoices(
    status_filter: Annotated[InvoiceStatus | None, Query(alias="status")] = None,
    supplier_filter: Annotated[str | None, Query(alias="supplier")] = None,
    page: Annotated[int, Query(ge=0)] = 0,
    page_size: Annotated[int, Query(ge=1, le=100, alias="page_size")] = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoicePage:
    """
    List invoices with cursor-style pagination.
    - page: zero-based page index.
    - page_size: number of items per page (default 10, max 100).
    - Returns `has_next=true` when there are more items after the current page.

    Administrador and Contador see all invoices.
    Asistente sees only invoices they created or are assigned to.
    Supports optional ?status= and ?supplier= filters.
    """
    query = select(Invoice).options(
        selectinload(Invoice.assignees).selectinload(InvoiceAssignee.user)
    )

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

    # Fetch one extra row to detect whether a next page exists
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


@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_invoice_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Upload an image, PDF, or DOCX document containing invoice data.
    Extracts text and returns structured invoice fields that can be used
    to pre-fill the invoice creation form.

    Accepted formats: JPEG, PNG, WEBP, BMP, TIFF, PDF, DOCX.
    Max file size: 10 MB.

    Returns a JSON object with extracted fields:
      - invoice_number, supplier, amount, description, due_date
      - raw_text (full extracted text for reference)
    Fields that could not be extracted are omitted.
    """
    # Validate file type
    content_type = file.content_type or ""
    filename = file.filename or "unknown"

    if content_type not in ALL_SUPPORTED_TYPES:
        # Try extension-based fallback before rejecting
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in {"jpg", "jpeg", "png", "webp", "bmp", "tiff", "tif", "pdf", "docx"}:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    f"Tipo de archivo no soportado: {content_type}. "
                    "Formatos aceptados: imágenes (JPEG, PNG), PDF, DOCX."
                ),
            )

    # Read file with size limit
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

    # Extract data
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

    return {
        "message": "Datos extraídos exitosamente" if extracted.get("invoice_number") or extracted.get("amount") else "Archivo procesado — revise los datos extraídos",
        "extracted": extracted,
        "filename": filename,
    }


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceOut:
    # Check for duplicate invoice number
    existing = await db.execute(
        select(Invoice).where(Invoice.invoice_number == payload.invoice_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una factura con número '{payload.invoice_number}'",
        )

    invoice = Invoice(
        invoice_number=payload.invoice_number,
        supplier=payload.supplier,
        description=payload.description,
        amount=payload.amount,
        status=payload.status,
        due_date=payload.due_date,
        creator_id=current_user.id,
    )
    db.add(invoice)
    await db.flush()

    for user_id in set(payload.assigned_user_ids):
        u = await db.get(User, user_id)
        if not u:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Usuario con id={user_id} no encontrado",
            )
        db.add(InvoiceAssignee(invoice_id=invoice.id, user_id=user_id))

    await db.commit()

    invoice = await _get_invoice_or_404(invoice.id, db)
    logger.info("Invoice id=%d created by user id=%d", invoice.id, current_user.id)
    return _invoice_to_out(invoice)


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceOut:
    invoice = await _get_invoice_or_404(invoice_id, db)
    _check_invoice_access(invoice, current_user)
    return _invoice_to_out(invoice)


# ── Update ────────────────────────────────────────────────────────────────────

@router.put("/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvoiceOut:
    invoice = await _get_invoice_or_404(invoice_id, db)
    _check_invoice_edit(invoice, current_user)

    if payload.invoice_number is not None:
        # Check uniqueness if changing invoice number
        existing = await db.execute(
            select(Invoice).where(
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

    # Sync assigned users if provided
    if payload.assigned_user_ids is not None:
        existing_user_ids = {a.user_id for a in invoice.assignees}
        new_user_ids = set(payload.assigned_user_ids)

        to_remove = existing_user_ids - new_user_ids
        for a in list(invoice.assignees):
            if a.user_id in to_remove:
                await db.delete(a)

        to_add = new_user_ids - existing_user_ids
        for user_id in to_add:
            u = await db.get(User, user_id)
            if not u:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Usuario con id={user_id} no encontrado",
                )
            db.add(InvoiceAssignee(invoice_id=invoice.id, user_id=user_id))

    await db.commit()
    invoice = await _get_invoice_or_404(invoice_id, db)
    logger.info("Invoice id=%d updated by user id=%d", invoice.id, current_user.id)
    return _invoice_to_out(invoice)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    invoice = await _get_invoice_or_404(invoice_id, db)
    _check_invoice_delete(invoice, current_user)
    await db.delete(invoice)
    await db.commit()
    logger.info("Invoice id=%d deleted by user id=%d", invoice_id, current_user.id)
