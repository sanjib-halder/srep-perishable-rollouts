## Environment
python 3.9.6 | numpy 2.0.2 | pandas 2.3.3 | macOS-15.6.1-arm64-arm-64bit
protocol hash 1efa0b18cd1078c6

## 1. Sales panel
file: /path/to/srep (18.7 MB) | sha256[:12] fc6e24d9dfbc
shape (492453, 6)
columns/dtypes: date:datetime64[ns], store_nbr:int32, item_nbr:int64, family:object, unit_sales:int64, onpromotion:int64
dates 2016-02-14 .. 2017-08-15 (549 days)
stores 3 | items 302 | store-items 897
missing values per column: {'item_nbr': 0, 'store_nbr': 0, 'unit_sales': 0, 'date': 0}
unit_sales: min 0.00 | mean 18.54 | max 11032.00 | share zero 0.130 | share negative 0.0000 | share non-integer 0.0000
by family:
               rows  store_items
family                          
BEVERAGES     90585          165
BREAD/BAKERY  74115          135
DAIRY         85644          156
FROZEN FOODS  76311          139
GROCERY I     82350          150
PRODUCE       83448          152
series length per store-item: min 549 | median 549 | max 549
sales dates covered by calendar: 1.0000

## 2. Store-level sales vs twin demand model (perishable store-items)
store-items checked: 443
ratio observed/model mean, quantiles: q5=0.49, q25=0.67, q50=0.86, q75=1.07, q95=1.40
correlation of daily pattern (median): 0.06
variance/mean of daily sales (Poisson = 1), quantiles: q25=2.88, q50=4.36, q75=7.51
store-level median ratio: min 0.71 | median 0.80 | max 1.07
store scaling needed (IQR of ratio outside 0.8–1.25): True

## 3. SGSG replay check
replay == run_sgsg_for_sku_store on 200 random perishable store-items: mismatches = 0 (0.8s)

## 4. Replication states
eligible store-items (>=120 days): 443 | items covered: 148 of 165 perishable items
built 3000 states from 443 store-items, 148 items, 3 stores (1.8s)
state profile by family (means; 'cover' = (onhand+pipeline)/mean daily sales):
              onhand  pipeline  cover  empty    old
family                                             
BREAD/BAKERY   22.52     28.85   3.97   0.18  11.33
DAIRY          84.26     29.61   8.66   0.12   7.93
PRODUCE       122.64     78.58   5.58   0.15  26.49
saved data/states_replication.pkl