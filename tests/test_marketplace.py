import http.cookiejar
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class MarketplaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        cls.url = f'http://127.0.0.1:{cls.port}'
        cls.env = dict(os.environ, PORT=str(cls.port), HOST='127.0.0.1',
                       MARKETPLACE_DB=str(Path(cls.temp.name) / 'test.sqlite3'))
        cls.start()

    @classmethod
    def start(cls):
        cls.process = subprocess.Popen([sys.executable, 'server.py'], cwd=ROOT, env=cls.env,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(100):
            if cls.process.poll() is not None:
                raise RuntimeError(cls.process.stderr.read().decode())
            try:
                urllib.request.urlopen(cls.url + '/api/me', timeout=1).close()
                return
            except urllib.error.URLError:
                time.sleep(.05)
        raise RuntimeError('Server failed to become ready')

    @classmethod
    def stop(cls):
        cls.process.terminate()
        cls.process.wait(timeout=5)
        cls.process.stderr.close()

    @classmethod
    def tearDownClass(cls):
        cls.stop()
        cls.temp.cleanup()

    def client(self):
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, client, path, method='GET', body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.url + path, data=data, method=method,
                                         headers={'Content-Type': 'application/json', **(headers or {})})
        try:
            response = client.open(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def test_user_listing_and_persistence_workflow(self):
        owner, other, visitor = self.client(), self.client(), self.client()
        credentials = {'name': 'Vendedora Lautaro', 'email': 'owner@example.test', 'password': 'UnaClaveSegura123'}
        status, account = self.request(owner, '/api/register', 'POST', credentials)
        self.assertEqual(status, 200)
        self.assertNotIn('password_hash', account)
        self.assertEqual(self.request(owner, '/api/me')[1]['name'], credentials['name'])
        self.assertEqual(self.request(visitor, '/api/register', 'POST', credentials)[0], 409)
        product = {'title': 'Bicicleta urbana', 'description': 'En buen estado y lista para usar.', 'price': 85000,
                   'category': 'Deportes', 'city': 'Lautaro', 'image': ''}
        self.assertEqual(self.request(visitor, '/api/listings', 'POST', product)[0], 401)
        self.assertEqual(self.request(owner, '/api/listings', 'POST', dict(product, price=-1))[0], 400)
        self.assertEqual(self.request(owner, '/api/listings', 'POST', dict(product, image='javascript:alert(1)'))[0], 400)
        self.assertEqual(self.request(owner, '/api/listings', 'POST', product, {'Origin': 'https://other.example'})[0], 403)
        status, listing = self.request(owner, '/api/listings', 'POST', product)
        self.assertEqual(status, 201)
        self.assertEqual(len(self.request(visitor, '/api/listings?q=Bicicleta&category=Deportes')[1]), 1)
        self.assertEqual(self.request(visitor, '/api/listings?category=Moda')[1], [])
        self.assertEqual(self.request(visitor, '/api/listings?mine=1')[0], 401)
        self.assertEqual(len(self.request(owner, '/api/listings?mine=1')[1]), 1)
        self.stop()
        self.start()
        self.assertEqual(self.request(owner, '/api/me')[1]['id'], account['id'])
        self.assertEqual(self.request(visitor, '/api/listings')[1][0]['title'], product['title'])
        self.request(other, '/api/register', 'POST', dict(credentials, email='other@example.test'))
        path = '/api/listings/' + str(listing['id'])
        self.assertEqual(self.request(other, path, 'DELETE')[0], 404)
        self.assertEqual(self.request(owner, '/api/logout', 'POST', {})[0], 200)
        self.assertIsNone(self.request(owner, '/api/me')[1])
        self.assertEqual(self.request(owner, '/api/login', 'POST', dict(credentials, password='WrongPassword123'))[0], 401)
        self.assertEqual(self.request(owner, '/api/login', 'POST', credentials)[0], 200)
        self.assertEqual(self.request(owner, path, 'DELETE')[0], 200)
        self.assertEqual(self.request(visitor, '/api/listings')[1], [])

    def test_frontend_and_invalid_requests(self):
        client = self.client()
        for route in ['/', '/style.css', '/app.js']:
            with client.open(self.url + route) as response:
                self.assertEqual(response.status, 200)
                self.assertGreater(len(response.read()), 100)
                self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(self.request(client, '/api/not-found')[0], 404)
        self.assertEqual(self.request(client, '/api/register', 'POST', [1, 2])[0], 400)
        self.assertEqual(self.request(client, '/api/register', 'POST', {'email': 'invalid', 'password': '1234567890'})[0], 400)


if __name__ == '__main__':
    unittest.main()
