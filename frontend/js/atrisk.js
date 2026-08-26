const AtRisk = (() => {
  let employees = [];

  function riskMeterHtml(prob, band) {
    const pct = Math.round(prob * 100);
    return `
      <div class="risk-meter">
        <div class="risk-meter__track">
          <div class="risk-meter__fill" style="width:${pct}%"></div>
        </div>
        <span class="risk-meter__label">${pct}%</span>
      </div>
      <div style="font-size:0.72rem;color:var(--ink-muted);margin-top:2px;">${band} risk</div>
    `;
  }

  function rowHtml(emp) {
    return `
      <tr>
        <td>${emp.EmployeeID}</td>
        <td>${emp.Department}</td>
        <td>${emp.JobRole}</td>
        <td>${emp.Age}</td>
        <td>${emp.YearsAtCompany}</td>
        <td>₹${Number(emp.MonthlyIncome).toLocaleString("en-IN")}</td>
        <td>${emp.OverTime}</td>
        <td>${riskMeterHtml(emp.leave_probability, emp.risk_band)}</td>
      </tr>
    `;
  }

  function render(list) {
    const body = document.getElementById("atRiskBody");
    const count = document.getElementById("atRiskCount");
    if (!list.length) {
      body.innerHTML = `<tr><td colspan="8" class="table-empty">No employees match your search.</td></tr>`;
    } else {
      body.innerHTML = list.map(rowHtml).join("");
    }
    count.textContent = `${list.length} shown`;
  }

  function filter(query) {
    const q = query.trim().toLowerCase();
    if (!q) return employees;
    return employees.filter((e) =>
      [e.EmployeeID, e.Department, e.JobRole].join(" ").toLowerCase().includes(q)
    );
  }

  async function load() {
    const body = document.getElementById("atRiskBody");
    body.innerHTML = `<tr><td colspan="8" class="table-empty">Loading…</td></tr>`;
    try {
      const data = await Api.get("/at-risk?limit=40");
      employees = data.employees;
      render(employees);
    } catch (err) {
      body.innerHTML = `<tr><td colspan="8" class="table-empty">Couldn't load at-risk list: ${err.message}</td></tr>`;
    }
  }

  function init() {
    document.getElementById("atRiskSearch").addEventListener("input", (e) => {
      render(filter(e.target.value));
    });
  }

  return { load, init };
})();
