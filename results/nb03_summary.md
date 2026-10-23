# Notebook 3 summary
python 3.9.6 | numpy 2.0.2 | pandas 2.3.3 | workers 10 | protocol hash 1efa0b18cd1078c6 | 2026-10-22 22:33
A twin/base: 81s
A twin/low: 47s
A twin/high: 341s
A favorita/base: 616s
A favorita/low: 388s
A favorita/high: 1704s
B window52/base: 703s

weeks of history actually used with the 52-week window: q5 31, q25 43, q50 52, q75 52, q95 52

### twin|base|H14  (states 500, clusters 157, K 2-12 mean 8.3, adequate 1.000, edge 0.006, near-tied 0.472)
N required: uniform 500 (BREA 250, PROD 1000, DAIR 500) | seq_elim 250 (BREA 100, PROD 500, DAIR 100) | ocba 250 (BREA 500, PROD 500, DAIR 100) | ocba_paired 250 (BREA 250, PROD 500, DAIR 250)
share within 0.5% [item-clustered 95% CI] / rollouts per candidate:
  N=  10: uniform 71.8 [67.4, 75.8] /10 | seq_elim 71.8 [67.7, 76.1] /10 | ocba 71.8 [67.7, 76.0] /10 | ocba_paired 71.8 [67.4, 76.0] /10
  N=  25: uniform 81.0 [77.2, 84.5] /25 | seq_elim 82.8 [79.2, 86.0] /24 | ocba 74.2 [70.2, 78.1] /25 | ocba_paired 72.0 [68.2, 76.2] /25
  N=  50: uniform 85.0 [81.6, 88.2] /50 | seq_elim 88.6 [85.5, 91.5] /44 | ocba 82.2 [78.9, 85.3] /50 | ocba_paired 82.2 [79.0, 85.4] /50
  N= 100: uniform 88.2 [84.8, 91.2] /100 | seq_elim 93.6 [91.5, 95.6] /76 | ocba 91.0 [88.4, 93.5] /100 | ocba_paired 91.0 [88.3, 93.7] /100
  N= 250: uniform 94.0 [92.0, 95.8] /250 | seq_elim 97.6 [96.2, 98.8] /148 | ocba 96.0 [94.2, 97.5] /250 | ocba_paired 96.0 [94.2, 97.6] /250
  N= 500: uniform 97.0 [95.6, 98.4] /500 | seq_elim 98.8 [97.8, 99.6] /237 | ocba 98.4 [97.2, 99.4] /500 | ocba_paired 98.0 [96.7, 99.1] /500
  N=1000: uniform 99.8 [99.4, 100.0] /1000 | seq_elim 99.0 [98.1, 99.8] /354 | ocba 99.0 [98.1, 99.8] /1000 | ocba_paired 99.4 [98.6, 100.0] /1000
paired difference vs uniform, all states (points, CI):
  seq_elim: N=50 +3.6 [0.8, 6.5] | N=100 +5.4 [2.7, 8.3] | N=250 +3.6 [1.8, 5.5] | N=500 +1.8 [0.4, 3.3] | N=1000 -0.8 [-1.7, -0.2]
  ocba: N=50 -2.8 [-6.2, 0.4] | N=100 +2.8 [-0.6, 6.2] | N=250 +2.0 [0.0, 3.8] | N=500 +1.4 [-0.2, 2.9] | N=1000 -0.8 [-1.6, -0.2]
  ocba_paired: N=50 -2.8 [-6.1, 0.4] | N=100 +2.8 [-0.4, 6.5] | N=250 +2.0 [0.0, 4.0] | N=500 +1.0 [-0.4, 2.4] | N=1000 -0.4 [-1.0, 0.0]

