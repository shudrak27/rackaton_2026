// Keep metric classes and missing values explicit when reading older exports.
export const finite = (value) => typeof value === "number" && Number.isFinite(value);
const probability = (value) => finite(value) && value >= 0 && value <= 1;

export function metric(d, name, scorer = "model") {
  const value = d?.test_metrics?.find((row) => row.metric === name)?.[scorer];
  return finite(value) ? value : null;
}

export function testPrevalence(d) {
  const random = d?.ranking_quality?.find((row) => row.scorer === "random")?.ap_attendance
    ?? metric(d, "ap_attendance_random");
  if (probability(random)) return { attendance: random, nonAttendance: 1 - random };
  // Only use complete test deciles, never the all-years overall attendance rate.
  const rows = d?.deciles || [];
  const total = rows.reduce((sum, row) => sum + (finite(row.n) ? row.n : 0), 0);
  if (!total || total !== d?.meta?.n_test || rows.some((row) => !probability(row.non_attendance))) {
    return { attendance: null, nonAttendance: null };
  }
  const nonAttendance = rows.reduce((sum, row) => sum + row.n * row.non_attendance, 0) / total;
  return { attendance: 1 - nonAttendance, nonAttendance };
}

export function benchmarks(d) {
  const prevalence = testPrevalence(d);
  const ranking = (scorer) => d?.ranking_quality?.find((row) => row.scorer === scorer);
  return [
    { scorer: "Chance", auc: 0.5, apNonAttendance: prevalence.nonAttendance, apAttendance: prevalence.attendance },
    ...[["Baseline", "baseline", "rule"], ["Model", "model", "model"]].map(([scorer, key, rankKey]) => ({
      scorer,
      auc: metric(d, "roc_auc", key) ?? (finite(ranking(rankKey)?.roc_auc) ? ranking(rankKey).roc_auc : null),
      apNonAttendance: metric(d, "average_precision", key),
      apAttendance: metric(d, "ap_attendance", key)
        ?? (finite(ranking(rankKey)?.ap_attendance) ? ranking(rankKey).ap_attendance : null),
    })),
  ];
}

export function rocPoints(rows, series) {
  // Repeated FPRs form vertical segments: retaining them preserves the ROC geometry.
  return (rows || []).filter((row) => probability(row.fpr) && probability(row.tpr))
    .map((row) => ({ ...row, series })).sort((a, b) => a.fpr - b.fpr);
}

export function capacityRows(d) {
  const byShare = new Map();
  for (const scorer of ["model", "baseline"]) {
    for (const row of d?.gain?.[scorer] || []) {
      if (!probability(row.top_share) || row.top_share === 0) continue;
      const key = row.top_share.toFixed(8);
      const out = byShare.get(key) || { share: row.top_share };
      out[`${scorer}Precision`] = probability(row.attendance_in_top) ? 1 - row.attendance_in_top : null;
      out[`${scorer}Recall`] = probability(row.captured) ? row.captured : null;
      byShare.set(key, out);
    }
  }
  return [...byShare.values()].sort((a, b) => a.share - b.share);
}

export function calibrationRows(d) {
  return (d?.calibration || []).filter((row) => probability(row.predicted)
    && probability(row.observed) && finite(row.n) && row.n > 0)
    .map((row) => ({ ...row })).sort((a, b) => a.predicted - b.predicted);
}

export function groupRows(d, key) {
  return (d?.fairness?.[key] || []).filter((row) => finite(row.n) && row.n > 0)
    .map((row) => ({ ...row, label: String(row[key] ?? "Unknown"),
      gap: probability(row.mean_risk) && probability(row.non_attendance)
        ? row.mean_risk - row.non_attendance : null,
    })).sort((a, b) => key === "age_band"
      ? a.label.localeCompare(b.label, undefined, { numeric: true }) : b.n - a.n);
}
