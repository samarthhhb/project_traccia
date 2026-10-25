"""
Seed realistic disaster response and inventory management data for SQL and MongoDB.
Optimised for Indian Operational Requirements and Nepal 2021 Melamchi Flood Case Study.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.sql_db import (
    init_sql_db, get_products, create_product, create_supplier, create_location,
    create_flood_event, create_or_update_telemetry,
    record_purchase, record_relief_distribution, record_stock_movement
)
from backend.mongo_db import get_consumers, create_consumer, create_grievance, update_grievance

def seed_sql():
    print("Initializing SQL Schema for Disaster Response & Inventory...")
    init_sql_db()

    print("Seeding Flood Disaster Datasets (Nepal Melamchi & Indian Flood Inventory)...")
    # 1. Nepal 2021 Melamchi Flood Dataset
    create_flood_event(
        event_id="NEP-2021-MELAMCHI",
        event_name="2021 Melamchi River Flash Flood & Debris Flow",
        country="Nepal",
        state_province="Sindhupalchok (Bagmati Province)",
        river_basin="Melamchi-Indrawati Basin",
        start_date="2021-06-15",
        end_date="2021-06-25",
        severity="CATASTROPHIC",
        displaced_population=2600,
        casualties=25,
        source_dataset="Nepal-FRES: 2021 Melamchi Flood Data (HydroShare)",
        geospatial_notes="Breach of upstream landslide-dammed lake in Bremdang/Helambu causing catastrophic debris flow; heavy aggradation in Melamchi Bazaar; washed away 5+ bridges; damaged Melamchi Water Supply Project."
    )

    # 2. Indian Flood Inventory Datasets (1967-2023)
    create_flood_event(
        event_id="IND-2018-KERALA",
        event_name="2018 Great Kerala Monsoon Inundation",
        country="India",
        state_province="Kerala",
        river_basin="Periyar & Pamba Basins",
        start_date="2018-08-08",
        end_date="2018-08-28",
        severity="CATASTROPHIC",
        displaced_population=1450000,
        casualties=483,
        source_dataset="India Flood Inventory and Impacts (1967–2023) (Zenodo)",
        geospatial_notes="Abnormally high monsoon rainfall; 35 out of 54 major reservoirs opened; severe inundation across Ernakulam, Alappuzha, Thrissur and Wayanad districts."
    )

    create_flood_event(
        event_id="IND-2019-BIHAR",
        event_name="2019 North Bihar Flood Crisis",
        country="India",
        state_province="Bihar",
        river_basin="Kosi, Gandak & Bagmati Basins",
        start_date="2019-07-11",
        end_date="2019-08-10",
        severity="SEVERE",
        displaced_population=8850000,
        casualties=130,
        source_dataset="India Flood Inventory and Impacts (1967–2023) (Zenodo)",
        geospatial_notes="Inundation across 13 districts including Darbhanga, Sitamarhi, Madhubani; breach of river embankments along Bagmati and Kamla Balan rivers."
    )

    create_flood_event(
        event_id="IND-2020-ASSAM",
        event_name="2020 Assam Brahmaputra Monsoon Flood",
        country="India",
        state_province="Assam",
        river_basin="Brahmaputra & Barak Basins",
        start_date="2020-05-22",
        end_date="2020-07-30",
        severity="SEVERE",
        displaced_population=5600000,
        casualties=118,
        source_dataset="India Flood Inventory and Impacts (1967–2023) (Zenodo)",
        geospatial_notes="Multiple flood waves submerging 30 districts; 85% of Kaziranga National Park inundated; critical bank erosion across Majuli and Dhubri."
    )

    create_flood_event(
        event_id="IND-2021-UTTARAKHAND",
        event_name="2021 Chamoli Glacial Flash Flood Disaster",
        country="India",
        state_province="Uttarakhand",
        river_basin="Alaknanda & Dhauliganga Basins",
        start_date="2021-02-07",
        end_date="2021-02-15",
        severity="CATASTROPHIC",
        displaced_population=4500,
        casualties=204,
        source_dataset="India Flood Inventory and Impacts (1967–2023) (Zenodo)",
        geospatial_notes="Massive rock/ice avalanche from Ronti Peak triggering flash flood in Rishiganga; destruction of Tapovan Vishnugad Hydropower Project infrastructure."
    )

    print("Seeding CWC Telemetry Hourly Rainfall & River Levels...")
    create_or_update_telemetry(
        station_id="CWC-NEP-MEL-01",
        station_name="Melamchi Hydrology Post",
        state_or_region="Sindhupalchok, Nepal",
        river_basin="Melamchi-Indrawati",
        hourly_rainfall_mm=42.5,
        cumulative_24h_mm=182.0,
        danger_level_meters=8.50,
        current_water_level_meters=9.85,
        alert_level="EXTREME",
        source_dataset="Nepal-FRES HydroShare Telemetry"
    )

    create_or_update_telemetry(
        station_id="CWC-ASM-GHY-01",
        station_name="Guwahati CWC River Gauge",
        state_or_region="Assam, India",
        river_basin="Brahmaputra",
        hourly_rainfall_mm=18.2,
        cumulative_24h_mm=96.4,
        danger_level_meters=49.68,
        current_water_level_meters=50.12,
        alert_level="DANGER",
        source_dataset="CWC Telemetry Hourly Rainfall Data (NWIC)"
    )

    create_or_update_telemetry(
        station_id="CWC-BHR-PAT-02",
        station_name="Patna Digha Telemetry Station",
        state_or_region="Bihar, India",
        river_basin="Ganga",
        hourly_rainfall_mm=12.0,
        cumulative_24h_mm=74.0,
        danger_level_meters=50.45,
        current_water_level_meters=49.80,
        alert_level="WARNING",
        source_dataset="CWC Telemetry Hourly Rainfall Data (NWIC)"
    )

    create_or_update_telemetry(
        station_id="CWC-KER-COI-03",
        station_name="Aluva River Monitoring Post",
        state_or_region="Kerala, India",
        river_basin="Periyar",
        hourly_rainfall_mm=8.5,
        cumulative_24h_mm=58.2,
        danger_level_meters=3.50,
        current_water_level_meters=3.10,
        alert_level="ADVISORY",
        source_dataset="CWC Telemetry Hourly Rainfall Data (NWIC)"
    )

    create_or_update_telemetry(
        station_id="CWC-UK-RSH-04",
        station_name="Rishikesh Hydrological Station",
        state_or_region="Uttarakhand, India",
        river_basin="Upper Ganga",
        hourly_rainfall_mm=4.5,
        cumulative_24h_mm=32.0,
        danger_level_meters=340.50,
        current_water_level_meters=338.20,
        alert_level="NORMAL",
        source_dataset="CWC Telemetry Hourly Rainfall Data (NWIC)"
    )

    existing_products = get_products()
    if not existing_products:
        print("Seeding Disaster Relief Products & Supplies...")
        p1 = create_product("Emergency Dry Rations Pack (10-Day Family Supply)", "Emergency Food & Nutrition", "REL-RAT-10D", 1850.00)
        p2 = create_product("Potable Water Purification Sachets (500 Pack)", "Water & Sanitation", "REL-WTR-500", 650.00)
        p3 = create_product("Disaster Trauma First Aid & Suture Kit", "Medical Supplies", "REL-MED-FAK", 2400.00)
        p4 = create_product("All-Weather Family Relief Tent (6-Person)", "Temporary Shelter", "REL-SHL-TNT6", 5800.00)
        p5 = create_product("Heavy-Duty Inflatable Rescue Boat with Oars", "Rescue Equipment", "REL-RSC-BOAT", 34500.00)
        p6 = create_product("High-Output Solar Emergency Lantern & Power Bank", "Power & Lighting", "REL-SOL-PWR", 1250.00)
        p7 = create_product("High-Capacity Diesel Dewatering Pump (5HP)", "Flood Drainage & Pumps", "REL-PMP-5HP", 28000.00)
        p8 = create_product("Family Hygiene & Sanitation Pack", "Sanitation", "REL-HYG-FAM", 750.00)

        print("Seeding Relief Suppliers & Humanitarian Agencies...")
        s1 = create_supplier("National Disaster Response Force (NDRF) Logistics Depot", "procurement@ndrf.gov.in | +91-11-24363260 (New Delhi)")
        s2 = create_supplier("Indian Red Cross Society Disaster Management Centre", "relief@indianredcross.org | +91-11-23716441 (New Delhi)")
        s3 = create_supplier("Nepal Red Cross Society Central Operations", "disaster.mgmt@nrcs.org | +977-1-4270650 (Kathmandu)")
        s4 = create_supplier("UNICEF South Asia Humanitarian Supplies", "emergency.supply@unicef.org | +91-11-24690401")
        s5 = create_supplier("Himalayan Emergency Life Logistics", "support@himalayanrelief.org | +977-1-4412345 (Pokhara/Sindhupalchok)")
        s6 = create_supplier("Bharat Medical & Surgical Relief Corp", "orders@bharatmedrelief.in | +91-361-2521199 (Guwahati)")

        print("Seeding Disaster Response Warehouses & Relief Hubs...")
        l1 = create_location("Melamchi Disaster Response Base (Sindhupalchok)", "Bazaar Road, Ward 11, Melamchi, Sindhupalchok, Bagmati, Nepal")
        l2 = create_location("Guwahati Regional Disaster Logistics Depot", "NH-37 Inland Container Depot, Guwahati, Assam, India")
        l3 = create_location("Patna Flood Emergency Warehouse", "Boring Road Industrial Estate, Patna, Bihar, India")
        l4 = create_location("Ernakulam Disaster Relief Hub", "Kalamassery Operations Complex, Kochi, Kerala, India")
        l5 = create_location("Dehradun Mountain Logistics Base", "Saharanpur Road Relief Depot, Dehradun, Uttarakhand, India")
        l6 = create_location("Silchar Forward Relief Distribution Camp", "National Highway Point, Silchar, Cachar, Assam, India")

        print("Executing Purchase Transactions (Incoming Stock Procurement)...")
        # Incoming relief supplies into regional hubs
        record_purchase(s1, p1, l2, 500) # 500 dry ration packs at Guwahati
        record_purchase(s1, p2, l2, 1000) # 1000 water sachets at Guwahati
        record_purchase(s6, p3, l2, 150) # 150 trauma kits at Guwahati
        record_purchase(s1, p5, l2, 20)  # 20 rescue boats at Guwahati
        record_purchase(s2, p4, l3, 200) # 200 relief tents at Patna
        record_purchase(s2, p1, l3, 600) # 600 dry ration packs at Patna
        record_purchase(s2, p2, l3, 500) # 500 water purification sachets at Patna
        record_purchase(s3, p1, l1, 350) # 350 dry ration packs at Melamchi Base
        record_purchase(s5, p2, l1, 800) # 800 water sachets at Melamchi Base
        record_purchase(s3, p4, l1, 100) # 100 relief tents at Melamchi Base
        record_purchase(s5, p6, l1, 180) # 180 solar lanterns at Melamchi Base
        record_purchase(s4, p8, l4, 400) # 400 hygiene packs at Ernakulam
        record_purchase(s1, p7, l4, 15)  # 15 dewatering pumps at Ernakulam
        record_purchase(s2, p3, l5, 80)  # 80 trauma kits at Dehradun

        print("Executing Stock Movements & Forward Deployment...")
        # Transfer 120 dry ration packs and 200 water sachets from Guwahati to Silchar forward camp
        record_stock_movement(p1, "TRANSFER", 120, from_location_id=l2, to_location_id=l6)
        record_stock_movement(p2, "TRANSFER", 200, from_location_id=l2, to_location_id=l6)
        # Adjustment/verification at Melamchi Base
        record_stock_movement(p6, "ADJUSTMENT", 175, to_location_id=l1)

        print("Executing Relief Distribution Transactions (Atomic Multi-Item Dispatches)...")
        # Dispatch relief kit to Pemba Sherpa in Melamchi
        record_relief_distribution(
            location_id=l1,
            beneficiary_id="BEN-NEP-2001",
            items=[
                {"product_id": p1, "quantity": 2}, # 2 ration packs
                {"product_id": p2, "quantity": 5}, # 5 water purification packs
                {"product_id": p6, "quantity": 1}  # 1 solar lantern
            ],
            flood_event_id="NEP-2021-MELAMCHI",
            relief_officer="Capt. Arpan Thapa (Nepal Army Relief Wing)",
            notes="Helicopter airdrop & base distribution at Melamchi Bazaar relief station"
        )

        # Dispatch shelter & rations to Sunita Adhikari in Helambu
        record_relief_distribution(
            location_id=l1,
            beneficiary_id="BEN-NEP-2002",
            items=[
                {"product_id": p4, "quantity": 1}, # 1 all-weather family tent
                {"product_id": p1, "quantity": 2}  # 2 ration packs
            ],
            flood_event_id="NEP-2021-MELAMCHI",
            relief_officer="Sushila Tamang (Nepal Red Cross Sindhupalchok)",
            notes="High-altitude porter dispatch to Helambu upper riverside"
        )

        # Dispatch to Rameshwar Sharma in Bihar
        record_relief_distribution(
            location_id=l3,
            beneficiary_id="BEN-IND-1001",
            items=[
                {"product_id": p1, "quantity": 3},
                {"product_id": p2, "quantity": 4}
            ],
            flood_event_id="IND-2019-BIHAR",
            relief_officer="Inspector R. K. Yadav (Bihar SDRF)",
            notes="Boat-delivered relief package at Darbhanga camp"
        )

        # Dispatch to Ananya Nair in Kerala
        record_relief_distribution(
            location_id=l4,
            beneficiary_id="BEN-IND-1002",
            items=[
                {"product_id": p8, "quantity": 2}
            ],
            flood_event_id="IND-2018-KERALA",
            relief_officer="Mathew Varghese (Kerala Disaster Management)",
            notes="Camp distribution at Meenangadi Wayanad"
        )

def seed_mongo():
    existing_consumers = get_consumers()
    if not existing_consumers:
        print("Seeding MongoDB Disaster Beneficiaries (Clearly Labelled Synthetic Data)...")
        create_consumer(
            consumer_id="BEN-NEP-2001",
            name="Pemba Sherpa",
            contact="+977-9841-892104 | pemba.s@himalmail.np",
            preferences="SMS in Nepali; Elderly parents at home, requires dry rations & warm blankets",
            verification_status="VERIFIED",
            address="Ward 11, Melamchi Bazaar, Sindhupalchok",
            district="Sindhupalchok",
            state_country="Bagmati Province, Nepal",
            flood_event_id="NEP-2021-MELAMCHI",
            vulnerability_category="DISPLACED_FAMILY",
            family_members_count=5,
            is_synthetic=True
        )

        create_consumer(
            consumer_id="BEN-NEP-2002",
            name="Sunita Adhikari",
            contact="+977-9803-128475",
            preferences="Needs immediate shelter tent; 2 infant children in family",
            verification_status="VERIFIED",
            address="Helambu Riverside Settlement, Sindhupalchok",
            district="Sindhupalchok",
            state_country="Bagmati Province, Nepal",
            flood_event_id="NEP-2021-MELAMCHI",
            vulnerability_category="FEMALE_HEADED_HOUSEHOLD",
            family_members_count=4,
            is_synthetic=True
        )

        create_consumer(
            consumer_id="BEN-IND-1001",
            name="Rameshwar Sharma",
            contact="+91-98350-41234",
            preferences="Ration Card: BHR-992144; Diabetic patient in shelter",
            verification_status="VERIFIED",
            address="Ward 4 Relief Camp, Darbhanga",
            district="Darbhanga",
            state_country="Bihar, India",
            flood_event_id="IND-2019-BIHAR",
            vulnerability_category="ELDERLY",
            family_members_count=6,
            is_synthetic=True
        )

        create_consumer(
            consumer_id="BEN-IND-1002",
            name="Ananya Nair",
            contact="+91-94471-88290",
            preferences="Malayalam communications; Requires replacement solar lantern",
            verification_status="VERIFIED",
            address="Meenangadi Community Shelter, Wayanad",
            district="Wayanad",
            state_country="Kerala, India",
            flood_event_id="IND-2018-KERALA",
            vulnerability_category="CHILD_CARE",
            family_members_count=3,
            is_synthetic=True
        )

        create_consumer(
            consumer_id="BEN-IND-1003",
            name="Biren Kalita",
            contact="+91-98640-19283",
            preferences="Assamese; Crop submerged, urgent family food sustenance",
            verification_status="PENDING",
            address="Silchar Flood Relief Camp 2, Cachar",
            district="Cachar",
            state_country="Assam, India",
            flood_event_id="IND-2020-ASSAM",
            vulnerability_category="DISPLACED_FARMER",
            family_members_count=5,
            is_synthetic=True
        )

        create_consumer(
            consumer_id="BEN-IND-1004",
            name="Devendra Rawat",
            contact="+91-97580-23910",
            preferences="Evacuee from Rishiganga valley; Emergency trauma dressings needed",
            verification_status="VERIFIED",
            address="Joshimath Evacuation Shelter, Chamoli",
            district="Chamoli",
            state_country="Uttarakhand, India",
            flood_event_id="IND-2021-UTTARAKHAND",
            vulnerability_category="GENERAL",
            family_members_count=4,
            is_synthetic=True
        )

        print("Seeding MongoDB Grievances & Lifecycle Updates...")
        create_grievance(
            grievance_id="GRV-NEP-001",
            consumer_id="BEN-NEP-2001",
            category="DRINKING_WATER",
            description="Upstream debris flow severed the main water supply pipe in Melamchi Bazaar Ward 11; immediate water purification packs needed for 30 displaced households.",
            priority="CRITICAL",
            assigned_team="Nepal Red Cross Sindhupalchok Rapid Unit",
            affected_location="Melamchi Bazaar Ward 11, Sindhupalchok",
            flood_event_id="NEP-2021-MELAMCHI"
        )
        update_grievance(
            grievance_id="GRV-NEP-001",
            status="IN_PROGRESS",
            assigned_team="Nepal Red Cross Sindhupalchok Rapid Unit",
            update_note="Field team dispatched with 250 water purification sachets; mobile water filtration rig en route from Kathmandu.",
            staff_id="DISPATCH_OFFICER_04"
        )

        create_grievance(
            grievance_id="GRV-NEP-002",
            consumer_id="BEN-NEP-2002",
            category="EMERGENCY_SHELTER",
            description="Helambu riverside home completely washed away by flash flood; family currently under temporary plastic sheet, urgently requires all-weather 6-person tent.",
            priority="HIGH",
            assigned_team="Himalayan Emergency Response Wing",
            affected_location="Helambu Riverside Settlement, Sindhupalchok",
            flood_event_id="NEP-2021-MELAMCHI"
        )
        update_grievance(
            grievance_id="GRV-NEP-002",
            status="RESOLVED",
            assigned_team="Himalayan Emergency Response Wing",
            resolution="6-person all-weather family tent erected on elevated terrace above flood line.",
            update_note="Tent delivered and pitched by volunteer team. Beneficiary provided safe shelter.",
            staff_id="FIELD_LEAD_NEPAL"
        )

        create_grievance(
            grievance_id="GRV-IND-001",
            consumer_id="BEN-IND-1001",
            category="TRAUMA_MEDICINE",
            description="Elderly beneficiary requires emergency antiseptic dressing and antibiotic supply following laceration during Darbhanga flood evacuation.",
            priority="HIGH",
            assigned_team="Bihar SDRF Medical Unit",
            affected_location="Ward 4 Relief Camp, Darbhanga, Bihar",
            flood_event_id="IND-2019-BIHAR"
        )
        update_grievance(
            grievance_id="GRV-IND-001",
            status="RESOLVED",
            assigned_team="Bihar SDRF Medical Unit",
            resolution="Wound cleaned, sutured, and dressed by medical officer. Antibiotic course administered.",
            update_note="Patient stable and under observation at base clinic.",
            staff_id="DR_BIHAR_RELIEF"
        )

        create_grievance(
            grievance_id="GRV-IND-002",
            consumer_id="BEN-IND-1003",
            category="FOOD_RATIONS",
            description="Community shelter running out of dry rations for 45 children and elderly evacuees cut off by Brahmaputra floodwaters near Silchar.",
            priority="CRITICAL",
            assigned_team="NDRF 1st Battalion Field Station",
            affected_location="Silchar Flood Relief Camp 2, Cachar, Assam",
            flood_event_id="IND-2020-ASSAM"
        )

        create_grievance(
            grievance_id="GRV-IND-003",
            consumer_id="BEN-IND-1002",
            category="RELIEF_KIT_DAMAGE",
            description="Solar lantern received in relief pack sustained water damage during river transit; replacement unit requested for night illumination at camp.",
            priority="MEDIUM",
            assigned_team="Kerala Disaster Management Cell",
            affected_location="Meenangadi Community Shelter, Wayanad",
            flood_event_id="IND-2018-KERALA"
        )
        update_grievance(
            grievance_id="GRV-IND-003",
            status="IN_PROGRESS",
            assigned_team="Kerala Disaster Management Cell",
            update_note="Replacement solar lantern logged for next supply sortie to Wayanad camp.",
            staff_id="OFFICER_KERALA_DESK"
        )

def seed_all():
    seed_sql()
    seed_mongo()
    print("Seed complete! Traccia database populated with Indian and Nepal disaster response data.")

if __name__ == "__main__":
    seed_all()