### twin|high|H14  (states 500, clusters 157, K 2-12 mean 8.3, adequate 0.998, edge 0.010, near-tied 0.546)
N required: uniform 1000 (BREA 500, PROD >1000, DAIR 500) | seq_elim 500 (BREA 250, PROD 1000, DAIR 500) | ocba 1000 (BREA 1000, PROD 1000, DAIR 250) | ocba_paired 500 (BREA 500, PROD 500, DAIR 500)
share within 0.5% [item-clustered 95% CI] / rollouts per candidate:
  N=  10: uniform 60.4 [55.8, 65.1] /10 | seq_elim 60.4 [55.5, 65.0] /10 | ocba 60.4 [55.6, 65.1] /10 | ocba_paired 60.4 [55.8, 64.9] /10
  N=  25: uniform 69.8 [65.5, 73.9] /25 | seq_elim 69.0 [64.8, 73.2] /24 | ocba 63.0 [58.8, 67.6] /25 | ocba_paired 61.6 [57.5, 65.9] /25
  N=  50: uniform 71.8 [67.5, 75.8] /50 | seq_elim 76.0 [72.3, 79.7] /46 | ocba 71.2 [67.1, 74.9] /50 | ocba_paired 72.0 [68.0, 76.0] /50
  N= 100: uniform 79.8 [76.0, 83.4] /100 | seq_elim 84.2 [80.8, 87.5] /86 | ocba 81.6 [77.6, 85.4] /100 | ocba_paired 77.8 [73.8, 81.7] /100
  N= 250: uniform 85.2 [82.2, 88.2] /250 | seq_elim 91.8 [89.1, 94.3] /187 | ocba 89.6 [86.7, 92.3] /250 | ocba_paired 90.0 [87.2, 92.7] /250
  N= 500: uniform 93.4 [91.1, 95.5] /500 | seq_elim 96.8 [95.3, 98.2] /320 | ocba 94.2 [91.9, 96.3] /500 | ocba_paired 95.8 [94.0, 97.4] /500
  N=1000: uniform 95.8 [94.0, 97.4] /1000 | seq_elim 97.6 [96.3, 98.8] /515 | ocba 97.2 [95.5, 98.6] /1000 | ocba_paired 97.6 [96.3, 98.8] /1000
paired difference vs uniform, all states (points, CI):
  seq_elim: N=50 +4.2 [1.6, 7.0] | N=100 +4.4 [1.0, 7.9] | N=250 +6.6 [3.6, 9.8] | N=500 +3.4 [1.2, 5.7] | N=1000 +1.8 [0.0, 3.5]
  ocba: N=50 -0.6 [-4.7, 3.5] | N=100 +1.8 [-1.9, 5.2] | N=250 +4.4 [1.0, 7.5] | N=500 +0.8 [-1.9, 3.4] | N=1000 +1.4 [-0.6, 3.4]
  ocba_paired: N=50 +0.2 [-3.5, 4.4] | N=100 -2.0 [-5.7, 1.8] | N=250 +4.8 [1.6, 7.9] | N=500 +2.4 [0.0, 4.9] | N=1000 +1.8 [0.0, 3.7]

### twin|low|H14  (states 500, clusters 157, K 2-12 mean 8.3, adequate 1.000, edge 0.002, near-tied 0.284)
N required: uniform 100 (BREA 100, PROD 250, DAIR 50) | seq_elim 50 (BREA 50, PROD 100, DAIR 25) | ocba 100 (BREA 100, PROD 250, DAIR 50) | ocba_paired 100 (BREA 50, PROD 250, DAIR 100)
share within 0.5% [item-clustered 95% CI] / rollouts per candidate:
  N=  10: uniform 75.8 [71.3, 80.0] /10 | seq_elim 75.8 [71.7, 80.0] /10 | ocba 75.8 [71.7, 79.8] /10 | ocba_paired 75.8 [71.7, 79.8] /10
  N=  25: uniform 88.4 [85.0, 91.4] /25 | seq_elim 90.4 [87.7, 93.0] /24 | ocba 84.0 [80.6, 87.5] /25 | ocba_paired 80.6 [76.9, 84.2] /25
  N=  50: uniform 92.0 [89.2, 94.7] /50 | seq_elim 95.2 [93.1, 97.2] /39 | ocba 90.0 [87.2, 92.7] /50 | ocba_paired 91.0 [88.3, 93.6] /50
  N= 100: uniform 95.6 [93.5, 97.5] /100 | seq_elim 98.4 [97.2, 99.4] /59 | ocba 95.6 [93.5, 97.5] /100 | ocba_paired 96.0 [94.1, 97.7] /100
  N= 250: uniform 98.4 [97.2, 99.4] /250 | seq_elim 100.0 [100.0, 100.0] /94 | ocba 99.0 [98.1, 99.8] /250 | ocba_paired 99.2 [98.4, 99.8] /250
  N= 500: uniform 99.6 [99.0, 100.0] /500 | seq_elim 100.0 [100.0, 100.0] /129 | ocba 99.2 [98.4, 99.8] /500 | ocba_paired 99.8 [99.4, 100.0] /500
  N=1000: uniform 100.0 [100.0, 100.0] /1000 | seq_elim 100.0 [100.0, 100.0] /176 | ocba 99.4 [98.6, 100.0] /1000 | ocba_paired 99.8 [99.4, 100.0] /1000
