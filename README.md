# ERP Multi-tenant Demo

Proyecto Django + DRF con multi-tenant simple por Company, autenticación JWT (SimpleJWT) y vistas HTML con Bootstrap 5.

## Requisitos
- Python 3.10+
- pipenv/venv

## Instalación local (sqlite)
```bash
python -m venv venv
venv\Scripts\activate
python.exe -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

## Datos de demo
- Ejecuta `python manage.py seed_demo --reset` para recrear datos completos (company DEMO plan Premium con inventario completo).
- Parámetros útiles: `--products 200 --suppliers 30 --branches 5 --purchases 80 --sales 180 --orders 120` (valores por defecto).
- Usuarios de prueba (todos con compañía asignada):
  - `admin_cliente` / `demo12345`
  - `gerente` / `demo12345`
  - `vendedor` / `demo12345`
- Login por sesión: `http://localhost:8000/login/`
- JWT: botón "Obtener JWT" en el login y página "Tokens API (JWT)" en el menú del usuario.

## JWT
- POST `/api/token/` con `username` y `password` -> access/refresh
- POST `/api/token/refresh/` -> nuevo access

## Roles
- `super_admin` (sin company): crea companies y admin_cliente
- `admin_cliente`: gestiona usuarios internos, productos, proveedores, sucursales, inventario, reportes
- `gerente`: ventas y reportes
- `vendedor`: ventas POS y carrito

## Endpoints clave
- `POST /api/users/` creación según rol
- `GET /api/users/me/`
- `GET/POST /api/companies/` (solo super_admin)
- `POST /api/companies/{id}/subscribe/`
- `GET /api/products/` público; CRUD restringido por compañía
- `POST /api/branches/` respeta límites de plan
- `POST /api/inventory/adjust/` ajusta stock
- `POST /api/purchases/` carga inventario
- `POST /api/sales/` descuenta inventario
- `POST /api/cart/add/` y `POST /api/cart/checkout/`
- `GET /api/reports/stock/` y `GET /api/reports/sales/` (según plan)

## Planes
- Básico: 1 sucursal, sin reportes
- Estándar: 3 sucursales, reportes habilitados
- Premium: ilimitado, reportes habilitados

## Deploy (ejemplo)
1. Configurar Postgres y variables `.env` (DB_ENGINE=django.db.backends.postgresql, etc.)
2. `pip install -r requirements.txt`
3. Ejecutar migraciones y collectstatic
```
python manage.py migrate
python manage.py collectstatic --noinput
```
4. Gunicorn: ver `deploy/gunicorn.service`
5. Nginx reverse proxy: ver `deploy/nginx.conf`

## Scripts útiles
- `scripts/curl_examples.sh` contiene llamadas de ejemplo a la API.
