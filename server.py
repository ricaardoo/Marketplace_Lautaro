"""Marketplace Lautaro: Python 3.12+, SQLite, no external dependencies."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import threading
from collections import defaultdict, deque
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('MARKETPLACE_DB', str(ROOT / '.data/marketplace.sqlite3')))
AUTH_ATTEMPTS = defaultdict(deque)
AUTH_LOCK = threading.Lock()

CATEGORIES = ['Tecnología', 'Hogar', 'Moda', 'Deportes', 'Vehículos', 'Otros']


def connect():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db


def initialize():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
                salt TEXT NOT NULL, password_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id), expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id),
                title TEXT NOT NULL, description TEXT NOT NULL, price INTEGER NOT NULL,
                category TEXT NOT NULL, city TEXT NOT NULL, image TEXT NOT NULL,
                created_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL REFERENCES users(id),
                listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
                PRIMARY KEY(user_id, listing_id));
            CREATE INDEX IF NOT EXISTS listings_owner ON listings(user_id);
            CREATE INDEX IF NOT EXISTS sessions_expiration ON sessions(expires);
        ''')
        columns = {row['name'] for row in db.execute('PRAGMA table_info(listings)')}
        if 'condition' not in columns:
            db.execute("ALTER TABLE listings ADD COLUMN condition TEXT NOT NULL DEFAULT 'Usado'")
        if 'status' not in columns:
            db.execute("ALTER TABLE listings ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


def clean(data, key, minimum, maximum):
    value = data.get(key, '')
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(f'El campo {key} debe tener entre {minimum} y {maximum} caracteres.')
    return value.strip()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Avoid logging URLs or request payloads that might contain personal data.
        pass

    def reply(self, status, data, cookie=None):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(body)

    def current_user(self, db):
        cookies = SimpleCookie()
        try:
            cookies.load(self.headers.get('Cookie', ''))
        except Exception:
            return None
        token = cookies.get('session')
        if not token:
            return None
        return db.execute('SELECT u.id,u.name,u.email FROM users u JOIN sessions s ON u.id=s.user_id '
                          'WHERE s.token=? AND s.expires>?',
                          (hashlib.sha256(token.value.encode()).hexdigest(), int(time.time()))).fetchone()

    def login(self, db, user):
        token = secrets.token_urlsafe(32)
        db.execute('DELETE FROM sessions WHERE expires<=?', (int(time.time()),))
        db.execute('INSERT INTO sessions VALUES (?,?,?)',
                   (hashlib.sha256(token.encode()).hexdigest(), user['id'], int(time.time()) + 604800))
        db.commit()
        secure = '; Secure' if os.environ.get('COOKIE_SECURE') == '1' else ''
        self.reply(200, dict(user), f'session={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800{secure}')

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path.startswith('/api/'):
            with connect() as db:
                if url.path == '/api/me':
                    user = self.current_user(db)
                    return self.reply(200, dict(user) if user else None)
                if url.path == '/api/stats':
                    return self.reply(200, {
                        'listings': db.execute("SELECT COUNT(*) FROM listings WHERE status='active'").fetchone()[0],
                        'sellers': db.execute("SELECT COUNT(DISTINCT user_id) FROM listings WHERE status='active'").fetchone()[0],
                        'cities': db.execute("SELECT COUNT(DISTINCT city) FROM listings WHERE status='active'").fetchone()[0]})
                if url.path == '/api/listings':
                    try:
                        query = parse_qs(url.query)
                        value = lambda key: query.get(key, [''])[0]
                        user = self.current_user(db)
                        uid = user['id'] if user else 0
                        conditions, params = [], []
                        search = value('q')[:200].strip()
                        if search:
                            conditions.append('(l.title LIKE ? OR l.description LIKE ? OR l.city LIKE ?)')
                            params.extend(['%' + search + '%'] * 3)
                        for field in ('category', 'city', 'condition'):
                            if value(field):
                                conditions.append(f'l.{field}=?')
                                params.append(value(field))
                        if value('mine') == '1' or value('favorites') == '1':
                            if not user:
                                return self.reply(401, {'error': 'Inicia sesión para ver esta sección.'})
                            if value('mine') == '1':
                                conditions.append('l.user_id=?')
                                params.append(uid)
                            else:
                                conditions.append('EXISTS(SELECT 1 FROM favorites f WHERE f.listing_id=l.id AND f.user_id=?)')
                                params.append(uid)
                        else:
                            conditions.append("l.status='active'")
                        for key, operator in [('min_price', '>='), ('max_price', '<=')]:
                            if value(key):
                                price = int(value(key))
                                if price < 0 or price > 1000000000:
                                    raise ValueError('Precio fuera de rango.')
                                conditions.append(f'l.price {operator} ?')
                                params.append(price)
                        if value('min_price') and value('max_price') and int(value('min_price')) > int(value('max_price')):
                            raise ValueError('El precio mínimo no puede superar el máximo.')
                        orders = {'recent': 'l.created_at DESC,l.id DESC', 'price_asc': 'l.price ASC,l.id DESC',
                                  'price_desc': 'l.price DESC,l.id DESC'}
                        order = orders.get(value('sort') or 'recent')
                        if not order:
                            raise ValueError('Orden no válido.')
                        where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
                        rows = db.execute('SELECT l.*,u.name AS seller,u.email AS contact, '
                                          'EXISTS(SELECT 1 FROM favorites f WHERE f.listing_id=l.id AND f.user_id=?) AS favorite '
                                          'FROM listings l JOIN users u ON u.id=l.user_id' + where +
                                          ' ORDER BY ' + order + ' LIMIT 200', [uid, *params]).fetchall()
                        return self.reply(200, [dict(row) for row in rows])
                    except ValueError as error:
                        return self.reply(400, {'error': str(error)})
            return self.reply(404, {'error': 'Ruta no encontrada.'})
        files = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css'}
        name = files.get(url.path)
        if not name:
            return self.reply(404, {'error': 'Página no encontrada.'})
        body = (ROOT / 'public' / name).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', {'html': 'text/html; charset=utf-8', 'js': 'text/javascript; charset=utf-8',
                                         'css': 'text/css; charset=utf-8'}[name.rsplit('.', 1)[1]])
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' https:; style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.mutate()

    def do_PATCH(self):
        self.mutate()

    def do_DELETE(self):
        self.mutate()

    def mutate(self):
        origin = self.headers.get('Origin')
        if origin and urlsplit(origin).netloc != self.headers.get('Host'):
            return self.reply(403, {'error': 'Origen no permitido.'})
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            return self.reply(403, {'error': 'Origen no permitido.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 0 or length > 20000:
                return self.reply(413, {'error': 'Solicitud demasiado grande.'})
            if self.command in ('POST', 'PATCH') and self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.reply(415, {'error': 'Se requiere JSON.'})
            data = json.loads(self.rfile.read(length) or b'{}')
            if not isinstance(data, dict):
                raise ValueError('Solicitud inválida.')
            path = urlsplit(self.path).path
            with connect() as db:
                if path in ('/api/register', '/api/login') and self.command == 'POST':
                    # Per-client limit, using the socket address rather than untrusted forwarded headers.
                    with AUTH_LOCK:
                        now = time.monotonic()
                        for address in list(AUTH_ATTEMPTS):
                            attempts = AUTH_ATTEMPTS[address]
                            while attempts and attempts[0] < now - 300:
                                attempts.popleft()
                            if not attempts:
                                del AUTH_ATTEMPTS[address]
                        attempts = AUTH_ATTEMPTS[self.client_address[0]]
                        if len(attempts) >= 20:
                            return self.reply(429, {'error': 'Demasiados intentos. Espera cinco minutos e inténtalo otra vez.'})
                        attempts.append(now)
                    email = clean(data, 'email', 5, 254).lower()
                    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
                        raise ValueError('Introduce un correo válido.')
                    password = data.get('password')
                    if not isinstance(password, str) or not 10 <= len(password) <= 128:
                        raise ValueError('La contraseña debe tener entre 10 y 128 caracteres.')
                    if path == '/api/register':
                        name = clean(data, 'name', 2, 60)
                        salt = secrets.token_hex(16)
                        try:
                            cursor = db.execute('INSERT INTO users(name,email,salt,password_hash) VALUES(?,?,?,?)',
                                                (name, email, salt, password_hash(password, salt)))
                        except sqlite3.IntegrityError:
                            return self.reply(409, {'error': 'Este correo ya tiene una cuenta.'})
                        user = {'id': cursor.lastrowid, 'name': name, 'email': email}
                    else:
                        row = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
                        # Run scrypt even when the account does not exist.
                        digest = password_hash(password, row['salt'] if row else '00' * 16)
                        if not row or not hmac.compare_digest(digest, row['password_hash']):
                            return self.reply(401, {'error': 'Correo o contraseña incorrectos.'})
                        user = {key: row[key] for key in ('id', 'name', 'email')}
                    return self.login(db, user)
                if path == '/api/logout' and self.command == 'POST':
                    cookies = SimpleCookie(self.headers.get('Cookie', ''))
                    if cookies.get('session'):
                        db.execute('DELETE FROM sessions WHERE token=?',
                                   (hashlib.sha256(cookies['session'].value.encode()).hexdigest(),))
                        db.commit()
                    return self.reply(200, {'ok': True}, 'session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0')
                user = self.current_user(db)
                if not user:
                    return self.reply(401, {'error': 'Inicia sesión para continuar.'})
                if path == '/api/profile' and self.command == 'PATCH':
                    name = clean(data, 'name', 2, 60)
                    db.execute('UPDATE users SET name=? WHERE id=?', (name, user['id']))
                    db.commit()
                    return self.reply(200, {'id': user['id'], 'name': name, 'email': user['email']})
                favorite_match = re.fullmatch(r'/api/favorites/(\d+)', path)
                if favorite_match and self.command in ('POST', 'DELETE'):
                    listing_id = int(favorite_match[1])
                    if not db.execute('SELECT id FROM listings WHERE id=?', (listing_id,)).fetchone():
                        return self.reply(404, {'error': 'El producto ya no está disponible.'})
                    if self.command == 'POST':
                        db.execute('INSERT OR IGNORE INTO favorites VALUES(?,?)', (user['id'], listing_id))
                    else:
                        db.execute('DELETE FROM favorites WHERE user_id=? AND listing_id=?', (user['id'], listing_id))
                    db.commit()
                    return self.reply(200, {'ok': True})
                listing_match = re.fullmatch(r'/api/listings/(\d+)', path)
                if path == '/api/listings' and self.command == 'POST' or listing_match and self.command == 'PATCH':
                    existing = None
                    if listing_match:
                        existing = db.execute('SELECT * FROM listings WHERE id=? AND user_id=?',
                                              (int(listing_match[1]), user['id'])).fetchone()
                        if not existing:
                            return self.reply(404, {'error': 'Publicación no encontrada o no te pertenece.'})
                        data = {**dict(existing), **data}
                    title = clean(data, 'title', 3, 100)
                    description = clean(data, 'description', 10, 2000)
                    city = clean(data, 'city', 2, 80)
                    category = clean(data, 'category', 2, 30)
                    if category not in CATEGORIES:
                        raise ValueError('Selecciona una categoría válida.')
                    price = data.get('price')
                    if type(price) is not int or not 1 <= price <= 1000000000:
                        raise ValueError('El precio debe ser un número entero entre $1 y $1.000.000.000.')
                    image = clean(data, 'image', 0, 1000)
                    if image:
                        parsed = urlsplit(image)
                        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                            raise ValueError('La imagen debe tener una URL HTTPS válida.')
                    condition = data.get('condition', 'Usado')
                    status = data.get('status', 'active')
                    if condition not in ('Nuevo', 'Como nuevo', 'Usado') or status not in ('active', 'sold'):
                        raise ValueError('Estado del producto no válido.')
                    fields = (title, description, price, category, city, image, condition, status)
                    if existing:
                        db.execute('UPDATE listings SET title=?,description=?,price=?,category=?,city=?,image=?,condition=?,status=? '
                                   'WHERE id=? AND user_id=?', (*fields, existing['id'], user['id']))
                        listing_id = existing['id']
                    else:
                        cursor = db.execute('INSERT INTO listings(title,description,price,category,city,image,condition,status,user_id,created_at) '
                                            'VALUES(?,?,?,?,?,?,?,?,?,?)', (*fields, user['id'], int(time.time())))
                        listing_id = cursor.lastrowid
                    db.commit()
                    return self.reply(200 if existing else 201, {'id': listing_id})
                if self.command == 'DELETE' and re.fullmatch(r'/api/listings/\d+', path):
                    cursor = db.execute('DELETE FROM listings WHERE id=? AND user_id=?',
                                        (int(path.rsplit('/', 1)[1]), user['id']))
                    db.commit()
                    if not cursor.rowcount:
                        return self.reply(404, {'error': 'Publicación no encontrada o no te pertenece.'})
                    return self.reply(200, {'ok': True})
                return self.reply(404, {'error': 'Ruta no encontrada.'})
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.reply(400, {'error': 'Solicitud JSON inválida.'})
        except ValueError as error:
            return self.reply(400, {'error': str(error)})
        except sqlite3.Error:
            return self.reply(500, {'error': 'No se pudo guardar. Inténtalo nuevamente.'})


if __name__ == '__main__':
    initialize()
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '8000'))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f'Marketplace Lautaro iniciado en {host}:{port}', flush=True)
    server.serve_forever()
