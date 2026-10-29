# UN Sustainable Development Goals (SDG) Mapping

TRACCIA is a hybrid database management system designed for disaster response operations and humanitarian inventory logistics. This document provides the formal mapping between TRACCIA's technical implementation (relational SQL database, MongoDB document store, and FastAPI orchestration layer) and the **United Nations 2030 Agenda for Sustainable Development**.

---

## Executive Summary Matrix

| UN SDG | Goal Title | Technical Layer | Schemas / Collections Involved | Key Mechanism | Operational Impact |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **SDG 11** | Sustainable Cities & Communities | SQL Relational | `flood_events`, `locations`, `relief_distributions` | Geospatial disaster tracking, field camp supply line allocation | Rapid urban recovery & reduced disaster mortality (Target 11.5) |
| **SDG 13** | Climate Action | SQL Relational | `cwc_rainfall_telemetry` | Real-time CWC river gauge ingestion & threshold danger alerts | Early warning & proactive staging ahead of flood crests (Target 13.1 & 13.3) |
| **SDG 6** | Clean Water & Sanitation | Hybrid Engine | `products`, `grievances`, `distribution_items` | Potable water purification tracking (`REL-WTR-500`) & camp water outage ticketing | Prevention of waterborne disease outbreaks (Target 6.1 & 6.2) |
| **SDG 2** | Zero Hunger | SQL Relational | `inventory`, `purchases`, `suppliers` | Emergency ration tracking (`REL-RAT-10D`) & automated reorder alarms | Elimination of nutrition bottlenecks in cutoff zones (Target 2.1) |
| **SDG 12** | Responsible Consumption | SQL Relational | `stock_movements`, `purchases`, ACID engine | Atomic dispatches with rollback on shortfall; multi-warehouse transfers | Elimination of aid hoarding, spoilage, and ghost distributions (Target 12.5) |
| **SDG 16** | Peace, Justice & Strong Institutions | MongoDB Document | `grievances`, `consumers` | Chronological `$push` audit trails & public grievance lifecycle | Transparent aid distribution and corruption-free delivery (Target 16.6 & 16.7) |

---

## Detailed Goal Alignments

### 1. SDG 11: Sustainable Cities and Communities
> **Target 11.5:** *By 2030, significantly reduce the number of deaths and the number of people affected and substantially decrease the direct economic losses relative to global gross domestic product caused by disasters, including water-related disasters, with a focus on protecting the poor and people in vulnerable situations.*

- **Technical Implementation**:
  - The `flood_events` table models historical disaster benchmarks (such as the 2021 Nepal Melamchi flash flood, the 2018 Kerala floods, and the 2019 Bihar crisis).
  - Cross-references affected district populations, river basin inundation extents, and regional warehouse nodes (`locations`).
  - Dispatches route life-saving aid directly to verified field camps and relief sectors, accelerating post-flood urban restoration.

### 2. SDG 13: Climate Action
> **Target 13.1 & 13.3:** *Strengthen resilience and adaptive capacity to climate-related hazards and natural disasters; improve education, awareness-raising and human and institutional capacity on climate change mitigation, adaptation, impact reduction and early warning.*

- **Technical Implementation**:
  - The `cwc_rainfall_telemetry` engine continuously ingests river gauge readings, comparing current water levels against official danger marks.
  - Automatically calculates threshold status codes (`EXTREME`, `DANGER`, `WARNING`, `ADVISORY`, `NORMAL`).
  - Gives disaster authorities a live operational feed to stage rescue boats (`REL-RSC-BOAT`) and emergency pumps before embankments fail.

### 3. SDG 6: Clean Water and Sanitation (WASH)
> **Target 6.1 & 6.2:** *Achieve universal and equitable access to safe and affordable drinking water and adequate sanitation and hygiene for all, paying special attention to the needs of vulnerable populations in emergencies.*

- **Technical Implementation**:
  - Direct tracking of water purification sachets (`REL-WTR-500`, 500-pack chlorine purification) and family hygiene packs (`REL-HYG-FAM`).
  - Citizens register water contamination or lack of drinking supply through MongoDB grievance tickets (`Category: WATER_SANITATION`).
  - High-priority tickets trigger dewatering pump dispatches (`REL-PMP-5HP`) to flooded wells and shelters.

### 4. SDG 2: Zero Hunger
> **Target 2.1:** *End hunger and ensure access by all people, in particular the poor and people in vulnerable situations, including infants, to safe, nutritious and sufficient food all year round.*

- **Technical Implementation**:
  - Catalogs 10-day family emergency ration packs (`REL-RAT-10D`).
  - Automated low-stock trigger (`quantity <= reorder_level`) prevents supply gaps in regional warehouses.
  - Multi-item dispatch forms enforce minimum nutritional quotas for registered displaced families.

### 5. SDG 12: Responsible Consumption and Production
> **Target 12.5:** *Substantially reduce waste generation through prevention, reduction, recycling and audited supply chains.*

- **Technical Implementation**:
  - All inventory adjustments operate under strict ACID transactions in SQL. If any requested item exceeds warehouse availability, the entire dispatch transaction rolls back, preventing inventory corruption or inaccurate stock claims.
  - The `stock_movements` table records inter-depot rebalancing, allowing managers to transfer surplus supplies to regions with critical deficits before goods expire.

### 6. SDG 16: Peace, Justice and Strong Institutions
> **Target 16.6 & 16.7:** *Develop effective, accountable and transparent institutions at all levels; ensure responsive, inclusive, participatory and representative decision-making at all levels.*

- **Technical Implementation**:
  - MongoDB stores grievances with embedded chronological timelines via atomic `$push`.
  - Every status change, assignment to response teams (e.g., *NDRF Relief Team Alpha*), and field action is timestamped and recorded.
  - Mitigates aid diversion, ensures vulnerable groups (women, children, elderly) receive verified aid, and gives oversight agencies an auditable record of every disaster interaction.
