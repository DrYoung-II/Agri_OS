"""
database.py
Lightweight local persistence layer using SQLite (stdlib only - no external DB needed).
Stores: farms, livestock batches, crop plots, financial transactions, chat history,
feed inventory, mortality logs, vaccination schedules, and batch harvests.
"""

import sqlite3
import datetime
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent.parent / "agri_os.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        
        # Farms
        c.execute("""
            CREATE TABLE IF NOT EXISTS farms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                country TEXT,
                region TEXT,
                farm_type TEXT,
                currency TEXT DEFAULT 'NGN',
                phone_number TEXT,
                created_at TEXT
            )
        """)
        
        # Backward-compatible column check for phone_number
        cursor = conn.execute("PRAGMA table_info(farms)")
        cols = [r["name"] for r in cursor.fetchall()]
        if "phone_number" not in cols:
            conn.execute("ALTER TABLE farms ADD COLUMN phone_number TEXT")

        # Livestock Batches
        c.execute("""
            CREATE TABLE IF NOT EXISTS livestock_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER,
                species TEXT,
                breed TEXT,
                stage TEXT,
                count INTEGER,
                initial_count INTEGER,
                avg_weight_kg REAL,
                age_weeks REAL,
                start_date TEXT,
                feed_type TEXT,
                feed_price_per_kg REAL,
                status TEXT DEFAULT 'active', -- active, harvested, archived
                notes TEXT,
                created_at TEXT
            )
        """)
        
        # Check columns for livestock_batches
        cursor = conn.execute("PRAGMA table_info(livestock_batches)")
        cols = [r["name"] for r in cursor.fetchall()]
        if "initial_count" not in cols:
            conn.execute("ALTER TABLE livestock_batches ADD COLUMN initial_count INTEGER")
        if "status" not in cols:
            conn.execute("ALTER TABLE livestock_batches ADD COLUMN status TEXT DEFAULT 'active'")

        # Crop Plots
        c.execute("""
            CREATE TABLE IF NOT EXISTS crop_plots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER,
                crop TEXT,
                area_ha REAL,
                planting_date TEXT,
                soil_type TEXT,
                fertilizer_used TEXT,
                status TEXT DEFAULT 'active', -- active, harvested
                notes TEXT,
                created_at TEXT
            )
        """)
        
        # Check columns for crop_plots
        cursor = conn.execute("PRAGMA table_info(crop_plots)")
        cols = [r["name"] for r in cursor.fetchall()]
        if "status" not in cols:
            conn.execute("ALTER TABLE crop_plots ADD COLUMN status TEXT DEFAULT 'active'")

        # Transactions (Ledger)
        c.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER,
                batch_id INTEGER,
                tx_type TEXT,       -- income / expense
                category TEXT,
                amount REAL,
                tx_date TEXT,
                notes TEXT,
                created_at TEXT
            )
        """)

        # Chat history
        c.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER,
                role TEXT,
                content TEXT,
                channel TEXT DEFAULT 'web', -- web, whatsapp, sms
                created_at TEXT
            )
        """)

        # Feed Inventory
        c.execute("""
            CREATE TABLE IF NOT EXISTS feed_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farm_id INTEGER NOT NULL,
                feed_name TEXT NOT NULL,
                category TEXT, -- Commercial Starter, Finisher, Mash, Raw Ingredient
                quantity_bags REAL DEFAULT 0,
                bag_weight_kg REAL DEFAULT 25.0,
                total_kg REAL DEFAULT 0,
                cost_per_bag REAL DEFAULT 0,
                minimum_alert_bags REAL DEFAULT 3.0,
                notes TEXT,
                updated_at TEXT
            )
        """)

        # Mortality & Health Logs
        c.execute("""
            CREATE TABLE IF NOT EXISTS mortality_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                log_date TEXT NOT NULL,
                count_dead INTEGER NOT NULL,
                cause_symptoms TEXT,
                action_taken TEXT,
                recorded_at TEXT
            )
        """)

        # Vaccination & Preventative Medication Schedules
        c.execute("""
            CREATE TABLE IF NOT EXISTS vaccination_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                vaccine_name TEXT NOT NULL,
                target_disease TEXT,
                due_day_age INTEGER,
                due_date TEXT,
                status TEXT DEFAULT 'pending', -- pending, completed, skipped
                administered_date TEXT,
                notes TEXT,
                created_at TEXT
            )
        """)

        # Batch Harvests / Sales
        c.execute("""
            CREATE TABLE IF NOT EXISTS batch_harvests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                harvest_date TEXT NOT NULL,
                units_sold INTEGER NOT NULL,
                total_weight_kg REAL,
                avg_weight_kg REAL,
                price_per_unit_or_kg REAL,
                total_revenue REAL,
                feed_cost REAL,
                other_cost REAL,
                net_profit REAL,
                notes TEXT,
                recorded_at TEXT
            )
        """)


