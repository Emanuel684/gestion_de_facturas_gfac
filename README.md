# Sistema de Gestión de Facturas (SGF)

API lista para producción con frontend en React para resolver la ineficiencia operativa en el procesamiento de facturas en PYMES.

## Funcionalidades

- **Autenticación JWT** — Login seguro con tokens
- **CRUD de Facturas** — Registro, actualización y seguimiento de estados (Pendiente, Pagada, Vencida)
- **Control de Acceso (RBAC)** — Administrador, Contador y Asistente con permisos diferenciados
- **Dashboard** — Resumen financiero con totales por estado en COP
- **Filtros** — Búsqueda por estado y proveedor en tiempo real
- **Asignación de usuarios** — Asociar responsables a cada factura

## Stack Tecnológico

| Capa | Tecnologías |
|------|-------------|
| Backend | Python 3.13+, FastAPI, SQLAlchemy 2.0, PostgreSQL, pytest |
| Frontend | React 18+, Vite, Axios, React Router v6 |
| Infraestructura | Docker, Nginx, uv |

## Inicio Rápido

### Con Docker (recomendado)

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs

### Desarrollo Local

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

### Ejecutar Tests

```bash
pytest -v
```

## Cuentas Predeterminadas

| Usuario | Contraseña | Rol            | Permisos |
|---------|------------|----------------|----------|
| admin   | admin123   | Administrador  | Control total: CRUD completo + eliminación |
| maria   | maria123   | Contador       | Crear, ver todas, editar propias/asignadas |
| carlos  | carlos123  | Asistente      | Crear, ver propias/asignadas |

## Endpoints de la API

```
POST   /api/auth/login         — Autenticación (retorna JWT)
GET    /api/invoices            — Listar facturas (con filtros ?status= &supplier=)
POST   /api/invoices            — Registrar nueva factura
GET    /api/invoices/{id}       — Detalle de factura
PUT    /api/invoices/{id}       — Actualizar factura
DELETE /api/invoices/{id}       — Eliminar factura (solo administrador)
GET    /api/users/me            — Perfil del usuario actual
GET    /api/users               — Listar usuarios activos
```

## Documentación

Ver [SOLUTION.md](SOLUTION.md) para decisiones arquitectónicas, trade-offs e impacto económico esperado.




