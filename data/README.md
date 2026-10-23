# Data

| File | Content |
|---|---|
| `proxy_products.pkl`, `proxy_calendar.pkl` | Product panel and calendar of the grocery digital twin |
| `states_benchmark.pkl` | The 500 pre-specified twin decision states (stratified by family and volume tertile) |
| `states_dev.pkl` | 30 development states, used only for smoke tests |
| `states_favorita_replication.pkl` | The 3,000 decision states reconstructed from Favorita sales (stock by age and pipeline on the decision day, store, item, date) |

## Favorita sales (not included)

The replication uses the Corporación Favorita Grocery Sales Forecasting data (Kaggle, 2018):
https://www.kaggle.com/c/favorita-grocery-sales-forecasting

Download `train.csv` and `items.csv` from Kaggle into one folder and pass it as `FAV_DIR`, e.g.

```bash
FAV_DIR="/path/to/favorita" python3 notebooks/_nb02_as_script.py
```

Notebook 1 builds the perishable panel cache `data/favorita_perishable.pkl` from these files; the cache is
derived from Kaggle data and is therefore not included either.
