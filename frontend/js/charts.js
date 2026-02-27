function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "N/A";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

export function drawPriceChart(canvas, points) {
  const ctx = canvas.getContext("2d");
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const dpr = window.devicePixelRatio || 1;

  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  ctx.clearRect(0, 0, width, height);
  if (!points || points.length === 0) {
    ctx.fillStyle = "#5c544b";
    ctx.font = "13px Trebuchet MS";
    ctx.fillText("No data points", 10, 20);
    return;
  }

  const padding = { top: 16, right: 20, bottom: 28, left: 62 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  const values = points.map((p) => Number(p.median_price));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);

  ctx.strokeStyle = "#e3d6c5";
  ctx.lineWidth = 1;
  for (let i = 0; i < 4; i += 1) {
    const y = padding.top + (chartH / 3) * i;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
  }

  ctx.fillStyle = "#6c6052";
  ctx.font = "11px Trebuchet MS";
  for (let i = 0; i < 4; i += 1) {
    const y = padding.top + (chartH / 3) * i;
    const ratio = 1 - i / 3;
    const price = min + range * ratio;
    ctx.fillText(formatCurrency(price), 8, y + 4);
  }

  ctx.strokeStyle = "#0e5a70";
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  points.forEach((point, idx) => {
    const x = padding.left + (idx / Math.max(points.length - 1, 1)) * chartW;
    const yRatio = (Number(point.median_price) - min) / range;
    const y = padding.top + (1 - yRatio) * chartH;
    if (idx === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  ctx.fillStyle = "#8f3f26";
  points.forEach((point, idx) => {
    const x = padding.left + (idx / Math.max(points.length - 1, 1)) * chartW;
    const yRatio = (Number(point.median_price) - min) / range;
    const y = padding.top + (1 - yRatio) * chartH;
    ctx.beginPath();
    ctx.arc(x, y, 2.7, 0, Math.PI * 2);
    ctx.fill();
  });

  const first = points[0];
  const last = points[points.length - 1];
  ctx.fillStyle = "#5c544b";
  ctx.font = "11px Trebuchet MS";
  ctx.fillText(first.captured_date, padding.left, height - 8);
  const lastLabel = String(last.captured_date);
  const textWidth = ctx.measureText(lastLabel).width;
  ctx.fillText(lastLabel, width - padding.right - textWidth, height - 8);
}

export function buildSignalBreakdown(latestStat) {
  if (!latestStat) {
    return null;
  }

  const soldRate = Number(latestStat.sold_rate_proxy || 0);
  const listings = Number(latestStat.listings_count || 0);
  const newListings = Number(latestStat.new_listings_count || 0);
  const availabilityRatio = clamp(1 - soldRate, 0, 1);
  const velocity = 0.6 * soldRate + 0.4 * (listings > 0 ? newListings / listings : 0);

  return {
    premiumOverMsrp: Number(latestStat.premium_over_msrp || 0),
    availabilityRatio,
    velocity,
  };
}

export function fmtCurrency(value) {
  return formatCurrency(value);
}
