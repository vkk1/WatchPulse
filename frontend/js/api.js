const DEFAULT_API_BASE = "http://127.0.0.1:8000";

export function getApiBase() {
  const saved = window.localStorage.getItem("watchpulse_api_base");
  return saved || DEFAULT_API_BASE;
}

export function setApiBase(base) {
  window.localStorage.setItem("watchpulse_api_base", base);
}

async function request(path, { signal } = {}) {
  const response = await fetch(`${getApiBase()}${path}`, { signal });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status}: ${text}`);
  }
  return response.json();
}

export function fetchModels({ page = 1, pageSize = 25, q = "", collection = "", sort = "wait_time_index_desc" }, opts = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    sort: String(sort),
  });
  if (q.trim()) {
    params.set("q", q.trim());
  }
  if (collection.trim()) {
    params.set("collection", collection.trim());
  }
  return request(`/v1/models?${params.toString()}`, opts);
}

export function fetchModelDetail(modelId, opts = {}) {
  return request(`/v1/models/${encodeURIComponent(modelId)}`, opts);
}

export async function fetchCollections() {
  const data = await fetchModels({ page: 1, pageSize: 100 });
  const values = new Set();
  for (const item of data.items || []) {
    if (item.collection) {
      values.add(item.collection);
    }
  }
  return [...values].sort((a, b) => a.localeCompare(b));
}
