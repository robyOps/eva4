# Despliegue en EC2 (Django + Gunicorn + Nginx)

Guía reproducible para levantar la aplicación en una instancia Ubuntu 22.04 en AWS EC2.

## 1. Preparar la instancia
1. Crear instancia t3.small (o similar) con Ubuntu 22.04.
2. Security Group: abrir puertos **22** (SSH) y **80** (HTTP). HTTPS opcional según el caso.
3. Asociar/descargar la clave SSH y conectarse: `ssh -i <key.pem> ubuntu@<public-ip>`.

## 2. Dependencias del sistema
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git nginx postgresql-client
```

## 3. Clonar el proyecto y entorno virtual
```bash
cd /opt
sudo git clone https://<url-del-repo>.git eva4
sudo chown -R ubuntu:ubuntu eva4
cd eva4
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Variables de entorno
Crear `.env` (basado en `.env.example` si existe) con al menos:
- `SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS="<dominio>,<IP>"`
- Credenciales de base de datos (`DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`).
- Configuración de correo y JWT según necesidad.

> **Postgres**: usar RDS o una instancia propia. Si se usa RDS, exponer el SG solo al SG de la app. Para Postgres local, instalar `postgresql` y crear base/usuario antes de migrar.

## 5. Migraciones y estáticos
```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_demo --reset  # opcional para datos de prueba
```

## 6. Gunicorn vía systemd
El repo incluye `deploy/gunicorn.service` como referencia. Copiarlo y habilitarlo:
```bash
sudo cp deploy/gunicorn.service /etc/systemd/system/gunicorn.service
sudo sed -i "s|/path/to/app|/opt/eva4|g" /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
sudo systemctl status gunicorn
```
Asegúrate de que la unidad apunte al binario `/opt/eva4/venv/bin/gunicorn` y a `config.wsgi:application`.

## 7. Nginx como proxy inverso
Usar `deploy/nginx.conf` como plantilla:
```bash
sudo cp deploy/nginx.conf /etc/nginx/sites-available/eva4
sudo sed -i "s|/path/to/app|/opt/eva4|g" /etc/nginx/sites-available/eva4
sudo ln -s /etc/nginx/sites-available/eva4 /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```
El bloque `location /static/` debe apuntar a `/opt/eva4/static/` (o al directorio definido en `STATIC_ROOT`).

## 8. Checklist de verificación
- Gunicorn activo: `systemctl status gunicorn` y puerto 8000 respondiendo localmente (`curl http://127.0.0.1:8000/health` si existe).
- Nginx sirviendo el dominio/IP público en el puerto 80.
- Migraciones aplicadas y usuario demo creado (si se ejecutó `seed_demo`).
- Variables `.env` protegidas (permisos 600) y `DEBUG=False`.
- Evidencias a adjuntar por el usuario: IP pública o Elastic IP asociada, y captura de pantalla de la app cargando vía Nginx.
