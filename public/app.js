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
let user = null,
  category = "",
  view = "browse",
  register = false,
  products = [],
  requestVersion = 0;
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
        `<button class="category ${category === c ? "selected" : ""}" data-category="${escape(c)}" aria-pressed="${category === c}">${c ? icon(c) : icon("box")}${c || "Todos los productos"}</button>`,
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
async function loadStats() {
  try {
    const stats = await api("/api/stats");
    for (const key of ["listings", "sellers", "cities"])
      $(`#stat-${key}`).textContent = stats[key];
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
        `<article class="product-card ${p.status === "sold" ? "sold" : ""}"><button class="card-main" data-id="${p.id}" aria-label="Ver ${escape(p.title)}"><div class="product-image">${imageMarkup(p)}<span class="product-category">${p.status === "sold" ? "Vendido" : escape(p.condition)}</span><span class="card-arrow">${icon("arrow")}</span></div><div class="product-info"><span class="location">${icon("pin")}${escape(p.city)} <span>· ${escape(p.category)}</span></span><h3>${escape(p.title)}</h3><div class="product-bottom"><strong>${money.format(p.price)}</strong><span>${escape(p.seller)}</span></div></div></button><button class="favorite-button ${p.favorite ? "saved" : ""}" data-favorite="${p.id}" aria-label="${p.favorite ? "Quitar de" : "Guardar en"} favoritos: ${escape(p.title)}" aria-pressed="${!!p.favorite}">${icon("heart")}</button>${view === "mine" ? `<div class="card-management"><button data-edit="${p.id}">Editar</button><button data-status="${p.id}">${p.status === "sold" ? "Republicar" : "Marcar vendido"}</button></div>` : ""}</article>`,
    )
    .join("");
  imageFallback($("#products"));
}
async function loadProducts() {
  const version = ++requestVersion;
  $("#load-error").hidden = true;
  $("#loading").hidden = false;
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
  ])
    $(`#${id}`).classList.toggle("active", view === v);
  renderCategories();
  try {
    const result = await api(`/api/listings?${filterParams()}`);
    if (version !== requestVersion) return;
    products = result;
    $("#count").textContent =
      `${products.length} ${products.length === 1 ? "producto" : "productos"}${products.length === 200 ? " · primeros 200 resultados" : ""}`;
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
  } catch (error) {
    if (version !== requestVersion) return;
    $("#products").replaceChildren();
    $("#empty").hidden = true;
    $("#count").textContent = "";
    $("#load-error-text").textContent = error.message;
    $("#load-error").hidden = false;
  } finally {
    if (version === requestVersion) {
      $("#loading").hidden = true;
      $("#products").setAttribute("aria-busy", "false");
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
    $("#image-preview").hidden = true;
    $("#publish-dialog").showModal();
  });
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
  if (!p) return;
  detailId = id;
  const owner = user && p.user_id === user.id;
  $("#detail-content").innerHTML =
    `<div class="detail-image">${imageMarkup(p)}</div><div class="detail-meta"><span class="eyebrow">${escape(p.category)} · ${escape(p.city)}</span><span class="condition-badge">${p.status === "sold" ? "Vendido" : escape(p.condition)}</span></div><h2>${escape(p.title)}</h2><strong class="detail-price">${money.format(p.price)}</strong><p class="published-date">Publicado el ${date.format(new Date(p.created_at * 1000))}</p><h3 class="detail-subtitle">Sobre este producto</h3><p class="description">${escape(p.description)}</p><div class="seller"><span class="avatar">${escape(p.seller.slice(0, 1).toUpperCase())}</span><div><small>Publicado por</small><strong>${escape(p.seller)}</strong></div></div>${p.status !== "sold" ? `<a class="button dark full" href="mailto:${encodeURIComponent(p.contact)}?subject=${encodeURIComponent("Consulta por " + p.title)}">Contactar al vendedor ${icon("arrow")}</a>` : '<p class="contact-note">Este producto ya fue vendido.</p>'}<p class="safety-note">Revisa el producto y acuerda la entrega antes de pagar. Lautaro no procesa pagos.</p>${owner ? '<div class="dialog-actions"><button class="button outline" id="edit-listing">Editar producto</button><button class="button outline" id="delete-listing">Eliminar</button></div>' : ""}`;
  imageFallback($("#detail-content"));
  $("#detail-dialog").showModal();
  $("#edit-listing")?.addEventListener("click", () => {
    $("#detail-dialog").close();
    openPublish(p);
  });
  $("#delete-listing")?.addEventListener("click", () => {
    deleteId = id;
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
(async () => {
  try {
    user = await api("/api/me");
    updateAccount();
  } catch (error) {
    toast(error.message);
  }
  await Promise.all([loadProducts(), loadStats()]);
})();
