"""Validación de `portal_path` (segmento de URL de login público por organización)."""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Organization

PORTAL_PATH_RESERVED = frozenset(
    {
        "plataforma",
        "login",
        "signup",
        "app",
        "api",
        "checkout",
        "public",
    }
)

PORTAL_PATH_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_portal_path(v: str) -> str:
    return v.strip().lower()


def validate_portal_path_format(v: str) -> str:
    v = normalize_portal_path(v)
    if not v or len(v) > 80:
        raise ValueError("portal_path inválido")
    if not PORTAL_PATH_RE.match(v):
        raise ValueError("portal_path: solo minúsculas, números y guiones")
    if v in PORTAL_PATH_RESERVED:
        raise ValueError("portal_path reservado")
    return v


async def find_org_identifier_conflict(
    db: AsyncSession,
    *,
    exclude_org_id: int | None,
    slug: str,
    portal_path: str,
) -> str | None:
    """Evita ambigüedad en login: un mismo string no puede ser slug de un tenant y portal_path de otro."""
    if exclude_org_id is not None:
        id_clause = Organization.id != exclude_org_id
    else:
        id_clause = True

    r_slug = await db.execute(select(Organization.id).where(Organization.slug == slug, id_clause))
    if r_slug.scalar_one_or_none() is not None:
        return f"Ya existe una organización con slug '{slug}'"

    r_portal = await db.execute(select(Organization.id).where(Organization.portal_path == portal_path, id_clause))
    if r_portal.scalar_one_or_none() is not None:
        return f"Ya existe una organización con ruta de acceso '{portal_path}'"

    r_cross_slug = await db.execute(
        select(Organization.id).where(Organization.slug == portal_path, id_clause)
    )
    if r_cross_slug.scalar_one_or_none() is not None:
        return f"La ruta de acceso '{portal_path}' coincide con el slug de otra organización"

    r_cross_portal = await db.execute(
        select(Organization.id).where(Organization.portal_path == slug, id_clause)
    )
    if r_cross_portal.scalar_one_or_none() is not None:
        return f"El slug '{slug}' coincide con la ruta de acceso de otra organización"

    return None
