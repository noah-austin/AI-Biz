"""Cottonwood Precision Manufacturing: a FICTIONAL contract fabricator and machine shop used to demo the kit.

Brackets and weldments, machined shafts, enclosures, trailer components and custom fabrication for equipment makers,
from two Texas plants. Customer orders ship from finished goods; production orders run through work centers; raw
steel and aluminum are bought weekly.
"""
import datetime as dt

SEED = 20261023
START = dt.date(2024, 1, 2)
START_OPS = dt.date(2025, 1, 1)
DOMAIN = "cottonwoodprecision.example"
EXEC = ("Logan Mercado", "VP of Sales")

BRANCHES = [  # plant code, city, relative size, win-rate nudge
    ("FTW", "Fort Worth", 1.2, 0.02),
    ("WAC", "Waco", 0.8, -0.02),
]
MISSING_MARGIN_BRANCH = "WAC"
REP_TITLE = "Account Manager"
REPS_BASE = 2

SEGMENTS = {
    "Agricultural equipment": (0.24, 1.1, {"Blanket order": 0.05}),
    "Trailer and truck body": (0.22, 1.0, {"Production quote": 0.04}),
    "Oil and gas equipment": (0.18, 1.3, {"Prototype / custom": 0.03}),
    "Industrial machinery": (0.20, 1.2, {}),
    "HVAC and electrical OEM": (0.16, 0.9, {"Blanket order": 0.03}),
}
DEAL_TYPES = {  # share, median, sigma, cap, base win, cycle days, margin mean
    "Production quote": (0.50, 45_000, 0.8, 600_000, 0.40, (10, 45), 24),
    "Blanket order": (0.25, 220_000, 0.7, 2_000_000, 0.35, (30, 120), 21),
    "Prototype / custom": (0.25, 18_000, 0.7, 150_000, 0.48, (5, 30), 32),
}
QUICK_TYPES = set()
DESCRIPTORS = {
    "Production quote": ["Mounting brackets, annual volume", "Machined shafts", "Electrical enclosures", "Hitch assemblies",
                         "Weldment frames", "Axle components"],
    "Blanket order": ["Annual blanket order, brackets", "Blanket order, enclosures", "Supply agreement, trailer components",
                      "Blanket order, machined parts"],
    "Prototype / custom": ["Prototype run", "Custom skid fabrication", "First-article parts", "Engineering samples"],
}
STAGES = [("Prospecting", 10), ("Qualification", 20), ("Proposal", 50), ("Negotiation", 75)]
LOSS_REASONS = ["Price", "Lead time", "Went offshore", "Chose incumbent", "No decision"]
LEAD_SOURCES = ["Existing customer", "Referral", "Trade show", "Website", "Engineering contact"]
ACCOUNT_WORDS = {
    "Agricultural equipment": (["Prairie Gate", "Red Plains", "Harvest Line", "Brazos Valley", "Blackland"],
                               ["Implements", "Ag Equipment", "Farm Machinery", "Sprayers"]),
    "Trailer and truck body": (["Lonehorn", "Roadrunner", "Iron Trail", "Caprock", "Mesa Grande"],
                               ["Trailers", "Truck Bodies", "Haulers", "Trailer Works"]),
    "Oil and gas equipment": (["Permian", "Wildcat", "Mesquite", "Pecos", "Caliche"],
                              ["Compression", "Well Equipment", "Pumping Systems", "Skid Works"]),
    "Industrial machinery": (["Tidewater", "Harbor Point", "Coral Ridge", "Saltgrass", "Bluefin"],
                             ["Machinery", "Conveyors", "Automation", "Industrial Systems"]),
    "HVAC and electrical OEM": (["Northgate", "Summit", "Ironwood", "Westlake", "Granite"],
                                ["Controls", "Power Systems", "Air Systems", "Switchgear"]),
}
ACCOUNTS_PER_BRANCH = 70
DEALS_PER_DAY = 0.35
SEASON_AMPLITUDE = 0.08

