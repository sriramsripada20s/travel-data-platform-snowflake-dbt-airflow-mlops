
## 1. suppliers

**Grain:** one row = one supplier

| Column               | Type   | Notes                                  |
|-----------------------|--------|------------------------------------------|
| supplier_id           | string | PK. Format `SUP{00001+i}` (5-digit)      |
| supplier_name         | string |                                          |
| country               | string |                                          |
| supplier_type         | string | Tour Operator / Attraction / Museum / Theme Park / Cruise Operator / Activity Provider |
| contract_start_date   | date   |                                          |
| commission_rate       | float  | 0.10 - 0.30                              |
| supplier_status       | string | ACTIVE (95%) / INACTIVE (5%)             |

**Rules:** `supplier_id` unique. `commission_rate` in [0.10, 0.30].

## 2. experiences

**Grain:** one row = one bookable experience

| Column          | Type   | Notes                                     |
|------------------|--------|----------------------------------------------|
| experience_id    | string | PK. Format `EXP{000001+i}` (6-digit)          |
| experience_name  | string |                                              |
| city             | string | Weighted: Paris 24%, Rome 22%, London 21%, Dubai 19%, Barcelona 14% |
| country          | string | Derived from city                           |
| category         | string | Attraction / Guided Tour / Museum / Theme Park / Cruise / Food & Drink / Adventure / Show |
| supplier_id      | string | FK -> suppliers.supplier_id, preferring an ACTIVE supplier in the same country |
| base_price       | float  | Within category's price_range               |
| capacity         | int    | Within category's capacity_range             |
| rating           | float  | 3.5 - 5.0                                    |
| active_flag      | bool   | True 97% of the time                         |

**Rules:** `experience_id` unique. `supplier_id` must exist in `suppliers` and be ACTIVE. `base_price`, `capacity` > 0. `rating` in [3.5, 5.0].

## 3. customers

**Grain:** one row = one customer

| Column                | Type   | Notes                                  |
|-------------------------|--------|--------------------------------------------|
| customer_id            | string | PK. Format `C{10000+i}`                    |
| signup_date            | date   | Between START_DATE - 3y and END_DATE       |
| country                | string | From YAML customer_countries               |
| preferred_language     | string | Derived from country                       |
| acquisition_channel    | string | From YAML acquisition_channels             |
| customer_segment       | string | New / Repeat / VIP / Dormant               |

**Rules:** `customer_id` unique. `signup_date` <= any of that customer's `booking_timestamp`.

## 4. availability

**Grain:** one row = one experience + one date + one timeslot

| Column              | Type     | Notes                                    |
|----------------------|----------|--------------------------------------------|
| experience_id        | string   | FK -> experiences.experience_id            |
| experience_date      | date     | Within START_DATE..END_DATE                |
| time_slot            | string   | e.g. "10:00", 2-4 slots/day                |
| total_capacity       | int      | Derived from experience.capacity           |
| available_capacity   | int      | 0 <= available_capacity <= total_capacity  |
| price                | float    | base_price adjusted by season/weekend      |

**Rules:** Composite key (`experience_id`, `experience_date`, `time_slot`) unique. Must be generated *before* `bookings`, since bookings decrement `available_capacity` and can never push it below 0.

## 5. bookings — primary fact table

**Grain:** one row = one booking

| Column              | Type      | Notes                                      |
|----------------------|-----------|----------------------------------------------|
| booking_id           | string    | PK. Format `B{90000+i}`                      |
| customer_id          | string    | FK -> customers.customer_id                  |
| experience_id        | string    | FK -> experiences.experience_id              |
| booking_timestamp    | datetime  | Before experience_date                       |
| experience_date      | date      | Must match a row in availability             |
| number_of_guests     | int       | >= 1                                         |
| ticket_price         | float     | From matching availability row               |
| discount_amount      | float     | >= 0                                         |
| booking_amount       | float     | = ticket_price * guests - discount, >= 0     |
| booking_status       | string    | CONFIRMED / CANCELLED / REFUNDED             |
| payment_status       | string    | PAID / PENDING / FAILED                      |
| booking_channel      | string    | MOBILE / WEB / PARTNER                       |
| currency             | string    | USD                                          |

**Rules:** `booking_timestamp` < `experience_date`. `(experience_id, experience_date)` must exist in `availability`. **Cancellation probability is not a flat draw** — see `docs/business_rules.md`.

## 6. web_events

**Grain:** one row = one behavioral event within one session

| Column          | Type      | Notes                                    |
|------------------|-----------|----------------------------------------------|
| event_id         | string    | PK. Format `EVT{1000000+i}`                  |
| customer_id      | string    | FK -> customers.customer_id                  |
| session_id       | string    | Groups events into one session               |
| experience_id    | string    | Null only for early SEARCH events            |
| event_timestamp  | datetime  | Strictly increasing within a session         |
| event_type       | string    | SEARCH / VIEW_EXPERIENCE / CHECK_AVAILABILITY / ADD_TO_CART / CHECKOUT / PURCHASE |
| device_type      | string    | mobile / desktop / tablet                    |
| traffic_source   | string    | From YAML traffic_sources                    |
| city_searched    | string    | City the session started from                |

**Rules:** Event order within a session cannot skip backward. A PURCHASE event should correspond to a real `bookings` row for the same customer + experience.

## Cross-dataset invariants

1. Every `bookings.customer_id` exists in `customers`.
2. Every `bookings.experience_id` exists in `experiences`.
3. Every `experiences.supplier_id` exists in `suppliers`.
4. Every `(bookings.experience_id, bookings.experience_date)` exists in `availability`.
5. Every `web_events.customer_id` exists in `customers`.
6. `availability.available_capacity` never negative, never exceeds `total_capacity`.

Rules 1-6 hold in `data/generated/clean/`. The `data/generated/raw/` copy intentionally violates a small, known percentage of rows (see `data_quality_injection` in the YAML) — the deliberate input Phase 2/3 work is built to catch.