# Marketplace Lautaro

Marketplace local en español donde las personas crean una cuenta, publican productos y contactan a vendedores por correo. Precios en pesos chilenos (CLP).

## Ejecutar

Requiere **Python 3.12 o posterior**. No necesita dependencias externas ni servicios de base de datos.

```bash
git clone https://github.com/ricaardoo/Marketplace_Lautaro.git
cd Marketplace_Lautaro
python3 server.py
```

Abre `http://localhost:8000` en tu navegador. En Windows puedes ejecutar `py server.py`. Si ya clonaste el proyecto, actualiza con `git pull origin main` y reinicia el servidor.

El servidor usa el puerto 8000 y escucha en `127.0.0.1` por defecto. Los datos se crean automáticamente en `.data/marketplace.sqlite3`, excluido de Git. La primera ejecución muestra un catálogo vacío; crea una cuenta y publica tu primer producto desde la interfaz. No hay cuentas, productos ni contraseñas de demostración.

Para recibir conexiones externas en un entorno de desarrollo con acceso configurado:

```bash
HOST=0.0.0.0 PORT=8000 python3 server.py
```

## Funciones

- Registro, inicio y cierre de sesión con cookies HttpOnly y contraseñas protegidas con scrypt.
- Catálogo público con búsqueda, filtros por categoría, ciudad exacta, condición y rango de precios; orden por fecha o precio.
- Favoritos guardados en la cuenta y persistentes entre sesiones.
- Estadísticas reales de productos disponibles, vendedores y ciudades.
- Publicación y edición con precio, descripción, ciudad, condición y URL HTTPS de foto opcional con vista previa.
- Panel de publicaciones propias: editar, marcar como vendido, republicar y eliminar con confirmación.
- Perfil con edición del nombre público.
- Límite de 20 solicitudes a registro/login por IP en cinco minutos.
- Detalle del producto y contacto por correo: el vendedor acepta que su correo sea público al publicar.
- Persistencia SQLite de usuarios, anuncios y sesiones; diseño adaptable a móvil.

## Validar

```bash
python3 -m unittest discover -s tests -v
node --check public/app.js
```

Las pruebas usan una base temporal y un servidor independiente. Cubren registro, login, logout, búsqueda, filtros, edición, autorización, favoritos, productos vendidos, perfil, eliminación, límites de acceso y persistencia después de reiniciar. También comprueban una migración repetible desde la base anterior sin perder cuentas ni anuncios. Node solo es necesario para la comprobación opcional de sintaxis JavaScript.

### Prueba opcional de interfaz

Con Playwright y Chromium disponibles:

```bash
python3 tests/browser_smoke.py
```

Puedes indicar el ejecutable de Chromium mediante `CHROMIUM_PATH`; en Linux utiliza `/usr/bin/chromium` si existe. Esta prueba usa una base temporal y recorre registro, publicación, edición, favoritos, venta y republicación, filtros, perfil, eliminación y cierre de sesión. Comprueba que escritorio y móvil no tengan desbordamiento horizontal ni errores JavaScript. Playwright es una herramienta de prueba opcional, no una dependencia de la aplicación.

## Actualización y datos

Al iniciar, las bases existentes se actualizan automáticamente para agregar condición, estado y favoritos. Los productos anteriores conservan sus datos y aparecen como usados y disponibles. La migración es repetible. Las consultas muestran hasta 200 resultados y la interfaz indica cuando se alcanza ese límite.

Antes de actualizar, respalda SQLite usando su API de backup (incluye cambios pendientes en WAL):

```bash
python3 -c "import sqlite3; source=sqlite3.connect('.data/marketplace.sqlite3'); target=sqlite3.connect('marketplace-backup.sqlite3'); source.backup(target); target.close(); source.close()"
```

El archivo de respaldo contiene información privada; guárdalo fuera del repositorio y no lo subas a GitHub.

## Configuración

| Variable | Valor predeterminado | Uso |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Interfaz de escucha |
| `PORT` | `8000` | Puerto HTTP |
| `MARKETPLACE_DB` | `.data/marketplace.sqlite3` | Ruta de base de datos |
| `COOKIE_SECURE` | desactivado | `1` para cookies exclusivas de HTTPS |

## Alcance y siguientes pasos

Esta es una base funcional para desarrollo, con compraventa coordinada directamente entre personas. No incluye pagos, chat, carga de archivos, verificación de correo, recuperación de contraseña ni moderación. Las fotos se cargan desde URLs públicas proporcionadas por vendedores.

Antes de abrirlo al público, incorpora protección contra abuso persistente y distribuida, moderación, verificación y recuperación de cuentas, y una política de privacidad. El límite de autenticación actual vive en memoria y se reinicia junto con el servidor; detrás de un proxy agrupa solicitudes según la IP de conexión y requiere una política apropiada en ese proxy. Usa un servidor y proxy apropiados para producción con HTTPS y `COOKIE_SECURE=1`; el servidor estándar de Python está destinado a desarrollo. Respalda la base de datos y define políticas de retención del correo público.
