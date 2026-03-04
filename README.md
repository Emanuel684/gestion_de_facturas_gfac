# Sistema de Gestión de Facturas (SGF)

API de producción con frontend en React para digitalizar y automatizar el procesamiento de facturas en PYMES. Incluye autenticación JWT, control de acceso basado en roles (RBAC) con tres niveles y extracción automática de datos desde documentos mediante OCR.

---

## Tabla de Contenidos

1. [Funcionalidades](#funcionalidades)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Arquitectura](#arquitectura)
4. [Inicio Rápido](#inicio-rápido)
5. [Configuración](#configuración)
6. [Cuentas Predeterminadas](#cuentas-predeterminadas)
7. [API Reference](#api-reference)
8. [Control de Acceso (RBAC)](#control-de-acceso-rbac)
9. [Carga de Documentos](#carga-de-documentos)
10. [Estructura del Proyecto](#estructura-del-proyecto)
11. [Modelos de Base de Datos](#modelos-de-base-de-datos)
12. [Pruebas](#pruebas)
13. [Decisiones Técnicas](#decisiones-técnicas)

---

## Funcionalidades

| Módulo | Detalle |
|---|---|
| **Autenticación JWT** | Login con usuario y contraseña, token Bearer de 24 h |
| **CRUD de Facturas** | Crear, leer, actualizar y eliminar facturas |
| **Estados de Factura** | `pendiente` → `pagada` / `vencida` |
| **RBAC de 3 niveles** | `administrador`, `contador`, `asistente` con permisos diferenciados |
| **Dashboard financiero** | Totales por estado en COP (pendiente / vencida / pagada) |
| **Filtros en tiempo real** | Por estado y búsqueda por proveedor (`ilike`) |
| **Asignación de usuarios** | Asociar responsables a cada factura |
| **Gestión de usuarios** | Crear y listar usuarios (solo administrador) |
| **Carga de documentos** | Subir foto, PDF o DOCX — extracción automática de datos por OCR |

---

## Stack Tecnológico

| Capa | Tecnologías |
|---|---|
| **Backend** | Python 3.13, FastAPI, SQLAlchemy 2.0 (async), asyncpg, Pydantic v2 |
| **Base de datos** | PostgreSQL 17 |
| **Autenticación** | JWT (`python-jose`), bcrypt |
| **OCR / Extracción** | Tesseract OCR (`pytesseract`), Pillow, pdfplumber, python-docx |
| **Frontend** | React 18, Vite, Axios, React Router v6 |
| **Infraestructura** | Docker, Docker Compose, Nginx, uv |
| **Testing** | pytest, pytest-asyncio, httpx (AsyncClient), aiosqlite |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Compose                       │
│                                                             │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────┐  │
│  │  frontend   │───▶│       api        │───▶│    db     │  │
│  │ React+Nginx │    │ FastAPI + uvicorn │    │ Postgres  │  │
│  │  port 5173  │    │    port 8000      │    │ port 5433 │  │
│  └─────────────┘    └──────────────────┘    └───────────┘  │
│         │                    │                              │
│    /api/* proxy         ASGI async                         │
│  (dev: Vite proxy)   JWT + SQLAlchemy                      │
└─────────────────────────────────────────────────────────────┘
```

**Flujo de una solicitud:**

1. El frontend hace una petición a `/api/*` (Vite la proxea a `http://localhost:8000` en dev; en prod Nginx la redirige al servicio `api`).
2. FastAPI valida el JWT en el middleware `get_current_user`.
3. El router correspondiente ejecuta la lógica de negocio con verificación RBAC.
4. SQLAlchemy 2.0 async ejecuta la consulta contra PostgreSQL vía asyncpg.
5. La respuesta se serializa con Pydantic v2 y se devuelve como JSON.

---

## Inicio Rápido

### Con Docker Compose (recomendado)

```bash
# 1. Clonar / posicionarse en el directorio del proyecto
cd gestion_de_facturas_gfac

# 2. Construir y levantar todos los servicios
docker compose up --build

# 3. Acceder
#    Frontend:  http://localhost:5173
#    API docs:  http://localhost:8000/docs
#    API JSON:  http://localhost:8000/redoc
```

Los tres usuarios semilla se crean automáticamente al iniciar la API.

### Desarrollo Local (sin Docker)

```bash
# ── Backend ───────────────────────────────────────────────────
# 1. Levantar solo la base de datos
docker compose up -d db

# 2. Instalar dependencias con uv
uv pip install -e ".[dev]"

# 3. Ejecutar la API con recarga automática
uvicorn src.main:app --reload

# ── Frontend ───────────────────────────────────────────────────
cd frontend
npm install
npm run dev        # http://localhost:5173
```

> **Nota:** Para la extracción OCR de imágenes se requiere Tesseract instalado localmente:
> - **Linux/Debian:** `apt-get install tesseract-ocr tesseract-ocr-spa`
> - **macOS:** `brew install tesseract tesseract-lang`
> - **Windows:** Descargue el instalador desde [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki) y añada el ejecutable al `PATH`.

---

## Configuración

La API lee su configuración desde variables de entorno o desde un archivo `.env` en la raíz del proyecto.

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://sgfuser:sgfpass@localhost:5433/sgf_db` | Cadena de conexión a PostgreSQL |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Clave de firma JWT — **cambiar en producción** |
| `ALGORITHM` | `HS256` | Algoritmo de firma JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 h) | Duración del token |
| `CORS_ORIGINS` | `http://localhost:5173` | Orígenes CORS permitidos (separados por coma) |

**Ejemplo `.env` para producción:**

```dotenv
DATABASE_URL=postgresql+asyncpg://sgfuser:StrongPass!@db:5432/sgf_db
SECRET_KEY=una-clave-muy-secreta-de-al-menos-32-caracteres
CORS_ORIGINS=https://mi-dominio.com
```

---

## Cuentas Predeterminadas

Creadas automáticamente al iniciar la API por primera vez.

| Usuario | Contraseña | Rol | Descripción |
|---|---|---|---|
| `admin` | `admin123` | `administrador` | Acceso total al sistema |
| `maria` | `maria123` | `contador` | Gestión y edición de facturas |
| `carlos` | `carlos123` | `asistente` | Solo visualización y registro |

> Cambie estas contraseñas en entornos de producción usando la funcionalidad de gestión de usuarios.

---

## API Reference

La documentación interactiva completa está disponible en:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Autenticación

| Método | Endpoint | Descripción | Auth |
|---|---|---|---|
| `POST` | `/api/auth/login` | Login — devuelve JWT | ❌ |

**Request:** `application/x-www-form-urlencoded`
```
username=admin&password=admin123
```

**Response 200:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

Incluir el token en todas las peticiones protegidas:
```
Authorization: Bearer <access_token>
```

---

### Facturas

| Método | Endpoint | Descripción | Roles permitidos |
|---|---|---|---|
| `GET` | `/api/invoices` | Listar facturas | Todos |
| `POST` | `/api/invoices` | Crear factura | Todos |
| `POST` | `/api/invoices/upload` | Cargar documento y extraer datos | Todos |
| `GET` | `/api/invoices/{id}` | Obtener factura por ID | Todos* |
| `PUT` | `/api/invoices/{id}` | Actualizar factura | `administrador`, `contador`* |
| `DELETE` | `/api/invoices/{id}` | Eliminar factura | Solo `administrador` |

*Sujeto a restricciones de visibilidad por rol (ver [RBAC](#control-de-acceso-rbac)).

**`GET /api/invoices` — Parámetros de filtro:**

| Parámetro | Tipo | Ejemplo | Descripción |
|---|---|---|---|
| `status` | string | `pendiente` | Filtrar por estado (`pendiente`, `pagada`, `vencida`) |
| `supplier` | string | `acme` | Búsqueda parcial por proveedor (insensible a mayúsculas) |

**`POST /api/invoices` — Cuerpo:**
```json
{
  "invoice_number": "FAC-2025-001",
  "supplier": "Distribuciones ABC S.A.S",
  "description": "Compra de insumos de oficina",
  "amount": 1500000.50,
  "status": "pendiente",
  "due_date": "2026-06-15T00:00:00Z",
  "assigned_user_ids": [2, 3]
}
```

**`InvoiceOut` — Respuesta:**
```json
{
  "id": 1,
  "invoice_number": "FAC-2025-001",
  "supplier": "Distribuciones ABC S.A.S",
  "description": "Compra de insumos de oficina",
  "amount": "1500000.50",
  "status": "pendiente",
  "due_date": "2026-06-15T00:00:00Z",
  "creator_id": 1,
  "created_at": "2026-03-04T10:00:00Z",
  "updated_at": "2026-03-04T10:00:00Z",
  "assigned_users": [
    { "id": 2, "username": "maria" }
  ]
}
```

**Validaciones de `InvoiceCreate`:**
- `invoice_number`: no puede estar vacío, debe ser único en la BD
- `supplier`: no puede estar vacío ni ser solo espacios
- `amount`: debe ser mayor que `0`
- `status`: uno de `pendiente`, `pagada`, `vencida`

---

### Usuarios

| Método | Endpoint | Descripción | Roles permitidos |
|---|---|---|---|
| `GET` | `/api/users/me` | Perfil del usuario autenticado | Todos |
| `GET` | `/api/users` | Listar todos los usuarios activos | Todos |
| `POST` | `/api/users` | Crear nuevo usuario | Solo `administrador` |

**`POST /api/users` — Cuerpo:**
```json
{
  "username": "nuevo_usuario",
  "email": "nuevo@empresa.com",
  "password": "contraseña_segura",
  "role": "contador"
}
```

**Validaciones de `UserCreate`:**
- `username`: mínimo 3 caracteres, único en la BD
- `email`: formato de email válido, único en la BD
- `password`: mínimo 6 caracteres
- `role`: uno de `administrador`, `contador`, `asistente` (por defecto: `asistente`)

---

### Carga de Documentos

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/invoices/upload` | Cargar documento — devuelve campos extraídos |

**Request:** `multipart/form-data`

| Campo | Tipo | Descripción |
|---|---|---|
| `file` | `UploadFile` | Archivo a procesar (máx. 10 MB) |

**Formatos soportados:**

| Formato | MIME type | Extracción |
|---|---|---|
| JPEG, PNG, WEBP, BMP, TIFF | `image/*` | OCR con Tesseract (spa+eng) |
| PDF | `application/pdf` | `pdfplumber` (fallback OCR para PDFs escaneados) |
| DOCX | `application/vnd.openxmlformats...` | `python-docx` |

**Response 200:**
```json
{
  "message": "Datos extraídos exitosamente",
  "filename": "factura_enero.pdf",
  "extracted": {
    "invoice_number": "FAC-2025-042",
    "supplier": "Distribuidora Nacional S.A.S",
    "amount": 10115000.0,
    "description": "Compra de materiales de construcción",
    "due_date": "2026-04-30T00:00:00+00:00",
    "raw_text": "FACTURA DE VENTA\nFactura No. FAC-2025-042..."
  }
}
```

Los campos extraídos se usan para pre-rellenar el formulario de nueva factura en el frontend. El usuario puede revisarlos y corregirlos antes de guardar.

---

## Control de Acceso (RBAC)

### Permisos por rol

| Acción | `administrador` | `contador` | `asistente` |
|---|:---:|:---:|:---:|
| Ver todas las facturas | ✅ | ✅ | ❌ |
| Ver sus propias facturas | ✅ | ✅ | ✅ |
| Ver facturas asignadas | ✅ | ✅ | ✅ |
| Crear facturas | ✅ | ✅ | ✅ |
| Cargar documentos | ✅ | ✅ | ✅ |
| Editar cualquier factura | ✅ | ❌ | ❌ |
| Editar sus propias facturas | ✅ | ✅ | ❌ |
| Editar facturas asignadas | ✅ | ✅ | ❌ |
| Eliminar facturas | ✅ | ❌ | ❌ |
| Crear usuarios | ✅ | ❌ | ❌ |
| Ver usuarios | ✅ | ✅ | ✅ |

### Implementación

```python
# src/dependencies.py
async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.administrador:
        raise HTTPException(status_code=403, detail="Se requiere rol de administrador")
    return current_user
```

Las comprobaciones de visibilidad para `asistente` se hacen a nivel de consulta SQL:
```python
# Solo ve facturas que creó o tiene asignadas
assigned_subq = select(InvoiceAssignee.invoice_id).where(
    InvoiceAssignee.user_id == current_user.id
)
query = query.where(
    or_(Invoice.creator_id == current_user.id, Invoice.id.in_(assigned_subq))
)
```

---

## Carga de Documentos

El módulo `src/extraction.py` orquesta la extracción de datos en tres pasos:

### 1. Extracción de texto

| Tipo de archivo | Librería | Estrategia |
|---|---|---|
| Imagen | `pytesseract` + `Pillow` | OCR directo con idiomas `spa+eng` |
| PDF con texto | `pdfplumber` | Extracción nativa del PDF |
| PDF escaneado | `pdfplumber` + `pytesseract` | Renderizado de páginas a imagen → OCR |
| DOCX | `python-docx` | Párrafos + texto de tablas |

### 2. Extracción de campos con regex

El texto extraído se analiza con expresiones regulares para detectar:

| Campo | Patrones detectados |
|---|---|
| `invoice_number` | `Factura No.`, `FAC-001`, `INV-2025-0042`, `#ABC-123` |
| `supplier` | `Proveedor:`, `Empresa:`, `Razón Social:`, `Emitido por:` |
| `amount` | `Total a pagar:`, `Valor Total:`, `Grand Total:` — soporta formato COP (`1.500.000,50`) y US (`1,500,000.50`) |
| `due_date` | `Fecha de vencimiento:`, `Vencimiento:`, `Due date:` — formatos DD/MM/YYYY, YYYY-MM-DD |
| `description` | `Descripción:`, `Concepto:`, `Detalle:` |

### 3. Pre-relleno del formulario

Los campos extraídos se devuelven al frontend y se usan para pre-rellenar `InvoiceModal`. El usuario revisa, corrige y guarda la factura definitiva.

```
[Subir archivo] → [OCR / parseo] → [Campos extraídos] → [Formulario pre-rellenado] → [Guardar factura]
```

---

## Estructura del Proyecto

```
gestion_de_facturas_gfac/
│
├── docker-compose.yml          # Orquestación: db + api + frontend
├── Dockerfile                  # Imagen del backend (python:3.13-slim + tesseract)
├── pyproject.toml              # Dependencias y configuración de pytest
│
├── src/                        # Código fuente del backend
│   ├── main.py                 # Punto de entrada FastAPI, startup, seeds
│   ├── models.py               # Modelos ORM: User, Invoice, InvoiceAssignee
│   ├── schemas.py              # Esquemas Pydantic: entrada/salida de la API
│   ├── auth.py                 # bcrypt + JWT (create/decode)
│   ├── config.py               # Settings via pydantic-settings + .env
│   ├── db.py                   # Motor async, sesión, Base declarativa
│   ├── dependencies.py         # get_current_user, require_admin
│   ├── extraction.py           # OCR + regex — extracción de datos de documentos
│   └── routers/
│       ├── auth.py             # POST /api/auth/login
│       ├── invoices.py         # CRUD /api/invoices + POST /api/invoices/upload
│       └── users.py            # GET|POST /api/users, GET /api/users/me
│
├── tests/                      # Suite de pruebas
│   ├── conftest.py             # Fixtures: SQLite in-memory, client, tokens
│   ├── test_auth.py            # 6 tests de autenticación
│   ├── test_invoices.py        # ~22 tests CRUD + RBAC de facturas
│   ├── test_users.py           # 12 tests de gestión de usuarios
│   ├── test_upload.py          # 12 tests del endpoint de carga (con mocks)
│   └── test_extraction.py      # ~30 unit tests del módulo de extracción
│
└── frontend/
    ├── Dockerfile              # Build React → Nginx
    ├── nginx.conf              # SPA routing + proxy /api → backend
    ├── vite.config.js          # Dev proxy /api → localhost:8000
    └── src/
        ├── api.js              # Cliente Axios con interceptores JWT
        ├── App.jsx             # Rutas: /login, /, /users
        ├── context/
        │   └── AuthContext.jsx # Estado global de autenticación
        ├── components/
        │   ├── Navbar.jsx/css         # Barra de navegación con roles
        │   ├── InvoiceModal.jsx/css   # Modal crear/editar factura
        │   ├── UploadModal.jsx/css    # Modal carga de documento
        │   ├── UserModal.jsx/css      # Modal crear usuario
        │   └── ProtectedRoute.jsx     # Guard de rutas privadas
        └── pages/
            ├── LoginPage.jsx/css      # Pantalla de login
            ├── InvoicesPage.jsx/css   # Dashboard principal de facturas
            └── UsersPage.jsx/css      # Gestión de usuarios
```

---

## Modelos de Base de Datos

### `users`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | integer PK | Identificador único |
| `username` | varchar(64) UNIQUE | Nombre de usuario |
| `email` | varchar(255) UNIQUE | Correo electrónico |
| `hashed_password` | varchar(255) | Hash bcrypt |
| `role` | enum | `administrador` / `contador` / `asistente` |
| `is_active` | boolean | Estado de la cuenta |
| `created_at` | timestamptz | Fecha de creación |

### `invoices`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | integer PK | Identificador único |
| `invoice_number` | varchar(100) UNIQUE | Número de factura |
| `supplier` | varchar(255) | Nombre del proveedor |
| `description` | text | Descripción opcional |
| `amount` | numeric(12,2) | Monto en COP |
| `status` | enum | `pendiente` / `pagada` / `vencida` |
| `due_date` | timestamptz | Fecha de vencimiento (nullable) |
| `creator_id` | integer FK → users | Usuario que registró la factura |
| `created_at` | timestamptz | Fecha de creación |
| `updated_at` | timestamptz | Última modificación |

### `invoice_assignees`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | integer PK | Identificador único |
| `invoice_id` | integer FK → invoices | Factura asociada |
| `user_id` | integer FK → users | Usuario responsable |
| `assigned_at` | timestamptz | Fecha de asignación |

**Restricción:** `UNIQUE(invoice_id, user_id)` — un usuario no puede ser asignado dos veces a la misma factura.

---

## Pruebas

Las pruebas usan una base de datos SQLite en memoria (`aiosqlite`) para no requerir PostgreSQL durante el CI.

```bash
# Ejecutar toda la suite
pytest -v

# Solo un módulo
pytest tests/test_invoices.py -v

# Solo tests de extracción (sin dependencias externas)
pytest tests/test_extraction.py -v

# Con cobertura
pytest --cov=src --cov-report=term-missing
```

### Resumen de la suite

| Archivo | Tests | Cobertura |
|---|---|---|
| `test_auth.py` | 6 | Login, tokens, rutas protegidas |
| `test_invoices.py` | ~22 | CRUD completo, filtros, RBAC, asignaciones |
| `test_users.py` | 12 | Listar, crear, duplicados, permisos, validaciones |
| `test_upload.py` | 12 | Endpoint upload: tipos, errores, permisos (mocks) |
| `test_extraction.py` | ~30 | Regex de campos, parseo de montos y fechas |

### Fixture principal (`conftest.py`)

```python
# Base de datos in-memory por cada test
@pytest_asyncio.fixture()
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", ...)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    ...

# Usuarios de prueba con tokens listos
@pytest_asyncio.fixture()
async def admin_token(client, admin_user) -> str: ...

@pytest_asyncio.fixture()
async def contador_token(client, contador_user) -> str: ...

@pytest_asyncio.fixture()
async def asistente_token(client, asistente_user) -> str: ...
```

---

## Decisiones Técnicas

### Backend async-first

Se eligió un stack completamente asíncrono (`asyncpg`, `AsyncSession`, `async_sessionmaker`) porque FastAPI está construido sobre ASGI y la E/S asíncrona evita bloquear el event loop en llamadas a la base de datos. Para una API multi-usuario esto significa mejor concurrencia sin necesidad de múltiples procesos worker.

### SQLAlchemy 2.0 con `Mapped`

El estilo `Mapped[T]` / `mapped_column()` de SQLAlchemy 2.0 brinda cobertura completa del type-checker sin boilerplate, y es el enfoque moderno recomendado sobre la API legacy `Column()`.

### bcrypt directo sin passlib

`passlib` está sin mantenimiento activo y falla con `bcrypt >= 4.1` (atributo `__about__` faltante). Se reemplazó con un wrapper delgado sobre `bcrypt` directamente — dos funciones, sin magia:
```python
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
```

### Ruta `/upload` antes de `/{invoice_id}`

En FastAPI, las rutas se evalúan en orden de declaración. La ruta `POST /api/invoices/upload` se declara **antes** de `GET /api/invoices/{invoice_id}` para evitar que "upload" sea interpretado como un `invoice_id` entero y genere un error 422.

### Tests con SQLite in-memory

Los tests usan SQLite en lugar de PostgreSQL para eliminar la dependencia de un servidor externo en CI. SQLAlchemy abstrae las diferencias de dialecto en las operaciones usadas (la única incompatibilidad real es `ilike` en SQLite, que no se testea directamente en los unit tests de filtros).

### Mocks en tests de upload

El endpoint `POST /api/invoices/upload` usa `unittest.mock.patch` para simular `extract_from_file`, lo que permite testear toda la lógica HTTP (validación de tipo, tamaño, errores) sin necesitar Tesseract, pdfplumber ni python-docx instalados en el entorno de CI.