# ---------- Farms ----------
def create_farm(name, country, region, farm_type, currency="NGN", phone_number=""):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO farms (name, country, region, farm_type, currency, phone_number, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (name, country, region, farm_type, currency, phone_number.strip(), datetime.datetime.now().isoformat()),
        )
        return cur.lastrowid


def get_farms():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM farms ORDER BY id DESC").fetchall()]


def get_farm(farm_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM farms WHERE id=?", (farm_id,)).fetchone()
        return dict(row) if row else None


def get_farm_by_phone(phone_number):
    if not phone_number:
        return None
    # Normalize phone: remove spaces and dashes
    clean_phone = "".join(c for c in str(phone_number) if c.isdigit() or c == "+")
    with get_conn() as conn:
        # Search either exact match or ends-with match (for country code variations)
        rows = conn.execute("SELECT * FROM farms").fetchall()
        for r in rows:
            db_phone = "".join(c for c in str(r["phone_number"] or "") if c.isdigit() or c == "+")
            if db_phone and (clean_phone == db_phone or clean_phone.endswith(db_phone[-9:]) or db_phone.endswith(clean_phone[-9:])):
                return dict(r)
        return None


def update_farm_phone(farm_id, phone_number):
    with get_conn() as conn:
        conn.execute("UPDATE farms SET phone_number=? WHERE id=?", (phone_number.strip(), farm_id))


# ---------- Livestock ----------
def add_livestock_batch(farm_id, **kwargs):
    fields = ["species", "breed", "stage", "count", "initial_count", "avg_weight_kg", "age_weeks",
              "start_date", "feed_type", "feed_price_per_kg", "status", "notes"]
    if "initial_count" not in kwargs or kwargs["initial_count"] is None:
        kwargs["initial_count"] = kwargs.get("count", 0)
    if "status" not in kwargs or not kwargs["status"]:
        kwargs["status"] = "active"

    values = [kwargs.get(f) for f in fields]
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO livestock_batches (farm_id,{','.join(fields)},created_at) "
            f"VALUES (?,{','.join(['?']*len(fields))},?)",
            [farm_id] + values + [datetime.datetime.now().isoformat()],
        )
        batch_id = cur.lastrowid

    # Auto-generate standard African vaccination schedule if poultry
    if "Poultry" in kwargs.get("species", "") or "Broiler" in kwargs.get("species", "") or "Layer" in kwargs.get("species", ""):
        generate_standard_poultry_schedule(batch_id, kwargs.get("start_date"), kwargs.get("species"))

    return batch_id


def get_livestock_batches(farm_id, status=None):
    with get_conn() as conn:
        if status:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM livestock_batches WHERE farm_id=? AND status=? ORDER BY id DESC", (farm_id, status)
            ).fetchall()]
        return [dict(r) for r in conn.execute(
            "SELECT * FROM livestock_batches WHERE farm_id=? ORDER BY id DESC", (farm_id,)
        ).fetchall()]