paired difference vs uniform, all states (points, CI):
  seq_elim: N=50 +3.2 [1.2, 5.4] | N=100 +2.8 [1.2, 4.5] | N=250 +1.6 [0.6, 2.7] | N=500 +0.4 [0.0, 1.0] | N=1000 +0.0 [0.0, 0.0]
  ocba: N=50 -2.0 [-5.0, 1.0] | N=100 +0.0 [-2.5, 2.4] | N=250 +0.6 [-0.6, 1.9] | N=500 -0.4 [-1.4, 0.6] | N=1000 -0.6 [-1.4, 0.0]
  ocba_paired: N=50 -1.0 [-3.9, 1.9] | N=100 +0.4 [-1.8, 2.7] | N=250 +0.8 [-0.6, 2.2] | N=500 +0.2 [-0.4, 0.9] | N=1000 -0.2 [-0.6, 0.0]

### favorita_w26|base|H14  (states 3000, clusters 636, K 1-12 mean 7.7, adequate 1.000, edge 0.010, near-tied 0.317)
N required: uniform 250 (BREA 250, PROD 500, DAIR 250) | seq_elim 250 (BREA 100, PROD 250, DAIR 100) | ocba 500 (BREA 500, PROD 1000, DAIR 250) | ocba_paired 500 (BREA 250, PROD 500, DAIR 250)
share within 0.5% [item-clustered 95% CI] / rollouts per candidate:
  N=  10: uniform 71.0 [69.3, 72.7] /10 | seq_elim 71.0 [69.2, 72.6] /10 | ocba 71.0 [69.3, 72.7] /10 | ocba_paired 71.0 [69.3, 72.7] /10
  N=  25: uniform 79.4 [77.9, 80.9] /25 | seq_elim 80.7 [79.3, 82.1] /24 | ocba 72.0 [70.2, 73.7] /25 | ocba_paired 69.8 [68.1, 71.5] /25
  N=  50: uniform 85.9 [84.7, 87.1] /50 | seq_elim 89.1 [87.9, 90.2] /41 | ocba 78.7 [77.2, 80.2] /50 | ocba_paired 78.9 [77.3, 80.4] /50
  N= 100: uniform 91.1 [90.0, 92.1] /100 | seq_elim 94.6 [93.8, 95.4] /67 | ocba 88.3 [87.1, 89.5] /100 | ocba_paired 88.1 [86.8, 89.3] /100
  N= 250: uniform 96.3 [95.6, 97.0] /250 | seq_elim 98.2 [97.7, 98.6] /120 | ocba 94.1 [93.1, 94.9] /250 | ocba_paired 94.8 [94.0, 95.7] /250
  N= 500: uniform 98.3 [97.8, 98.7] /500 | seq_elim 98.7 [98.3, 99.0] /177 | ocba 96.6 [95.9, 97.2] /500 | ocba_paired 97.2 [96.5, 97.8] /500
  N=1000: uniform 99.5 [99.2, 99.7] /1000 | seq_elim 98.8 [98.4, 99.2] /254 | ocba 97.4 [96.8, 98.0] /1000 | ocba_paired 98.5 [98.1, 99.0] /1000
paired difference vs uniform, all states (points, CI):
  seq_elim: N=50 +3.1 [2.1, 4.2] | N=100 +3.5 [2.6, 4.5] | N=250 +1.9 [1.2, 2.5] | N=500 +0.4 [-0.1, 0.9] | N=1000 -0.7 [-1.1, -0.3]
  ocba: N=50 -7.2 [-8.7, -5.6] | N=100 -2.7 [-4.0, -1.4] | N=250 -2.2 [-3.2, -1.2] | N=500 -1.7 [-2.5, -0.9] | N=1000 -2.1 [-2.8, -1.5]
  ocba_paired: N=50 -7.1 [-8.6, -5.5] | N=100 -3.0 [-4.2, -1.7] | N=250 -1.5 [-2.4, -0.5] | N=500 -1.1 [-1.8, -0.4] | N=1000 -1.0 [-1.4, -0.5]

