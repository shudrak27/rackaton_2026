import test from "node:test";
import assert from "node:assert/strict";
import { benchmarks, capacityRows, groupRows, metric, rocPoints, testPrevalence } from "./technical-data.js";

test("AP for the two positive classes is independent, with the correct chance reference", () => {
  const d = { meta: { attendance_overall: 0.3 }, test_metrics: [
    { metric: "average_precision", model: 0.947, baseline: 0.927 },
  ], ranking_quality: [
    { scorer: "random", ap_attendance: 0.192 },
    { scorer: "model", ap_attendance: 0.571 },
    { scorer: "rule", ap_attendance: 0.425 },
  ] };
  const [chance, baseline, model] = benchmarks(d);
  assert.equal(chance.apAttendance, 0.192);
  assert.equal(chance.apNonAttendance, 0.808);
  assert.equal(model.apAttendance, 0.571);
  assert.equal(model.apNonAttendance, 0.947);
  assert.equal(baseline.apAttendance, 0.425);
});

test("new attendance-only metrics do not silently become non-attendance AP", () => {
  const d = { test_metrics: [{ metric: "ap_attendance", model: 0.57 },
    { metric: "ap_attendance_random", model: 0.19 }] };
  const model = benchmarks(d).at(-1);
  assert.equal(model.apAttendance, 0.57);
  assert.equal(model.apNonAttendance, null);
  assert.equal(testPrevalence(d).attendance, 0.19);
});

test("missing or invalid results remain unavailable rather than becoming zeros", () => {
  assert.equal(metric({}, "roc_auc"), null);
  assert.equal(metric({ test_metrics: [{ metric: "roc_auc", model: NaN }] }, "roc_auc"), null);
  assert.equal(metric({ test_metrics: [{ metric: "brier", model: 0 }] }, "brier"), 0);
  assert.equal(benchmarks({}).at(-1).auc, null);
  assert.deepEqual(testPrevalence({ meta: { attendance_overall: 0.19 } }), { attendance: null, nonAttendance: null });
});

test("prevalence fallback is weighted and requires complete test deciles", () => {
  const d = { meta: { n_test: 100 }, deciles: [{ n: 25, non_attendance: 0.4 }, { n: 75, non_attendance: 0.8 }] };
  assert.equal(testPrevalence(d).nonAttendance, 0.7);
  assert.equal(testPrevalence({ ...d, meta: { n_test: 120 } }).nonAttendance, null);
});

test("ROC retains repeated x coordinates and does not change its source", () => {
  const points = [{ fpr: 0.2, tpr: 0.8 }, { fpr: 0, tpr: 0 }, { fpr: 0, tpr: 0.2 }];
  assert.deepEqual(rocPoints(points, "Model").map(({ fpr, tpr }) => [fpr, tpr]), [[0, 0], [0, 0.2], [0.2, 0.8]]);
  assert.equal(points[0].fpr, 0.2);
});

test("capacity matches scorers by share, never by position, and separates precision from recall", () => {
  const d = { gain: {
    model: [{ top_share: 0.1, captured: 0.12, attendance_in_top: 0.02 }],
    baseline: [{ top_share: 0.2, captured: 0.24, attendance_in_top: 0.04 },
      { top_share: 0.1, captured: 0.11, attendance_in_top: 0.03 }],
  } };
  const [a, b] = capacityRows(d);
  assert.equal(a.modelPrecision, 0.98);
  assert.equal(a.modelRecall, 0.12);
  assert.equal(a.baselinePrecision, 0.97);
  assert.equal(b.modelPrecision, undefined);
});

test("group calibration gap is prediction minus observed, preserving unavailable values", () => {
  const rows = groupRows({ fairness: { age_band: [
    { age_band: "60-64", n: 30, mean_risk: 0.8, non_attendance: 0.7 },
    { age_band: "45-49", n: 50, mean_risk: null, non_attendance: 0.5 },
  ] } }, "age_band");
  assert.equal(rows[0].label, "45-49");
  assert.equal(rows[0].gap, null);
  assert.ok(Math.abs(rows[1].gap - 0.1) < 1e-12);
});