def get_livestock_batch(batch_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM livestock_batches WHERE id=?", (batch_id,)).fetchone()
        return dict(row) if row else None


def update_batch_count(batch_id, new_count):
    with get_conn() as conn:
        conn.execute("UPDATE livestock_batches SET count=? WHERE id=?", (max(0, new_count), batch_id))


def mark_batch_status(batch_id, status):
    with get_conn() as conn:
        conn.execute("UPDATE livestock_batches SET status=? WHERE id=?", (status, batch_id))


def delete_livestock_batch(batch_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM livestock_batches WHERE id=?", (batch_id,))
        conn.execute("DELETE FROM mortality_logs WHERE batch_id=?", (batch_id,))
        conn.execute("DELETE FROM vaccination_schedules WHERE batch_id=?", (batch_id,))


# ---------- Mortality & Health Logging ----------
def log_mortality(batch_id, log_date, count_dead, cause_symptoms="", action_taken=""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO mortality_logs (batch_id, log_date, count_dead, cause_symptoms, action_taken, recorded_at) "
            "VALUES (?,?,?,?,?,?)",
            (batch_id, log_date, count_dead, cause_symptoms, action_taken, datetime.datetime.now().isoformat()),
        )
        # Automatically deduct dead animals from active count
        row = conn.execute("SELECT count FROM livestock_batches WHERE id=?", (batch_id,)).fetchone()
        if row:
            curr_count = row["count"] or 0
            new_count = max(0, curr_count - count_dead)
            conn.execute("UPDATE livestock_batches SET count=? WHERE id=?", (new_count, batch_id))


def get_batch_mortality_logs(batch_id):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM mortality_logs WHERE batch_id=? ORDER BY log_date DESC", (batch_id,)
        ).fetchall()]


def get_batch_mortality_summary(batch_id):
    with get_conn() as conn:
        batch = conn.execute("SELECT * FROM livestock_batches WHERE id=?", (batch_id,)).fetchone()
        if not batch:
            return {"total_dead": 0, "initial_count": 0, "current_count": 0, "mortality_pct": 0.0}
        total_dead = conn.execute("SELECT SUM(count_dead) as sum_dead FROM mortality_logs WHERE batch_id=?", (batch_id,)).fetchone()["sum_dead"] or 0
        init_count = batch["initial_count"] or (batch["count"] + total_dead)
        curr_count = batch["count"]
        pct = (total_dead / init_count * 100.0) if init_count > 0 else 0.0
        return {
            "total_dead": total_dead,
            "initial_count": init_count,
            "current_count": curr_count,
            "mortality_pct": round(pct, 2)
        }


# ---------- Vaccination & Medication Calendar ----------
def generate_standard_poultry_schedule(batch_id, start_date_str, species="Poultry - Broiler"):
    try:
        start_d = datetime.date.fromisoformat(start_date_str)
    except Exception:
        start_d = datetime.date.today()

    is_layer = "Layer" in species
    broiler_vaccines = [
        ("Day 1-3", 1, "Anti-Stress + Glucose / Marek's", "Marek's Disease & Stress"),
        ("Day 7", 7, "Newcastle Disease (ND Lasota / Hitchner B1)", "Newcastle Disease"),
        ("Day 10", 10, "Gumboro (IBD) 1st Dose", "Infectious Bursal Disease"),
        ("Day 14-16", 14, "Coccidiosis Preventive / Vitamin Booster", "Coccidiosis"),
        ("Day 18", 18, "Gumboro (IBD) 2nd Booster", "Infectious Bursal Disease"),
        ("Day 21", 21, "Newcastle (ND Lasota Booster)", "Newcastle Disease"),
        ("Day 28", 28, "Dewormer / Liver Tonic", "Internal Parasites"),
    ]
    layer_extra = [
        ("Week 6", 42, "Fowl Pox (Wing Web Stab)", "Fowl Pox"),
        ("Week 8", 56, "Newcastle (Komarov / Lasota)", "Newcastle Disease"),
        ("Week 10", 70, "Fowl Typhoid Vaccine", "Fowl Typhoid"),
        ("Week 14", 98, "Deworming Cycle 2", "Internal Parasites"),
        ("Week 16", 112, "Egg Drop Syndrome (EDS) + ND Killed", "EDS & Newcastle"),
    ]

    schedule = broiler_vaccines + (layer_extra if is_layer else [])
    with get_conn() as conn:
        for label, day_offset, vname, disease in schedule:
            due_d = (start_d + datetime.timedelta(days=day_offset)).isoformat()
            conn.execute(
                "INSERT INTO vaccination_schedules (batch_id, vaccine_name, target_disease, due_day_age, due_date, status, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (batch_id, f"{vname} ({label})", disease, day_offset, due_d, "pending", datetime.datetime.now().isoformat())
            )


def get_vaccination_schedule(batch_id):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM vaccination_schedules WHERE batch_id=? ORDER BY due_day_age ASC", (batch_id,)
        ).fetchall()]


