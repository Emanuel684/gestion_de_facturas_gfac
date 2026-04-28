# Guía de Buenas Prácticas del Proyecto SGF

Esta guía resume las buenas prácticas que ya usamos en el proyecto y que debemos mantener en nuevas funcionalidades.

## 1) Arquitectura y diseño

- Mantener separación clara por capas:
  - `src/models.py`: persistencia/ORM.
  - `src/schemas.py`: contratos de entrada/salida.
  - `src/routers/*.py`: endpoints HTTP.
  - `src/dependencies.py`: autenticación/autorización reusable.
  - `src/notifications.py` y módulos de dominio: lógica transversal.
- Diseñar backend async-first con FastAPI + SQLAlchemy async para evitar bloqueo del event loop.
- Evitar mezclar lógica de negocio compleja directamente en el router; extraer helpers/servicios cuando crezca.

## 2) Seguridad y control de acceso

- Aplicar principio de menor privilegio con RBAC (`administrador`, `contador`, `asistente`, `plataforma_admin`).
- Centralizar validación de identidad/autorización en dependencias (`get_current_user`, `require_*`).
- Nunca confiar en filtros del frontend: validar permisos siempre en backend.
- Limpiar sesión en frontend ante `401` y redirigir a login para evitar estados inválidos.
- No exponer secretos en código; usar variables de entorno para `SECRET_KEY`, DB, CORS.

## 3) Datos y persistencia

- Definir restricciones en base de datos para proteger integridad:
  - `UniqueConstraint` (por ejemplo, número de factura por organización).
  - índices en columnas de consulta frecuente.
- Preferir enums para estados de dominio (`InvoiceStatus`, `NotificationType`, etc.).
- Mantener multi-tenant estricto: toda consulta sensible debe filtrar por `organization_id`.
- Usar migraciones Alembic para cada cambio de esquema (nunca cambios manuales en producción).

## 4) API y contratos

- Mantener contratos tipados con Pydantic y validaciones explícitas.
- Responder códigos HTTP correctos (`401`, `403`, `404`, `409`, `422`, etc.).
- Usar paginación (`page`, `page_size`, `has_next`) para listados escalables.
- Diseñar endpoints orientados a UX real:
  - ejemplo: contador de no leídas (`/notifications/unread-count`) para badge de campana.
- Mantener consistencia de nombres y payloads entre backend y frontend.

## 5) Frontend y experiencia de usuario

- Proteger rutas por sesión y rol (`ProtectedRoute` + redirecciones coherentes).
- Mantener estado UI resiliente:
  - loaders durante carga,
  - estados vacíos,
  - manejo de errores no bloqueante.
- Persistir preferencias de vista cuando aporta valor (`localStorage`).
- Evitar sobrecarga visual: notificaciones como panel compacto y acciones simples (marcar leída/todas).
- Para datos casi en tiempo real, comenzar con polling controlado y evolucionar a SSE/WebSocket cuando sea necesario.

## 6) Notificaciones entre usuarios (implementado)

- Modelo persistente por usuario (`notifications`) con soporte `is_read/read_at`.
- Generación automática en eventos relevantes:
  - creación/actualización de factura,
  - cambio de estado,
  - asignación/desasignación,
  - vencimiento automático.
- Endpoints mínimos del módulo:
  - listar paginado,
  - contador no leídas,
  - marcar individual,
  - marcar todas.
- Integración UI con campana, badge y bandeja.

## 7) Calidad, pruebas y mantenibilidad

- Cubrir permisos por rol/tenant en pruebas (no solo casos felices).
- Probar ciclo completo de módulos críticos:
  - creación,
  - lectura,
  - actualización,
  - reglas de acceso,
  - errores esperados.
- Mantener tests aislados con SQLite in-memory para CI rápido.
- Evitar dependencias externas en tests de integración cuando no aporten valor (uso de mocks en upload/OCR).
- Registrar eventos de dominio relevantes para trazabilidad/auditoría (`invoice_events`).

## 8) Operación y despliegue

- Asegurar fallback SPA en infraestructura (`index.html`) para evitar errores al abrir rutas directas.
- Mantener compatibilidad entre dev/prod:
  - Vite proxy en dev (`/api`),
  - Nginx/rewrite en producción.
- Automatizar preparación de esquema al arranque con Alembic en entornos controlados.
- Usar logs informativos en tareas de fondo (por ejemplo, cambio automático a `vencida`).

## 9) Convenciones de trabajo del equipo

- Cambios pequeños, coherentes y revisables.
- No romper contratos existentes sin plan de migración.
- Documentar cada módulo nuevo con:
  - propósito,
  - reglas de negocio,
  - endpoints,
  - pruebas asociadas.
- Cuando se agregue una funcionalidad transversal (como notificaciones), integrar backend + frontend + tests en la misma entrega.

---

## Checklist rápido para nuevos cambios

- [ ] ¿La consulta está aislada por `organization_id`?
- [ ] ¿Se validan permisos por rol en backend?
- [ ] ¿Hay esquema/migración si cambia la BD?
- [ ] ¿Hay validaciones Pydantic y códigos HTTP correctos?
- [ ] ¿Se agregaron pruebas de éxito y de permisos/errores?
- [ ] ¿El frontend maneja carga, error y estado vacío?
- [ ] ¿La funcionalidad quedó documentada?
