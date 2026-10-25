# TRACCIA: Database Management for Inventory and Disaster Response

TRACCIA is a hybrid database-centric application combining a relational SQL engine (PostgreSQL/MySQL/SQLite) and a document-oriented MongoDB store. It is optimised for Indian operational requirements and incorporates Nepal flood data as a disaster-response case study.

---

## 1. Project Overview & Datasets

### A. System Role
- **SQL Relational Engine**: Manages structured relief inventory, humanitarian procurement, multi-echelon disaster warehouse depots, atomic multi-item relief distribution transactions, and historical flood telemetry records.
- **MongoDB Document Store**: Manages flexible citizen/beneficiary onboarding profiles, field assistance requests, and evolving multi-stakeholder grievance resolution lifecycles with embedded audit timelines.
- **Hybrid Cross-Database Integration**: Links SQL relief distribution dispatches with MongoDB beneficiary records and connects geospatial flood events to field assistance requests.

### B. Dataset Sources Incorporated
1. **Nepal Flood Dataset**: [Nepal-FRES: 2021 Melamchi Flood Data](https://hydroshare.cuahsi.org/resource/b6da096000284d5882d13b085b7669ac/)
   - Geospatial information on landslides, debris flows, riverbed aggradation, and landscape changes associated with the June 2021 Melamchi flash flood in Sindhupalchok District, Nepal.
2. **Indian Flood Dataset**: [India Flood Inventory and Impacts (1967–2023)](https://zenodo.org/records/16994648)
   - Historical flood event, severity, casualty, and population displacement data across Indian states and river basins (e.g. 2018 Kerala floods, 2019 Bihar floods, 2020 Assam Brahmaputra floods, 2021 Uttarakhand Chamoli disaster).
3. **Hydrological Telemetry Dataset**: [CWC Hourly Rainfall Data](https://nwdp.nwic.gov.in/dataset/rainfall-cwc-telemetry-hourly)
   - Central Water Commission (CWC) telemetry observations providing river gauge water levels, hourly rainfall (mm), danger marks, and early flood warning alerts.
4. **Beneficiary & Grievance Records**: Sourced separately as clearly labelled synthetic data mapped to disaster event references.

---

## 2. Entity-Relationship (ER) Architecture

### SQL Relational Schema Diagram

```mermaid
erDiagram
    FLOOD_EVENTS ||--o{ RELIEF_DISTRIBUTIONS : "contextualizes"
    LOCATIONS ||--o{ RELIEF_DISTRIBUTIONS : "dispatches from"
    RELIEF_DISTRIBUTIONS ||--|{ DISTRIBUTION_ITEMS : "contains"
    PRODUCTS ||--o{ DISTRIBUTION_ITEMS : "included in"
    PRODUCTS ||--o{ INVENTORY : "stocked in"
    LOCATIONS ||--o{ INVENTORY : "holds"
    SUPPLIERS ||--o{ PURCHASES : "procures from"
    PRODUCTS ||--o{ PURCHASES : "received"
    LOCATIONS ||--o{ PURCHASES : "delivered to"
    PRODUCTS ||--o{ STOCK_MOVEMENTS : "transferred"
    LOCATIONS ||--o{ STOCK_MOVEMENTS : "source location"
    LOCATIONS ||--o{ STOCK_MOVEMENTS : "target location"
    PRODUCTS ||--o{ SALES : "dispatched"
    LOCATIONS ||--o{ SALES : "fulfilled from"

    FLOOD_EVENTS {
        VARCHAR event_id PK
        VARCHAR event_name
        VARCHAR country
        VARCHAR state_province
        VARCHAR river_basin
        DATE start_date
        DATE end_date
        VARCHAR severity
        INTEGER displaced_population
        INTEGER casualties
        VARCHAR source_dataset
        TEXT geospatial_notes
    }

    CWC_RAINFALL_TELEMETRY {
        INTEGER telemetry_id PK
        VARCHAR station_id UK
        VARCHAR station_name
        VARCHAR state_or_region
        VARCHAR river_basin
        REAL hourly_rainfall_mm
        REAL cumulative_24h_mm
        REAL danger_level_meters
        REAL current_water_level_meters
        VARCHAR alert_level
        VARCHAR source_dataset
    }

    PRODUCTS {
        INTEGER product_id PK
        VARCHAR name
        VARCHAR category
        VARCHAR sku UK
        REAL unit_price
    }

    SUPPLIERS {
        INTEGER supplier_id PK
        VARCHAR name
        VARCHAR contact_details
    }

    LOCATIONS {
        INTEGER location_id PK
        VARCHAR name
        VARCHAR address
    }

    INVENTORY {
        INTEGER inventory_id PK
        INTEGER product_id FK
        INTEGER location_id FK
        INTEGER quantity_on_hand
        INTEGER reorder_level
    }

    PURCHASES {
        INTEGER purchase_id PK
        INTEGER supplier_id FK
        INTEGER product_id FK
        INTEGER location_id FK
        INTEGER quantity_received
        TIMESTAMP purchase_date
    }

    RELIEF_DISTRIBUTIONS {
        INTEGER distribution_id PK
        INTEGER location_id FK
        VARCHAR beneficiary_id "Logical FK -> MongoDB"
        VARCHAR flood_event_id FK
        TIMESTAMP distribution_date
        VARCHAR relief_officer
        VARCHAR status
        TEXT notes
    }

    DISTRIBUTION_ITEMS {
        INTEGER item_id PK
        INTEGER distribution_id FK
        INTEGER product_id FK
        INTEGER quantity
    }

    SALES {
        INTEGER sale_id PK
        INTEGER product_id FK
        INTEGER location_id FK
        VARCHAR consumer_id
        INTEGER quantity_sold
        TIMESTAMP sale_date
    }

    STOCK_MOVEMENTS {
        INTEGER movement_id PK
        INTEGER product_id FK
        INTEGER from_location_id FK
        INTEGER to_location_id FK
        VARCHAR movement_type
        INTEGER quantity
        TIMESTAMP movement_date
    }
```

---

### MongoDB Document Model Diagram

```mermaid
erDiagram
    BENEFICIARIES ||--o{ GRIEVANCES : "submits assistance request"
    GRIEVANCES ||--|{ GRIEVANCE_UPDATES : "embeds audit timeline"

    BENEFICIARIES {
        ObjectId _id PK
        string consumer_id UK "Beneficiary ID"
        string name
        string contact
        string address
        string district
        string state_country
        string flood_event_id "References SQL flood_events.event_id"
        string vulnerability_category
        int family_members_count
        string preferences "Ration / medical details"
        string verification_status
        boolean is_synthetic
        date onboarding_date
        boolean is_deleted
    }

    GRIEVANCES {
        ObjectId _id PK
        string grievance_id UK
        string consumer_id FK "References Beneficiaries.consumer_id"
        string flood_event_id "References SQL flood_events.event_id"
        string affected_location
        string category
        string priority
        string status
        string assigned_team
        string resolution
        boolean is_synthetic
        date created_date
        array updates "Embedded timeline objects"
        boolean is_deleted
    }

    GRIEVANCE_UPDATES {
        date timestamp
        string status
        string assigned_team
        string note
        string staff_id
    }
```

---

## 3. Database Operations & Verification

### SQL Operations
1. **CRUD**: Full lifecycle for products, suppliers, disaster warehouse locations, flood events, and CWC telemetry.
2. **JOIN Operations**:
   - 3-Way JOIN for stock levels (`inventory` + `products` + `locations`).
   - 4-Way JOIN for incoming humanitarian procurement (`purchases` + `suppliers` + `products` + `locations`).
   - 5-Way JOIN for relief distribution tracking (`relief_distributions` + `distribution_items` + `products` + `locations` + `flood_events`).
3. **Aggregate Queries (GROUP BY, HAVING)**:
   - Total stock units by warehouse hub.
   - Procurement order volume and units supplied by relief agency (`HAVING SUM(pu.quantity_received) > 0`).
   - Dispatched relief supplies and valuation by product category (`HAVING SUM(di.quantity) > 0`).
   - Disaster operations summary: Relief volume and total valuation aggregated by flood event (`GROUP BY fe.event_id`).
   - Low inventory deficit threshold alerts (`WHERE quantity_on_hand <= reorder_level`).
4. **ACID Transactions**:
   - `record_purchase`: Atomically logs purchase order and increments inventory buffer.
   - `record_relief_distribution`: Verifies stock availability, atomically decrements inventory across all line items, logs master distribution and items, and synchronizes sales tracking. Rolls back atomically on stock deficit.
   - `record_stock_movement`: Validates source depot stock and transfers units atomically.

### MongoDB Operations
1. **Beneficiary Profile Onboarding**:
   - Strict unique index on `consumer_id`.
   - Disaster vulnerability tagging (`DISPLACED_FAMILY`, `ELDERLY`, `CHILD_CARE`, `FEMALE_HEADED_HOUSEHOLD`).
   - Soft deletion pattern preserving transactional audit trails.
2. **Grievance Lifecycle Tracking**:
   - Assistance request filing across categories: `DRINKING_WATER`, `FOOD_RATIONS`, `EMERGENCY_SHELTER`, `TRAUMA_MEDICINE`, `RESCUE_ASSISTANCE`, `INFRASTRUCTURE_HAZARD`.
   - Embedded `$push` updates timeline maintaining immutable timestamps and staff audit identifiers.
   - Filtered retrieval by status (`OPEN`, `IN_PROGRESS`, `RESOLVED`), priority (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), and flood event ID.