### favorita_w26|high|H14  (states 3000, clusters 636, K 1-12 mean 7.7, adequate 0.993, edge 0.020, near-tied 0.407)
N required: uniform 1000 (BREA 500, PROD >1000, DAIR 1000) | seq_elim 500 (BREA 250, PROD 1000, DAIR 250) | ocba 1000 (BREA >1000, PROD >1000, DAIR 500) | ocba_paired 1000 (BREA 1000, PROD >1000, DAIR 500)
share within 0.5% [item-clustered 95% CI] / rollouts per candidate:
  N=  10: uniform 59.9 [58.0, 61.8] /10 | seq_elim 59.9 [57.9, 61.7] /10 | ocba 59.9 [58.0, 61.7] /10 | ocba_paired 59.9 [58.0, 61.9] /10
  N=  25: uniform 68.7 [66.7, 70.4] /25 | seq_elim 69.2 [67.4, 70.9] /24 | ocba 62.9 [61.1, 64.7] /25 | ocba_paired 61.1 [59.3, 62.9] /25
  N=  50: uniform 75.9 [74.3, 77.4] /50 | seq_elim 79.1 [77.6, 80.7] /45 | ocba 68.5 [66.8, 70.2] /50 | ocba_paired 68.0 [66.2, 69.8] /50
  N= 100: uniform 82.6 [81.2, 84.0] /100 | seq_elim 87.2 [85.8, 88.4] /80 | ocba 78.2 [76.6, 79.7] /100 | ocba_paired 77.9 [76.3, 79.5] /100
  N= 250: uniform 89.7 [88.6, 90.9] /250 | seq_elim 93.5 [92.6, 94.5] /163 | ocba 88.2 [87.0, 89.4] /250 | ocba_paired 87.8 [86.6, 88.9] /250
  N= 500: uniform 93.2 [92.2, 94.2] /500 | seq_elim 95.7 [94.9, 96.5] /263 | ocba 91.9 [90.9, 92.9] /500 | ocba_paired 91.5 [90.4, 92.5] /500
  N=1000: uniform 96.9 [96.2, 97.5] /1000 | seq_elim 97.2 [96.5, 97.8] /407 | ocba 95.5 [94.7, 96.3] /1000 | ocba_paired 95.8 [95.1, 96.4] /1000
paired difference vs uniform, all states (points, CI):
  seq_elim: N=50 +3.2 [2.1, 4.4] | N=100 +4.5 [3.4, 5.7] | N=250 +3.8 [2.8, 4.8] | N=500 +2.5 [1.6, 3.5] | N=1000 +0.3 [-0.4, 1.1]
  ocba: N=50 -7.3 [-9.0, -5.6] | N=100 -4.4 [-6.1, -2.8] | N=250 -1.5 [-2.9, -0.1] | N=500 -1.3 [-2.5, -0.1] | N=1000 -1.4 [-2.2, -0.4]
  ocba_paired: N=50 -7.9 [-9.6, -6.2] | N=100 -4.7 [-6.3, -3.2] | N=250 -2.0 [-3.3, -0.6] | N=500 -1.7 [-2.9, -0.6] | N=1000 -1.1 [-2.0, -0.2]

