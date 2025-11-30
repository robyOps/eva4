#!/bin/bash
# Ejemplos básicos usando JWT Bearer. Ajusta BASE_URL y credenciales.

BASE_URL="http://localhost:8000"
ADMIN_USER="admin_cliente"
ADMIN_PASS="demo12345"
GERENTE_USER="gerente"
GERENTE_PASS="demo12345"
VENDEDOR_USER="vendedor"
VENDEDOR_PASS="demo12345"

# Obtener token JWT (devuelve access/refresh)
ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/api/token/" -H 'Content-Type: application/json' \
  -d '{"username":"'"$ADMIN_USER"'","password":"'"$ADMIN_PASS"'"}' | jq -r .access)
GERENTE_TOKEN=$(curl -s -X POST "$BASE_URL/api/token/" -H 'Content-Type: application/json' \
  -d '{"username":"'"$GERENTE_USER"'","password":"'"$GERENTE_PASS"'"}' | jq -r .access)
VENDEDOR_TOKEN=$(curl -s -X POST "$BASE_URL/api/token/" -H 'Content-Type: application/json' \
  -d '{"username":"'"$VENDEDOR_USER"'","password":"'"$VENDEDOR_PASS"'"}' | jq -r .access)

echo "Admin token: $ADMIN_TOKEN"

# Crear producto (admin)
curl -X POST "$BASE_URL/api/products/" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"sku":"SKU-DEMO-1","name":"Producto demo","description":"Desc","price":19990,"cost":12000,"category":"General"}'

# Crear proveedor (admin)
curl -X POST "$BASE_URL/api/suppliers/" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Proveedor Demo","rut":"11.111.111-1","contact_name":"Contacto","contact_email":"demo@proveedor.cl","contact_phone":"+56911111111"}'

# Crear sucursal (admin_cliente)
curl -X POST "$BASE_URL/api/branches/" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Casa Matriz","address":"Av. Demo 123","phone":"+56922222222"}'

# Ajustar inventario (admin o gerente)
curl -X POST "$BASE_URL/api/inventory/adjust/" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"branch":1,"product":1,"quantity_delta":50,"reason":"Stock inicial"}'

# Registrar compra (admin o gerente)
curl -X POST "$BASE_URL/api/purchases/" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"branch":1,"supplier":1,"date":"2024-01-15","items":[{"product":1,"quantity":5,"unit_cost":10000}]}'

# Registrar venta (vendedor puede crear, gerente/admin listan)
curl -X POST "$BASE_URL/api/sales/" -H "Authorization: Bearer $VENDEDOR_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"branch":1,"payment_method":"efectivo","items":[{"product":1,"quantity":1,"unit_price":19990}]}'

# Operaciones de carrito
curl -X POST "$BASE_URL/api/cart/add/" -H "Authorization: Bearer $VENDEDOR_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"product":1,"quantity":2}'

curl -X POST "$BASE_URL/api/cart/checkout/" -H "Authorization: Bearer $VENDEDOR_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"branch_id":1}'

# Reportes (según plan con reports habilitados)
curl -X GET "$BASE_URL/api/reports/stock/?branch=1" -H "Authorization: Bearer $GERENTE_TOKEN"
curl -X GET "$BASE_URL/api/reports/sales/?date_from=2024-01-01&date_to=2024-12-31" -H "Authorization: Bearer $GERENTE_TOKEN"

# Listar ventas (solo admin/gerente)
curl -X GET "$BASE_URL/api/sales/" -H "Authorization: Bearer $GERENTE_TOKEN"
