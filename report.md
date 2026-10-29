# TRACCIA: Implementation Progress Report

## Overview
TRACCIA is a disaster response and inventory management system that uses both a relational database (SQL) and a document database (MongoDB). SQL handles structured records that need strict consistency—like inventory levels, purchase orders, and relief dispatches. MongoDB handles more flexible records—like beneficiary registrations and citizen grievance tickets with update histories.

This report outlines what has been built so far, starting from Step 1.

---

## What Has Been Implemented

### Step 1: Database Setup & Schemas
- **SQL Relational Database (`backend/sql_db.py`)**:
  - Created tables with primary keys, foreign keys, and practical validation checks:
    - `products`: Product catalog with unique SKUs and positive prices.
    - `suppliers` and `locations`: Relief agencies, regional warehouses, and field camps.
    - `inventory`: Tracks stock per warehouse, prevents negative counts, and sets reorder thresholds.
    - `purchases`: Logs incoming stock shipments from suppliers.
    - `relief_distributions` and `distribution_items`: Records outgoing aid packages sent to affected areas.
    - `sales` and `stock_movements`: Tracks items handed out and transfers between warehouses.
    - `flood_events`: Stores historical disaster records (regions, river basins, impact severity).
    - `cwc_rainfall_telemetry`: Stores river gauge readings, rainfall numbers, and flood alert levels.
- **MongoDB Collections (`backend/mongo_db.py`)**:
  - `consumers`: Stores beneficiary profiles with contact details, flood event references, vulnerability groups (e.g., displaced families, elderly), and soft deletion support.
  - `grievances`: Tracks assistance requests across categories (water, food, shelter, medical aid) through statuses (`OPEN`, `IN_PROGRESS`, `RESOLVED`).
  - **Embedded Updates**: Uses MongoDB's `$push` to add dated status notes and staff IDs directly inside the grievance document, keeping the full history in one place.
- **Cross-Database Linking**:
  - SQL relief dispatches reference MongoDB beneficiary IDs, and MongoDB records reference SQL flood event IDs.

---

### Step 2: Data Sourcing & Seeding
- **Disaster Data Sources (`backend/seed_data.py`)**:
  - **Nepal Melamchi Flood (2021)**: Real-world flood impact data from HydroShare.
  - **India Flood Inventory (1967–2023)**: Historical event data from Zenodo covering major floods in Kerala, Bihar, Assam, and Uttarakhand.
  - **CWC Telemetry Data**: River water levels and danger marks based on Central Water Commission stations.
  - **Synthetic Records**: Realistic sample data for beneficiaries and relief requests, clearly marked with a test flag.
- **Seeding Script**:
  - Created an automated seed script that resets or fills the databases with sample products, warehouses, events, and tickets so the system is immediately usable.

---

### Step 3: Transactions, Queries, and Aggregations
- **Safe Transactions (ACID)**:
  - **Purchases**: Adds the purchase record and updates warehouse stock in a single transaction.
  - **Relief Dispatches**: Validates stock across multiple items before dispatching. If any item is short on stock, the entire transaction rolls back so inventory counts stay correct.
  - **Warehouse Transfers**: Safely moves stock from one location to another.
- **Multi-Table JOINs**:
  - **3-Way JOIN**: Combines `inventory`, `products`, and `locations` to show where items are stored.
  - **4-Way JOIN**: Combines `purchases`, `suppliers`, `products`, and `locations` for procurement tracking.
  - **5-Way JOIN**: Combines `relief_distributions`, `distribution_items`, `products`, `locations`, and `flood_events` to trace aid from warehouse to disaster area.
- **Aggregations & Reports**:
  - Stock totals grouped by warehouse.
  - Supplier order volumes (`HAVING SUM > 0`).
  - Total aid dispatched by product category.
  - Relief distribution totals broken down by disaster event.
  - Low-stock alerts triggered when warehouse counts drop below reorder levels.

---

### Step 4: Backend API & Logging
- **FastAPI Endpoints (`backend/server.py`)**:
  - Over 25 REST endpoints covering:
    - CRUD operations for products, suppliers, locations, and inventory.
    - Transaction execution (purchases, transfers, relief dispatches).
    - JOIN queries and summary reports.
    - MongoDB beneficiary and grievance management (including timeline updates).
    - Flood event lookups and live telemetry readings.
- **Database Logger (`backend/logger.py`)**:
  - Added clean terminal logging showing SQL queries, transaction steps (`TX BEGIN`, `TX COMMIT`, `TX ROLLBACK`), and MongoDB queries.
- **App Launcher (`main.py`)**:
  - Simple entry point that handles command-line flags (`--seed`, `--reset`, `--port`), checks database files, and starts the server.

---

### Step 5: Web Operations Dashboard
- **Frontend UI (`static/index.html`)**:
  - Built a responsive single-page interface with 9 functional tabs:
    1. **Overview**: Key metrics, recent activity, and quick-action shortcuts.
    2. **Products & Catalog**: Relief supply items, categories, and unit values.
    3. **Warehouses & Inventory**: Stock levels per warehouse with low-stock warnings.
    4. **Transactions**: Forms to log purchases, warehouse transfers, and multi-item dispatches.
    5. **Reports**: Clean tables showing the multi-table JOINs and aggregated summaries.
    6. **Beneficiaries**: Registration form and list of registered citizens with filtering.
    7. **Grievances**: Ticket management with status updates, assignments, and visible history logs.
    8. **Data Pipeline**: Clear diagram explaining how data moves through ingestion, validation, storage, and operations.
    9. **Flood Intelligence**: Overview of past disaster events and current river gauge alerts.
    10. **SDG Impact Mapping**: Dedicated page linking database architecture to UN Sustainable Development Goals (SDG 11, 13, 6, 2, 12, 16).

---

### Step 6: Testing & Verification
- **Test Suite (`tests/test_system.py`)**:
  - Wrote 7 automated unit and integration tests:
    1. Product CRUD and table constraints (SKU uniqueness, positive prices).
    2. SQL transaction rollbacks when attempting to over-dispatch stock.
    3. Multi-table JOINs and `GROUP BY` / `HAVING` queries.
    4. MongoDB beneficiary onboarding and soft deletion.
    5. Grievance lifecycle updates and history appending.
    6. Multi-item relief dispatches and automatic stock reduction.
    7. Flood event lookups and cross-database linking.
  - **Result**: All 7 tests pass cleanly.

---

## Summary Table

| Step | Area | Main Files | Status |
| :--- | :--- | :--- | :--- |
| **Step 1** | SQL Tables & Constraints | `backend/sql_db.py`, `docs/schema.md` | Done |
| **Step 1** | MongoDB Collections & Embedded History | `backend/mongo_db.py` | Done |
| **Step 2** | Flood & River Datasets (Nepal & India) | `backend/seed_data.py`, `README.md` | Done |
| **Step 2** | Database Seeding Script | `backend/seed_data.py` | Done |
| **Step 3** | ACID Transactions & Rollbacks | `backend/sql_db.py` | Done |
| **Step 3** | Multi-Table JOINs & Aggregated Reports | `backend/sql_db.py` | Done |
| **Step 4** | FastAPI Backend Endpoints | `backend/server.py` | Done |
| **Step 4** | Console Query Logger & Launcher | `backend/logger.py`, `main.py` | Done |
| **Step 5** | 10-Tab Web Dashboard (incl. SDG Impact) | `static/index.html` | Done |
| **Step 6** | Automated Test Suite (7 tests) | `tests/test_system.py` | Passed |
