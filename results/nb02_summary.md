# Notebook 2 summary (amendment A11 — added after review)
python 3.9.6 | numpy 2.0.2 | pandas 2.3.3 | macOS-15.6.1-arm64-arm-64bit | workers 10
protocol hash 1efa0b18cd1078c6 | started 2026-10-22 18:37

## 1. Raw Favorita perishable panel
days 2015-08-01 .. 2017-08-15 | train.csv rows read 125,497,040
store-items 27313 | stores 54 | items 682
              store_items  items  mean_sales  share_selling
family                                                     
BREAD/BAKERY         4970    134        3.50           0.83
DAIRY               10642    242        3.26           0.84
PRODUCE             11701    306        5.06           0.85
variance/mean of daily sales (Poisson = 1), quantiles: q25=2.08, q50=3.34, q75=6.00

## 2. Replication states
family median prices used (Favorita has no prices): BREAD/BAKERY 2.97, DAIRY 3.56, PRODUCE 2.73
eligible store-items: 20224 (of 27313); stores 53; items 660
built in 5s
states 3000 | store-items 2764 | items 636 | stores 53 | dates 2016-02-17 .. 2017-07-15

## 3. Original 500 states (twin demand) with OCBA and extended reference
original/base: 1000 state-horizons in 153s
original/low: 1000 state-horizons in 94s
original/high: 1000 state-horizons in 528s

## 4. Replication (raw Favorita, empirical demand)
replication/base: 6000 state-horizons in 1017s
replication/low: 3000 state-horizons in 396s
replication/high: 3000 state-horizons in 1385s

### Original 500 states (twin demand)
reference adequate: base/H7 0.998, base/H14 1.000, high/H7 0.970, high/H14 0.998, low/H7 0.998, low/H14 1.000 | candidate-edge: base/H7 0.008, base/H14 0.006, high/H7 0.024, high/H14 0.010, low/H7 0.002, low/H14 0.002 | near-tied: base/H7 0.314, base/H14 0.472, high/H7 0.372, high/H14 0.546, low/H7 0.176, low/H14 0.284

Original 500 states (twin demand) | ratio base | H 7 | n states 500
share of states with regret <= 0.5%:
method   ocba  seq_elim  uniform
N                               
10      0.704     0.704    0.704
25      0.724     0.804    0.794
50      0.808     0.882    0.848
100     0.904     0.944    0.910
250     0.964     0.978    0.968
500     0.970     0.982    0.986
1000    0.982     0.982    0.998
rollouts used per candidate (ratio of totals):
method    ocba  seq_elim  uniform
N                                
10        10.0      10.0     10.0
25        25.0      24.0     25.0
50        50.0      39.0     50.0
100      100.0      62.0    100.0
250      250.0     108.0    250.0
500      500.0     158.0    500.0
1000    1000.0     221.0   1000.0
N required (>=95% within 0.5%): uniform: all 250, BREA 250, PROD 250, DAIR 100 | seq_elim: all 250, BREA 100, PROD 250, DAIR 50 | ocba: all 250, BREA 250, PROD 500, DAIR 250
adequate-reference subset, share ok at N=100/250/500: uniform: 0.910/0.968/0.986 | seq_elim: 0.944/0.978/0.982 | ocba: 0.904/0.964/0.970

Original 500 states (twin demand) | ratio base | H 14 | n states 500
share of states with regret <= 0.5%:
method   ocba  seq_elim  uniform
N                               
10      0.718     0.718    0.718
25      0.742     0.828    0.810
50      0.822     0.886    0.850
100     0.910     0.936    0.882
250     0.960     0.976    0.940
500     0.984     0.988    0.970
1000    0.990     0.990    0.998
rollouts used per candidate (ratio of totals):
method    ocba  seq_elim  uniform
N                                
10        10.0      10.0     10.0
25        25.0      24.0     25.0
50        50.0      44.0     50.0
100      100.0      76.0    100.0
250      250.0     148.0    250.0
500      500.0     237.0    500.0
1000    1000.0     354.0   1000.0
N required (>=95% within 0.5%): uniform: all 500, BREA 250, PROD 1000, DAIR 500 | seq_elim: all 250, BREA 100, PROD 500, DAIR 100 | ocba: all 250, BREA 500, PROD 500, DAIR 100
adequate-reference subset, share ok at N=100/250/500: uniform: 0.882/0.940/0.970 | seq_elim: 0.936/0.976/0.988 | ocba: 0.910/0.960/0.984

