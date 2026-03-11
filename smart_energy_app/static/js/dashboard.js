/**
 * dashboard.js — SmartEnergy
 * ─────────────────────────────────────────────
 * • Dark-themed Chart.js line/bar chart with period switching
 * • Live kWh estimate as user types
 * • AJAX device usage form submission
 * • Animated table row insertion
 * • Toast notification system
 */

"use strict";

// ── DOM refs ──────────────────────────────────
const deviceSelect   = document.getElementById("device");
const hoursInput     = document.getElementById("hours");
const usageDateInput = document.getElementById("usageDate");
const customWattInput= document.getElementById("customWatt");
const wattTip        = document.getElementById("wattTip");
const logForm        = document.getElementById("logForm");
const logBtn         = document.getElementById("logBtn");
const kwhPreview     = document.getElementById("kwhPreview");
const logToast       = document.getElementById("logToast");
const tableBody      = document.getElementById("tableBody");
const periodTabs     = document.getElementById("periodTabs");

// ── Default date ──────────────────────────────
usageDateInput.value = new Date().toISOString().split("T")[0];

// ── Chart globals ─────────────────────────────
let chart         = null;
let currentPeriod = "daily";

// ════════════════════════════════════════════════
// WATT INPUT — auto-fill on device change, allow override
// ════════════════════════════════════════════════

/**
 * When user picks a device, pre-fill the watt input with the default.
 * They can still type their own value to override it.
 */
function onDeviceChange() {
  const device = deviceSelect.value;
  const defaultWatts = DEVICE_RATINGS[device] || 100;
  customWattInput.value = defaultWatts;
  wattTip.textContent = `Default for ${device}: ${defaultWatts}W — change if your device differs`;
  updatePreview();
}

deviceSelect.addEventListener("change", onDeviceChange);

// Set initial watt value on page load
onDeviceChange();

// ════════════════════════════════════════════════
// LIVE kWh PREVIEW
// ════════════════════════════════════════════════
function updatePreview() {
  const hours = parseFloat(hoursInput.value) || 0;
  const watts = parseFloat(customWattInput.value) || 0;
  const kwh   = ((watts / 1000) * hours).toFixed(3);
  kwhPreview.textContent = (hours > 0 && watts > 0)
    ? `Estimated: ${kwh} kWh`
    : "Estimated: — kWh";
}

hoursInput.addEventListener("input", updatePreview);
customWattInput.addEventListener("input", updatePreview);

// ════════════════════════════════════════════════
// TOAST
// ════════════════════════════════════════════════
let toastTimer = null;
function showToast(msg, type = "success") {
  if (toastTimer) clearTimeout(toastTimer);
  logToast.textContent = msg;
  logToast.className = `toast ${type}`;
  toastTimer = setTimeout(() => { logToast.className = "toast hidden"; }, 4200);
}

// ════════════════════════════════════════════════
// SUBMIT FORM (AJAX)
// ════════════════════════════════════════════════
logForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  logBtn.disabled    = true;
  logBtn.textContent = "Saving…";

  const customWatts = parseFloat(customWattInput.value);
  const payload = {
    device      : deviceSelect.value,
    hours       : parseFloat(hoursInput.value),
    date        : usageDateInput.value,
    custom_watt : isNaN(customWatts) ? null : customWatts,
  };

  try {
    const res  = await fetch("/api/log_usage", {
      method  : "POST",
      headers : { "Content-Type": "application/json" },
      body    : JSON.stringify(payload),
    });
    const data = await res.json();

    if (data.success) {
      showToast(`✓ Logged ${data.energy_kwh} kWh for ${payload.device}`, "success");
      loadChartData(currentPeriod);
      loadTableData();
      hoursInput.value = "";
      updatePreview();
    } else {
      showToast("Failed to save. Try again.", "error");
    }
  } catch (err) {
    showToast("Network error.", "error");
    console.error(err);
  } finally {
    logBtn.disabled    = false;
    logBtn.textContent = "Log Usage";
  }
});

