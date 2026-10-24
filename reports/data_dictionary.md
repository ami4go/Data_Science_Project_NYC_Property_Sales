| column | type | unit / format | range (cleaned, all rows) | missing | meaning |
|---|---|---|---|---|---|
| `borough` | Nominal | name (from code 1-5) | 5 values | 0.0% | Borough of the property |
| `neighborhood` | Nominal | text | 262 values | 0.0% | DOF assessor neighbourhood |
| `building_category` | Nominal | code + text | 47 values | 0.0% | Building class category (e.g. 01 ONE FAMILY DWELLINGS) |
| `tax_class_final_roll` | Nominal | code | 11 values | 0.5% | Tax class on the final roll (present) |
| `block` | Identifier | integer | 1 to 1.635e+04 | 0.0% | Tax block |
| `lot` | Identifier | integer | 1 to 9,139 | 0.0% | Tax lot |
| `building_class_final_roll` | Nominal | code | 204 values | 0.5% | Building class on the final roll (present) |
| `address` | Identifier | text | 623,244 values | 0.0% | Street address (co-op unit often appended) |
| `apartment_number` | Identifier | text | 18,567 values | 75.3% | Unit number (condos) |
| `zip_code` | Nominal | 5 digits | 208 values | 0.3% | Postal code |
| `residential_units` | Discrete | count | 0 to 8,764 | 15.8% | Residential units on the lot |
| `commercial_units` | Discrete | count | 0 to 2,261 | 25.1% | Commercial units on the lot |
| `total_units` | Discrete | count | 0 to 8,812 | 14.1% | Total units |
| `land_sqft` | Continuous | sq ft | 1 to 1.985e+07 | 43.0% | Lot area |
| `gross_sqft` | Continuous | sq ft | 1 to 8.942e+06 | 44.3% | Total floor area of the building(s) |
| `year_built` | Discrete | year | 1,800 to 2,025 | 7.5% | Year the structure was built (assessor estimate) |
| `tax_class_at_sale` | Nominal | code 1-4 | 1 to 4 | 0.0% | Tax class at the time of sale |
| `building_class_at_sale` | Nominal | code | 203 values | 0.0% | Building class at the time of sale |
| `sale_price` | Continuous | US$ | 0 to 2.398e+09 | 0.0% | Recorded sale price (RESPONSE) |
| `sale_date` | Date | YYYY-MM-DD | 2016-01-01 to 2025-12-31 | 0.0% | Date the deed was recorded |
| `latitude` | Continuous | degrees | 40.5 to 40.91 | 2.7% | Geocoded latitude |
| `longitude` | Continuous | degrees | -74.25 to -73.7 | 2.7% | Geocoded longitude |
| `community_board` | Nominal | code | 64 values | 2.7% | Community board |
| `council_district` | Nominal | code | 51 values | 2.7% | City council district |
| `bin` | Identifier | code | 356,498 values | 3.1% | Building identification number |
| `bbl_building` | Identifier | code | 348,028 values | 3.3% | Raw BBL column: building-level (condo billing lot) |
| `census_tract_2020` | Nominal | code | 1,454 values | 2.7% | 2020 census tract |
| `nta_2020` | Nominal | code | 216 values | 2.7% | 2020 Neighbourhood Tabulation Area |
| `bbl_lot` | Identifier | code | 507,455 values | 0.0% | DERIVED borough*1e9 + block*1e4 + lot (unit/parcel) |
| `price_class` | Nominal | nominal / low / market | 3 values | 0.0% | DERIVED <=$100, $101-$10k, >$10k |
| `multi_lot_sale` | Nominal | bool | True 4.2% | 0.0% | DERIVED one deed over several lots (price is the total) |
| `transaction_id` | Identifier | code | 820,934 values | 0.0% | DERIVED one id per deal (R = single lot, B/D = multi-lot) |
| `first_in_transaction` | Nominal | bool | True 97.5% | 0.0% | DERIVED first row of its deal; price statistics use these rows |
| `price_per_sqft` | Continuous | US$ / sq ft | 0.0671 to 1.426e+06 | 70.0% | DERIVED sale_price / gross_sqft (valid rows only) |
| `log10_price` | Continuous | log10 US$ | 4 to 9.38 | 32.7% | DERIVED, market sales only |
| `prewar` | Nominal | bool | True 44.3% | 7.5% | DERIVED year_built < 1940 |
| `building_age_at_sale` | Discrete | years | -1 to 225 | 7.5% | DERIVED sale_year - year_built |
| `period` | Nominal | 4 levels | 4 values | 0.0% | DERIVED pre-COVID / COVID / recovery / 2024-25 |
| `toll_zone` | Nominal | bool | True 54.0% | 78.6% | DERIVED Manhattan, 60th St and below (from coordinates) |
| `post_toll` | Nominal | bool | True 10.0% | 0.0% | DERIVED sale on/after 5 Jan 2025 |