Original 500 states (twin demand) | ratio high | H 7 | n states 500
share of states with regret <= 0.5%:
method   ocba  seq_elim  uniform
N                               
10      0.618     0.618    0.618
25      0.602     0.712    0.706
50      0.704     0.812    0.762
100     0.826     0.870    0.846
250     0.918     0.930    0.910
500     0.950     0.948    0.958
1000    0.960     0.956    0.970
rollouts used per candidate (ratio of totals):
method    ocba  seq_elim  uniform
N                                
10        10.0      10.0     10.0
25        25.0      24.0     25.0
50        50.0      42.0     50.0
100      100.0      69.0    100.0
250      250.0     133.0    250.0
500      500.0     207.0    500.0
1000    1000.0     311.0   1000.0
N required (>=95% within 0.5%): uniform: all 500, BREA 500, PROD >1000, DAIR 100 | seq_elim: all 1000, BREA 500, PROD 1000, DAIR 100 | ocba: all 500, BREA >1000, PROD >1000, DAIR 250
adequate-reference subset, share ok at N=100/250/500: uniform: 0.862/0.920/0.965 | seq_elim: 0.880/0.938/0.951 | ocba: 0.837/0.926/0.957

Original 500 states (twin demand) | ratio high | H 14 | n states 500
share of states with regret <= 0.5%:
method   ocba  seq_elim  uniform
N                               
10      0.604     0.604    0.604
25      0.630     0.690    0.698
50      0.712     0.760    0.718
100     0.816     0.842    0.798
250     0.896     0.918    0.852
500     0.942     0.968    0.934
1000    0.972     0.976    0.958
rollouts used per candidate (ratio of totals):
method    ocba  seq_elim  uniform
N                                
10        10.0      10.0     10.0
25        25.0      24.0     25.0
50        50.0      46.0     50.0
100      100.0      86.0    100.0
250      250.0     187.0    250.0
500      500.0     320.0    500.0
1000    1000.0     515.0   1000.0
N required (>=95% within 0.5%): uniform: all 1000, BREA 500, PROD >1000, DAIR 500 | seq_elim: all 500, BREA 250, PROD 1000, DAIR 500 | ocba: all 1000, BREA 1000, PROD 1000, DAIR 250
adequate-reference subset, share ok at N=100/250/500: uniform: 0.798/0.852/0.934 | seq_elim: 0.842/0.918/0.968 | ocba: 0.816/0.896/0.942

Original 500 states (twin demand) | ratio low | H 7 | n states 500
share of states with regret <= 0.5%:
method   ocba  seq_elim  uniform
N                               
10      0.806     0.806    0.806
25      0.850     0.910    0.904
50      0.920     0.960    0.938
100     0.972     0.984    0.966
250     0.986     0.984    0.992
500     0.994     0.984    1.000
1000    0.994     0.984    1.000
rollouts used per candidate (ratio of totals):
method    ocba  seq_elim  uniform
N                                
10        10.0      10.0     10.0
25        25.0      23.0     25.0
50        50.0      33.0     50.0
100      100.0      45.0    100.0
250      250.0      63.0    250.0
500      500.0      83.0    500.0
1000    1000.0     107.0   1000.0
N required (>=95% within 0.5%): uniform: all 100, BREA 50, PROD 250, DAIR 100 | seq_elim: all 50, BREA 25, PROD 50, DAIR 100 | ocba: all 100, BREA 50, PROD 100, DAIR 100
adequate-reference subset, share ok at N=100/250/500: uniform: 0.966/0.992/1.000 | seq_elim: 0.984/0.984/0.984 | ocba: 0.972/0.986/0.994

Original 500 states (twin demand) | ratio low | H 14 | n states 500
share of states with regret <= 0.5%:
method   ocba  seq_elim  uniform
N                               
10      0.758     0.758    0.758
25      0.840     0.904    0.884
50      0.900     0.952    0.920
100     0.956     0.984    0.956
250     0.990     1.000    0.984
500     0.992     1.000    0.996
1000    0.994     1.000    1.000
rollouts used per candidate (ratio of totals):
method    ocba  seq_elim  uniform
N                                
10        10.0      10.0     10.0
25        25.0      24.0     25.0
50        50.0      39.0     50.0
100      100.0      59.0    100.0
250      250.0      94.0    250.0
500      500.0     129.0    500.0
1000    1000.0     176.0   1000.0
N required (>=95% within 0.5%): uniform: all 100, BREA 100, PROD 250, DAIR 50 | seq_elim: all 50, BREA 50, PROD 100, DAIR 25 | ocba: all 100, BREA 100, PROD 250, DAIR 50
adequate-reference subset, share ok at N=100/250/500: uniform: 0.956/0.984/0.996 | seq_elim: 0.984/1.000/1.000 | ocba: 0.956/0.990/0.992

### Replication on raw Favorita (empirical demand)
reference adequate: base/H7 0.998, base/H14 1.000, high/H14 0.993, low/H14 1.000 | candidate-edge: base/H7 0.025, base/H14 0.010, high/H14 0.020, low/H14 0.004 | near-tied: base/H7 0.284, base/H14 0.317, high/H14 0.407, low/H14 0.197

