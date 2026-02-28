import { fetchCollections, fetchModels } from "./api.js";
import { fmtCurrency } from "./charts.js";

const state = {
  page: 1,
  pageSize: 12,
  q: "",
  collection: "",
  sort: "wait_time_index_desc",
  totalPages: 1,
};

function waitBadgeClass(waitBand) {
  if (!waitBand) {
    return "badge";
  }
  if (waitBand.includes("0-6") || waitBand.includes("6-18")) {
    return "badge cool";
  }
  return "badge hot";
}

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return map[ch];
  });
}

function renderShell() {
  const app = document.getElementById("app");
  app.innerHTML = `
    <main class="page">
      <header class="hero">
        <p class="eyebrow">WatchPulse</p>
        <h1>Rolex Scarcity Index Intelligence</h1>
        <p class="subtle">Search References and Filter Collections</p>
      </header>

      <section class="panel controls">
        <div class="control">
          <label for="searchInput">Search (reference or model)</label>
          <input id="searchInput" type="text" placeholder="e.g. 116500LN or Daytona" />
        </div>
        <div class="control">
          <label for="collectionSelect">Collection</label>
          <select id="collectionSelect"><option value="">All collections</option></select>
        </div>
        <div class="control">
          <label for="sortSelect">Sort</label>
          <select id="sortSelect">
            <option value="wait_time_index_desc">Scarcity Index (high to low)</option>
            <option value="premium_desc">Price vs retail (high to low)</option>
            <option value="price_asc">Market price (low to high)</option>
            <option value="price_desc">Market price (high to low)</option>
          </select>
        </div>
        <button id="sortBtn" class="btn secondary">Sort By</button>
        <button id="applyBtn" class="btn">Apply</button>
      </section>

      <section class="panel">
        <div class="panel-title-row">
          <h2>Models</h2>
          <p id="resultMeta" class="subtle">Loading...</p>
        </div>
        <div id="modelsGrid" class="models-grid"></div>
        <p id="emptyState" class="empty hidden">No models found for this filter.</p>
      </section>

      <section class="pagination-row">
        <button id="prevBtn" class="btn secondary">Previous</button>
        <span id="pageLabel" class="page-label">Page 1</span>
        <button id="nextBtn" class="btn secondary">Next</button>
      </section>
    </main>
  `;
}

function bindControls() {
  const searchInput = document.getElementById("searchInput");
  const collectionSelect = document.getElementById("collectionSelect");
  const sortSelect = document.getElementById("sortSelect");

  searchInput.value = state.q;
  collectionSelect.value = state.collection;
  sortSelect.value = state.sort;

  const apply = () => {
    state.q = searchInput.value.trim();
    state.collection = collectionSelect.value;
    state.page = 1;
    loadModels();
  };

  const applySort = () => {
    state.sort = sortSelect.value;
    state.page = 1;
    loadModels();
  };

  document.getElementById("applyBtn").addEventListener("click", apply);
  searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      apply();
    }
  });
  collectionSelect.addEventListener("change", () => {
    state.collection = collectionSelect.value;
    state.page = 1;
    loadModels();
  });
  document.getElementById("sortBtn").addEventListener("click", applySort);

  document.getElementById("prevBtn").addEventListener("click", () => {
    if (state.page > 1) {
      state.page -= 1;
      loadModels();
    }
  });
  document.getElementById("nextBtn").addEventListener("click", () => {
    if (state.page < state.totalPages) {
      state.page += 1;
      loadModels();
    }
  });
}

async function loadCollections() {
  const select = document.getElementById("collectionSelect");
  const values = await fetchCollections();
  for (const collection of values) {
    const opt = document.createElement("option");
    opt.value = collection;
    opt.textContent = collection;
    select.appendChild(opt);
  }
}

function renderCards(items) {
  const grid = document.getElementById("modelsGrid");
  const empty = document.getElementById("emptyState");
  if (!items.length) {
    grid.innerHTML = "";
    empty.classList.remove("hidden");
    return;
  }

  empty.classList.add("hidden");
  grid.innerHTML = items
    .map((item) => {
      const waitIndex = item.wait_time_index === null || item.wait_time_index === undefined
        ? "N/A"
        : Number(item.wait_time_index).toFixed(3);
      return `
        <article class="model-card">
          <div class="card-top">
            <div>
              <h3 class="model-name">${esc(item.model_name || "Unknown model")}</h3>
              <p class="model-meta">${esc(item.collection || "Unknown collection")} | Ref ${esc(item.ref_code || "N/A")}</p>
            </div>
            <div class="metric-row">
              <span class="badge">MSRP ${fmtCurrency(item.msrp)}</span>
              <span class="badge">Median ${fmtCurrency(item.current_median_price)}</span>
              <span class="${waitBadgeClass(item.wait_band)}">Scarcity Index Band: ${esc(item.wait_band || "No band")}</span>
              <span class="badge">Scarcity Index: ${esc(waitIndex)}</span>
            </div>
          </div>
          <div class="card-actions">
            <a class="card-link" href="./model.html?id=${encodeURIComponent(item.id)}">View model</a>
          </div>
        </article>
      `;
    })
    .join("");
}

async function loadModels() {
  const meta = document.getElementById("resultMeta");
  const pageLabel = document.getElementById("pageLabel");
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");

  meta.textContent = "Loading...";

  try {
    const data = await fetchModels({
      page: state.page,
      pageSize: state.pageSize,
      q: state.q,
      collection: state.collection,
      sort: state.sort,
    });

    state.totalPages = Math.max(1, Number(data.total_pages || 1));
    pageLabel.textContent = `Page ${state.page} of ${state.totalPages}`;
    prevBtn.disabled = state.page <= 1;
    nextBtn.disabled = state.page >= state.totalPages;

    meta.textContent = `${data.total || 0} models found`;
    renderCards(data.items || []);
  } catch (error) {
    meta.textContent = "Failed to load models";
    document.getElementById("modelsGrid").innerHTML = `<p class="empty">${esc(error.message)}</p>`;
  }
}

async function init() {
  renderShell();
  bindControls();
  try {
    await loadCollections();
  } catch (error) {
    console.error(error);
  }
  await loadModels();
}

init();
