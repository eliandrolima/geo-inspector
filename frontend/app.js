const form = document.querySelector("#audit-form");
const urlInput = document.querySelector("#url");
const statusEl = document.querySelector("#status");
const errorEl = document.querySelector("#error");
const resultEl = document.querySelector("#result");
const scoreEl = document.querySelector("#score");
const classificationEl = document.querySelector("#classification");
const summaryEl = document.querySelector("#summary");
const strengthsEl = document.querySelector("#strengths");
const criticalEl = document.querySelector("#critical-findings");
const quickWinsEl = document.querySelector("#quick-wins");
const breakdownEl = document.querySelector("#breakdown");
const findingsEl = document.querySelector("#findings");
const jsonLink = document.querySelector("#download-json");
const markdownLink = document.querySelector("#download-markdown");

const categoryLabels = {
  crawlability_access: "Rastreabilidade e acesso",
  technical_structure: "Estrutura técnica e semântica",
  clarity_answerability: "Clareza e capacidade de resposta",
  authority_trust: "Autoridade e confiabilidade",
  evidence_citability: "Evidências, fontes e citabilidade",
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearState();
  setLoading(true);

  try {
    const response = await fetch("/api/v1/audits", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: urlInput.value }),
    });
    const payload = await response.json();
    if (!response.ok) {
      errorEl.textContent = payload.error || "A auditoria não pôde ser concluída.";
      if (payload.report) {
        renderReport(payload.report);
      }
      return;
    }
    renderReport(payload);
  } catch (error) {
    errorEl.textContent = "Falha ao comunicar com a API local.";
  } finally {
    setLoading(false);
  }
});

function clearState() {
  statusEl.textContent = "";
  errorEl.textContent = "";
  resultEl.classList.add("hidden");
  clearList(strengthsEl);
  clearList(criticalEl);
  clearList(quickWinsEl);
  clearNode(breakdownEl);
  clearNode(findingsEl);
}

function setLoading(isLoading) {
  const button = form.querySelector("button");
  button.disabled = isLoading;
  statusEl.textContent = isLoading ? "Processando auditoria..." : "";
}

function renderReport(report) {
  resultEl.classList.remove("hidden");
  if (report.status === "error" && !errorEl.textContent) {
    errorEl.textContent = report.summary || "A auditoria não pôde ser concluída.";
  }
  scoreEl.textContent = `${Number(report.geo_score || 0).toFixed(1)}/100`;
  classificationEl.textContent = report.classification || "-";
  summaryEl.textContent = report.summary || "";
  renderTextList(strengthsEl, report.strengths || []);
  renderCriticalFindings(report.critical_findings || []);
  renderTextList(quickWinsEl, report.quick_wins || []);
  renderBreakdown(report.score_breakdown || {});
  renderFindings(report.findings || []);

  const executionId = encodeURIComponent(report.execution_id);
  jsonLink.href = `/api/v1/reports/${executionId}/download?format=json`;
  markdownLink.href = `/api/v1/reports/${executionId}/download?format=markdown`;
}

function renderTextList(target, items) {
  clearList(target);
  const values = items.length ? items : ["Nenhum item registrado."];
  for (const item of values) {
    const li = document.createElement("li");
    li.textContent = String(item);
    target.appendChild(li);
  }
}

function renderCriticalFindings(items) {
  clearList(criticalEl);
  if (!items.length) {
    const li = document.createElement("li");
    li.textContent = "Nenhum achado crítico registrado.";
    criticalEl.appendChild(li);
    return;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = `${item.criterion}: ${item.evidence?.observed || ""}`;
    criticalEl.appendChild(li);
  }
}

function renderBreakdown(breakdown) {
  clearNode(breakdownEl);
  for (const [category, score] of Object.entries(breakdown)) {
    const row = document.createElement("div");
    row.className = "breakdown-row";

    const label = document.createElement("span");
    label.textContent = categoryLabels[category] || category;

    const value = document.createElement("strong");
    value.textContent = Number(score).toFixed(1);

    const meter = document.createElement("div");
    meter.className = "meter";
    const fill = document.createElement("span");
    fill.style.width = `${Math.max(0, Math.min(100, Number(score)))}%`;
    meter.appendChild(fill);

    row.appendChild(label);
    row.appendChild(value);
    breakdownEl.appendChild(row);
    breakdownEl.appendChild(meter);
  }
}

function renderFindings(findings) {
  clearNode(findingsEl);
  for (const item of findings) {
    const block = document.createElement("article");
    block.className = "finding";

    const title = document.createElement("div");
    title.className = "finding-title";
    title.textContent = item.criterion || "Achado";

    const meta = document.createElement("div");
    meta.className = "finding-meta";
    meta.textContent = `${categoryLabels[item.category] || item.category} · ${item.status} · ${item.priority}`;

    const evidence = document.createElement("p");
    evidence.textContent = item.evidence?.observed || "";

    const recommendation = document.createElement("p");
    recommendation.textContent = item.recommendation || "";

    block.appendChild(title);
    block.appendChild(meta);
    block.appendChild(evidence);
    block.appendChild(recommendation);
    findingsEl.appendChild(block);
  }
}

function clearList(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

function clearNode(node) {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}