// ════════════════════════════════════════════════
// TABLE REFRESH
// ════════════════════════════════════════════════
async function loadTableData() {
  try {
    const res  = await fetch("/api/table_data");
    const rows = await res.json();

    if (!rows.length) {
      tableBody.innerHTML = `<tr><td colspan="4" class="empty-row">No records yet — log your first device above</td></tr>`;
      return;
    }

    tableBody.innerHTML = rows.map((r, i) => `
      <tr class="${i === 0 ? 'new-row' : ''}">
        <td>${r.usage_date}</td>
        <td><span class="device-badge">${r.device}</span></td>
        <td>${r.hours_used}</td>
        <td>${r.energy_kwh}</td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Table refresh failed:", err);
  }
}

// ════════════════════════════════════════════════
// CHART — Dark themed
// ════════════════════════════════════════════════

/**
 * Build a vertical gradient fill for the chart area.
 */
function makeGradient(ctx, height) {
  const g = ctx.createLinearGradient(0, 0, 0, height);
  g.addColorStop(0,   "rgba(0, 212, 106, 0.28)");
  g.addColorStop(0.5, "rgba(0, 212, 106, 0.08)");
  g.addColorStop(1,   "rgba(0, 212, 106, 0.00)");
  return g;
}

function initChart(labels, values) {
  const canvas = document.getElementById("energyChart");
  const ctx    = canvas.getContext("2d");
  const grad   = makeGradient(ctx, 280);

  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label           : "Energy (kWh)",
        data            : values,
        borderColor     : "#00d46a",
        backgroundColor : grad,
        borderWidth     : 2,
        pointRadius     : 4,
        pointBackgroundColor: "#00d46a",
        pointBorderColor: "#070c09",
        pointBorderWidth: 2,
        pointHoverRadius: 7,
        pointHoverBackgroundColor: "#00e874",
        tension         : 0.4,
        fill            : true,
      }],
    },
    options: {
      responsive         : true,
      maintainAspectRatio: false,
      interaction        : { mode: "index", intersect: false },
      animation          : { duration: 500, easing: "easeOutQuart" },
      plugins: {
        legend : { display: false },
        tooltip: {
          backgroundColor  : "#111a15",
          titleColor       : "#dff0e8",
          bodyColor        : "#7fa892",
          borderColor      : "rgba(0,212,106,0.25)",
          borderWidth      : 1,
          padding          : 12,
          titleFont        : { family: "'Syne', sans-serif", size: 12, weight: "700" },
          bodyFont         : { family: "'Outfit', sans-serif", size: 12 },
          cornerRadius     : 10,
          callbacks        : { label: ctx => `  ${ctx.parsed.y} kWh` },
        },
      },
      scales: {
        x: {
          grid : { color: "rgba(255,255,255,0.04)", drawBorder: false },
          ticks: {
            color      : "#4a6a58",
            font       : { family: "'Outfit', sans-serif", size: 11 },
            maxRotation: 40,
          },
          border: { color: "rgba(255,255,255,0.06)" },
        },
        y: {
          beginAtZero: true,
          grid : { color: "rgba(255,255,255,0.05)", drawBorder: false },
          ticks: {
            color   : "#4a6a58",
            font    : { family: "'Outfit', sans-serif", size: 11 },
            callback: v => `${v} kWh`,
            padding : 8,
          },
          border: { color: "rgba(255,255,255,0.06)", dash: [4,4] },
        },
      },
    },
  });
}

async function loadChartData(period) {
  currentPeriod = period;
  try {
    const res  = await fetch(`/api/chart_data?period=${period}`);
    const data = await res.json();

    if (!chart) {
      initChart(data.labels, data.values);
    } else {
      chart.data.labels           = data.labels;
      chart.data.datasets[0].data = data.values;

      // Re-build gradient for correct canvas size
      const ctx  = document.getElementById("energyChart").getContext("2d");
      chart.data.datasets[0].backgroundColor = makeGradient(ctx, chart.height);
      chart.update("active");
    }
  } catch (err) {
    console.error("Chart load failed:", err);
  }
}

// ── Period Tab Switching ──────────────────────
periodTabs.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    periodTabs.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    loadChartData(btn.dataset.period);
  });
});

// ── Boot ──────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadChartData("daily");
});
