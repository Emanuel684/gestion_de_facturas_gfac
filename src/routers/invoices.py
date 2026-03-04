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
from datetime import datetime, timezone
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
