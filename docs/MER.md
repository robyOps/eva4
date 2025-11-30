# Modelo Entidad-Relación

Diagrama basado en los modelos actuales de Django. Todas las tablas usan llave primaria `id` autoincremental y las relaciones respetan el multi-tenant por `company`.

```mermaid
erDiagram
    Company ||--|| Subscription : "1-1"
    Company ||--o{ User : "users"
    Company ||--o{ Product : "products"
    Company ||--o{ Branch : "branches"
    Company ||--o{ Inventory : ""
    Company ||--o{ InventoryMovement : ""
    Company ||--o{ Supplier : "suppliers"
    Company ||--o{ Purchase : ""
    Company ||--o{ Sale : ""
    Company ||--o{ Order : ""

    Subscription {
        int id
        FK company
        varchar plan_name
        date start_date
        date end_date
        bool active
    }

    Company {
        int id
        varchar name
        varchar rut
        datetime created_at
    }

    User {
        int id
        FK company
        varchar username
        varchar email
        varchar role
        varchar rut
        datetime created_at
    }

    Product {
        int id
        FK company
        varchar sku
        varchar name
        text description
        decimal price
        decimal cost
        varchar category
    }

    Branch {
        int id
        FK company
        varchar name
        varchar address
        varchar phone
    }

    Inventory {
        int id
        FK company
        FK branch
        FK product
        int stock
        int reorder_point
    }
    Branch ||--o{ Inventory : "inventories"
    Product ||--o{ Inventory : "inventories"

    InventoryMovement {
        int id
        FK company
        FK branch
        FK product
        varchar movement_type
        int quantity_delta
        varchar reason
        datetime created_at
        FK created_by
    }
    Branch ||--o{ InventoryMovement : ""
    Product ||--o{ InventoryMovement : ""
    User ||--o{ InventoryMovement : ""

    Supplier {
        int id
        FK company
        varchar name
        varchar rut
        varchar contact_name
        varchar contact_email
        varchar contact_phone
    }

    Purchase {
        int id
        FK company
        FK branch
        FK supplier
        date date
        FK created_by
        decimal total_cost
    }
    Branch ||--o{ Purchase : ""
    Supplier ||--o{ Purchase : ""
    User ||--o{ Purchase : ""

    PurchaseItem {
        int id
        FK purchase
        FK product
        int quantity
        decimal unit_cost
    }
    Purchase ||--o{ PurchaseItem : "items"
    Product ||--o{ PurchaseItem : ""

    Sale {
        int id
        FK company
        FK branch
        FK seller
        decimal total
        varchar payment_method
        datetime created_at
    }
    Branch ||--o{ Sale : ""
    User ||--o{ Sale : ""

    SaleItem {
        int id
        FK sale
        FK product
        int quantity
        decimal unit_price
    }
    Sale ||--o{ SaleItem : "items"
    Product ||--o{ SaleItem : ""

    CartItem {
        int id
        FK user
        FK product
        int quantity
    }
    User ||--o{ CartItem : "cart_items"
    Product ||--o{ CartItem : ""

    Order {
        int id
        FK company
        FK branch
        varchar customer_name
        varchar customer_email
        varchar status
        decimal total
        datetime created_at
    }
    Branch ||--o{ Order : ""

    OrderItem {
        int id
        FK order
        FK product
        int quantity
        decimal unit_price
    }
    Order ||--o{ OrderItem : "items"
    Product ||--o{ OrderItem : ""
```

## Tablas en 3NF

- **Company**: PK `id`; UK `rut`.
- **Subscription**: PK `id`; FK `company -> Company.id` (1:1).
- **User**: PK `id`; UK `email`; FK `company -> Company.id` (nullable para super_admin).
- **Product**: PK `id`; FK `company`; UK compuesta (`company`, `sku`).
- **Branch**: PK `id`; FK `company`; UK compuesta (`company`, `name`).
- **Inventory**: PK `id`; FKs `company`, `branch`, `product`; UK compuesta (`company`, `branch`, `product`).
- **InventoryMovement**: PK `id`; FKs `company`, `branch`, `product`, `created_by -> User.id`.
- **Supplier**: PK `id`; FK `company`; UK compuesta (`company`, `rut`).
- **Purchase**: PK `id`; FKs `company`, `branch`, `supplier`, `created_by -> User.id`.
- **PurchaseItem**: PK `id`; FKs `purchase`, `product`.
- **Sale**: PK `id`; FKs `company`, `branch`, `seller -> User.id`.
- **SaleItem**: PK `id`; FKs `sale`, `product`.
- **CartItem**: PK `id`; FKs `user`, `product`; UK compuesta (`user`, `product`).
- **Order**: PK `id`; FKs `company`, `branch`.
- **OrderItem**: PK `id`; FKs `order`, `product`.

## Decisiones clave
- Multi-tenant estricto: casi todas las tablas llevan `company` y los viewsets filtran por `request.user.company`.
- Roles internos (`admin_cliente`, `gerente`, `vendedor`) dependen de `User.company`; `super_admin` no tiene compañía asociada.
- Stocks e inventario se mantienen en `Inventory` y se auditan con `InventoryMovement` (compras, ventas, ajustes).
- Precios de venta se guardan en `SaleItem.unit_price` y `PurchaseItem.unit_cost` para dejar snapshots de cada transacción.
- Suscripciones limitan sucursales via `Subscription.branch_limit` para planes básico/estándar.
