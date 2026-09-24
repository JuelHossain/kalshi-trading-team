# Calibration report

_Updated 2026-09-24 17:37 UTC_

```

==============================================================
  variant: blind    settled markets: 5
==============================================================

Forecast accuracy (lower is better)
  model  Brier 0.0793   log loss 0.2700
  market Brier 0.0855   log loss 0.2897

Paired difference (market Brier minus model Brier)
  mean +0.0062  stderr 0.0043  t +1.42

Calibration of the model
  bucket             n   predicted   realised
  0.0 - 0.2          2       0.020      0.000
  0.2 - 0.4          1       0.240      0.000
  0.4 - 0.6          1       0.480      1.000
  0.6 - 0.8          1       0.740      1.000

Hypothetical P&L  (edge >= 0.10, confidence >= 0.00)
  no signals cleared the thresholds

--------------------------------------------------------------
  VERDICT: too early. 5 settled, want 100+.
--------------------------------------------------------------

```