Replication on raw Favorita (empirical demand) | ratio base | H 7 | n states 3000
share of states with regret <= 0.5%:
method   ocba  seq_elim  uniform
N                               
10      0.707     0.707    0.707
25      0.687     0.816    0.811
50      0.765     0.891    0.867
100     0.848     0.938    0.907
250     0.917     0.968    0.962
500     0.947     0.977    0.980
1000    0.963     0.979    0.990
rollouts used per candidate (ratio of totals):
method    ocba  seq_elim  uniform
N                                
10        10.0      10.0     10.0
25        25.0      24.0     25.0
50        50.0      40.0     50.0
100      100.0      63.0    100.0
250      250.0     108.0    250.0
500      500.0     158.0    500.0
1000    1000.0     222.0   1000.0
N required (>=95% within 0.5%): uniform: all 250, BREA 250, PROD 500, DAIR 250 | seq_elim: all 250, BREA 250, PROD 250, DAIR 250 | ocba: all 1000, BREA 500, PROD >1000, DAIR 500
adequate-reference subset, share ok at N=100/250/500: uniform: 0.908/0.963/0.981 | seq_elim: 0.938/0.969/0.977 | ocba: 0.848/0.918/0.949

Replication on raw Favorita (empirical demand) | ratio base | H 14 | n states 3000
share of states with regret <= 0.5%:
method   ocba  seq_elim  uniform
N                               
10      0.710     0.710    0.710
25      0.720     0.807    0.794
50      0.787     0.891    0.859
100     0.883     0.946    0.911
250     0.941     0.982    0.963
500     0.966     0.987    0.983
1000    0.974     0.988    0.995
rollouts used per candidate (ratio of totals):
method    ocba  seq_elim  uniform
N                                
10        10.0      10.0     10.0
25        25.0      24.0     25.0
50        50.0      41.0     50.0
100      100.0      67.0    100.0
250      250.0     120.0    250.0
500      500.0     177.0    500.0
1000    1000.0     254.0   1000.0
N required (>=95% within 0.5%): uniform: all 250, BREA 250, PROD 500, DAIR 250 | seq_elim: all 250, BREA 100, PROD 250, DAIR 100 | ocba: all 500, BREA 500, PROD 1000, DAIR 250
adequate-reference subset, share ok at N=100/250/500: uniform: 0.911/0.963/0.983 | seq_elim: 0.946/0.982/0.987 | ocba: 0.883/0.941/0.966

Replication on raw Favorita (empirical demand) | ratio high | H 14 | n states 3000
share of states with regret <= 0.5%:
method   ocba  seq_elim  uniform
N                               
10      0.599     0.599    0.599
25      0.629     0.692    0.687
50      0.685     0.791    0.759
100     0.782     0.872    0.826
250     0.882     0.935    0.897
500     0.919     0.957    0.932
1000    0.955     0.972    0.969
rollouts used per candidate (ratio of totals):
method    ocba  seq_elim  uniform
N                                
10        10.0      10.0     10.0
25        25.0      24.0     25.0
50        50.0      45.0     50.0
100      100.0      80.0    100.0
250      250.0     163.0    250.0
500      500.0     263.0    500.0
1000    1000.0     407.0   1000.0
N required (>=95% within 0.5%): uniform: all 1000, BREA 500, PROD >1000, DAIR 1000 | seq_elim: all 500, BREA 250, PROD 1000, DAIR 250 | ocba: all 1000, BREA >1000, PROD >1000, DAIR 500
adequate-reference subset, share ok at N=100/250/500: uniform: 0.827/0.899/0.933 | seq_elim: 0.873/0.936/0.958 | ocba: 0.784/0.883/0.919

Replication on raw Favorita (empirical demand) | ratio low | H 14 | n states 3000
share of states with regret <= 0.5%:
method   ocba  seq_elim  uniform
N                               
10      0.790     0.790    0.790
25      0.822     0.892    0.880
50      0.905     0.952    0.926
100     0.957     0.981    0.959
250     0.982     0.989    0.989
500     0.987     0.990    0.996
1000    0.993     0.990    0.999
rollouts used per candidate (ratio of totals):
method    ocba  seq_elim  uniform
N                                
10        10.0      10.0     10.0
25        25.0      23.0     25.0
50        50.0      36.0     50.0
100      100.0      50.0    100.0
250      250.0      75.0    250.0
500      500.0      99.0    500.0
1000    1000.0     131.0   1000.0
N required (>=95% within 0.5%): uniform: all 100, BREA 50, PROD 250, DAIR 50 | seq_elim: all 50, BREA 50, PROD 100, DAIR 50 | ocba: all 100, BREA 100, PROD 250, DAIR 100
adequate-reference subset, share ok at N=100/250/500: uniform: 0.959/0.989/0.996 | seq_elim: 0.981/0.989/0.990 | ocba: 0.957/0.982/0.987
replication demand CV (std/mean over trailing 26 weeks), quantiles: q25=0.60, q50=0.77, q75=0.99

### 5. Wider-grid check (gap of best candidate to best of a 24-point grid, relative to J*)
               n  median     p95     max  share_over_0_5pct  grid_best_outside_range
set                                                                                 
original     100     0.0  0.0020  0.0055               0.01                      0.0
replication  100     0.0  0.0011  0.0069               0.01                      0.0

### 6. Measured end-to-end timing
50,000 decisions, N=1000, H=14, 10 workers: runs 293.3s, 286.7s, 295.6s (median 293.3s); includes problem build + candidate generation + scenario generation + simulation + selection