### favorita_w26|low|H14  (states 3000, clusters 636, K 1-12 mean 7.7, adequate 1.000, edge 0.004, near-tied 0.197)
N required: uniform 100 (BREA 50, PROD 250, DAIR 50) | seq_elim 50 (BREA 50, PROD 100, DAIR 50) | ocba 100 (BREA 100, PROD 250, DAIR 100) | ocba_paired 100 (BREA 100, PROD 250, DAIR 100)
share within 0.5% [item-clustered 95% CI] / rollouts per candidate:
  N=  10: uniform 79.0 [77.5, 80.5] /10 | seq_elim 79.0 [77.4, 80.5] /10 | ocba 79.0 [77.5, 80.5] /10 | ocba_paired 79.0 [77.5, 80.6] /10
  N=  25: uniform 88.0 [86.7, 89.2] /25 | seq_elim 89.2 [88.0, 90.5] /23 | ocba 82.2 [80.7, 83.7] /25 | ocba_paired 81.3 [79.7, 82.8] /25
  N=  50: uniform 92.6 [91.7, 93.6] /50 | seq_elim 95.2 [94.4, 96.0] /36 | ocba 90.5 [89.3, 91.7] /50 | ocba_paired 89.6 [88.3, 90.8] /50
  N= 100: uniform 95.9 [95.2, 96.6] /100 | seq_elim 98.1 [97.6, 98.6] /50 | ocba 95.7 [95.0, 96.5] /100 | ocba_paired 95.3 [94.5, 96.1] /100
  N= 250: uniform 98.9 [98.5, 99.3] /250 | seq_elim 98.9 [98.5, 99.3] /75 | ocba 98.2 [97.6, 98.6] /250 | ocba_paired 98.3 [97.8, 98.7] /250
  N= 500: uniform 99.6 [99.4, 99.8] /500 | seq_elim 99.0 [98.7, 99.4] /99 | ocba 98.7 [98.3, 99.1] /500 | ocba_paired 99.1 [98.7, 99.4] /500
  N=1000: uniform 99.9 [99.8, 100.0] /1000 | seq_elim 99.0 [98.7, 99.3] /131 | ocba 99.3 [99.0, 99.6] /1000 | ocba_paired 99.3 [99.0, 99.6] /1000
paired difference vs uniform, all states (points, CI):
  seq_elim: N=50 +2.6 [1.8, 3.4] | N=100 +2.2 [1.6, 2.8] | N=250 +0.0 [-0.4, 0.5] | N=500 -0.6 [-1.0, -0.2] | N=1000 -0.9 [-1.2, -0.5]
  ocba: N=50 -2.1 [-3.2, -1.0] | N=100 -0.2 [-1.0, 0.6] | N=250 -0.7 [-1.3, -0.2] | N=500 -0.9 [-1.4, -0.5] | N=1000 -0.6 [-0.9, -0.3]
  ocba_paired: N=50 -3.1 [-4.2, -1.9] | N=100 -0.6 [-1.5, 0.3] | N=250 -0.6 [-1.1, -0.2] | N=500 -0.6 [-1.0, -0.2] | N=1000 -0.6 [-0.9, -0.3]

### favorita_w26_storecluster|base|H14  (states 3000, clusters 53, K 1-12 mean 7.7, adequate 1.000, edge 0.010, near-tied 0.317)
N required: uniform 250 (BREA 250, PROD 500, DAIR 250) | seq_elim 250 (BREA 100, PROD 250, DAIR 100) | ocba 500 (BREA 500, PROD 1000, DAIR 250) | ocba_paired 500 (BREA 250, PROD 500, DAIR 250)
share within 0.5% [item-clustered 95% CI] / rollouts per candidate:
  N=  10: uniform 71.0 [69.3, 72.7] /10 | seq_elim 71.0 [69.1, 72.8] /10 | ocba 71.0 [69.1, 72.8] /10 | ocba_paired 71.0 [69.2, 72.8] /10
  N=  25: uniform 79.4 [78.2, 80.9] /25 | seq_elim 80.7 [79.4, 82.1] /24 | ocba 72.0 [70.6, 73.5] /25 | ocba_paired 69.8 [68.1, 71.5] /25
  N=  50: uniform 85.9 [84.7, 87.2] /50 | seq_elim 89.1 [87.9, 90.3] /41 | ocba 78.7 [77.2, 80.3] /50 | ocba_paired 78.9 [77.4, 80.5] /50
  N= 100: uniform 91.1 [89.9, 92.2] /100 | seq_elim 94.6 [93.5, 95.6] /67 | ocba 88.3 [87.3, 89.4] /100 | ocba_paired 88.1 [86.7, 89.5] /100
  N= 250: uniform 96.3 [95.6, 97.0] /250 | seq_elim 98.2 [97.7, 98.7] /120 | ocba 94.1 [93.3, 94.8] /250 | ocba_paired 94.8 [94.0, 95.6] /250
  N= 500: uniform 98.3 [97.9, 98.7] /500 | seq_elim 98.7 [98.2, 99.1] /177 | ocba 96.6 [96.0, 97.2] /500 | ocba_paired 97.2 [96.6, 97.7] /500
  N=1000: uniform 99.5 [99.3, 99.7] /1000 | seq_elim 98.8 [98.4, 99.2] /254 | ocba 97.4 [96.9, 97.9] /1000 | ocba_paired 98.5 [98.1, 99.0] /1000
