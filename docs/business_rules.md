# Business Rules — Synthetic Data Signal Design

## 🎯 Purpose of This File
If we create synthetic data using purely random numbers, our machine learning models in Phase 6 will fail. Why? Because pure randomness contains no real patterns to learn.

This document defines the exact business formulas used to generate our fake data. These rules ensure that:
1. Our dbt dashboards in Phase 4 show realistic, explainable trends (e.g., higher cancellations on impulse buys).
2. Our XGBoost ML models in Phase 6 have real signals and relationships to discover.
3. We have an "answer key" to verify that our predictive models are finding true patterns rather than guessing.

---

## 1. Cancellation Probability Logic
Base Cancellation Rate: 15% (0.15)

To calculate whether a specific booking gets cancelled, we start with the base rate (15%) and multiply it by several risk factors.

Formula:
Final Probability = Base Rate (0.15) * Multiplier_1 * Multiplier_2 * ... * Multiplier_N

| Feature Category | Condition / Rule | Risk Multiplier | Business Reason / Human Behavior |
| :--- | :--- | :--- | :--- |
| **Booking Lead Time** | Booked > 60 days in advance | **x1.6** | High uncertainty; plans are more likely to change over 2+ months. |
| | Booked 14 - 60 days in advance | **x1.2** | Standard advance planning window; moderate cancellation risk. |
| | Booked < 3 days in advance | **x0.5** | High intent; last-minute bookers rarely cancel their trips. |
| **Discount Size** | Discount > 20% | **x1.3** | Impulse buying; customers buy because it's cheap, then reconsider. |
| **Booking Channel** | Booked via Affiliate/Partner | **x1.25** | Lower brand loyalty compared to direct website or app users. |
| **Experience Category**| Adventure Tour or Cruise | **x1.3** | Weather-dependent and higher safety/equipment friction. |
| | Museum or Indoor Attraction | **x0.85** | Low effort, indoor activity; less sensitive to weather or scheduling. |
| **Customer History** | 1 prior cancellation in history | **x1.4** | Repeat behavioral pattern. |
| | 2+ prior cancellations in history| **x1.9** | High-risk customer segment. |

⚠️ Safeguard Rule:
After multiplying all factors together, the final probability is capped (clipped) between 2% (0.02) and 85% (0.85). This prevents impossible rates like 0% or 100% and keeps every booking realistic.

---

## 2. Experience Demand & Booking Volume Logic
Each experience receives an expected daily booking volume based on five core factors:

Formula:
Expected Bookings = Base Popularity * Seasonality * Weekend Boost * Price Factor * Rating Factor

1. **Base Popularity (Fixed per experience):**
   - Set once when the experience is created (e.g., Eiffel Tower vs. a quiet local gallery).
   - This gives the ML model a historical popularity feature to learn.

2. **Seasonality Multiplier (Month-based):**
   - Peak travel months (e.g., June, July, August) increase booking volume across all experiences.

3. **Weekend Boost:**
   - If the experience date lands on Saturday or Sunday, multiply demand by a weekend factor (e.g., 1.4x).

4. **Price Elasticity Factor:**
   - Higher prices slightly suppress expected demand compared to cheaper options in the same city.

5. **Rating Factor:**
   - Ratings below 4.0 penalize demand.
   - Ratings above 4.5 give a mild demand boost.

⚠️ Realism Cap:
Actual daily bookings are sampled around `Expected Bookings` using a Poisson distribution and are strictly capped by `availability.total_capacity`. If expected bookings exceed capacity, the experience sells out!

---

## 3. Web & App Event Funnel Rules
Each customer session follows a natural sequential user journey:

SEARCH ──► VIEW_EXPERIENCE ──► CHECK_AVAILABILITY ──► ADD_TO_CART ──► CHECKOUT ──► PURCHASE

- Drop-off rates occur naturally at each stage of the funnel.
- **Critical Data Integrity Rule:** If a session reaches `PURCHASE`, a matching row **must** be created in the `bookings` table with identical `customer_id`, `experience_id`, and a timestamp occurring shortly after the `CHECKOUT` event.