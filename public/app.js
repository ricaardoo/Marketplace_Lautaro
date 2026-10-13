const $ = (selector) => document.querySelector(selector);
const categories = [
  "Tecnología",
  "Hogar",
  "Moda",
  "Deportes",
  "Vehículos",
  "Otros",
];
const money = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
  maximumFractionDigits: 0,
});
const date = new Intl.DateTimeFormat("es-CL", {
  day: "numeric",
  month: "long",
  year: "numeric",
});
const icons = {
  heart:
    '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
  arrow: '<path d="M5 19 19 5M5 5h14v14"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  pin: '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/>',
  box: '<path d="m12 3 9 5v9l-9 5-9-5V8l9-5ZM3 8l9 5 9-5M12 13v9M7.5 5.5l9 5"/>',
  Tecnología:
    '<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',
  Hogar: '<path d="m3 10 9-7 9 7M5 9v12h14V9M9 21v-7h6v7"/>',
  Moda: '<path d="m8 3-5 3-2 6 5 2v7h12v-7l5-2-2-6-5-3a4 4 0 0 1-8 0Z"/>',
  Deportes:
    '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3v18M5 5c8 2 12 6 14 14M19 5C11 7 7 11 5 19"/>',
  Vehículos:
    '<path d="m5 7 2-4h10l2 4 2 5v6H3v-6l2-5ZM5 7h14M7 18v3M17 18v3M6 13h2M16 13h2"/>',
  Otros: '<path d="m12 3 9 9-9 9-9-9 9-9Z"/>',
  share:
    '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 10.6 6.8-4.2M8.6 13.4l6.8 4.2"/>',
};
const icon = (name) =>
  `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${icons[name] || icons.box}</svg>`;
const escape = (text) =>
  String(text).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const prefersReducedMotion =
  window.matchMedia?.("(prefers-reduced-motion: reduce)").matches || false;
function timeAgo(seconds) {
  const diff = Math.max(0, Date.now() / 1000 - seconds);
  for (const [name, size] of [
    ["año", 31536000],
    ["mes", 2592000],
    ["día", 86400],
    ["hora", 3600],
    ["minuto", 60],
  ]) {
    const value = Math.floor(diff / size);
    if (value >= 1) {
      const plural = value === 1 ? "" : name === "mes" ? "es" : "s";
      return `hace ${value} ${name}${plural}`;
    }
  }
  return "recién publicado";
}
let user = null,
  category = "",
  view = "browse",
  register = false,
  products = [],
  totalProducts = 0,
  requestVersion = 0;
const PAGE_SIZE = 24;
let editing = null,
  detailId = null,
  deleteId = null,
  afterLogin = null;
