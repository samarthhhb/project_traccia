"""
Comprehensive test suite verifying:
1. SQL Schema integrity, constraints, CRUD operations
2. SQL multi-step transactions (atomic stock increments/decrements)
3. SQL multi-table JOINs and GROUP BY / HAVING aggregations
4. MongoDB consumer onboarding, uniqueness, and soft deletion
5. MongoDB grievance lifecycle, priority filters, and timeline updates
6. Cross-database reference validation
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend import sql_db, mongo_db

TEST_DB = os.path.join(os.path.dirname(__file__), "test_traccia.db")

class TestTracciaSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Set clean isolated test database
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        sql_db.DB_PATH = TEST_DB
        os.environ["TRACCIA_SQL_PATH"] = TEST_DB

        # Initialize SQL schema and Mongo mock with disaster seed data
        from backend.seed_data import seed_all
        seed_all()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(TEST_DB):
            try:
                os.remove(TEST_DB)
            except Exception:
                pass

    def test_01_sql_product_crud_and_constraints(self):
        # Create
        pid = sql_db.create_product("Test Keyboard", "Peripherals", "TEST-KB-001", 49.99)
        self.assertIsInstance(pid, int)

        # Unique SKU constraint violation
        with self.assertRaises(Exception):
            sql_db.create_product("Duplicate SKU Product", "Peripherals", "TEST-KB-001", 10.00)

        # Check Price constraint
        with self.assertRaises(Exception):
            sql_db.create_product("Negative Price Product", "Peripherals", "TEST-KB-NEG", -5.00)

        # Read
        products = sql_db.get_products()
        found = any(p["sku"] == "TEST-KB-001" for p in products)
        self.assertTrue(found)

        # Update
        sql_db.update_product(pid, "Test Keyboard Mechanical", "Peripherals", "TEST-KB-001", 59.99)
        updated = next(p for p in sql_db.get_products() if p["product_id"] == pid)
        self.assertEqual(updated["name"], "Test Keyboard Mechanical")
        self.assertEqual(updated["unit_price"], 59.99)

        # Delete
        ok = sql_db.delete_product(pid)
        self.assertTrue(ok)

    def test_02_sql_atomic_purchase_and_sale_transactions(self):
        import time
        unique_suffix = int(time.time() * 1000)
        # Setup supplier, product, location
        sup_id = sql_db.create_supplier(f"Test Dist Corp {unique_suffix}", "test@distcorp.com")
        prod_id = sql_db.create_product("Monitor 4K", "Display", f"TEST-MON-{unique_suffix}", 299.99)
        loc_id = sql_db.create_location(f"Austin Warehouse {unique_suffix}", "123 Tech Ridge")

        # Purchase transaction: should add 20 units
        po_id = sql_db.record_purchase(sup_id, prod_id, loc_id, 20)
        self.assertIsInstance(po_id, int)

        # Check inventory quantity
        inv = sql_db.get_inventory_records()
        pos = next(r for r in inv if r["product_id"] == prod_id and r["location_id"] == loc_id)
        self.assertEqual(pos["quantity_on_hand"], 20)

        # Sale transaction: sold 5 units
        sale_id = sql_db.record_sale(prod_id, loc_id, 5, consumer_id="CONS-TEST")
        self.assertIsInstance(sale_id, int)

        # Check remaining inventory (should be 15)
        inv = sql_db.get_inventory_records()
        pos = next(r for r in inv if r["product_id"] == prod_id and r["location_id"] == loc_id)
        self.assertEqual(pos["quantity_on_hand"], 15)

        # Oversell transaction must fail and rollback
        with self.assertRaises(ValueError):
            sql_db.record_sale(prod_id, loc_id, 100)

        # Stock remains at 15
        inv = sql_db.get_inventory_records()
        pos = next(r for r in inv if r["product_id"] == prod_id and r["location_id"] == loc_id)
        self.assertEqual(pos["quantity_on_hand"], 15)

    def test_03_sql_joins_and_aggregates(self):
        # Test Purchases Join
        purchases = sql_db.get_purchases_report()
        self.assertIsInstance(purchases, list)
        if purchases:
            p = purchases[0]
            self.assertIn("supplier_name", p)
            self.assertIn("product_name", p)
            self.assertIn("location_name", p)

        # Test Sales Join
        sales = sql_db.get_sales_report()
        self.assertIsInstance(sales, list)

        # Test Location Stock Aggregation
        stock_loc = sql_db.report_stock_by_location()
        self.assertIsInstance(stock_loc, list)
        if stock_loc:
            self.assertIn("total_units_in_stock", stock_loc[0])

        # Test Sales by Product Aggregation
        sales_prod = sql_db.report_sales_by_product()
        self.assertIsInstance(sales_prod, list)

    def test_04_mongodb_consumer_crud(self):
        cid = "CONS-UNIT-99"
        # Create
        c = mongo_db.create_consumer(
            consumer_id=cid,
            name="Alice Wonder",
            contact="alice@wonderland.com",
            preferences="Audio gear",
            verification_status="VERIFIED"
        )
        self.assertEqual(c["consumer_id"], cid)

        # Duplicate ID rejection
        with self.assertRaises(ValueError):
            mongo_db.create_consumer(consumer_id=cid, name="Duplicate Alice", contact="alice2@mail.com")

        # Read
        retrieved = mongo_db.get_consumer_by_id(cid)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["name"], "Alice Wonder")

        # Update
        ok = mongo_db.update_consumer(cid, {"name": "Alice Liddell"})
        self.assertTrue(ok)
        self.assertEqual(mongo_db.get_consumer_by_id(cid)["name"], "Alice Liddell")

        # Soft Delete
        del_ok = mongo_db.delete_consumer(cid, soft_delete=True)
        self.assertTrue(del_ok)
        self.assertIsNone(mongo_db.get_consumer_by_id(cid))

    def test_05_mongodb_grievance_crud_and_lifecycle(self):
        # Setup consumer
        c = mongo_db.create_consumer("CONS-TICKET-01", "Bob Smith", "bob@smith.io")

        # Create Grievance
        gid = "GRV-UNIT-01"
        g = mongo_db.create_grievance(
            grievance_id=gid,
            consumer_id="CONS-TICKET-01",
            category="PRODUCT_DEFECT",
            description="Speaker does not turn on.",
            priority="HIGH",
            assigned_team="Electronics Support"
        )
        self.assertEqual(g["status"], "OPEN")
        self.assertEqual(len(g["updates"]), 1)

        # Update Status & Timeline
        upd_ok = mongo_db.update_grievance(
            grievance_id=gid,
            status="IN_PROGRESS",
            update_note="Diagnostic in progress with hardware team.",
            staff_id="TECH-07"
        )
        self.assertTrue(upd_ok)

        # Check timeline entry
        g_updated = mongo_db.get_grievance_by_id(gid)
        self.assertEqual(g_updated["status"], "IN_PROGRESS")
        self.assertEqual(len(g_updated["updates"]), 2)
        self.assertEqual(g_updated["updates"][-1]["staff_id"], "TECH-07")

        # Resolve
        res_ok = mongo_db.update_grievance(
            grievance_id=gid,
            status="RESOLVED",
            resolution="Replacement provided",
            update_note="Customer confirmed happy"
        )
        self.assertTrue(res_ok)
        g_resolved = mongo_db.get_grievance_by_id(gid)
        self.assertEqual(g_resolved["status"], "RESOLVED")
        self.assertEqual(g_resolved["resolution"], "Replacement provided")

    def test_06_sql_disaster_relief_distributions(self):
        import time
        unique_suffix = int(time.time() * 1000)
        # Create supplier, products, location
        sup_id = sql_db.create_supplier(f"Relief Agency {unique_suffix}", "agency@disaster.in")
        p_food = sql_db.create_product(f"Emergency Ration {unique_suffix}", "Food", f"REL-FOD-{unique_suffix}", 1200.0)
        p_water = sql_db.create_product(f"Water Sachet {unique_suffix}", "Water", f"REL-WAT-{unique_suffix}", 400.0)
        loc_id = sql_db.create_location(f"Forward Relief Hub {unique_suffix}", "Sindhupalchok Relief Sector")

        # Inbound procurement: 50 food packs, 100 water packs
        sql_db.record_purchase(sup_id, p_food, loc_id, 50)
        sql_db.record_purchase(sup_id, p_water, loc_id, 100)

        # Multi-item atomic relief distribution
        dist_id = sql_db.record_relief_distribution(
            location_id=loc_id,
            beneficiary_id="BEN-NEP-TEST",
            items=[
                {"product_id": p_food, "quantity": 10},
                {"product_id": p_water, "quantity": 25}
            ],
            flood_event_id="NEP-2021-MELAMCHI",
            relief_officer="Officer Subba",
            notes="Helicopter drops in remote ward"
        )
        self.assertIsInstance(dist_id, int)

        # Check decremented inventory
        inv = sql_db.get_inventory_records()
        stock_food = next(r["quantity_on_hand"] for r in inv if r["product_id"] == p_food and r["location_id"] == loc_id)
        stock_water = next(r["quantity_on_hand"] for r in inv if r["product_id"] == p_water and r["location_id"] == loc_id)
        self.assertEqual(stock_food, 40)
        self.assertEqual(stock_water, 75)

        # Insufficient stock test must fail and rollback
        with self.assertRaises(ValueError):
            sql_db.record_relief_distribution(
                location_id=loc_id,
                beneficiary_id="BEN-NEP-TEST",
                items=[{"product_id": p_food, "quantity": 999}],
                flood_event_id="NEP-2021-MELAMCHI"
            )

        # Stock remained unchanged at 40
        inv = sql_db.get_inventory_records()
        stock_food_after = next(r["quantity_on_hand"] for r in inv if r["product_id"] == p_food and r["location_id"] == loc_id)
        self.assertEqual(stock_food_after, 40)

        # Verify JOIN report
        rep = sql_db.get_relief_distributions_report()
        self.assertTrue(any(r["distribution_id"] == dist_id for r in rep))

    def test_07_flood_events_and_cross_database_integration(self):
        # Verify Nepal Melamchi case study exists
        nepal_event = sql_db.get_flood_event_by_id("NEP-2021-MELAMCHI")
        self.assertIsNotNone(nepal_event)
        self.assertEqual(nepal_event["country"], "Nepal")
        self.assertIn("Melamchi", nepal_event["river_basin"])
        self.assertIn("HydroShare", nepal_event["source_dataset"])

        # Verify Indian flood dataset event
        bihar_event = sql_db.get_flood_event_by_id("IND-2019-BIHAR")
        self.assertIsNotNone(bihar_event)
        self.assertEqual(bihar_event["country"], "India")
        self.assertIn("Zenodo", bihar_event["source_dataset"])

        # Verify CWC rainfall telemetry data
        stations = sql_db.get_rainfall_telemetry()
        self.assertTrue(len(stations) >= 3)
        melamchi_st = next((s for s in stations if s["station_id"] == "CWC-NEP-MEL-01"), None)
        self.assertIsNotNone(melamchi_st)
        self.assertEqual(melamchi_st["alert_level"], "EXTREME")

        # Verify MongoDB Beneficiary linked to flood event
        beneficiaries = mongo_db.get_consumers(flood_event_id="NEP-2021-MELAMCHI")
        self.assertTrue(len(beneficiaries) >= 1)
        self.assertTrue(all(b["flood_event_id"] == "NEP-2021-MELAMCHI" for b in beneficiaries))

        # Verify MongoDB Grievances filtered by flood event
        grievances = mongo_db.get_grievances(flood_event_id="NEP-2021-MELAMCHI")
        self.assertTrue(len(grievances) >= 1)

if __name__ == "__main__":
    unittest.main()
