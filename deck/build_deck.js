// Builds Nostradamus_Executive_Summary.pptx from out/report.json.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require(path.join(process.env.PPTX_SKILL_DIR, "scripts", "apply_theme.js"));
const R = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "out", "report.json"), "utf8"));
const TESTS = process.env.TESTS || "?";
const M = R.model, EW = R.equal_workload;
const pct = (x, d = 1) => (x * 100).toFixed(d) + "%";
const n = (x) => Number(x).toLocaleString("en-US");
const baseRate180 = (M.live_notices_of_sale / 10 * 6) / R.borrowers;       // notices per 180 days per borrower
const lift = Math.round(M.precision / baseRate180);

const THEME = {
  name: "Nostradamus", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "14122B", lt1: "FFFFFF", dk2: "211E4A", lt2: "F0EEF8", accent1: "211E4A", accent2: "D9A441", accent3: "5B6BC0", accent4: "7D7A9C", accent5: "F1D9A0", accent6: "B8433A", hlink: "211E4A", folHlink: "5B6BC0" },
};
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "Nostradamus Executive Summary";
pres.author = "Christian Kouadio Kouassi";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const num = { x: 9.2, y: 5.2, w: 0.5, h: 0.3, fontSize: 10, color: C.accent4 };
pres.defineSlideMaster({ title: "DARK", background: { color: C.text2 }, objects: [], slideNumber: num });
pres.defineSlideMaster({
  title: "CONTENT", background: { color: C.background1 },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9.0, h: 0.8, fontSize: 24, bold: true, color: C.text2, fontFace: "Cambria", margin: 0, valign: "top", align: "left" }, text: "" } }],
  slideNumber: num,
});
const card = (s, x, y, w, h, name, fill) => s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: fill || C.background2 }, line: { color: fill || C.background2, width: 0 }, objectName: name });
const txt = (s, t, o) => s.addText(t, { margin: 0, isTextBox: true, ...o });

// 1 Title
let s = pres.addSlide({ masterName: "DARK" });
txt(s, "Nostradamus", { x: 0.7, y: 1.3, w: 8.6, h: 1.0, fontFace: "Cambria", fontSize: 54, bold: true, color: C.background1, objectName: "Title" });
txt(s, "A streaming pipeline that flags Dallas County, Plano and Frisco mortgage borrowers likely to face a foreclosure sale notice within 180 days", { x: 0.7, y: 2.4, w: 8.2, h: 1.1, fontSize: 20, color: C.background2, objectName: "Subtitle" });
txt(s, "Kafka-style stream  |  Iceberg  |  dbt  |  MetricFlow  |  Airflow  |  Snowflake design  |  Christian Kouadio Kouassi", { x: 0.7, y: 4.55, w: 8.6, h: 0.4, fontSize: 13, color: C.accent5, objectName: "Byline" });
s.addNotes("Nostradamus is a portfolio project built to practice the DataExpert.io Senior AI Analytics Engineer curriculum. All borrower data is synthetic.");

// 2 Summary and goal
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("Goal: find borrowers in trouble early enough for a servicer to offer help", { placeholder: "title" });
card(s, 0.5, 1.3, 4.35, 3.7, "GoalCard");
s.addText([
  { text: "What it is", options: { bold: true, color: C.text2, fontSize: 15, breakLine: true } },
  { text: "A pipeline that reads bank, credit, household-debt and mortgage servicing events as they arrive, keeps each borrower's state in event time, and scores every borrower at month close.", options: { breakLine: true } },
  { text: "Why it matters", options: { bold: true, color: C.text2, fontSize: 15, breakLine: true } },
  { text: "In Texas a sale can follow a notice of default in about six weeks (Property Code 51.002). The signals that predict a miss, overdrafts, closed accounts and rising debt, show up months earlier.", options: {} },
], { x: 0.7, y: 1.45, w: 3.95, h: 3.4, fontSize: 14, color: C.text1, paraSpaceAfter: 8, valign: "top", margin: 0, isTextBox: true, objectName: "GoalText" });
card(s, 5.1, 1.3, 4.4, 3.7, "ScopeCard", C.accent5);
s.addText([
  { text: "Built to show", options: { bold: true, color: C.text2, fontSize: 15, breakLine: true } },
  { text: "Streaming with late, duplicate and malformed events", options: { bullet: true, breakLine: true } },
  { text: "Write, audit, publish on Apache Iceberg", options: { bullet: true, breakLine: true } },
  { text: "dbt models and tests, one MetricFlow definition of each KPI", options: { bullet: true, breakLine: true } },
  { text: "Airflow dynamic task mapping, Terraform and Snowflake designs", options: { bullet: true, breakLine: true } },
  { text: "Honest scope", options: { bold: true, color: C.text2, fontSize: 15, breakLine: true } },
  { text: "All borrower events are synthetic. Foreclosure concerns owners, so the model scores borrowers, not tenants. No geographic features are used.", options: {} },
], { x: 5.3, y: 1.45, w: 4.0, h: 3.4, fontSize: 13, color: C.text1, paraSpaceAfter: 6, valign: "top", margin: 0, isTextBox: true, objectName: "ScopeText" });
s.addNotes("The bullets on the right are the curriculum topics this project exercises.");

