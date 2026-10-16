// Two-proportion sample size, same formula as screening.experiment.power.n_per_group.

// Inverse standard normal CDF (Acklam's rational approximation, |error| < 1.2e-9).
function normInv(p) {
  const a = [-39.69683028665376, 220.9460984245205, -275.9285104469687, 138.357751867269, -30.66479806614716, 2.506628277459239];
  const b = [-54.47609879822406, 161.5858368580409, -155.6989798598866, 66.80131188771972, -13.28068155288572];
  const c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
  const d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996, 3.754408661907416];
  const lo = 0.02425;
  if (p < lo) {
    const q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  if (p > 1 - lo) return -normInv(1 - p);
  const q = p - 0.5;
  const r = q * q;
  return ((((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q) /
    (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
}

export function nPerGroup(pControl, mde, alpha = 0.05, power = 0.8, ratio = 1) {
  const pT = pControl + mde;
  if (!(pControl > 0 && pControl < 1 && pT > 0 && pT < 1 && mde > 0)) return null;
  const z = normInv(1 - alpha / 2) + normInv(power);
  const variance = pControl * (1 - pControl) + (pT * (1 - pT)) / ratio;
  return Math.ceil((z * z * variance) / (mde * mde));
}
