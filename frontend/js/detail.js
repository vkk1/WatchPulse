import { fetchModelDetail } from "./api.js";
import { buildSignalBreakdown, drawPriceChart, fmtCurrency } from "./charts.js";

const state = {
  modelId: null,
  allPoints: [],
  rangeDays: 180,
};

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return map[ch];
  });
}

function getModelId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("id");
}

function renderShell() {
  const app = document.getElementById("app");
  app.innerHTML = `
    <main class="page">
      <header class="hero">
        <p class="eyebrow">WatchPulse</p>
        <h1 id="modelTitle">Model Detail</h1>
        <p id="modelSubtitle" class="subtle">Loading...</p>
      </header>

      <section class="panel">
        <a class="back-link" href="./index.html">Back to models</a>
      </section>

      <section class="panel">
        <h2>Current Snapshot</h2>
        <div class="kpis">
          <div class="kpi"><span class="label">Median Price</span><span id="kpiMedian" class="value">-</span></div>
          <div class="kpi"><span class="label">Price vs Retail</span><span id="kpiPremium" class="value">-</span></div>
          <div class="kpi"><span class="label">Scarcity Index Band</span><span id="kpiWaitBand" class="value">-</span></div>
          <div class="kpi"><span class="label">Scarcity Index</span><span id="kpiWaitIndex" class="value">-</span></div>
        </div>
      </section>

      <section class="panel chart-wrap">
        <div class="chart-toolbar">
          <h2>Price Trend</h2>
          <div class="control" style="min-width: 160px;">
            <label for="rangeSelect">Range</label>
            <select id="rangeSelect">
              <option value="90">Last 90 days</option>
              <option value="180" selected>Last 180 days</option>
              <option value="all">All points</option>
            </select>
          </div>
        </div>
        <canvas id="priceChart" class="chart-canvas"></canvas>
        <p id="pointCount" class="subtle"></p>
      </section>

      <section class="panel">
        <h2>Why This Scarcity Index</h2>
        <div class="signal-grid">
          <div class="signal"><span class="label">Price vs Retail</span><span id="sigPremium" class="value">-</span></div>
          <div class="signal"><span class="label">Available Now</span><span id="sigAvailability" class="value">-</span></div>
          <div class="signal"><span class="label">Market Speed</span><span id="sigVelocity" class="value">-</span></div>
        </div>
      </section>

      <section class="panel">
        <h2>Methodology</h2>
        <ul>
          <li>We estimate the Scarcity Index using three signals: price vs retail, current availability, and market speed.</li>
          <li>When market prices stay above retail and fewer listings are available, the Scarcity Index increases.</li>
          <li>Market speed reflects how fast listings turn over from day to day.</li>
          <li>Scarcity Index is mapped to bands: 0-6 months, 6-18 months, 18 months-3 years, 3-5 years, and 5-8+ years.</li>
        </ul>
      </section>
    </main>
  `;
}

function selectPoints(points) {
  if (state.rangeDays === "all") {
    return points;
  }
  const days = Number(state.rangeDays);
  if (!Number.isFinite(days) || days <= 0) {
    return points;
  }
  const start = Math.max(points.length - days, 0);
  return points.slice(start);
}

function renderChart() {
  const points = selectPoints(state.allPoints);
  const canvas = document.getElementById("priceChart");
  drawPriceChart(canvas, points);
  document.getElementById("pointCount").textContent = `${points.length} data points shown`;
}

function renderDetail(payload) {
  const model = payload.model || {};
  const points = (payload.daily_stats || []).slice().sort((a, b) => String(a.captured_date).localeCompare(String(b.captured_date)));
  state.allPoints = points;

  document.getElementById("modelTitle").textContent = model.model_name || "Model Detail";
  document.getElementById("modelSubtitle").textContent = `${model.collection || "Unknown"} | Ref ${model.ref_code || "N/A"}`;

  const latest = points.length ? points[points.length - 1] : null;
  const breakdown = buildSignalBreakdown(latest);

  document.getElementById("kpiMedian").textContent = fmtCurrency(latest?.median_price);
  document.getElementById("kpiPremium").textContent = latest ? `${(Number(latest.premium_over_msrp || 0) * 100).toFixed(2)}%` : "N/A";
  document.getElementById("kpiWaitBand").textContent = latest?.wait_band || "N/A";
  document.getElementById("kpiWaitIndex").textContent = latest?.wait_time_index !== undefined && latest?.wait_time_index !== null
    ? Number(latest.wait_time_index).toFixed(3)
    : "N/A";

  if (breakdown) {
    document.getElementById("sigPremium").textContent = `${(breakdown.premiumOverMsrp * 100).toFixed(2)}%`;
    document.getElementById("sigAvailability").textContent = `${(breakdown.availabilityRatio * 100).toFixed(1)}% available`;
    document.getElementById("sigVelocity").textContent = breakdown.velocity.toFixed(4);
  }

  renderChart();
}

async function init() {
  renderShell();

  state.modelId = getModelId();
  if (!state.modelId) {
    document.getElementById("modelSubtitle").textContent = "Missing model id. Open this page with ?id=<model_id>.";
    return;
  }

  document.getElementById("rangeSelect").addEventListener("change", (event) => {
    const value = event.target.value;
    state.rangeDays = value === "all" ? "all" : Number(value);
    renderChart();
  });

  try {
    const payload = await fetchModelDetail(state.modelId);
    renderDetail(payload);
  } catch (error) {
    document.getElementById("modelSubtitle").textContent = `Failed to load model: ${esc(error.message)}`;
  }

  window.addEventListener("resize", () => {
    if (state.allPoints.length) {
      renderChart();
    }
  });
}

init();