// 3 End to end pipeline
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("The whole pipeline on one page, from source event to outreach list", { placeholder: "title" });
const boxes = [
  ["1 Sources", "Servicer, bank, credit bureau, data vendor", `${n(R.events_streamed)} synthetic events: payments, overdrafts, credit snapshots, household debt and liens, NOD, NOS, SALE`],
  ["2 Stream", "NostraLog (Kafka-style) / Azure Event Hubs", "4 partitions, offsets, consumer group, commit after process"],
  ["3 Processor", "Python stateful micro-batch", "Dedup by id, contract check, event-time state, 45 day lateness, watermark"],
  ["4 Lake", "Apache Iceberg (pyiceberg)", "Write, audit, publish by batch id. Bad batches never reach readers"],
  ["5 Warehouse", "DuckDB now, Snowflake Dynamic Tables by design", "dbt silver and gold, 29 tests, reconciled to Python"],
  ["6 Serve", "MetricFlow + alert queue", "Precision, lead time, alerts by city. Reasons per alert"],
];
const bw = 1.43, gap = 0.1, x0 = 0.4;
boxes.forEach(([t, p, d], i) => {
  const x = x0 + i * (bw + gap);
  card(s, x, 1.3, bw, 2.45, `Box${i + 1}`, i % 2 ? C.background2 : C.accent5);
  s.addText([
    { text: t, options: { bold: true, fontSize: 14, color: C.text2, breakLine: true } },
    { text: p, options: { bold: true, fontSize: 11, color: C.accent3, breakLine: true } },
    { text: d, options: { fontSize: 11, color: C.text1 } },
  ], { x: x + 0.07, y: 1.38, w: bw - 0.14, h: 2.3, valign: "top", margin: 0, paraSpaceAfter: 4, isTextBox: true, objectName: `BoxText${i + 1}` });
  if (i < boxes.length - 1) s.addText(">", { x: x + bw - 0.02, y: 2.35, w: gap + 0.04, h: 0.3, fontSize: 12, bold: true, color: C.accent2, align: "center", margin: 0, isTextBox: true, objectName: `Arrow${i + 1}` });
});
card(s, 0.4, 3.9, 9.2, 0.55, "OrchBand", C.text2);
txt(s, "Airflow: one mapped task per area (Dallas, Plano, Frisco), stage, audit, publish, then dbt build and MetricFlow validate. Safe to retry.", { x: 0.55, y: 3.9, w: 8.9, h: 0.55, fontSize: 11, color: C.background1, valign: "middle", objectName: "OrchText" });
card(s, 0.4, 4.55, 9.2, 0.55, "GovBand", C.accent3);
txt(s, `Controls: dead-letter table + drift alarm, 60 day alert cooldown, no geographic features, Terraform for Event Hubs, ADLS, Snowflake (not applied), CI, ${TESTS} tests.`, { x: 0.55, y: 4.55, w: 8.9, h: 0.55, fontSize: 11, color: C.background1, valign: "middle", objectName: "GovText" });
s.addNotes("DuckDB stands in for Snowflake and NostraLog for Kafka because the build sandbox had neither. The mapping is in docs/architecture.md.");

