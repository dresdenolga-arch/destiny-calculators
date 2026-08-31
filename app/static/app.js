const tabs = document.querySelectorAll(".tab");
const forms = {
  matrix: document.getElementById("matrix-form"),
  bazi: document.getElementById("bazi-form"),
  jyotish: document.getElementById("jyotish-form"),
};
const resultEl = document.getElementById("result");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    Object.entries(forms).forEach(([key, form]) => {
      form.style.display = key === tab.dataset.system ? "block" : "none";
    });
    resultEl.classList.remove("visible");
    resultEl.innerHTML = "";
  });
});

function isoToDDMMYYYY(iso) {
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function callApi(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "Ошибка расчёта");
  }
  return data;
}

function showError(message) {
  resultEl.innerHTML = `<div class="error">${escapeHtml(message)}</div>`;
  resultEl.classList.add("visible");
}

// Переходит на готовую HTML-страницу с разбором в этой же вкладке.
// Не используем window.open() после await: браузеры блокируют такие попапы,
// потому что к моменту ответа сервера жест пользователя уже "остыл".
// Прямой переход (location.href) под это ограничение не подпадает.
function goToResult(url) {
  window.location.href = url;
}

forms.matrix.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(forms.matrix);
  const isoDate = fd.get("date");
  if (!isoDate) return;
  const date = isoToDDMMYYYY(isoDate);
  const name = fd.get("name") || "";
  const child = fd.get("child") === "on";
  const partnerIso = fd.get("partner_date");
  const partner_date = partnerIso ? isoToDDMMYYYY(partnerIso) : null;

  const btn = forms.matrix.querySelector("button");
  btn.disabled = true;
  try {
    await callApi("/api/matrix", { date, child, partner_date });
    const params = new URLSearchParams({ date, name, child });
    if (partner_date) params.set("partner_date", partner_date);
    goToResult(`/api/matrix/html?${params.toString()}`);
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
  }
});

forms.bazi.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(forms.bazi);
  const payload = {
    date: fd.get("date"),
    time: fd.get("time") || null,
    gender: fd.get("gender") || "f",
    city: fd.get("city") || null,
    lon: fd.get("lon") ? Number(fd.get("lon")) : null,
    utc_offset: fd.get("utc_offset") ? Number(fd.get("utc_offset")) : null,
  };
  const btn = forms.bazi.querySelector("button");
  btn.disabled = true;
  try {
    await callApi("/api/bazi", payload);
    const params = new URLSearchParams({ date: payload.date, gender: payload.gender });
    if (payload.time) params.set("time", payload.time);
    if (payload.city) params.set("city", payload.city);
    if (payload.lon !== null) params.set("lon", payload.lon);
    if (payload.utc_offset !== null) params.set("utc_offset", payload.utc_offset);
    goToResult(`/api/bazi/html?${params.toString()}`);
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
  }
});

forms.jyotish.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(forms.jyotish);
  const payload = {
    date: fd.get("date"),
    time: fd.get("time") || null,
    city: fd.get("city") || null,
    lat: fd.get("lat") ? Number(fd.get("lat")) : null,
    lon: fd.get("lon") ? Number(fd.get("lon")) : null,
    utc_offset: fd.get("utc_offset") ? Number(fd.get("utc_offset")) : null,
  };
  const btn = forms.jyotish.querySelector("button");
  btn.disabled = true;
  try {
    await callApi("/api/jyotish", payload);
    const params = new URLSearchParams({ date: payload.date });
    if (payload.time) params.set("time", payload.time);
    if (payload.city) params.set("city", payload.city);
    if (payload.lat !== null) params.set("lat", payload.lat);
    if (payload.lon !== null) params.set("lon", payload.lon);
    if (payload.utc_offset !== null) params.set("utc_offset", payload.utc_offset);
    goToResult(`/api/jyotish/html?${params.toString()}`);
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
  }
});
