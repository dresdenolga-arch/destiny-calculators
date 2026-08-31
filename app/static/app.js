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

function renderValue(value) {
  if (value === null || value === undefined || value === "") {
    return `<span class="v">—</span>`;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return `<span class="v">—</span>`;
    if (value.every((v) => typeof v !== "object")) {
      return `<span class="v">${value.map(escapeHtml).join(", ")}</span>`;
    }
    return `<div class="nested">${value.map((v) => renderNode(null, v)).join("")}</div>`;
  }
  if (typeof value === "object") {
    return `<div class="nested">${Object.entries(value)
      .map(([k, v]) => renderNode(k, v))
      .join("")}</div>`;
  }
  return `<span class="v">${escapeHtml(String(value))}</span>`;
}

function renderNode(key, value) {
  if (value && typeof value === "object") {
    return `<div class="kv">${key ? `<div class="k">${escapeHtml(key)}</div>` : ""}${renderValue(value)}</div>`;
  }
  return `<div class="kv"><div class="k">${escapeHtml(key ?? "")}</div>${renderValue(value)}</div>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function renderTopLevel(data) {
  return Object.entries(data)
    .map(([key, value]) => {
      return `<details class="section" open><summary>${escapeHtml(key)}</summary>${renderValue(value)}</details>`;
    })
    .join("");
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

function showResult(html, extraActions = "") {
  resultEl.innerHTML = `${extraActions ? `<div class="result-actions">${extraActions}</div>` : ""}${html}`;
  resultEl.classList.add("visible");
  resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
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
    const data = await callApi("/api/matrix", { date, child, partner_date });
    const htmlUrl = `/api/matrix/html?date=${encodeURIComponent(date)}&name=${encodeURIComponent(name)}&child=${child}`;
    showResult(
      renderTopLevel(data),
      `<a class="link-btn" href="${htmlUrl}" target="_blank" rel="noopener">Открыть полную схему (HTML)</a>`
    );
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
    lon: fd.get("lon") ? Number(fd.get("lon")) : null,
    utc_offset: fd.get("utc_offset") ? Number(fd.get("utc_offset")) : null,
  };
  const btn = forms.bazi.querySelector("button");
  btn.disabled = true;
  try {
    const data = await callApi("/api/bazi", payload);
    showResult(renderTopLevel(data));
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
    lat: fd.get("lat") ? Number(fd.get("lat")) : null,
    lon: fd.get("lon") ? Number(fd.get("lon")) : null,
    utc_offset: Number(fd.get("utc_offset")),
  };
  const btn = forms.jyotish.querySelector("button");
  btn.disabled = true;
  try {
    const data = await callApi("/api/jyotish", payload);
    showResult(renderTopLevel(data));
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
  }
});
