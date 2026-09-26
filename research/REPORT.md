# Calibration report

_Updated 2026-09-26 16:49 UTC_

```

==============================================================
  variant: blind    settled markets: 6
==============================================================

Forecast accuracy (lower is better)
  model  Brier 0.0699   log loss 0.2521
  market Brier 0.0718   log loss 0.2517

Paired difference (market Brier minus model Brier)
  mean +0.0020  stderr 0.0055  t +0.36

Calibration of the model
  bucket             n   predicted   realised
  0.0 - 0.2          2       0.020      0.000
  0.2 - 0.4          1       0.240      0.000
  0.4 - 0.6          1       0.480      1.000
  0.6 - 0.8          1       0.740      1.000
  0.8 - 1.0          1       0.850      1.000

Hypothetical P&L  (edge >= 0.10, confidence >= 0.00)
  no signals cleared the thresholds

--------------------------------------------------------------
  VERDICT: too early. 6 settled, want 100+.
--------------------------------------------------------------

```
