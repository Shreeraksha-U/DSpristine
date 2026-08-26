(async function () {
  const tabs = document.querySelectorAll(".navtab");
  const panels = document.querySelectorAll(".tabpanel");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("is-active"));
      panels.forEach((p) => p.classList.remove("is-active"));
      tab.classList.add("is-active");
      document.getElementById(`tab-${tab.dataset.tab}`).classList.add("is-active");
    });
  });

  async function loadOverview() {
    const [meta, eda, importance] = await Promise.all([
      Api.get("/meta"),
      Api.get("/eda"),
      Api.get("/feature-importance"),
    ]);

    document.getElementById("kpiTotal").textContent = eda.total_employees.toLocaleString("en-IN");
    document.getElementById("kpiRate").textContent = `${Math.round(eda.overall_attrition_rate * 100)}%`;
    document.getElementById("kpiAuc").textContent = meta.metrics.roc_auc ?? "—";
    document.getElementById("kpiModel").textContent =
      meta.model_name === "random_forest" ? "Random Forest" : "Decision Tree";

    Charts.renderBarPercent(
      "chartDept",
      eda.by_department.map((d) => d.label),
      eda.by_department.map((d) => d.attrition_rate)
    );
    Charts.renderBarPercent(
      "chartOvertime",
      eda.by_overtime.map((d) => d.label),
      eda.by_overtime.map((d) => d.attrition_rate)
    );
    Charts.renderBarPercent(
      "chartIncome",
      eda.by_income_band.map((d) => d.label),
      eda.by_income_band.map((d) => d.attrition_rate)
    );
    Charts.renderBarPercent(
      "chartSatisfaction",
      eda.by_job_satisfaction.map((d) => d.label),
      eda.by_job_satisfaction.map((d) => d.attrition_rate)
    );
    Charts.renderImportance("chartImportance", importance.features);

    return meta;
  }

  const statusDot = document.getElementById("modelStatus");
  const statusText = document.getElementById("modelStatusText");

  try {
    const meta = await loadOverview();
    Predict.populateSelects(meta);
    Predict.init();
    AtRisk.init();
    AtRisk.load();

    statusDot.classList.add("is-online");
    statusText.textContent = `${meta.model_name === "random_forest" ? "Random Forest" : "Decision Tree"} model live`;
  } catch (err) {
    statusText.textContent = "API unreachable — is the Flask server running?";
    console.error(err);
  }
})();