// 4 Data and events
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("The data: five event types, built to match what a servicer and a data vendor would send", { placeholder: "title" });
const rows = [
  ["Event", "Signal", "Source category"],
  ["payment", "days past due, amount paid", "Mortgage servicer"],
  ["overdraft", "amount, balance after, fee", "Bank"],
  ["credit_snapshot", "score, utilization, accounts closed in 12 months, other lates", "Credit bureau"],
  ["alt_signal", "overspend index, household loans, liens and judgments", "Data vendor (LexisNexis style)"],
  ["servicing_status", "NOD, NOS, SALE, CURE with Texas timing", "Servicer / county"],
];
s.addTable(rows.map((r, ri) => r.map((c) => ({ text: c, options: { bold: ri === 0, color: ri === 0 ? "FFFFFF" : "14122B", fill: { color: ri === 0 ? "211E4A" : ri % 2 ? "F0EEF8" : "FFFFFF" }, fontSize: 11 } }))),
  { x: 0.5, y: 1.3, w: 9.0, colW: [1.7, 4.3, 3.0], rowH: 0.36, border: { type: "none" }, objectName: "EventTable" });
card(s, 0.5, 3.65, 4.4, 1.4, "RealCard");
s.addText([{ text: "Real inputs", options: { bold: true, color: C.text2, fontSize: 13, breakLine: true } },
  { text: "Texas Property Code 51.002 timing, Dallas County Clerk notice file counts, ATTOM Texas foreclosure figures, ZIPs for Plano, Frisco and Dallas County.", options: {} }],
  { x: 0.65, y: 3.72, w: 4.1, h: 1.28, fontSize: 12, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "RealText" });
card(s, 5.1, 3.65, 4.4, 1.4, "SynthCard", C.accent5);
s.addText([{ text: "Synthetic, disclosed", options: { bold: true, color: C.text2, fontSize: 13, breakLine: true } },
  { text: `10,000 borrowers and every event about them. No licensed bureau or vendor data. ${n(R.duplicates_removed)} duplicates, late events and a renamed field were injected on purpose.`, options: {} }],
  { x: 5.25, y: 3.72, w: 4.1, h: 1.28, fontSize: 12, color: C.text1, valign: "top", margin: 0, isTextBox: true, objectName: "SynthText" });

// 5 Incidents
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("12 problems found while building, each fixed by a failing test first", { placeholder: "title" });
const inc = [
  ["Duplicate redelivery counted twice", "Drop by event id"],
  ["Late older payment overwrote newer", "Keep newest event time"],
  ["Offset committed before processing", "Commit after publish"],
  ["Renamed field read as zero, null borrower", "Data contract, dead letter, replay"],
  ["Retried batch stored twice", "Write, audit, publish by batch id"],
  ["Future leaked into training features", "Point-in-time features"],
  ["Very late event changed state unseen", "Park beyond 45 days"],
  ["Same borrower alerted every month", "60 day cooldown"],
  ["ZIP risk feature, a redlining proxy", "Removed, test guards it"],
  ["Future timestamp froze the watermark", "Quarantine beyond 62 days"],
  ["Unfinished windows labeled negative", "Train on matured windows"],
  ["SQL months shifted by time zone", "Bucket in UTC, 0 mismatches"],
];
s.addTable([[{ text: "#", options: { bold: true, color: "FFFFFF", fill: { color: "211E4A" } } }, { text: "Problem", options: { bold: true, color: "FFFFFF", fill: { color: "211E4A" } } }, { text: "Fix", options: { bold: true, color: "FFFFFF", fill: { color: "211E4A" } } }],
  ...inc.map(([a, b], i) => [i + 1, a, b].map((c) => ({ text: String(c), options: { color: "14122B", fontSize: 10.5, fill: { color: i % 2 ? "FFFFFF" : "F0EEF8" } } })))],
  { x: 0.5, y: 1.2, w: 9.0, colW: [0.5, 4.6, 3.9], rowH: 0.29, border: { type: "none" }, fontSize: 10.5, objectName: "IncidentTable" });
txt(s, "scripts/verify_incidents.py runs each pair in a clean checkout: the reproduce commit fails and the fix commit passes, 12 of 12.", { x: 0.5, y: 5.0, w: 8.6, h: 0.3, fontSize: 10.5, color: C.accent4, objectName: "IncidentNote" });