def mark_vaccination_status(vac_id, status, notes=""):
    with get_conn() as conn:
        admin_date = datetime.date.today().isoformat() if status == "completed" else None
        conn.execute(
            "UPDATE vaccination_schedules SET status=?, administered_date=?, notes=? WHERE id=?",
            (status, admin_date, notes, vac_id)
        )


def get_upcoming_vaccinations_for_farm(farm_id, days_ahead=7):
    today = datetime.date.today()
    limit_date = (today + datetime.timedelta(days=days_ahead)).isoformat()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT v.*, b.species, b.breed, b.count 
            FROM vaccination_schedules v
            JOIN livestock_batches b ON v.batch_id = b.id
            WHERE b.farm_id = ? AND b.status = 'active' AND v.status = 'pending' AND v.due_date <= ?
            ORDER BY v.due_date ASC
        """, (farm_id, limit_date)).fetchall()
        return [dict(r) for r in rows]


# ---------- Feed Inventory Management ----------
def add_feed_inventory_item(farm_id, feed_name, category, quantity_bags, bag_weight_kg=25.0, cost_per_bag=0.0, minimum_alert_bags=3.0, notes=""):
    total_kg = quantity_bags * bag_weight_kg
    with get_conn() as conn:
        # Check if already exists for this farm
        existing = conn.execute("SELECT id, quantity_bags, total_kg FROM feed_inventory WHERE farm_id=? AND feed_name=?", (farm_id, feed_name)).fetchone()
        if existing:
            new_bags = existing["quantity_bags"] + quantity_bags
            new_kg = existing["total_kg"] + total_kg
            conn.execute(
                "UPDATE feed_inventory SET quantity_bags=?, total_kg=?, cost_per_bag=?, minimum_alert_bags=?, notes=?, updated_at=? WHERE id=?",
                (new_bags, new_kg, cost_per_bag, minimum_alert_bags, notes, datetime.datetime.now().isoformat(), existing["id"])
            )
            return existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO feed_inventory (farm_id, feed_name, category, quantity_bags, bag_weight_kg, total_kg, cost_per_bag, minimum_alert_bags, notes, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (farm_id, feed_name, category, quantity_bags, bag_weight_kg, total_kg, cost_per_bag, minimum_alert_bags, notes, datetime.datetime.now().isoformat())
            )
            return cur.lastrowid


def deduct_feed_inventory(farm_id, feed_name, bags_used=0.0, kg_used=0.0):
    with get_conn() as conn:
        item = conn.execute("SELECT * FROM feed_inventory WHERE farm_id=? AND feed_name=?", (farm_id, feed_name)).fetchone()
        if not item:
            return False, "Feed item not found in inventory."
        
        bag_wt = item["bag_weight_kg"] or 25.0
        used_in_kg = kg_used + (bags_used * bag_wt)
        used_in_bags = used_in_kg / bag_wt
        
        new_kg = max(0.0, item["total_kg"] - used_in_kg)
        new_bags = max(0.0, item["quantity_bags"] - used_in_bags)
        
        conn.execute(
            "UPDATE feed_inventory SET quantity_bags=?, total_kg=?, updated_at=? WHERE id=?",
            (new_bags, new_kg, datetime.datetime.now().isoformat(), item["id"])
        )
        return True, f"Deducted {used_in_kg:.1f}kg ({used_in_bags:.1f} bags). Remaining: {new_bags:.1f} bags ({new_kg:.1f}kg)."


def get_feed_inventory(farm_id):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM feed_inventory WHERE farm_id=? ORDER BY feed_name ASC", (farm_id,)).fetchall()]


def delete_feed_inventory_item(item_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM feed_inventory WHERE id=?", (item_id,))


def get_low_feed_alerts(farm_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM feed_inventory WHERE farm_id=? AND quantity_bags <= minimum_alert_bags", (farm_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Crops ----------
def add_crop_plot(farm_id, **kwargs):
    fields = ["crop", "area_ha", "planting_date", "soil_type", "fertilizer_used", "status", "notes"]
    if "status" not in kwargs or not kwargs["status"]:
        kwargs["status"] = "active"
    values = [kwargs.get(f) for f in fields]
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO crop_plots (farm_id,{','.join(fields)},created_at) "
            f"VALUES (?,{','.join(['?']*len(fields))},?)",
            [farm_id] + values + [datetime.datetime.now().isoformat()],
        )
        return cur.lastrowid


def get_crop_plots(farm_id, status=None):
    with get_conn() as conn:
        if status:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM crop_plots WHERE farm_id=? AND status=? ORDER BY id DESC", (farm_id, status)
            ).fetchall()]
        return [dict(r) for r in conn.execute(
            "SELECT * FROM crop_plots WHERE farm_id=? ORDER BY id DESC", (farm_id,)
        ).fetchall()]


def delete_crop_plot(plot_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM crop_plots WHERE id=?", (plot_id,))


# ---------- Transactions ----------
def add_transaction(farm_id, tx_type, category, amount, tx_date, notes="", batch_id=None):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO transactions (farm_id, batch_id, tx_type, category, amount, tx_date, notes, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (farm_id, batch_id, tx_type, category, amount, tx_date, notes, datetime.datetime.now().isoformat()),
        )
        return cur.lastrowid


def get_transactions(farm_id, batch_id=None):
    with get_conn() as conn:
        if batch_id:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM transactions WHERE farm_id=? AND batch_id=? ORDER BY tx_date DESC", (farm_id, batch_id)
            ).fetchall()]
        return [dict(r) for r in conn.execute(
            "SELECT * FROM transactions WHERE farm_id=? ORDER BY tx_date DESC", (farm_id,)
        ).fetchall()]


def delete_transaction(tx_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))


# ---------- Batch Harvest / Sale Recording ----------
def record_batch_harvest(batch_id, harvest_date, units_sold, total_weight_kg, avg_price_per_unit, feed_cost, other_cost, notes=""):
    total_rev = units_sold * avg_price_per_unit
    net_profit = total_rev - (feed_cost + other_cost)
    avg_wt = (total_weight_kg / units_sold) if units_sold > 0 else 0
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO batch_harvests (batch_id, harvest_date, units_sold, total_weight_kg, avg_weight_kg, price_per_unit_or_kg, total_revenue, feed_cost, other_cost, net_profit, notes, recorded_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (batch_id, harvest_date, units_sold, total_weight_kg, avg_wt, avg_price_per_unit, total_rev, feed_cost, other_cost, net_profit, notes, datetime.datetime.now().isoformat())
        )
        # Mark batch as harvested
        conn.execute("UPDATE livestock_batches SET status='harvested' WHERE id=?", (batch_id,))
        # Also auto-log transaction for the farm
        batch = conn.execute("SELECT farm_id, species FROM livestock_batches WHERE id=?", (batch_id,)).fetchone()
        if batch:
            conn.execute(
                "INSERT INTO transactions (farm_id, batch_id, tx_type, category, amount, tx_date, notes, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (batch["farm_id"], batch_id, "income", f"Harvest Sale: {batch['species']}", total_rev, harvest_date, f"Sold {units_sold} units @ {avg_price_per_unit}", datetime.datetime.now().isoformat())
            )
        return cur.lastrowid


def get_batch_harvests(farm_id):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT h.*, b.species, b.breed, b.start_date
            FROM batch_harvests h
            JOIN livestock_batches b ON h.batch_id = b.id
            WHERE b.farm_id = ?
            ORDER BY h.harvest_date DESC
        """, (farm_id,)).fetchall()
        return [dict(r) for r in rows]


# ---------- Chat history ----------
def save_chat_message(farm_id, role, content, channel="web"):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_history (farm_id, role, content, channel, created_at) VALUES (?,?,?,?,?)",
            (farm_id, role, content, channel, datetime.datetime.now().isoformat()),
        )


def get_chat_history(farm_id, limit=40, channel=None):
    with get_conn() as conn:
        if channel:
            rows = conn.execute(
                "SELECT * FROM chat_history WHERE farm_id=? AND channel=? ORDER BY id DESC LIMIT ?", (farm_id, channel, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM chat_history WHERE farm_id=? ORDER BY id DESC LIMIT ?", (farm_id, limit)
            ).fetchall()
        return [dict(r) for r in rows][::-1]


def clear_chat_history(farm_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM chat_history WHERE farm_id=?", (farm_id,))
