const $ = (selector) => document.querySelector(selector);
const categories = ['Tecnología', 'Hogar', 'Moda', 'Deportes', 'Vehículos', 'Otros'];
const symbols = {Tecnología: '⌘', Hogar: '⌂', Moda: '✦', Deportes: '◉', Vehículos: '↗', Otros: '◇'};
const money = new Intl.NumberFormat('es-CL', {style: 'currency', currency: 'CLP', maximumFractionDigits: 0});
let user = null, category = '', mine = false, register = false, products = [], requestVersion = 0;
const escape = (text) => String(text).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, method = 'GET', body) {
  const response = await fetch(path, {method, headers: body ? {'Content-Type':'application/json'} : {}, body: body ? JSON.stringify(body) : undefined});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'No pudimos completar la solicitud.');
  return data;
}
function toast(message) {
  $('#toast').textContent = message; $('#toast').hidden = false;
  clearTimeout(toast.timer); toast.timer = setTimeout(() => $('#toast').hidden = true, 4500);
}
function updateAccount() {
  $('#auth').hidden = Boolean(user); $('#logout').hidden = !user; $('#mine').hidden = !user;
  $('#logout').textContent = user ? `Salir · ${user.name}` : 'Salir';
}
function renderCategories() {
  $('#categories').innerHTML = ['', ...categories].map(c => `<button type="button" class="category ${category === c ? 'selected' : ''}" data-category="${escape(c)}" aria-pressed="${category === c}">${c ? `${symbols[c]} ${c}` : 'Todos los productos'}</button>`).join('');
}
function imageMarkup(product, large = false) {
  return product.image ? `<img src="${escape(product.image)}" alt="${escape(product.title)}" loading="lazy" referrerpolicy="no-referrer">` : `<div class="product-placeholder ${large ? 'large' : ''}"><span>${symbols[product.category] || '◇'}</span><small>${escape(product.category)}</small></div>`;
}
function imageFallback(container) {
  container.querySelectorAll('img').forEach(img => img.addEventListener('error', () => {
    const fallback = document.createElement('div'); fallback.className = 'product-placeholder'; fallback.textContent = '◇'; img.replaceWith(fallback);
  }, {once:true}));
}
async function loadProducts() {
  const version = ++requestVersion;
  $('#load-error').hidden = true;
  $('#catalog-title').textContent = mine ? 'Mis publicaciones' : 'Explora el marketplace';
  renderCategories();
  try {
    const params = new URLSearchParams({q: $('#search').value.trim(), category, mine: mine ? '1' : '0'});
    const result = await api(`/api/listings?${params}`);
    if (version !== requestVersion) return;
    products = result;
    $('#count').textContent = `${products.length} ${products.length === 1 ? 'producto' : 'productos'}`;
    $('#products').innerHTML = products.map(p => `<button class="product-card" data-id="${p.id}"><div class="product-image">${imageMarkup(p)}<span class="product-category">${escape(p.category)}</span><span class="card-arrow">↗</span></div><div class="product-info"><span class="location">⌖ ${escape(p.city)}</span><h3>${escape(p.title)}</h3><div class="product-bottom"><strong>${money.format(p.price)}</strong><span>${escape(p.seller)}</span></div></div></button>`).join('');
    imageFallback($('#products'));
    $('#empty').hidden = products.length > 0;
    $('#empty-copy').textContent = $('#search').value.trim() || category ? 'No hay resultados con estos filtros. Prueba otra búsqueda.' : mine ? 'Publica tu primer producto y comienza a vender.' : 'Todavía no hay productos. Sé la primera persona en publicar.';
  } catch (error) {
    if (version !== requestVersion) return;
    $('#products').replaceChildren(); $('#empty').hidden = true; $('#count').textContent = '';
    $('#load-error').textContent = error.message; $('#load-error').hidden = false;
  }
}
function openPublish() {
  if (!user) { $('#auth-dialog').showModal(); return; }
  $('#publish-dialog').showModal();
}
function detail(id) {
  const p = products.find(p => p.id === id); if (!p) return;
  $('#detail-content').innerHTML = `<div class="detail-image">${imageMarkup(p,true)}</div><span class="eyebrow">${escape(p.category)} · ${escape(p.city)}</span><h2>${escape(p.title)}</h2><strong class="detail-price">${money.format(p.price)}</strong><p class="description">${escape(p.description)}</p><div class="seller"><span class="avatar">${escape(p.seller.slice(0,1).toUpperCase())}</span><div><small>Publicado por</small><strong>${escape(p.seller)}</strong></div></div><a class="button dark full" href="mailto:${encodeURIComponent(p.contact)}?subject=${encodeURIComponent('Consulta por ' + p.title)}">Contactar al vendedor ↗</a>${user && p.user_id === user.id ? '<button class="text-button delete-button" id="delete-listing">Eliminar publicación</button>' : ''}`;
  imageFallback($('#detail-content'));
  $('#detail-dialog').showModal();
  $('#delete-listing')?.addEventListener('click', async () => {
    if (!confirm('¿Eliminar esta publicación? Esta acción no se puede deshacer.')) return;
    try { await api(`/api/listings/${id}`, 'DELETE'); $('#detail-dialog').close(); toast('Publicación eliminada.'); await loadProducts(); }
    catch (error) { toast(error.message); }
  });
}
$('#publish-category').innerHTML = categories.map(c => `<option>${c}</option>`).join('');
for (const id of ['publish','banner-publish','empty-publish']) $(`#${id}`).addEventListener('click', openPublish);
$('#auth').addEventListener('click', () => $('#auth-dialog').showModal());
document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
$('#auth-toggle').addEventListener('click', () => {
  register = !register; $('#name-field').hidden = !register; $('#name-field input').required = register;
  $('#auth-title').textContent = register ? 'Tu comunidad te espera' : 'Qué bueno verte';
  $('#auth-submit').textContent = register ? 'Crear cuenta' : 'Ingresar';
  $('#auth-toggle').textContent = register ? '¿Ya tienes cuenta? Ingresa' : '¿No tienes cuenta? Regístrate';
  $('#auth-form .form-error').textContent = '';
  $('#auth-form [name=password]').autocomplete = register ? 'new-password' : 'current-password';
});
function submitForm(form, action) {
  form.addEventListener('submit', async event => {
    event.preventDefault(); const button = form.querySelector('[type=submit]'); button.disabled = true;
    form.querySelector('.form-error').textContent = '';
    try { await action(Object.fromEntries(new FormData(form))); }
    catch (error) { form.querySelector('.form-error').textContent = error.message; }
    finally { button.disabled = false; }
  });
}
submitForm($('#auth-form'), async data => {
  user = await api(register ? '/api/register' : '/api/login', 'POST', data);
  $('#auth-dialog').close(); $('#auth-form').reset(); updateAccount(); await loadProducts(); toast(`Hola, ${user.name}. Ya puedes publicar.`);
});
submitForm($('#publish-form'), async data => {
  data.price = Number(data.price); await api('/api/listings', 'POST', data);
  $('#publish-dialog').close(); $('#publish-form').reset(); mine = true; category = ''; $('#search').value = '';
  await loadProducts(); toast('Tu producto ya está publicado.');
});
$('#logout').addEventListener('click', async () => {
  try { await api('/api/logout', 'POST', {}); user = null; mine = false; updateAccount(); await loadProducts(); toast('Sesión cerrada.'); }
  catch (error) { toast(error.message); }
});
$('#browse').addEventListener('click', () => { mine = false; category = ''; $('#search').value = ''; loadProducts(); });
$('#mine').addEventListener('click', () => { mine = true; category = ''; $('#search').value = ''; loadProducts(); });
$('#search-form').addEventListener('submit', e => { e.preventDefault(); loadProducts(); });
$('#categories').addEventListener('click', event => { const button = event.target.closest('[data-category]'); if (button) { category = button.dataset.category; loadProducts(); } });
$('#products').addEventListener('click', event => { const button = event.target.closest('[data-id]'); if (button) detail(Number(button.dataset.id)); });
(async () => { try { user = await api('/api/me'); updateAccount(); } catch (error) { toast(error.message); } await loadProducts(); })();
