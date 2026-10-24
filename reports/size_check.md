# Size check (rows x columns >= 3,000,000)

* Raw: 845,607 rows x 29 columns = 24,522,603 cells.
* Cleaned (all rows, flags kept): 842,221 rows x 55 columns.
* Encoded model table (market sales only): 566,956 rows x 71 columns (15 numeric/derived + 5 borough + 47 building_category + 4 tax_class_at_sale one-hot) = 40,253,876 cells = 13.4 x the 3,000,000 minimum.
* Adding neighbourhood one-hot (261 levels) gives 332 columns = 188,229,392 cells.
* Step that clears 3M: already the raw table does; encoding the 3 categoricals adds 53 columns.
* Smallest test population (P1, price per sq ft with year built): 248,409 x 71 = 17,637,039 cells.
