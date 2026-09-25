// Renders the site from data/*.json and research/*.md.
const DOCS = [
  ["Physical-AI brief", "/research/physical_ai_research.md"],
  ["Kimi review", "/research/kimi_research.md"],
  ["XLeRobot BOM", "/research/xlerobot_official_bom.md"],
];

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const money = (n, cur = "CAD") => (cur === "USD" ? "US$" : "$") + Number(n).toLocaleString("en-CA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const sum = (rows) => rows.reduce((t, r) => t + r.price * r.qty, 0);

function table(el, rows, cur, extra = []) {
  const head = `<thead><tr><th>Item</th><th>Product</th><th class="num">Unit</th><th class="num">Qty</th><th class="num">Total</th></tr></thead>`;
  const body = rows
    .map((r) => `<tr><td>${esc(r.item)}</td><td><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.product)}</a><div class="note">${esc(r.notes)}</div></td>`
      + `<td class="num">${money(r.price, cur)}</td><td class="num">${r.qty}</td><td class="num">${money(r.price * r.qty, cur)}</td></tr>`)
    .join("");
  const foot = extra.map(([label, val, cls]) => `<tr class="${cls}"><td colspan="4">${label}</td><td class="num">${val}</td></tr>`).join("");
  el.innerHTML = head + `<tbody>${body}${foot}</tbody>`;
}

async function load() {
  const [bom, road] = await Promise.all([fetch("/data/bom.json").then((r) => r.json()), fetch("/data/roadmap.json").then((r) => r.json())]);
  const p1 = bom.phase1, p2 = bom.phase2;
  const core = sum(p1.core), opt = sum(p1.optional), taxed = core * (1 + bom.tax_rate);
  const p2usd = sum(p2.items);
  const cards = road.steps.flatMap((st) => [st.hardware, st.software]);
  const done = cards.filter((c) => c.done).length;

  $("stats").innerHTML = [
    [money(taxed), "Hands cart incl. tax"],
    [money(bom.budget_cad - taxed), "Under the $" + bom.budget_cad + " budget"],
    [money(p2usd, "USD"), "Full robot (draft)"],
    [`${done}/${cards.length}`, "Plan steps done"],
  ].map(([v, k]) => `<div class="stat"><div class="v">${v}</div><div class="k">${k}</div></div>`).join("");

  renderPlan(road);

  $("parts-updated").textContent = `Prices checked on the linked pages on ${bom.updated}. They change, so re-check before ordering.`;
  $("p1-title").textContent = p1.title;
  table($("p1-core"), p1.core, "CAD", [
    ["Subtotal", money(core), "sub"],
    [`HST ${Math.round(bom.tax_rate * 100)}%`, money(core * bom.tax_rate), "sub"],
    ["Total", money(taxed), "total"],
  ]);
  table($("p1-opt"), p1.optional, "CAD", [["With sensors, incl. tax", money((core + opt) * (1 + bom.tax_rate)), "total"]]);
  table($("p1-alt"), p1.alternatives, "CAD");
  $("p2-title").textContent = p2.title;
  table($("p2"), p2.items, "USD", [
    ["Subtotal", money(p2usd, "USD"), "sub"],
    [`≈ CAD at ${bom.usd_to_cad}`, money(p2usd * bom.usd_to_cad), "total"],
  ]);
}

function card(c, lane) {
  const img = c.image ? `<img src="${esc(c.image)}" alt="${esc(c.title)}" loading="lazy">` : "";
  return `<div class="card ${lane}${c.done ? " done" : ""}">${img}<div class="ct"><span class="tick"></span>${esc(c.title)}</div><div class="cx">${esc(c.text)}</div></div>`;
}

function renderPlan(road) {
  const L = road.lanes;
  $("lanes-head").innerHTML = ["hardware", "software"]
    .map((k) => `<div class="lane-label ${k}"><b>${esc(L[k].name)}</b> · ${esc(L[k].owner)}</div>`).join("");
  $("plan-progress").textContent = `16 weeks from ${road.start}`;
  $("plan-list").innerHTML = road.steps
    .map((st) => `<li class="${st.hardware.done && st.software.done ? "done" : ""}">${card(st.hardware, "hardware")}<div class="wk"><span>Wk ${esc(st.weeks)}</span></div>${card(st.software, "software")}</li>`)
    .join("");
}

async function showDoc(i) {
  document.querySelectorAll("#doc-tabs button").forEach((b, j) => b.setAttribute("aria-selected", i === j));
  const md = await fetch(DOCS[i][1]).then((r) => (r.ok ? r.text() : "Document not found."));
  $("doc").innerHTML = marked.parse(md);
  $("doc").querySelectorAll("a").forEach((a) => { a.target = "_blank"; a.rel = "noopener"; });
}

$("doc-tabs").innerHTML = DOCS.map(([name], i) => `<button role="tab" data-i="${i}">${esc(name)}</button>`).join("");
$("doc-tabs").addEventListener("click", (e) => e.target.dataset.i && showDoc(+e.target.dataset.i));
load();
showDoc(0);
