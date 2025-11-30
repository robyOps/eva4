# ERP Multi-tenant Demo

Proyecto Django + DRF con multi-tenant simple por Company, autenticación JWT (SimpleJWT) y vistas HTML con Bootstrap 5.

## Requisitos
- Python 3.10+
- pipenv/venv

## Instalación local (sqlite)
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

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
