# TRACCIA: Database Management for Inventory and Disaster Response

TRACCIA is a hybrid database-centric application combining a relational SQL engine (PostgreSQL/MySQL/SQLite) and a document-oriented MongoDB store. It is optimised for Indian operational requirements and incorporates Nepal flood data as a disaster-response case study.

---

## 1. Project Overview & Datasets

### A. System Architecture
```
                    ┌───────────────────────────────────────────────┐
                    │  Frontend Disaster Operations Dashboard UI    │
                    │         (HTML5, CSS3, JavaScript)             │
                    └───────────────────────┬───────────────────────┘
                                            │ HTTP / JSON REST APIs
                    ┌───────────────────────▼───────────────────────┐
                    │         Python Backend (FastAPI)              │
                    │        CRUD, Transactions, Routing            │
                    └──────────────┬─────────────────┬──────────────┘
                                   │                 │
                ┌──────────────────▼─┐             ┌─▼──────────────────┐
                │  SQL (SQLite / PG) │             │     MongoDB        │
                │  - Flood Events    │             │  - Beneficiaries   │
                │  - CWC Telemetry   │             │  - Grievances      │
                │  - Relief Supplies │             │    (Embedded logs) │
                │  - Warehouses      │             │  - Flood Event     │
                │  - Relief Dispatches│            │    References      │
                │  - Movements (Tx)  │             └────────────────────┘
                └────────────────────┘
```

### B. Dataset Sources Incorporated
1. **Nepal Flood Dataset**: [Nepal-FRES: 2021 Melamchi Flood Data](https://hydroshare.cuahsi.org/resource/b6da096000284d5882d13b085b7669ac/)
   - Geospatial information on landslides, debris flows, river channels, and landscape changes associated with the 2021 Melamchi flood in Sindhupalchok District, Nepal.
2. **Indian Flood Dataset**: [India Flood Inventory and Impacts (1967–2023)](https://zenodo.org/records/16994648)
   - Historical flood-event, population displacement, casualty, and damage impact data across Indian regions (Assam, Bihar, Kerala, Uttarakhand).
3. **Optional Rainfall Dataset**: [CWC Hourly Rainfall Data](https://nwdp.nwic.gov.in/dataset/rainfall-cwc-telemetry-hourly)
   - Real-time rainfall observations and river gauge water levels compared to danger marks for environmental context and early flood warnings.
4. **Beneficiary & Grievance Records**: Generated as clearly labelled synthetic data mapped to disaster case studies.

---

## 2. Database Implementation

### SQL Engine (`backend/sql_db.py`)
- **Structured Schemas & Constraints**:
  - `flood_events`: Event ID (PK), disaster event name, country (`CHECK IN ('Nepal', 'India')`), river basin, severity, casualties, displaced population, and geospatial notes.
  - `cwc_rainfall_telemetry`: Gauge station ID (UNIQUE), river basin, hourly rainfall (`mm >= 0`), 24h cumulative rainfall, danger levels, current water levels, and alert levels (`EXTREME`, `DANGER`, `WARNING`, `ADVISORY`, `NORMAL`).
  - `products`: SKU (UNIQUE), unit price/relief valuation (`CHECK >= 0`), name, category (dry rations, water purification, trauma kits, relief tents, rescue boats, dewatering pumps).
  - `suppliers`: NDRF, Red Cross Society, UN agencies, and medical suppliers.
  - `locations`: Regional disaster logistics hubs and forward relief camps.
  - `inventory`: `(product_id, location_id)` UNIQUE constraint, `quantity_on_hand` (`CHECK >= 0`), and `reorder_level`.
  - `purchases`: Inbound procurement receipts with foreign keys.
  - `relief_distributions` & `distribution_items`: Atomic multi-item relief dispatches linking logically to MongoDB's `beneficiary_id` and SQL's `flood_event_id`.
  - `sales`: Outbound transactions synchronized with relief distributions for backwards compatibility.
  - `stock_movements`: Inter-depot transfers, return shipments, and inventory count adjustments.
- **ACID Transactions**:
  - `record_purchase`: Atomically inserts purchase order and increments warehouse inventory.
  - `record_relief_distribution`: Atomically validates inventory availability, decrements stock across all line items, logs master distribution and item records, and updates sales tracking. Rolls back on stock deficit.
  - `record_stock_movement`: Validates source stock and transfers units atomically.
- **JOINs & Aggregations**:
  - 5-Way JOIN for relief distributions (`relief_distributions` + `distribution_items` + `products` + `locations` + `flood_events`).
  - 4-Way JOIN for humanitarian procurement (`purchases` + `suppliers` + `products` + `locations`).
  - 3-Way JOIN between `inventory`, `products`, and `locations`.
  - `GROUP BY` and `HAVING` aggregations:
    - Stock grouped by location.
    - Supplier procurement volume (`HAVING SUM(quantity_received) > 0`).
    - Low-stock deficit alerts (`WHERE quantity_on_hand <= reorder_level`).
    - Relief supplies dispatched by product (`HAVING SUM(di.quantity) > 0`).
    - Disaster operations summary grouped by flood event.

### MongoDB Document Store (`backend/mongo_db.py`)
- **`consumers` Collection (Beneficiaries)**:
  - Onboarding records with unique `consumer_id`.
  - District, state, country, and reference to `flood_event_id`.
  - Vulnerability categorization (`DISPLACED_FAMILY`, `ELDERLY`, `CHILD_CARE`, `FEMALE_HEADED_HOUSEHOLD`).
  - Clearly labelled synthetic data flag (`is_synthetic: true`).
  - Soft-deletion support to maintain transactional integrity.
- **`grievances` Collection (Assistance Requests)**:
  - Lifecycle tracking (`OPEN` &rarr; `IN_PROGRESS` &rarr; `RESOLVED`).
  - Disaster relief categories: `DRINKING_WATER`, `FOOD_RATIONS`, `EMERGENCY_SHELTER`, `TRAUMA_MEDICINE`, `RESCUE_ASSISTANCE`, `INFRASTRUCTURE_HAZARD`, `RELIEF_KIT_DAMAGE`.
  - References to flood events and affected locations.
  - Embedded `updates` timeline with immutable timestamps, notes, and staff audit identifiers.
  - Multi-field filtering by `status`, `priority`, `flood_event_id`, and `consumer_id`.

---

## 3. Running & Testing the Application

### Prerequisites
- Python 3.10+
- Installed dependencies:
  ```bash
  pip install fastapi uvicorn pymongo mongomock
  ```

### Launch the Application
```bash
python3 main.py
```
Open your browser to **http://127.0.0.1:8000**.

### Running the Test Suite
```bash
python3 tests/test_system.py
```
The test suite validates:
1. SQL product catalog CRUD, unique SKU, and price constraints.
2. SQL ACID transactions with rollback on overselling.
3. Multi-table JOINs and GROUP BY / HAVING aggregations.
4. MongoDB beneficiary onboarding, uniqueness, and soft deletion.
5. MongoDB grievance lifecycle, priority filtering, and embedded audit logs.
6. SQL relief distributions multi-item atomic dispatch and stock reduction.
7. Flood event queries, CWC rainfall telemetry alerts, and hybrid cross-database integration.
