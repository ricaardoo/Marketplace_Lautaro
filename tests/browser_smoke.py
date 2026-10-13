"""Optional browser validation: requires Playwright and installed Chromium."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen([sys.executable, 'server.py'], cwd=ROOT,
                               env=dict(os.environ, PORT=str(port), HOST='127.0.0.1',
                                        MARKETPLACE_DB=str(Path(directory) / 'browser.sqlite3')),
                               stdout=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{port}/api/me', timeout=1).close()
                break
            except OSError:
                time.sleep(.05)
        with sync_playwright() as p:
            executable = os.environ.get('CHROMIUM_PATH')
            if not executable and Path('/usr/bin/chromium').exists():
                executable = '/usr/bin/chromium'
            browser = p.chromium.launch(headless=True, executable_path=executable)
            page = browser.new_page(viewport={'width': 1440, 'height': 1000})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{port}')
            page.locator('#empty').wait_for(state='visible')
            page.locator('#publish').click()
            page.locator('#auth-toggle').click()
            page.locator('#auth-form [name=name]').fill('Vendedora de prueba')
            page.locator('#auth-form [name=email]').fill('browser@example.test')
            page.locator('#auth-form [name=password]').fill('ClaveDePrueba123')
            page.locator('#auth-submit').click()
            page.locator('#publish-dialog').wait_for(state='visible')
            page.locator('#publish-form [name=title]').fill('Bicicleta urbana')
            page.locator('#publish-form [name=price]').fill('85000')
            page.locator('#publish-category').select_option('Deportes')
            page.locator('#publish-form [name=condition]').select_option('Como nuevo')
            page.locator('#publish-form [name=city]').fill('Lautaro')
            page.locator('#publish-form [name=description]').fill('Una bicicleta en excelente estado para tu próxima aventura.')
            page.locator('#publish-form [type=submit]').click()
            page.get_by_role('heading', name='Bicicleta urbana', exact=True).wait_for()
            page.locator('[data-edit]').click()
            page.locator('#publish-form [name=price]').fill('75000')
            page.locator('#publish-form [type=submit]').click()
            page.get_by_text('$75.000', exact=True).wait_for()
            page.locator('[data-favorite]').click()
            page.locator('[data-favorite][aria-pressed=true]').wait_for()
            page.locator('#favorites-nav').click()
            page.get_by_role('heading', name='Mis favoritos', exact=True).wait_for()
            page.locator('.card-main').click()
            assert 'browser%40example.test' in page.get_by_role('link', name='Contactar al vendedor').get_attribute('href')
            page.locator('#detail-dialog [data-close]').click()
            page.locator('#mine').click()
            page.locator('[data-status]').click()
            page.get_by_role('button', name='Republicar', exact=True).wait_for()
            page.locator('#browse').click()
            page.locator('#empty').wait_for(state='visible')
            page.locator('#mine').click()
            page.get_by_role('button', name='Republicar', exact=True).click()
            page.get_by_role('button', name='Marcar vendido', exact=True).wait_for()
            page.locator('#browse').click()
            page.locator('#min-price').fill('80000')
            page.locator('#apply-filters').click()
            page.locator('#empty').wait_for(state='visible')
            page.locator('#reset-filters').click()
            page.get_by_role('heading', name='Bicicleta urbana', exact=True).wait_for()
            page.locator('#profile').click()
            page.locator('#profile-form [name=name]').fill('Nuevo nombre')
            page.locator('#profile-form [type=submit]').click()
            page.get_by_role('button', name='Nuevo nombre', exact=True).wait_for()
            page.locator('.product-seller').get_by_text('Nuevo nombre', exact=True).wait_for()
            page.screenshot(path='/tmp/lautaro-improved-desktop.png', full_page=True)
            assert page.locator('body').evaluate('(el) => el.scrollWidth <= innerWidth')
            page.set_viewport_size({'width': 390, 'height': 844})
            assert page.locator('body').evaluate('(el) => el.scrollWidth <= innerWidth')
            page.screenshot(path='/tmp/lautaro-improved-mobile.png', full_page=True)
            page.locator('.card-main').click()
            page.locator('#delete-listing').click()
            page.locator('#cancel-delete').click()
            assert page.locator('#detail-dialog').is_visible()
            page.locator('#delete-listing').click()
            page.locator('#confirm-delete').click()
            page.locator('#empty').wait_for(state='visible')
            page.locator('#favorites-nav').click()
            page.locator('#empty-copy').get_by_text('Guarda los productos', exact=False).wait_for()
            page.locator('#logout').click()
            page.locator('#auth').wait_for(state='visible')
            assert not errors, errors
            browser.close()
            print('Browser PASS: registration, publish, edit, favorites, sold/relist, filters, profile, delete, logout, responsive layout')
    finally:
        process.terminate()
        process.wait(timeout=5)
