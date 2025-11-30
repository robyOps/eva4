#!/bin/bash
# Obtener token
curl -X POST http://localhost:8000/api/token/ -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'
# Crear producto
curl -X POST http://localhost:8000/api/products/ -H 'Authorization: Bearer <ACCESS>' -H 'Content-Type: application/json' -d '{"sku":"SKU2","name":"Prod","description":"Desc","price":1000,"cost":500,"category":"General"}'
# Registrar compra
curl -X POST http://localhost:8000/api/purchases/ -H 'Authorization: Bearer <ACCESS>' -H 'Content-Type: application/json' -d '{"branch":1,"supplier":1,"date":"2024-01-01","items":[{"product":1,"quantity":2,"unit_cost":400}]}'
# Registrar venta
curl -X POST http://localhost:8000/api/sales/ -H 'Authorization: Bearer <ACCESS>' -H 'Content-Type: application/json' -d '{"branch":1,"payment_method":"efectivo","items":[{"product":1,"quantity":1,"unit_price":1000}]}'
# Reporte stock
curl -X GET 'http://localhost:8000/api/reports/stock/?branch=1' -H 'Authorization: Bearer <ACCESS>'
