# Marketplace Lautaro

Marketplace local en español donde las personas crean una cuenta, publican productos y contactan a vendedores por correo. Precios en pesos chilenos (CLP).

El backend está construido para escalar: **FastAPI** (ASGI, async), **PostgreSQL** con **SQLAlchemy 2.0** asíncrono y migraciones **Alembic**, caché y rate limiting con **Redis**, y subida de imágenes a **almacenamiento de objetos S3**. El frontend se mantiene como HTML/CSS/JS sin build.

## Arquitectura

```
app/
  main.py            # fábrica de la app FastAPI, middleware y estáticos
  config.py          # configuración por variables de entorno (pydantic-settings)
  database.py        # engine async, sesión y Base
  models.py          # tablas: users, sessions, listings, favorites
  schemas.py         # validación de entrada/salida (Pydantic v2)
  security.py        # hashing de contraseñas (Argon2) y tokens de sesión
  cache.py           # caché Redis con respaldo en memoria
  ratelimit.py       # límite de intentos de autenticación
  storage.py         # subida a S3 con respaldo en disco
  dependencies.py    # sesión, usuario actual y cookies
  routers/           # auth, listings, favorites, stats, uploads
alembic/             # migraciones de base de datos
public/              # frontend estático
tests/               # suite pytest
```

## Ejecutar con Docker (recomendado)

Levanta PostgreSQL, Redis, MinIO (S3) y la app:

```bash
cp .env.example .env          # ajusta SECRET_KEY
docker compose up --build
```

Abre `http://localhost:8000`. La app aplica las migraciones (`alembic upgrade head`) al iniciar.

## Ejecutar en local

Requiere **Python 3.12+**. Para desarrollo rápido puedes usar SQLite y la caché en memoria:

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# SQLite + caché en memoria para desarrollo
export DATABASE_URL="sqlite+aiosqlite:///./.data/marketplace.db"   # Windows: set DATABASE_URL=...
export REDIS_URL=""

uvicorn app.main:app --reload --port 8000
```

Con `AUTO_CREATE_TABLES=1` (por defecto) las tablas se crean automáticamente al iniciar. Con PostgreSQL en producción usa migraciones (`alembic upgrade head`) y desactiva `AUTO_CREATE_TABLES`.

Documentación interactiva de la API: `http://localhost:8000/api/docs` (con `DEBUG=1`).

## Funciones

- Registro, inicio y cierre de sesión con cookies HttpOnly y contraseñas protegidas con Argon2.
- Catálogo público paginado con búsqueda, filtros por categoría, ciudad exacta, condición y rango de precios; orden por fecha o precio.
- Conteo total de resultados y endpoint de detalle por producto.
- Favoritos persistentes por cuenta.
- Estadísticas reales de productos, vendedores y ciudades (cacheadas con Redis).
- Publicación y edición con precio, descripción, ciudad, condición y foto por **subida de archivo** o URL HTTPS.
- Panel de publicaciones propias: editar, marcar como vendido, republicar y eliminar.
- Perfil con edición del nombre público.
- Límite de intentos de registro/login por IP (Redis, distribuido).
- Persistencia PostgreSQL; diseño adaptable a móvil.

## Configuración

| Variable | Valor predeterminado | Uso |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://marketplace:marketplace@localhost:5432/marketplace` | Conexión a la base de datos |
| `AUTO_CREATE_TABLES` | `1` | Crea tablas al iniciar (desactivar en producción con migraciones) |
| `REDIS_URL` | vacío | Redis para caché y rate limit (vacío = memoria) |
| `CACHE_TTL_SECONDS` | `30` | TTL de la caché de catálogo |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Clave de la aplicación |
| `COOKIE_SECURE` | `0` | `1` para cookies exclusivas de HTTPS |
| `SESSION_TTL_DAYS` | `7` | Duración de la sesión |
| `AUTH_RATE_LIMIT` | `20` | Intentos de auth por ventana |
| `AUTH_RATE_WINDOW_SECONDS` | `300` | Ventana del rate limit |
| `MAX_UPLOAD_BYTES` | `5242880` | Tamaño máximo de imagen (5 MB) |
| `S3_BUCKET` | vacío | Bucket S3/MinIO (vacío = disco local) |
| `S3_ENDPOINT_URL` | vacío | Endpoint S3-compatible (MinIO/Cloudflare R2) |
| `MEDIA_DIR` | `.data/media` | Carpeta de subidas cuando no hay S3 |
| `CSP_IMG_EXTRA` | vacío | Host extra permitido en `img-src` (p. ej. MinIO local) |

## Validar

```bash
pip install -r requirements-dev.txt
pytest -q
node --check public/app.js
```

La suite corre contra SQLite y caché en memoria en local, y contra **PostgreSQL + Redis** en CI (`services` en `.github/workflows/checks.yml`).

## Migraciones

```bash
alembic revision --autogenerate -m "descripción"
alembic upgrade head
```

## Alcance

No incluye pagos ni envío. El contacto es por correo del vendedor. Antes de abrirlo al público, configura HTTPS, `COOKIE_SECURE=1`, un `SECRET_KEY` fuerte, respaldos de la base y una política de privacidad.