paired difference vs uniform, all states (points, CI):
  seq_elim: N=50 +3.1 [2.2, 4.0] | N=100 +3.5 [2.7, 4.4] | N=250 +1.9 [1.2, 2.5] | N=500 +0.4 [-0.2, 0.9] | N=1000 -0.7 [-1.2, -0.2]
  ocba: N=50 -7.2 [-8.8, -5.6] | N=100 -2.7 [-4.1, -1.4] | N=250 -2.2 [-3.2, -1.3] | N=500 -1.7 [-2.4, -1.1] | N=1000 -2.1 [-2.7, -1.5]
  ocba_paired: N=50 -7.1 [-8.9, -5.4] | N=100 -3.0 [-4.1, -1.9] | N=250 -1.5 [-2.4, -0.6] | N=500 -1.1 [-1.7, -0.5] | N=1000 -1.0 [-1.3, -0.6]

### favorita_w52|base|H14  (states 3000, clusters 636, K 1-12 mean 7.8, adequate 1.000, edge 0.007, near-tied 0.327)
N required: uniform 250 (BREA 250, PROD 500, DAIR 250) | seq_elim 250 (BREA 100, PROD 250, DAIR 100) | ocba 500 (BREA 500, PROD 1000, DAIR 250) | ocba_paired 500 (BREA 250, PROD 500, DAIR 250)
share within 0.5% [item-clustered 95% CI] / rollouts per candidate:
  N=  10: uniform 70.1 [68.3, 71.8] /10 | seq_elim 70.1 [68.4, 71.8] /10 | ocba 70.1 [68.4, 71.8] /10 | ocba_paired 70.1 [68.3, 71.8] /10
  N=  25: uniform 80.8 [79.3, 82.3] /25 | seq_elim 81.2 [79.7, 82.6] /24 | ocba 71.8 [69.8, 73.5] /25 | ocba_paired 70.7 [68.9, 72.4] /25
  N=  50: uniform 85.9 [84.6, 87.2] /50 | seq_elim 89.6 [88.5, 90.7] /41 | ocba 77.5 [75.9, 79.2] /50 | ocba_paired 77.1 [75.6, 78.7] /50
  N= 100: uniform 91.3 [90.2, 92.4] /100 | seq_elim 94.7 [93.8, 95.5] /69 | ocba 87.8 [86.5, 88.9] /100 | ocba_paired 87.5 [86.3, 88.7] /100
  N= 250: uniform 96.3 [95.7, 97.0] /250 | seq_elim 97.9 [97.4, 98.5] /123 | ocba 93.9 [93.0, 94.8] /250 | ocba_paired 94.9 [94.0, 95.7] /250
  N= 500: uniform 98.4 [98.0, 98.9] /500 | seq_elim 98.3 [97.8, 98.7] /183 | ocba 96.3 [95.5, 97.0] /500 | ocba_paired 97.3 [96.7, 97.8] /500
  N=1000: uniform 99.5 [99.3, 99.8] /1000 | seq_elim 98.4 [98.0, 98.9] /261 | ocba 97.6 [97.0, 98.1] /1000 | ocba_paired 98.3 [97.9, 98.8] /1000
paired difference vs uniform, all states (points, CI):
  seq_elim: N=50 +3.7 [2.7, 4.7] | N=100 +3.4 [2.5, 4.3] | N=250 +1.6 [0.9, 2.3] | N=500 -0.1 [-0.7, 0.4] | N=1000 -1.1 [-1.6, -0.6]
  ocba: N=50 -8.4 [-10.1, -6.8] | N=100 -3.5 [-4.8, -2.2] | N=250 -2.4 [-3.4, -1.4] | N=500 -2.1 [-2.9, -1.3] | N=1000 -2.0 [-2.6, -1.4]
  ocba_paired: N=50 -8.8 [-10.3, -7.2] | N=100 -3.8 [-5.1, -2.4] | N=250 -1.4 [-2.5, -0.4] | N=500 -1.1 [-1.8, -0.5] | N=1000 -1.2 [-1.7, -0.7]