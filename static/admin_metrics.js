(() => {
  "use strict";

  const root = document.getElementById("metricsDashboard");
  if (!root) return;

  let payload = {};
  try {
    payload = JSON.parse(root.dataset.payload || "{}");
  } catch (error) {
    console.error("Metrics payload could not be parsed.", error);
    return;
  }

  const css = getComputedStyle(document.documentElement);
  const palette = {
    primary: css.getPropertyValue("--admin-blue").trim() || "#087db6",
    secondary: css.getPropertyValue("--admin-cyan").trim() || "#12a9c6",
    navy: css.getPropertyValue("--admin-navy").trim() || "#06275c",
    muted: css.getPropertyValue("--admin-muted").trim() || "#64788a",
    line: css.getPropertyValue("--admin-line").trim() || "#d9e3eb",
    good: css.getPropertyValue("--admin-good").trim() || "#0b7d4c",
  };

  const charts = Array.from(root.querySelectorAll("canvas[data-metrics-chart]"));

  function prepareCanvas(canvas) {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.max(1, window.devicePixelRatio || 1);
    const width = Math.max(320, Math.floor(rect.width || canvas.parentElement.clientWidth || 640));
    const height = Math.max(220, Math.floor(rect.height || canvas.parentElement.clientHeight || 260));
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);
    return { ctx, width, height };
  }

  function niceMax(value) {
    if (!Number.isFinite(value) || value <= 0) return 1;
    const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
    const scaled = value / magnitude;
    const nice = scaled <= 1 ? 1 : scaled <= 2 ? 2 : scaled <= 5 ? 5 : 10;
    return nice * magnitude;
  }

  function drawAxes(ctx, width, height, yMax, labels, opts = {}) {
    const margin = { left: 44, right: 18, top: 18, bottom: 42 };
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;
    ctx.font = "10px system-ui, -apple-system, Segoe UI, sans-serif";
    ctx.textBaseline = "middle";

    const ticks = 4;
    for (let i = 0; i <= ticks; i += 1) {
      const value = (yMax * i) / ticks;
      const y = margin.top + plotH - (plotH * i) / ticks;
      ctx.beginPath();
      ctx.strokeStyle = palette.line;
      ctx.lineWidth = 1;
      ctx.moveTo(margin.left, y);
      ctx.lineTo(width - margin.right, y);
      ctx.stroke();
      ctx.fillStyle = palette.muted;
      ctx.textAlign = "right";
      const display = yMax <= 10 ? value.toFixed(value % 1 ? 1 : 0) : Math.round(value).toString();
      ctx.fillText(display, margin.left - 7, y);
    }

    const count = labels.length;
    if (count) {
      const maxLabels = opts.maxLabels || 8;
      const every = Math.max(1, Math.ceil(count / maxLabels));
      ctx.textAlign = "center";
      ctx.fillStyle = palette.muted;
      labels.forEach((label, index) => {
        if (index % every !== 0 && index !== count - 1) return;
        const x = count === 1
          ? margin.left + plotW / 2
          : margin.left + (plotW * index) / (count - 1);
        ctx.fillText(String(label), x, height - 18);
      });
    }
    return { ...margin, plotW, plotH };
  }

  function renderLine(canvas, labels, series, opts = {}) {
    const { ctx, width, height } = prepareCanvas(canvas);
    const values = series.flatMap((s) => s.values.filter((v) => Number.isFinite(v)));
    const yMax = niceMax(Math.max(1, ...values));
    const box = drawAxes(ctx, width, height, yMax, labels, opts);

    series.forEach((s, seriesIndex) => {
      ctx.save();
      ctx.beginPath();
      ctx.strokeStyle = s.color || (seriesIndex === 0 ? palette.primary : palette.secondary);
      ctx.lineWidth = s.lineWidth || 2;
      if (s.dashed) ctx.setLineDash([6, 5]);
      let started = false;

      s.values.forEach((value, index) => {
        if (!Number.isFinite(value)) {
          started = false;
          return;
        }
        const x = labels.length === 1
          ? box.left + box.plotW / 2
          : box.left + (box.plotW * index) / Math.max(1, labels.length - 1);
        const y = box.top + box.plotH - (Math.max(0, value) / yMax) * box.plotH;
        if (!started) {
          ctx.moveTo(x, y);
          started = true;
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.stroke();

      if (labels.length <= 80) {
        s.values.forEach((value, index) => {
          if (!Number.isFinite(value)) return;
          const x = labels.length === 1
            ? box.left + box.plotW / 2
            : box.left + (box.plotW * index) / Math.max(1, labels.length - 1);
          const y = box.top + box.plotH - (Math.max(0, value) / yMax) * box.plotH;
          ctx.beginPath();
          ctx.fillStyle = s.color || (seriesIndex === 0 ? palette.primary : palette.secondary);
          ctx.arc(x, y, 2.4, 0, Math.PI * 2);
          ctx.fill();
        });
      }
      ctx.restore();
    });

    if (opts.yLabel) {
      ctx.save();
      ctx.translate(12, box.top + box.plotH / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillStyle = palette.muted;
      ctx.font = "10px system-ui, -apple-system, Segoe UI, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(opts.yLabel, 0, 0);
      ctx.restore();
    }
  }

  function renderBars(canvas, labels, series, opts = {}) {
    const { ctx, width, height } = prepareCanvas(canvas);
    const values = series.flatMap((s) => s.values.filter((v) => Number.isFinite(v)));
    const yMax = niceMax(Math.max(1, ...values));
    const box = drawAxes(ctx, width, height, yMax, labels, opts);
    const groups = Math.max(1, labels.length);
    const groupW = box.plotW / groups;
    const barGap = Math.max(2, Math.min(6, groupW * 0.08));
    const usable = Math.max(2, groupW - barGap * 2);
    const barW = Math.max(1, usable / Math.max(1, series.length));

    series.forEach((s, seriesIndex) => {
      ctx.fillStyle = s.color || (seriesIndex === 0 ? palette.primary : palette.secondary);
      s.values.forEach((value, index) => {
        if (!Number.isFinite(value)) return;
        const h = (Math.max(0, value) / yMax) * box.plotH;
        const x = box.left + index * groupW + barGap + seriesIndex * barW;
        const y = box.top + box.plotH - h;
        ctx.fillRect(x, y, Math.max(1, barW - 1), h);
      });
    });
  }

  function chartData(type) {
    if (type === "hourly-users") {
      const rows = payload.hourly || [];
      return {
        kind: "line",
        labels: rows.map((r) => r.label),
        series: [
          { values: rows.map((r) => Number(r.avg_users)), color: palette.primary },
          { values: rows.map((r) => Number(r.peak_users)), color: palette.secondary },
        ],
        opts: { maxLabels: 12, yLabel: "Connected users" },
      };
    }
    if (type === "hourly-events") {
      const rows = payload.hourly || [];
      return {
        kind: "bar",
        labels: rows.map((r) => r.label),
        series: [
          { values: rows.map((r) => Number(r.events)), color: palette.primary },
          { values: rows.map((r) => Number(r.calculations)), color: palette.secondary },
        ],
        opts: { maxLabels: 12 },
      };
    }
    if (type === "concurrency") {
      const rows = payload.concurrency_24h || [];
      return {
        kind: "line",
        labels: rows.map((r) => r.label),
        series: [{ values: rows.map((r) => Number(r.users)), color: palette.primary }],
        opts: { maxLabels: 8, yLabel: "Connected users" },
      };
    }
    if (type === "daily-active") {
      const rows = payload.daily || [];
      return {
        kind: "line",
        labels: rows.map((r) => r.label),
        series: [{ values: rows.map((r) => Number(r.active_users)), color: palette.primary }],
        opts: { maxLabels: 8, yLabel: "Active users" },
      };
    }
    if (type === "forecast") {
      const rows = payload.forecast || [];
      return {
        kind: "line",
        labels: rows.map((r) => r.label),
        series: [
          {
            values: rows.map((r) => r.observed == null ? NaN : Number(r.observed)),
            color: palette.navy,
          },
          {
            values: rows.map((r) => r.forecast == null ? NaN : Number(r.forecast)),
            color: palette.secondary,
            dashed: true,
          },
        ],
        opts: { maxLabels: 10, yLabel: "Peak connected users" },
      };
    }
    return null;
  }

  function renderChart(canvas) {
    const spec = chartData(canvas.dataset.metricsChart);
    if (!spec) return;
    if (spec.kind === "bar") {
      renderBars(canvas, spec.labels, spec.series, spec.opts);
    } else {
      renderLine(canvas, spec.labels, spec.series, spec.opts);
    }
  }

  charts.forEach(renderChart);

  if ("ResizeObserver" in window) {
    const observer = new ResizeObserver((entries) => {
      entries.forEach((entry) => {
        const canvas = entry.target.querySelector
          ? entry.target.querySelector("canvas[data-metrics-chart]")
          : null;
        if (canvas) renderChart(canvas);
      });
    });
    charts.forEach((canvas) => observer.observe(canvas.parentElement));
  } else {
    window.addEventListener("resize", () => charts.forEach(renderChart), { passive: true });
  }

  async function refreshLive() {
    const url = root.dataset.liveUrl;
    if (!url) return;
    try {
      const response = await fetch(url, {
        headers: { Accept: "application/json" },
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!response.ok) return;
      const data = await response.json();
      if (!data || data.ok !== true) return;

      const users = root.querySelector('[data-live-kpi="users"]');
      const cpu = root.querySelector('[data-live-kpi="cpu"]');
      const memory = root.querySelector('[data-live-kpi="memory"]');
      const rss = root.querySelector('[data-live-kpi="rss"]');
      if (users) users.textContent = String(data.connected_users ?? "—");
      if (cpu) cpu.textContent = Number.isFinite(data.cpu_pressure_percent)
        ? `${Math.round(data.cpu_pressure_percent)}%`
        : "—";
      if (memory) memory.textContent = Number.isFinite(data.memory_percent)
        ? `${Math.round(data.memory_percent)}%`
        : "—";
      if (rss) rss.textContent = Number.isFinite(data.process_memory_mb)
        ? `${Math.round(data.process_memory_mb)} MB`
        : "—";
    } catch (_error) {
      // Live polling is optional; a temporary network failure must not disturb
      // the administrator dashboard.
    }
  }

  window.setInterval(refreshLive, 30000);
})();