# Finished goods (category = product family) and raw materials (category "Raw material").
# sku, description, category, standard unit cost, weekly use per unit of plant size, vendor, critical
ITEMS = [
    ("BRK-100", "Mounting bracket, powder coated", "Brackets & weldments", 18, 120, "inhouse", False),
    ("BRK-220", "Heavy weldment frame", "Brackets & weldments", 340, 10, "inhouse", False),
    ("BRK-310", "Gusseted angle bracket", "Brackets & weldments", 26, 80, "inhouse", False),
    ("SHF-125", "Machined shaft 1.25 in", "Machined parts", 64, 40, "inhouse", False),
    ("SHF-200", "Machined shaft 2 in, keyed", "Machined parts", 118, 22, "inhouse", False),
    ("MCH-HUB", "Machined hub", "Machined parts", 96, 25, "inhouse", False),
    ("ENC-1612", "Electrical enclosure 16x12", "Enclosures", 145, 18, "inhouse", False),
    ("ENC-2420", "Electrical enclosure 24x20", "Enclosures", 238, 10, "inhouse", False),
    ("TRL-HCH", "Hitch assembly", "Trailer components", 182, 15, "inhouse", False),
    ("TRL-AXL", "Axle bracket set", "Trailer components", 74, 30, "inhouse", False),
    ("TRL-FND", "Fender, formed", "Trailer components", 58, 28, "inhouse", False),
    ("CST-SKID", "Custom skid base", "Custom fabrication", 1850, 1, "inhouse", False),
    ("OLD-TANK", "Tank cradle (discontinued design)", "Custom fabrication", 420, 0, "inhouse", False),
    ("RM-PL38", "Steel plate 3/8 in (sheet)", "Raw material", 210, 30, "steel", True),
    ("RM-SHT14", "Steel sheet 14 ga (sheet)", "Raw material", 88, 45, "steel", True),
    ("RM-TUBE2", "Steel tube 2x2 in (20 ft)", "Raw material", 96, 25, "steel", True),
    ("RM-BAR125", "Steel round bar 1.25 in (12 ft)", "Raw material", 72, 20, "bar", True),
    ("RM-AL6061", "Aluminum bar 6061 (12 ft)", "Raw material", 145, 10, "aluminum", False),
    ("RM-PWD", "Powder coat, black (50 lb)", "Raw material", 260, 6, "coating", False),
    ("RM-WIRE", "Welding wire ER70S-6 (spool)", "Raw material", 118, 12, "weld", True),
    ("RM-FAST", "Fastener kit (box)", "Raw material", 34, 30, "fastener", False),
    ("RM-HINGE", "Enclosure hinge set", "Raw material", 12, 25, "fastener", False),
]
# Selling price = standard cost x (1 + markup), set at the start of the year; steel-heavy families feel steel price rises.
MARKUP = {"Brackets & weldments": 0.42, "Machined parts": 0.48, "Enclosures": 0.40, "Trailer components": 0.36,
          "Custom fabrication": 0.55}
STEEL_SHARE = {"Brackets & weldments": 0.55, "Machined parts": 0.30, "Enclosures": 0.45, "Trailer components": 0.60,
               "Custom fabrication": 0.40}
# How much raw material each finished good uses per unit (sku: [(raw sku, qty)]).
BOM_RAW = {"Brackets & weldments": [("RM-PL38", 0.04), ("RM-WIRE", 0.01), ("RM-PWD", 0.004)],
           "Machined parts": [("RM-BAR125", 0.12), ("RM-AL6061", 0.03)],
           "Enclosures": [("RM-SHT14", 0.35), ("RM-HINGE", 1.0), ("RM-PWD", 0.01)],
           "Trailer components": [("RM-TUBE2", 0.12), ("RM-PL38", 0.03), ("RM-WIRE", 0.01), ("RM-FAST", 0.2)],
           "Custom fabrication": [("RM-PL38", 1.5), ("RM-TUBE2", 1.0), ("RM-WIRE", 0.2)]}
NO_COST = {"RM-HINGE"}