async function api(path, method = "GET", body) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error(
      "No hay conexión con el servidor. Revisa tu conexión e inténtalo otra vez.",
    );
  }
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error("El servidor no pudo responder. Inténtalo nuevamente.");
  }
  if (!response.ok) {
    if (response.status === 401 && user) {
      user = null;
      updateAccount();
    }
    throw new Error(data.error || "No pudimos completar la solicitud.");
  }
  return data;
}
function toast(message) {
  $("#toast").textContent = message;
  $("#toast").hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => ($("#toast").hidden = true), 4500);
}
function updateAccount() {
  $("#auth").hidden = !!user;
  for (const id of ["logout", "mine", "profile"]) $(`#${id}`).hidden = !user;
  $("#logout").textContent = "Salir";
  $("#profile").textContent = user ? user.name : "Mi cuenta";
}
function renderCategories() {
  $("#categories").innerHTML = ["", ...categories]
    .map(
      (c) =>
        `<button class="category ${category === c ? "selected" : ""}" data-category="${escape(c)}" aria-pressed="${category === c}"><span class="category-icon" aria-hidden="true">${c ? icon(c) : icon("box")}</span><span>${c || "Todos los productos"}</span></button>`,
    )
    .join("");
}
function imageMarkup(p) {
  return p.image
    ? `<img src="${escape(p.image)}" alt="${escape(p.title)}" loading="lazy" referrerpolicy="no-referrer">`
    : `<div class="product-placeholder">${icon(p.category)}<small>${escape(p.category)}</small></div>`;
}
function imageFallback(container) {
  container.querySelectorAll("img").forEach((img) =>
    img.addEventListener(
      "error",
      () => {
        const fallback = document.createElement("div");
        fallback.className = "product-placeholder";
        fallback.innerHTML = icon("box") + "<small>Foto no disponible</small>";
        img.replaceWith(fallback);
      },
      { once: true },
    ),
  );
}
function animateStat(element, target) {
  const duration = 700;
  const start = performance.now();
  const step = (now) => {
    const progress = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    element.textContent = Math.round(target * eased).toLocaleString("es-CL");
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
async function loadStats() {
  try {
    const stats = await api("/api/stats");
    for (const key of ["listings", "sellers", "cities"]) {
      const element = $(`#stat-${key}`);
      if (prefersReducedMotion) element.textContent = stats[key];
      else animateStat(element, stats[key]);
    }
  } catch {
    for (const key of ["listings", "sellers", "cities"])
      $(`#stat-${key}`).textContent = "—";
  }
}
function filterParams() {
  const params = new URLSearchParams({
    q: $("#search").value.trim(),
    category,
    mine: view === "mine" ? "1" : "0",
    favorites: view === "favorites" ? "1" : "0",
    sort: $("#sort").value,
  });
  for (const [key, id] of [
    ["city", "filter-city"],
    ["min_price", "min-price"],
    ["max_price", "max-price"],
    ["condition", "filter-condition"],
  ]) {
    if ($(`#${id}`).value.trim()) params.set(key, $(`#${id}`).value.trim());
  }
  return params;
}
function renderProducts() {
  $("#products").innerHTML = products
    .map(
      (p) =>
        `<article class="product-card ${p.status === "sold" ? "sold" : ""}"><button class="card-main" data-id="${p.id}" aria-label="Ver ${escape(p.title)}"><div class="product-image">${imageMarkup(p)}<span class="product-category">${p.status === "sold" ? "Vendido" : escape(p.condition)}</span><span class="card-arrow">${icon("arrow")}</span></div><div class="product-info"><span class="location">${icon("pin")}${escape(p.city)} <span>· ${escape(p.category)}</span></span><h3>${escape(p.title)}</h3><div class="product-bottom"><strong>${money.format(p.price)}</strong><span class="fav-count" title="Personas que lo guardaron">${icon("heart")}${p.favorite_count || 0}</span></div><div class="product-seller"><span class="mini-avatar">${escape(p.seller.slice(0, 1).toUpperCase())}</span><span>${escape(p.seller)}</span><span>·</span><span>${timeAgo(p.created_at)}</span></div></div></button><button class="favorite-button ${p.favorite ? "saved" : ""}" data-favorite="${p.id}" aria-label="${p.favorite ? "Quitar de" : "Guardar en"} favoritos: ${escape(p.title)}" aria-pressed="${!!p.favorite}">${icon("heart")}</button>${view === "mine" ? `<div class="card-management"><button data-edit="${p.id}">Editar</button><button data-status="${p.id}">${p.status === "sold" ? "Republicar" : "Marcar vendido"}</button></div>` : ""}</article>`,
    )
    .join("");
  imageFallback($("#products"));
}
function renderActiveFilters() {
  const entries = [];
  if (category) entries.push(["category", `Categoría: ${category}`]);
  const search = $("#search").value.trim();
  if (search) entries.push(["search", `Búsqueda: “${search}”`]);
  const city = $("#filter-city").value.trim();
  if (city) entries.push(["city", `Ciudad: ${city}`]);
  if ($("#min-price").value.trim())
    entries.push([
      "min",
      `Desde: ${money.format(Number($("#min-price").value))}`,
    ]);
  if ($("#max-price").value.trim())
    entries.push([
      "max",
      `Hasta: ${money.format(Number($("#max-price").value))}`,
    ]);
  if ($("#filter-condition").value)
    entries.push(["condition", `Condición: ${$("#filter-condition").value}`]);
  if ($("#sort").value !== "recent") entries.push(["sort", "Orden personalizado"]);
  const wrap = $("#active-filters");
  if (!entries.length) {
    wrap.hidden = true;
    wrap.innerHTML = "";
    return;
  }
  wrap.hidden = false;
  wrap.innerHTML = entries
    .map(
      ([key, label]) =>
        `<span class="filter-chip"><em>${escape(label)}</em><button type="button" data-remove-filter="${key}" aria-label="Quitar filtro ${escape(label)}">×</button></span>`,
    )
    .join("");
}
function renderSkeletons() {
  $("#products").innerHTML = Array.from(
    { length: 8 },
    () =>
      '<div class="skeleton-card"><div class="skeleton-block skeleton-image"></div><div class="skeleton-block skeleton-line"></div><div class="skeleton-block skeleton-line short"></div></div>',
  ).join("");
}
function updateCount() {
  const shown = products.length;
  const noun = totalProducts === 1 ? "producto" : "productos";
  $("#count").textContent =
    totalProducts > shown
      ? `Mostrando ${shown} de ${totalProducts} ${noun}`
      : `${shown} ${noun}`;
}
async function loadProducts({ append = false } = {}) {
  const version = ++requestVersion;
  $("#load-error").hidden = true;
  if (append) {
    $("#load-more").disabled = true;
  } else {
    $("#loading").hidden = true;
    $("#load-more-wrap").hidden = true;
    renderSkeletons();
  }
  $("#products").setAttribute("aria-busy", "true");
  $("#catalog-title").textContent = {
    browse: "Explora el marketplace",
    mine: "Mis publicaciones",
    favorites: "Mis favoritos",
  }[view];
  $("#results-summary").textContent = {
    browse: "Productos con una nueva historia",
    mine: "Gestiona tus anuncios y marca tus ventas",
    favorites: "Tus descubrimientos, en un solo lugar",
  }[view];
  for (const [id, v] of [
    ["browse", "browse"],
    ["mine", "mine"],
    ["favorites-nav", "favorites"],
  ]) {
    const el = $(`#${id}`);
    el.classList.toggle("active", view === v);
    if (view === v) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  }
  renderCategories();
  renderActiveFilters();
  const params = filterParams();
  params.set("limit", PAGE_SIZE);
  params.set("offset", append ? products.length : 0);
  try {
    const [result, count] = await Promise.all([
      api(`/api/listings?${params}`),
      api(`/api/listings/count?${filterParams()}`),
    ]);
    if (version !== requestVersion) return;
    totalProducts = count.total;
    products = append ? products.concat(result) : result;
    updateCount();
    renderProducts();
    $("#empty").hidden = products.length > 0;
    const filtered =
      category ||
      $("#search").value ||
      $("#filter-city").value ||
      $("#min-price").value ||
      $("#max-price").value ||
      $("#filter-condition").value;
    $("#empty h3").textContent = filtered
      ? "No encontramos productos"
      : view === "favorites"
        ? "Tus favoritos comienzan aquí"
        : "Aquí comienza una nueva historia";
    $("#empty-copy").textContent = filtered
      ? "Prueba otra búsqueda o limpia los filtros."
      : view === "favorites"
        ? "Guarda los productos que te gustan con el corazón de cada anuncio."
        : view === "mine"
          ? "Publica tu primer producto y comienza a vender."
          : "Todavía no hay productos. Sé la primera persona en publicar.";
    $("#empty-publish").textContent =
      view === "favorites" ? "Explorar productos" : "Publicar un producto";
    $("#load-more-wrap").hidden =
      products.length >= totalProducts || products.length === 0;
  } catch (error) {
    if (version !== requestVersion) return;
    if (append) {
      toast(error.message);
    } else {
      $("#products").replaceChildren();
      $("#empty").hidden = true;
      $("#count").textContent = "";
      $("#load-error-text").textContent = error.message;
      $("#load-error").hidden = false;
      $("#load-more-wrap").hidden = true;
    }
  } finally {
    if (version === requestVersion) {
      $("#loading").hidden = true;
      $("#products").setAttribute("aria-busy", "false");
      $("#load-more").disabled = false;
    }
  }
}
function requireLogin(action) {
  if (user) {
    action();
    return;
  }
  afterLogin = action;
  $("#auth-form .form-error").textContent = "";
  $("#auth-dialog").showModal();
}
function openPublish(product = null) {
  requireLogin(() => {
    editing = product?.id || null;
    $("#publish-form").reset();
    $("#publish-form .form-error").textContent = "";
    $("#publish-title").textContent = editing
      ? "Mejora tu publicación"
      : "Dale una nueva historia";
    $("#publish-form [type=submit]").textContent = editing
      ? "Guardar cambios"
      : "Publicar producto";
    if (product)
      for (const key of [
        "title",
        "description",
        "price",
        "city",
        "category",
        "image",
        "condition",
      ])
        $("#publish-form").elements[key].value = product[key];
    updateDescriptionCount();
    $("#image-preview").hidden = true;
    $("#publish-dialog").showModal();
  });
}
function updateDescriptionCount() {
  const field = $("#publish-form [name=description]");
  $("#description-count").textContent = `${field.value.length}/2000`;
}
function setView(next) {
  const action = () => {
    view = next;
    resetFilters(false);
    loadProducts();
    $("#catalog").scrollIntoView({ behavior: "smooth", block: "start" });
  };
  if (next !== "browse") requireLogin(action);
  else action();
}
function resetFilters(reload = true) {
  category = "";
  for (const id of [
    "search",
    "filter-city",
    "min-price",
    "max-price",
    "filter-condition",
  ])
    $(`#${id}`).value = "";
  $("#sort").value = "recent";
  if (reload) loadProducts();
}
async function toggleFavorite(id) {
  requireLogin(async () => {
    const p = products.find((p) => p.id === id);
    if (!p) return;
    const button = $(`[data-favorite="${id}"]`);
    if (button) button.disabled = true;
    try {
      await api(
        `/api/favorites/${id}`,
        p.favorite ? "DELETE" : "POST",
        p.favorite ? undefined : {},
      );
      toast(
        p.favorite
          ? "Producto retirado de favoritos."
          : "Producto guardado en favoritos.",
      );
      await loadProducts();
    } catch (error) {
      toast(error.message);
    } finally {
      if (button) button.disabled = false;
    }
  });
}
async function changeStatus(id) {
  const p = products.find((p) => p.id === id);
  if (!p) return;
  const button = $(`[data-status="${id}"]`);
  if (button) button.disabled = true;
  try {
    await api(`/api/listings/${id}`, "PATCH", {
      status: p.status === "sold" ? "active" : "sold",
    });
    toast(
      p.status === "sold"
        ? "Producto disponible nuevamente."
        : "¡Venta completada! Producto marcado como vendido.",
    );
    await Promise.all([loadProducts(), loadStats()]);
  } catch (error) {
    toast(error.message);
  } finally {
    if (button) button.disabled = false;
  }
}
function detail(id) {
  const p = products.find((p) => p.id === id);
  if (p) openDetail(p);
}
async function shareListing(p) {
  const url = `${location.origin}/?producto=${p.id}`;
  try {
    if (navigator.share) {
      await navigator.share({
        title: p.title,
        text: `${p.title} · ${money.format(p.price)}`,
        url,
      });
      return;
    }
    await navigator.clipboard.writeText(url);
    toast("Enlace copiado al portapapeles.");
  } catch {
    /* La persona canceló el diálogo de compartir. */
  }
}
function openDetail(p) {
  detailId = p.id;
  const owner = user && p.user_id === user.id;
  $("#detail-content").innerHTML =
    `<div class="detail-image">${imageMarkup(p)}</div><div class="detail-meta"><span class="eyebrow">${escape(p.category)} · ${escape(p.city)}</span><span class="condition-badge">${p.status === "sold" ? "Vendido" : escape(p.condition)}</span></div><h2>${escape(p.title)}</h2><strong class="detail-price">${money.format(p.price)}</strong><p class="published-date">Publicado el ${date.format(new Date(p.created_at * 1000))}</p><h3 class="detail-subtitle">Sobre este producto</h3><p class="description">${escape(p.description)}</p><div class="seller"><span class="avatar">${escape(p.seller.slice(0, 1).toUpperCase())}</span><div><small>Publicado por</small><strong>${escape(p.seller)}</strong></div></div>${p.status !== "sold" ? `<a class="button dark full" href="mailto:${encodeURIComponent(p.contact)}?subject=${encodeURIComponent("Consulta por " + p.title)}">Contactar al vendedor ${icon("arrow")}</a>` : '<p class="contact-note">Este producto ya fue vendido.</p>'}<div class="detail-actions"><button type="button" class="button outline" id="share-listing">Compartir enlace ${icon("share")}</button></div><p class="safety-note">Revisa el producto y acuerda la entrega antes de pagar. Lautaro no procesa pagos.</p>${owner ? '<div class="dialog-actions"><button class="button outline" id="edit-listing">Editar producto</button><button class="button outline" id="delete-listing">Eliminar</button></div>' : ""}`;
  imageFallback($("#detail-content"));
  $("#detail-dialog").showModal();
  $("#share-listing")?.addEventListener("click", () => shareListing(p));
  $("#edit-listing")?.addEventListener("click", () => {
    $("#detail-dialog").close();
    openPublish(p);
  });
  $("#delete-listing")?.addEventListener("click", () => {
    deleteId = p.id;
    $("#confirm-error").textContent = "";
    $("#confirm-dialog").showModal();
  });
}
function submitForm(form, action) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("[type=submit]");
    button.disabled = true;
    const label = button.textContent;
    button.textContent = "Guardando…";
    form.querySelector(".form-error").textContent = "";
    try {
      await action(Object.fromEntries(new FormData(form)));
    } catch (error) {
      form.querySelector(".form-error").textContent = error.message;
    } finally {
      button.disabled = false;
      button.textContent = label;
    }
  });
}
$("#publish-category").innerHTML = categories
  .map((c) => `<option>${c}</option>`)
  .join("");
