const Predict = (() => {
  const GAUGE_ARC_LENGTH = 251.2; // matches the SVG path length in index.html

  function populateSelects(meta) {
    const form = document.getElementById("predictForm");
    Object.entries(meta.categorical_options).forEach(([field, options]) => {
      const select = form.querySelector(`select[name="${field}"]`);
      if (!select) return;
      select.innerHTML = options.map((opt) => `<option value="${opt}">${opt}</option>`).join("");
    });
    // sensible defaults for a first-time demo
    setSelectValue(form, "OverTime", "No");
    setSelectValue(form, "BusinessTravel", "Travel_Rarely");
    setSelectValue(form, "MaritalStatus", "Married");
  }

  function setSelectValue(form, name, value) {
    const select = form.querySelector(`select[name="${name}"]`);
    if (select && [...select.options].some((o) => o.value === value)) {
      select.value = value;
    }
  }

  function collectPayload(form) {
    const data = new FormData(form);
    const payload = {};
    for (const [key, value] of data.entries()) payload[key] = value;
    return payload;
  }

  function updateGauge(leaveProbability) {
    const fill = document.getElementById("gaugeFill");
    const offset = GAUGE_ARC_LENGTH * (1 - leaveProbability);
    fill.style.strokeDashoffset = offset;
  }

  function renderResult(result) {
    updateGauge(result.leave_probability);
    document.getElementById("gaugeLabel").textContent = result.prediction;
    document.getElementById("gaugePct").textContent =
      `${Math.round(result.leave_probability * 100)}% probability of leaving`;

    document.getElementById("resultOutcome").textContent = result.prediction;
    document.getElementById("resultLeaveProb").textContent = `${Math.round(result.leave_probability * 100)}%`;
    document.getElementById("resultBand").textContent = result.risk_band;
    document.getElementById("resultModel").textContent =
      result.model_used === "random_forest" ? "Random Forest" : "Decision Tree";

    const hint = document.getElementById("resultHint");
    if (result.prediction === "Leave") {
      hint.textContent = `This profile shows a ${result.risk_band.toLowerCase()} risk pattern. Consider a retention conversation, a compensation review, or a growth/promotion discussion.`;
    } else {
      hint.textContent = "This profile currently shows a healthy retention outlook based on the model.";
    }
  }

  function init() {
    const form = document.getElementById("predictForm");
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = form.querySelector(".btn-primary");
      btn.disabled = true;
      btn.textContent = "Predicting…";
      try {
        const payload = collectPayload(form);
        const result = await Api.post("/predict", payload);
        renderResult(result);
      } catch (err) {
        document.getElementById("resultHint").textContent = `Prediction failed: ${err.message}`;
      } finally {
        btn.disabled = false;
        btn.textContent = "Run prediction";
      }
    });
  }

  return { populateSelects, init };
})();