WORK_CENTERS = [  # id, name, plant, hours per day, families it makes, standard hours per unit (for those families)
    ("FTW-LASER", "Laser cutting", "FTW", 16, ["Brackets & weldments", "Enclosures"], 0.04),
    ("FTW-BRAKE", "Press brake", "FTW", 16, ["Enclosures", "Trailer components"], 0.06),
    ("FTW-WELD", "Welding cell", "FTW", 16, ["Brackets & weldments", "Trailer components", "Custom fabrication"], 0.18),
    ("FTW-CNC", "CNC machining", "FTW", 20, ["Machined parts"], 0.35),
    ("WAC-BRAKE", "Press brake", "WAC", 8, ["Trailer components", "Enclosures"], 0.07),
    ("WAC-WELD", "Welding cell", "WAC", 16, ["Trailer components", "Brackets & weldments"], 0.20),
    ("WAC-PAINT", "Powder coat line", "WAC", 16, ["Brackets & weldments", "Enclosures"], 0.03),
]
PROBLEM_MACHINE = "WAC-BRAKE"    # planted: the old Waco press brake keeps breaking down
SCRAP_SPIKE = ("FTW-CNC", dt.date(2026, 7, 1))   # planted: CNC scrap jumped after two experienced machinists left
STEEL_VENDOR = "steel"           # planted: raises prices and delivers late, so production waits on material

VENDORS = [  # key, name, category, terms days, lead days, chance late, yearly drift
    ("steel", "Trinity Steel Service Center", "Steel", 30, 5, 0.30, 0.12),
    ("bar", "Lone Star Bar & Tube", "Steel", 30, 6, 0.12, 0.06),
    ("aluminum", "Gulf Aluminum Supply", "Aluminum", 30, 7, 0.10, 0.04),
    ("coating", "Prairie Powder Coatings", "Coatings", 30, 6, 0.08, 0.03),
    ("weld", "Brazos Welding Supply", "Consumables", 30, 3, 0.06, 0.04),
    ("fastener", "Lone Prairie Fasteners", "Hardware", 30, 4, 0.07, 0.03),
    ("inhouse", "Made in-house", "In-house", 0, 0, 0.0, 0.0),
    ("steel_dup", "TRINITY STEEL SERVICE CENTER INC", "Steel", 30, 5, 0.30, 0.12),
]
RESTOCK_KIND = "Raw material"

ORDERS_PER_DAY = 16
CHANNELS = [("EDI", 0.35), ("Email / phone", 0.45), ("Blanket release", 0.20)]

PEOPLE = {
    "head_office": [("Plant Manager", "Operations", "Salary"), ("Controller", "Finance", "Salary"),
                    ("AP Specialist", "Finance", "Hourly"), ("Buyer", "Purchasing", "Salary"),
                    ("Quality Manager", "Quality", "Salary"), ("HR Generalist", "People", "Salary"),
                    ("Production Planner", "Operations", "Salary")],
    "frontline_head_dept": "Operations",
    "roles": [
        {"title": "Machinist", "department": "Production", "seats": 6, "quit": 0.018, "fill_days": 55, "lead": "Lead Machinist"},
        {"title": "Welder", "department": "Production", "seats": 8, "quit": 0.022, "fill_days": 45},
        {"title": "Machine Operator", "department": "Production", "seats": 8, "quit": 0.03, "fill_days": 25},
        {"title": "Assembler", "department": "Production", "seats": 5, "quit": 0.03, "fill_days": 20},
        {"title": "Quality Inspector", "department": "Quality", "seats": 1.5, "quit": 0.01, "fill_days": 40},
        {"title": "Material Handler", "department": "Shipping & Receiving", "seats": 2.5, "quit": 0.025, "fill_days": 20},
    ],
    "frontline": "Production",
    "short": ("FTW", [1, 3]),
    "growth": [("WAC", dt.date(2025, 11, 3))],
    "certs": [("AWS certified welder (D1.1)", 2, "Welder"), ("Forklift operator", 3, "Material Handler"),
              ("Forklift operator", 3, "Assembler"), ("OSHA 10", None, "Machine Operator")],
    "license": "AWS certified welder (D1.1)",
    "overtime": {"frontline": 4.0, "summer": 1.5, "busy_months": (3, 4, 5, 9, 10), "short_factor": 22, "branch": {"WAC": 1.5}},
}
