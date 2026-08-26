const Charts = (() => {
  const BLUE = "#1F1A69";
  const registry = {};

  // Monochrome shade ramp derived purely from the blue brand color -
  // no new hues are introduced, only opacity steps.
  function blueShades(n) {
    const shades = [];
    for (let i = 0; i < n; i++) {
      const t = n === 1 ? 1 : 0.35 + (0.65 * i) / (n - 1);
      shades.push(hexToRgba(BLUE, t));
    }
    return shades;
  }

  function hexToRgba(hex, alpha) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function baseOptions(extra = {}) {
    return Object.assign({
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#1F1A69",
          titleFont: { family: "Inter" },
          bodyFont: { family: "Inter" },
          padding: 10,
          cornerRadius: 8,
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: "rgba(31,26,105,0.6)", font: { size: 11 } },
        },
        y: {
          grid: { color: "rgba(31,26,105,0.08)" },
          ticks: { color: "rgba(31,26,105,0.6)", font: { size: 11 } },
        },
      },
    }, extra);
  }

  function renderBarPercent(canvasId, labels, values) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (registry[canvasId]) registry[canvasId].destroy();
    registry[canvasId] = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          data: values.map((v) => Math.round(v * 1000) / 10),
          backgroundColor: blueShades(values.length),
          borderRadius: 6,
          maxBarThickness: 42,
        }],
      },
      options: baseOptions({
        scales: {
          x: { grid: { display: false }, ticks: { color: "rgba(31,26,105,0.6)", font: { size: 11 } } },
          y: {
            grid: { color: "rgba(31,26,105,0.08)" },
            ticks: {
              color: "rgba(31,26,105,0.6)",
              font: { size: 11 },
              callback: (v) => v + "%",
            },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "#1F1A69",
            callbacks: { label: (item) => `${item.parsed.y}% attrition rate` },
          },
        },
      }),
    });
  }

  function renderImportance(canvasId, features) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (registry[canvasId]) registry[canvasId].destroy();
    const labels = features.map((f) => prettifyFeature(f.feature));
    const values = features.map((f) => f.importance);
    registry[canvasId] = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: blueShades(values.length).reverse(),
          borderRadius: 6,
        }],
      },
      options: baseOptions({
        indexAxis: "y",
        scales: {
          x: { grid: { color: "rgba(31,26,105,0.08)" }, ticks: { color: "rgba(31,26,105,0.6)" } },
          y: { grid: { display: false }, ticks: { color: "rgba(31,26,105,0.75)", font: { size: 11 } } },
        },
      }),
    });
  }

  function prettifyFeature(name) {
    const map = {
      MonthlyIncome: "Monthly income",
      DistanceFromHome: "Distance from home",
      YearsAtCompany: "Years at company",
      WorkLifeBalance: "Work-life balance",
      JobSatisfaction: "Job satisfaction",
      EnvironmentSatisfaction: "Environment satisfaction",
      YearsSinceLastPromotion: "Years since last promotion",
      PercentSalaryHike: "Percent salary hike",
      NumCompaniesWorked: "Companies worked previously",
      TrainingTimesLastYear: "Trainings last year",
      Age: "Age",
    };
    if (map[name]) return map[name];
    // one-hot encoded categorical, e.g. "cat__OverTime_Yes" style names
    const cleaned = name.replace(/^(num__|cat__)/, "").replace(/_/g, " ");
    return cleaned;
  }

  return { renderBarPercent, renderImportance, prettifyFeature };
})();