// 6 Results chart
s = pres.addSlide({ masterName: "CONTENT" });
s.addText("At the same outreach workload the model matches a simple rule, it does not beat it", { placeholder: "title" });
s.addChart(pres.charts.BAR, [
  { name: "Model", labels: ["Share of sales flagged first", "Precision"], values: [EW.model.recall * 100, EW.model.precision * 100] },
  { name: "Rule: 60+ days past due", labels: ["Share of sales flagged first", "Precision"], values: [EW.rule_dpd60.recall * 100, EW.rule_dpd60.precision * 100] },
], { x: 0.5, y: 1.3, w: 5.6, h: 3.8, barDir: "col", barGrouping: "clustered", chartColors: ["D9A441", "5B6BC0"], showLegend: true, legendPos: "b", legendFontFace: "+mn-lt", showValue: true, dataLabelFormatCode: "0.0", dataLabelPosition: "outEnd", dataLabelFontFace: "+mn-lt", dataLabelFontSize: 12,
  showTitle: true, title: "Percent, 718 borrowers alerted by each", titleFontFace: "+mn-lt", titleFontSize: 12, catAxisLabelFontFace: "+mn-lt", catAxisLabelFontSize: 11, valAxisHidden: true, valAxisMinVal: 0, valAxisMaxVal: 110, valGridLine: { style: "none" }, catGridLine: { style: "none" }, objectName: "CompareChart" });
card(s, 6.3, 1.4, 3.2, 3.6, "ReadCard");
s.addText([
  { text: "What this says", options: { bold: true, color: C.text2, fontSize: 15, breakLine: true } },
  { text: `The rule flagged ${EW.rule_dpd60.caught_before_notice} of ${M.live_notices_of_sale} sales first, the model ${EW.model.caught_before_notice}.`, options: { breakLine: true } },
  { text: "In this synthetic world strain shows up in the same months as missed payments, so a past-due rule is hard to beat. Real servicer data may differ, and that test has not been run.", options: { breakLine: true } },
  { text: "The finished value is the pipeline and its controls.", options: { bold: true, color: C.text2 } },
], { x: 6.45, y: 1.5, w: 2.9, h: 3.4, fontSize: 11.5, color: C.text1, paraSpaceAfter: 6, valign: "top", margin: 0, isTextBox: true, objectName: "ReadText" });

// 7 Conclusion KPIs
s = pres.addSlide({ masterName: "DARK" });
txt(s, "Conclusion: a reliable early-warning stream, with the impact measured", { x: 0.6, y: 0.35, w: 8.8, h: 0.8, fontFace: "Cambria", fontSize: 24, bold: true, color: C.background1, objectName: "ConclusionTitle" });
const kp = [
  [pct(M.recall), `of ${M.live_notices_of_sale} sale notices flagged first (${M.caught_before_notice} borrowers)`],
  [`${Math.round(M.median_lead_days)} days`, "median warning before the notice of sale"],
  [pct(M.precision), `precision on closed windows, about ${lift}x the base rate`],
  [pct(M.alerted_borrowers / R.borrowers), `of the book alerted, ${n(R.borrowers - M.alerted_borrowers)} borrowers need no review`],
  [n(R.duplicates_removed), "duplicate events removed, with none stored twice"],
  [`${n(R.replayed_from_dead_letter)}`, `of ${n(R.dead_letter["missing_payload:days_past_due"])} events lost to a field rename recovered by replay`],
];
kp.forEach(([big, label], i) => {
  const x = 0.6 + (i % 3) * 3.0, y = 1.3 + Math.floor(i / 3) * 1.55;
  card(s, x, y, 2.8, 1.4, `Kpi${i + 1}`, "2E2B63");
  txt(s, big, { x: x + 0.15, y: y + 0.08, w: 2.5, h: 0.6, fontFace: "Cambria", fontSize: 30, bold: true, color: C.accent2, objectName: `KpiValue${i + 1}` });
  txt(s, label, { x: x + 0.15, y: y + 0.72, w: 2.5, h: 0.62, fontSize: 11.5, color: C.background1, valign: "top", objectName: `KpiLabel${i + 1}` });
});
txt(s, "Synthetic data: figures show the pipeline works, not what a real servicer would see. Next: replay real servicer extracts, run Snowflake, test on a held-out real period.", { x: 0.6, y: 4.5, w: 8.8, h: 0.6, fontSize: 12, color: C.accent5, objectName: "ConclusionNote" });
s.addNotes("Base rate: about 1.2 percent of borrowers reach a notice of sale in a 180 day window in the synthetic book. Precision 34.7 percent is about 29 times that.");

(async () => {
  await pres.writeFile({ fileName: path.join(__dirname, "..", "Nostradamus_Executive_Summary.pptx") });
  await applyTheme(path.join(__dirname, "..", "Nostradamus_Executive_Summary.pptx"), THEME);
  console.log("built");
})();
