# Marketplace Lautaro

Marketplace local en español donde las personas crean una cuenta, publican productos y contactan a vendedores por correo. Precios en pesos chilenos (CLP).

## Ejecutar

Requiere **Python 3.12 o posterior**. No necesita dependencias externas ni servicios de base de datos.

```bash
cd /workspace/Marketplace_Lautaro
python3 server.py
```

El servidor usa el puerto 8000 y escucha en `127.0.0.1` por defecto. Los datos se crean automáticamente en `.data/marketplace.sqlite3`, excluido de Git. La primera ejecución muestra un catálogo vacío; crea una cuenta y publica tu primer producto desde la interfaz. No hay cuentas, productos ni contraseñas de demostración.

Para recibir conexiones externas en un entorno de desarrollo con acceso configurado:

```bash
HOST=0.0.0.0 PORT=8000 python3 server.py
```

## Funciones

- Registro, inicio y cierre de sesión con cookies HttpOnly y contraseñas protegidas con scrypt.
- Catálogo público, búsqueda por título, descripción o ciudad, y filtros por categoría.
- Publicación con precio, descripción, ciudad y URL HTTPS de foto opcional.
- Vista de publicaciones propias y eliminación exclusiva por su propietario.
- Detalle del producto y contacto por correo: el vendedor acepta que su correo sea público al publicar.
- Persistencia SQLite de usuarios, anuncios y sesiones; diseño adaptable a móvil.

## Validar

```bash
python3 -m unittest discover -s tests -v
node --check public/app.js
```

Las pruebas usan una base temporal y un servidor independiente. Cubren registro, login, logout, búsqueda, filtros, autorización, eliminación, validación y persistencia después de reiniciar. Node solo es necesario para la comprobación opcional de sintaxis JavaScript.

## Configuración

| Variable | Valor predeterminado | Uso |
| --- | --- | --- |
| `HOST` | `127.0.0.1` | Interfaz de escucha |
| `PORT` | `8000` | Puerto HTTP |
| `MARKETPLACE_DB` | `.data/marketplace.sqlite3` | Ruta de base de datos |
| `COOKIE_SECURE` | desactivado | `1` para cookies exclusivas de HTTPS |

## Alcance y siguientes pasos

Esta es una base funcional para desarrollo, con compraventa coordinada directamente entre personas. No incluye pagos, chat, carga de archivos, verificación de correo, recuperación de contraseña ni moderación. Las fotos se cargan desde URLs públicas proporcionadas por vendedores.

Antes de abrirlo al público, incorpora límites de solicitudes y protección contra abuso en login/registro, moderación, verificación y recuperación de cuentas, y una política de privacidad. Usa un servidor y proxy apropiados para producción con HTTPS y `COOKIE_SECURE=1`; el servidor estándar de Python está destinado a desarrollo. Respalda la base de datos y define políticas de retención del correo público.
