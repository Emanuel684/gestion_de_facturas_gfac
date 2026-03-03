# SOLUTION.md — Sistema de Gestión de Facturas (SGF)

## Decisiones Arquitectónicas

### Backend

**Async-first con FastAPI + asyncpg**
Se eligió un stack completamente asíncrono (`asyncpg` driver, `AsyncSession`, `async_sessionmaker`) porque FastAPI está construido sobre ASGI y la E/S asíncrona evita bloquear el event loop en llamadas a la base de datos. Para una API orientada a equipos de PYMES, esto significa mejor concurrencia sin necesidad de procesos worker adicionales.

**SQLAlchemy 2.0 ORM con anotaciones `Mapped`**
El estilo `Mapped[T]` / `mapped_column()` de SQLAlchemy 2.0 brinda cobertura completa del type-checker sin boilerplate, y es el enfoque moderno recomendado sobre la API legacy `Column()`.

**JWT via `python-jose`, contraseñas con `bcrypt` directo**
`passlib` está efectivamente sin mantenimiento y falla con `bcrypt >= 4.1` (atributo `__about__` faltante). Se reemplazó con un wrapper delgado sobre `bcrypt` directamente — dos funciones, sin magia. Los JWTs llevan `sub` (user id) y `role` para que el middleware pueda hacer verificaciones de rol sin una consulta extra a la BD.

**Control de Acceso Basado en Roles (RBAC)**
Tres roles — `administrador`, `contador` y `asistente`:
- `administrador` (Gerente): visibilidad total y derechos de edición/eliminación sobre todas las facturas.
- `contador`: puede ver todas las facturas, crear facturas, y editar las que creó o tiene asignadas. No puede eliminar.
- `asistente`: puede ver facturas que creó o tiene asignadas, puede crear facturas, pero no puede editar ni eliminar.

Esto se aplica en los helpers del router de facturas `_check_invoice_access`, `_check_invoice_edit` y `_check_invoice_delete`, manteniendo la lógica de permisos co-localizada con el recurso.

**Modelo de datos**
Tres tablas: `users`, `invoices`, `invoice_assignees` (tabla join con constraint único sobre `(invoice_id, user_id)`). El modelo de `Invoice` incluye: `invoice_number` (único), `supplier`, `amount` (Numeric 12,2), `due_date`, `status` (pendiente/pagada/vencida) y relación con el usuario que la registró. Esto cubre el MVP y la funcionalidad de asignación de facturas.

**Usuarios predeterminados al inicio**
El registro no es requerido. Al arrancar por primera vez, el hook de startup crea tres usuarios (`admin`/administrador, `maria`/contador, `carlos`/asistente) si no existen — idempotente y seguro de re-ejecutar.

---

### Frontend

**React Router v6 + Axios**
Librerías simples y bien conocidas. Los interceptores de Axios manejan la inyección del token y redirección automática en 401 globalmente.

**Flujo de autenticación**
Token almacenado en `localStorage`. Al cargar la app, `AuthContext` re-valida contra `/api/users/me` para detectar tokens expirados inmediatamente.

**Estructura de componentes**
```
App.jsx              ← router + AuthProvider
pages/
  LoginPage          ← formulario de login
  InvoicesPage       ← dashboard de facturas con resumen, filtros y CRUD
components/
  Navbar             ← navegación sticky con badge de rol + logout
  InvoiceModal       ← modal para crear / editar factura (compartido)
  ProtectedRoute     ← redirige usuarios no autenticados a /login
context/
  AuthContext        ← estado del usuario, signIn, signOut
api.js               ← instancia axios + todas las llamadas a la API
```

**Dashboard con tarjetas de resumen**
El frontend muestra tarjetas de resumen con totales por estado (Pendiente, Vencida, Pagada) en formato COP, dando visibilidad inmediata del estado financiero.

**Filtros por estado y proveedor**
Búsqueda rápida por estado (botones de filtro) y por proveedor (campo de texto), reduciendo el tiempo de búsqueda de 10-30 min a segundos como se especifica en los requisitos.

**Sin librería de state management**
`useState` / `useEffect` / `useContext` de React son suficientes para este alcance. Agregar Redux o Zustand sería sobre-ingeniería.

---

### Docker / Producción

**Build multi-etapa para frontend**
`node:20-alpine` construye el bundle de Vite; `nginx:alpine` sirve los archivos estáticos. Nginx también proxifica `/api/*` al contenedor backend para que el frontend nunca necesite configuración CORS en producción.

**Health check en Postgres**
`pg_isready` asegura que el servicio `api` solo arranca después de que la BD acepta conexiones.

---

## Impacto Económico Esperado

Según el análisis de la problemática de gestión de facturas en PYMES:

| Métrica | Antes (manual) | Después (SGF) | Mejora |
|---|---|---|---|
| Horas mensuales en procesamiento | 79-146 h | 20-50 h | **65-75% reducción** |
| Errores de digitación | 15-20% | 1-3% | **85-90% reducción** |
| Tiempo de búsqueda de facturas | 10-30 min | Segundos | **>95% reducción** |
| Ahorro anual proyectado | — | $10.2M - $31.2M COP | — |

---

## Trade-offs

| Decisión | Compromiso |
|---|---|
| Contraseñas con `bcrypt` directo | Más control, evita deps obsoletas de passlib; algo más de código |
| SQLite en memoria para tests | Rápido, sin infraestructura; no cubre comportamiento específico de Postgres (ej. tipos enum) |
| `@app.on_event("startup")` para init BD | Deprecated en FastAPI ≥ 0.93 a favor de lifespan; adecuado para este alcance |
| Sin migraciones Alembic | Tablas creadas con `create_all` al inicio — más simple, pero no apto para cambios de esquema en producción |
| JWT expiry = 24 h | Conveniente para desarrollo; producción debería usar tokens de corta duración + refresh tokens |

---

## Qué Mejoraría con Más Tiempo

- **Migraciones Alembic** — reemplazar `create_all` con migraciones versionadas
- **Refresh tokens** — JWTs de corta duración (15 min) + endpoint `/api/auth/refresh`
- **Paginación** — `GET /api/invoices` debería aceptar `?page=` / `?limit=`
- **Carga de documentos** — adjuntar archivos PDF/imágenes de facturas (almacenamiento S3/MinIO)
- **Notificaciones de vencimiento** — tarea en segundo plano (APScheduler/Celery) que envíe alertas antes del vencimiento
- **Generación de reportes** — exportar datos financieros a PDF/Excel con gráficos
- **Log de actividad** — tabla `events` registrando cada operación con actor + diff
- **Sanitización de entrada** — limpiar HTML de campos de texto libre
- **Rate limiting** — middleware `slowapi` en el endpoint de login
- **Tests E2E** — tests de Playwright contra el stack Docker completo

---

## Cómo Ejecutar

### Stack completo (Docker)

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

### Desarrollo local

```bash
# 1. Iniciar la base de datos
docker compose up -d db

# 2. Instalar dependencias del backend
uv pip install -e ".[dev]"

# 3. Ejecutar la API
uvicorn src.main:app --reload

# 4. En otra terminal, ejecutar el frontend
cd frontend
npm install
npm run dev
```

### Ejecutar tests

```bash
pytest -v
```

Los tests usan una base de datos SQLite en memoria — no requieren Postgres corriendo.

### Cuentas predeterminadas

| Usuario | Contraseña | Rol            |
|---------|------------|----------------|
| admin   | admin123   | Administrador  |
| maria   | maria123   | Contador       |
| carlos  | carlos123  | Asistente      |