$(".search-box>span").innerHTML = icon("search");
for (const id of ["publish", "banner-publish"])
  $(`#${id}`).addEventListener("click", () => openPublish());
$("#empty-publish").addEventListener("click", () =>
  view === "favorites" ? setView("browse") : openPublish(),
);
$("#auth").addEventListener("click", () => {
  afterLogin = null;
  $("#auth-form .form-error").textContent = "";
  $("#auth-dialog").showModal();
});
document
  .querySelectorAll("[data-close]")
  .forEach((button) =>
    button.addEventListener("click", () => button.closest("dialog").close()),
  );
$("#auth-dialog").addEventListener("close", () => {
  if (!user) afterLogin = null;
});
$("#auth-toggle").addEventListener("click", () => {
  register = !register;
  $("#name-field").hidden = !register;
  $("#name-field input").required = register;
  $("#auth-title").textContent = register
    ? "Tu comunidad te espera"
    : "Qué bueno verte";
  $("#auth-submit").textContent = register ? "Crear cuenta" : "Ingresar";
  $("#auth-toggle").textContent = register
    ? "¿Ya tienes cuenta? Ingresa"
    : "¿No tienes cuenta? Regístrate";
  $("#auth-form .form-error").textContent = "";
  $("#auth-form [name=password]").autocomplete = register
    ? "new-password"
    : "current-password";
});
submitForm($("#auth-form"), async (data) => {
  user = await api(register ? "/api/register" : "/api/login", "POST", data);
  $("#auth-dialog").close();
  $("#auth-form").reset();
  updateAccount();
  await loadProducts();
  toast(`Hola, ${user.name}. Bienvenido a tu comunidad.`);
  const action = afterLogin;
  afterLogin = null;
  if (action) action();
});
submitForm($("#publish-form"), async (data) => {
  data.price = Number(data.price);
  await api(
    editing ? `/api/listings/${editing}` : "/api/listings",
    editing ? "PATCH" : "POST",
    data,
  );
  $("#publish-dialog").close();
  $("#publish-form").reset();
  view = "mine";
  resetFilters(false);
  await Promise.all([loadProducts(), loadStats()]);
  toast(editing ? "Cambios guardados." : "Tu producto ya está publicado.");
  editing = null;
});
submitForm($("#profile-form"), async (data) => {
  user = await api("/api/profile", "PATCH", data);
  updateAccount();
  $("#profile-dialog").close();
  await loadProducts();
  toast("Perfil actualizado.");
});
$("#profile").addEventListener("click", () => {
  if (!user) return;
  $("#profile-form [name=name]").value = user.name;
  $("#profile-email").value = user.email;
  $("#profile-form .form-error").textContent = "";
  $("#profile-dialog").showModal();
});
$("#logout").addEventListener("click", async () => {
  try {
    await api("/api/logout", "POST", {});
    user = null;
    view = "browse";
    afterLogin = null;
    updateAccount();
    await loadProducts();
    toast("Sesión cerrada.");
  } catch (error) {
    toast(error.message);
  }
});
$("#browse").addEventListener("click", () => setView("browse"));
$("#mine").addEventListener("click", () => setView("mine"));
$("#favorites-nav").addEventListener("click", () => setView("favorites"));
$("#search-form").addEventListener("submit", (e) => {
  e.preventDefault();
  loadProducts();
});
$("#apply-filters").addEventListener("click", () => loadProducts());
$("#sort").addEventListener("change", () => loadProducts());
$("#reset-filters").addEventListener("click", () => resetFilters());
$("#retry").addEventListener("click", () => loadProducts());
$("#categories").addEventListener("click", (e) => {
  const button = e.target.closest("[data-category]");
  if (button) {
    category = button.dataset.category;
    loadProducts();
  }
});
$("#products").addEventListener("click", (e) => {
  const favorite = e.target.closest("[data-favorite]"),
    edit = e.target.closest("[data-edit]"),
    status = e.target.closest("[data-status]"),
    card = e.target.closest("[data-id]");
  if (favorite) toggleFavorite(Number(favorite.dataset.favorite));
  else if (edit)
    openPublish(products.find((p) => p.id === Number(edit.dataset.edit)));
  else if (status) changeStatus(Number(status.dataset.status));
  else if (card) detail(Number(card.dataset.id));
});
$("#cancel-delete").addEventListener("click", () =>
  $("#confirm-dialog").close(),
);
$("#confirm-delete").addEventListener("click", async () => {
  const button = $("#confirm-delete");
  button.disabled = true;
  try {
    await api(`/api/listings/${deleteId}`, "DELETE");
    $("#confirm-dialog").close();
    $("#detail-dialog").close();
    await Promise.all([loadProducts(), loadStats()]);
    toast("Publicación eliminada.");
  } catch (error) {
    $("#confirm-error").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
$("#publish-form [name=image]").addEventListener("change", (e) => {
  const url = e.target.value.trim();
  $("#image-preview").replaceChildren();
  $("#image-preview").hidden = true;
  if (!url) return;
  try {
    if (new URL(url).protocol !== "https:") throw new Error();
  } catch {
    return;
  }
  const img = document.createElement("img");
  img.src = url;
  img.alt = "Vista previa de tu producto";
  img.referrerPolicy = "no-referrer";
  $("#image-preview").append(img);
  $("#image-preview").hidden = false;
  imageFallback($("#image-preview"));
});
$("#publish-form [name=description]").addEventListener(
  "input",
  updateDescriptionCount,
);
$("#load-more").addEventListener("click", () =>
  loadProducts({ append: true }),
);
document.querySelectorAll("dialog").forEach((dialog) =>
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  }),
);
const menuToggle = $("#menu-toggle");
const mainNav = $("#main-nav");
function closeMenu() {
  if (!mainNav.classList.contains("open")) return;
  mainNav.classList.remove("open");
  menuToggle.setAttribute("aria-expanded", "false");
  menuToggle.setAttribute("aria-label", "Abrir menú");
}
menuToggle.addEventListener("click", () => {
  const open = mainNav.classList.toggle("open");
  menuToggle.setAttribute("aria-expanded", String(open));
  menuToggle.setAttribute(
    "aria-label",
    open ? "Cerrar menú" : "Abrir menú",
  );
});
mainNav.addEventListener("click", (event) => {
  if (event.target.closest("button")) closeMenu();
});
document.addEventListener("click", (event) => {
  if (
    mainNav.classList.contains("open") &&
    !event.target.closest("#main-nav") &&
    !event.target.closest("#menu-toggle")
  )
    closeMenu();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeMenu();
});
window.addEventListener("resize", () => {
  if (window.innerWidth > 800) closeMenu();
});
$("#active-filters").addEventListener("click", (event) => {
  const button = event.target.closest("[data-remove-filter]");
  if (!button) return;
  const key = button.dataset.removeFilter;
  if (key === "category") category = "";
  else if (key === "search") $("#search").value = "";
  else if (key === "city") $("#filter-city").value = "";
  else if (key === "min") $("#min-price").value = "";
  else if (key === "max") $("#max-price").value = "";
  else if (key === "condition") $("#filter-condition").value = "";
  else if (key === "sort") $("#sort").value = "recent";
  loadProducts();
});
$("#hero-browse").addEventListener("click", () => setView("browse"));
$("#hero-publish").addEventListener("click", () => openPublish());
document
  .querySelectorAll("[data-footer-view]")
  .forEach((button) =>
    button.addEventListener("click", () =>
      setView(button.dataset.footerView),
    ),
  );
document
  .querySelectorAll("[data-footer-category]")
  .forEach((button) =>
    button.addEventListener("click", () => {
      view = "browse";
      resetFilters(false);
      category = button.dataset.footerCategory;
      loadProducts();
      $("#catalog").scrollIntoView({
        behavior: prefersReducedMotion ? "auto" : "smooth",
        block: "start",
      });
    }),
  );
document
  .querySelectorAll("[data-footer-action]")
  .forEach((button) =>
    button.addEventListener("click", () => {
      const action = button.dataset.footerAction;
      if (action === "publish") openPublish();
      else if (action === "profile" && user) $("#profile").click();
      else {
        afterLogin = null;
        $("#auth-form .form-error").textContent = "";
        $("#auth-dialog").showModal();
      }
    }),
  );
const topbar = $(".topbar");
const toTop = $("#to-top");
function onScroll() {
  topbar.classList.toggle("scrolled", window.scrollY > 8);
  toTop.hidden = window.scrollY < 420;
}
window.addEventListener("scroll", onScroll, { passive: true });
onScroll();
toTop.addEventListener("click", () =>
  window.scrollTo({
    top: 0,
    behavior: prefersReducedMotion ? "auto" : "smooth",
  }),
);
const revealObserver =
  "IntersectionObserver" in window
    ? new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              entry.target.classList.add("visible");
              revealObserver.unobserve(entry.target);
            }
          }
        },
        { threshold: 0.15 },
      )
    : null;
document.querySelectorAll(".reveal").forEach((element) => {
  if (revealObserver) revealObserver.observe(element);
  else element.classList.add("visible");
});
(async () => {
  try {
    user = await api("/api/me");
    updateAccount();
  } catch (error) {
    toast(error.message);
  }
  await Promise.all([loadProducts(), loadStats()]);
  const deepLink = new URLSearchParams(location.search).get("producto");
  if (deepLink && /^\d+$/.test(deepLink)) {
    try {
      openDetail(await api(`/api/listings/${deepLink}`));
    } catch {
      /* El producto enlazado ya no está disponible. */
    }
  }
})();
