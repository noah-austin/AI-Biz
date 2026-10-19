"""Bramblewood Industrial Supply: a FICTIONAL industrial and MRO distributor used to demo the kit.

Six Texas branches selling pipe, valves, fittings, fasteners, safety gear, electrical, tools and janitorial
supplies to contractors, plants and facilities, mostly over the counter, by phone and through outside reps.
"""
import datetime as dt

SEED = 20261020
START = dt.date(2024, 1, 2)          # CRM history
START_OPS = dt.date(2025, 1, 1)      # orders, purchasing, timesheets
DOMAIN = "bramblewood.example"
EXEC = ("Jordan Esparza", "VP of Sales")

BRANCHES = [  # code, city, relative size, win-rate nudge
    ("HOU-01", "Houston", 1.4, 0.02),
    ("DAL-02", "Dallas", 1.2, 0.00),
    ("SAT-03", "San Antonio", 0.9, 0.03),
    ("AUS-04", "Austin", 0.8, -0.02),
    ("CRP-05", "Corpus Christi", 0.6, -0.04),
    ("BMT-06", "Beaumont", 0.6, 0.01),
]
MISSING_MARGIN_BRANCH = "BMT-06"
REP_TITLE = "Outside Sales Rep"

SEGMENTS = {
    "Mechanical contractor": (0.24, 1.0, {"Project bid": 0.05}),
    "Industrial plant": (0.20, 1.4, {"Supply agreement": 0.06}),
    "Facilities & institutions": (0.18, 0.9, {"Supply agreement": 0.03}),
    "General contractor": (0.14, 1.1, {"Project bid": -0.04}),
    "Oil & gas services": (0.14, 1.3, {"Spot quote": 0.04}),
    "Municipal & utilities": (0.10, 1.2, {"Project bid": -0.06, "Supply agreement": -0.05}),
}
DEAL_TYPES = {  # share, median, sigma, cap, base win, cycle days, margin mean
    "Spot quote": (0.55, 6_500, 0.8, 120_000, 0.46, (2, 14), 26),
    "Project bid": (0.28, 48_000, 0.9, 900_000, 0.27, (20, 90), 17),
    "Supply agreement": (0.17, 160_000, 0.7, 1_500_000, 0.34, (45, 150), 21),
}
QUICK_TYPES = {"Spot quote"}
DESCRIPTORS = {
    "Spot quote": ["Valve package", "Pipe and fittings", "Safety supplies restock", "Fastener order", "Electrical materials",
                   "Shutdown supplies", "Tool order"],
    "Project bid": ["Mechanical room package", "Plant expansion materials", "New school MEP materials", "Hospital wing piping",
                    "Process piping package", "Utility vault materials"],
    "Supply agreement": ["Annual MRO supply agreement", "PPE vending program", "Vendor-managed inventory", "Fastener bin program",
                         "Janitorial supply agreement"],
}
STAGES = [("Prospecting", 10), ("Qualification", 20), ("Proposal", 50), ("Negotiation", 75)]
LOSS_REASONS = ["Price", "Lead time", "Chose incumbent", "No decision", "Project canceled"]
LEAD_SOURCES = ["Existing customer", "Counter walk-in", "Website", "Referral", "Trade show", "Bid board"]
ACCOUNT_WORDS = {
    "Mechanical contractor": (["Gulfstar", "Alamo", "Ironside", "Bluewater", "Prairie", "Lonestar", "Redline", "Cypress"],
                              ["Mechanical", "Plumbing & Heating", "Pipe Works", "Mechanical Services", "Plumbing Co."]),
    "Industrial plant": (["Tidewater", "Saltgrass", "Harbor Point", "Bluefin", "Marsh Hollow", "Redfish Bay", "Coral Ridge"],
                         ["Chemical", "Refining", "Polymers", "Terminal", "Fabricators", "Packaging Plant"]),
    "Facilities & institutions": (["St. Anne", "Riverside", "Hill Country", "Mission", "Trinity", "Northpark"],
                                  ["Medical Center", "University", "School District", "Hospital", "Mall", "Campus Facilities"]),
    "General contractor": (["Summit", "Keystone", "Frontier", "Landmark", "Cornerstone", "Benchmark"],
                           ["Builders", "Construction", "Contractors", "Constructors"]),
    "Oil & gas services": (["Permian", "Eagle Ford", "Wildcat", "Caliche", "Mesquite", "Pecos"],
                           ["Well Services", "Energy Services", "Pipeline", "Oilfield Supply", "Compression"]),
    "Municipal & utilities": (["Port Larkin", "Rio Seco", "Cypress Flats", "Mesquite Springs", "Lake Coralline"],
                              ["Water Utility", "Public Works", "Parks Department", "Wastewater Plant"]),
}
ACCOUNTS_PER_BRANCH = 120
DEALS_PER_DAY = 0.55
SEASON_AMPLITUDE = 0.10

# Products: sku, description, product line, unit cost, weekly use per unit of branch size, vendor, critical.
# Weekly use with 0 = legacy stock nobody buys any more (dead stock).
ITEMS = [
    ("PIP-BLK2", "Black steel pipe 2 in x 21 ft", "Pipe & fittings", 68, 30, "gulfway", False),
    ("PIP-PVC4", "PVC Sch 40 pipe 4 in x 20 ft", "Pipe & fittings", 42, 40, "gulfway", False),
    ("PIP-CU34", "Copper type L 3/4 in x 20 ft", "Pipe & fittings", 96, 25, "gulfway", False),
    ("FIT-ELB1", "Malleable iron elbow 1 in", "Pipe & fittings", 4.2, 300, "gulfway", True),
    ("FIT-CPL2", "PVC coupling 2 in", "Pipe & fittings", 1.1, 500, "gulfway", True),
    ("FIT-TEE34", "Copper tee 3/4 in", "Pipe & fittings", 3.8, 250, "gulfway", False),
    ("FIT-FLG4", "Flange 4 in class 150", "Pipe & fittings", 38, 30, "gulfway", False),
    ("VLV-BALL1", "Brass ball valve 1 in", "Valves", 24, 80, "redbud", True),
    ("VLV-GATE2", "Gate valve 2 in", "Valves", 118, 20, "redbud", False),
    ("VLV-BFY4", "Butterfly valve 4 in", "Valves", 210, 12, "redbud", False),
    ("VLV-CHK2", "Swing check valve 2 in", "Valves", 96, 15, "redbud", False),
    ("VLV-SPC10", "Flanged valve 10 in (special order)", "Valves", 2400, 0, "redbud", False),
    ("FAS-HEX", "Hex bolt 1/2 x 2 in (box of 50)", "Fasteners", 18, 120, "loneprairie", True),
    ("FAS-ANC", "Wedge anchor 1/2 in (box of 25)", "Fasteners", 34, 60, "loneprairie", False),
    ("FAS-ROD", "Threaded rod 3/8 in x 10 ft", "Fasteners", 6, 200, "loneprairie", False),
    ("FAS-SDS", "Self-drilling screws (box of 1000)", "Fasteners", 42, 70, "loneprairie", False),
    ("PPE-GLV", "Nitrile gloves (case)", "Safety & PPE", 46, 140, "shieldline", True),
    ("PPE-GLS", "Safety glasses (dozen)", "Safety & PPE", 28, 90, "shieldline", False),
    ("PPE-HAT", "Hard hat", "Safety & PPE", 14, 60, "shieldline", False),
    ("PPE-VST", "Hi-vis vest", "Safety & PPE", 9, 80, "shieldline", False),
    ("PPE-EAR", "Ear plugs (box of 200)", "Safety & PPE", 24, 70, "shieldline", False),
    ("PPE-HRN", "Fall protection harness", "Safety & PPE", 165, 8, "shieldline", False),
    ("PPE-RSP", "Half-mask respirator", "Safety & PPE", 32, 25, "shieldline", False),
    ("ELE-THHN", "THHN wire 12 AWG (500 ft)", "Electrical", 132, 20, "brazos", False),
    ("ELE-EMT", "EMT conduit 3/4 in x 10 ft", "Electrical", 8, 250, "brazos", True),
    ("ELE-BRK", "Breaker 20A single pole", "Electrical", 11, 60, "brazos", False),
    ("ELE-CORD", "Extension cord 50 ft, 12/3", "Electrical", 38, 40, "brazos", False),
    ("ELE-LED", "LED high-bay fixture", "Electrical", 145, 15, "brazos", False),
    ("TOL-DRL", "Cordless drill kit", "Tools", 189, 10, "trinity", False),
    ("TOL-WRN", "Pipe wrench 18 in", "Tools", 42, 14, "trinity", False),
    ("TOL-BLD", "Band saw blades (pack of 3)", "Tools", 58, 20, "trinity", False),
    ("TOL-BIT", "Drill bit set", "Tools", 36, 25, "trinity", False),
    ("JAN-TWL", "Shop towels (case)", "MRO & janitorial", 38, 90, "pecos", False),
    ("JAN-DGR", "Degreaser (5 gal)", "MRO & janitorial", 64, 40, "pecos", False),
    ("JAN-BAG", "Trash liners (case)", "MRO & janitorial", 36, 80, "pecos", False),
    ("JAN-ABS", "Absorbent pads (bale)", "MRO & janitorial", 72, 30, "pecos", False),
    ("HVR-FLT", "Air filter 20x20x2 (case of 12)", "HVAC/R supplies", 54, 60, "coastal", False),
    ("HVR-410", "Refrigerant R-410A (25 lb)", "HVAC/R supplies", 262, 12, "coastal", False),
    ("HVR-CAP", "Run capacitor 45/5 MFD", "HVAC/R supplies", 22, 40, "coastal", False),
    ("HVR-PMP", "Condensate pump", "HVAC/R supplies", 92, 12, "coastal", False),
    ("HVR-LNS", "Copper line set 3/8 x 3/4 in, 50 ft", "HVAC/R supplies", 210, 10, "coastal", False),
    ("HYD-HOSE", "Hydraulic hose assembly (discontinued)", "MRO & janitorial", 380, 0, "pecos", False),
    ("CTL-PNU", "Pneumatic controls kit (legacy)", "HVAC/R supplies", 260, 0, "coastal", False),
]
PACK = {"FIT-ELB1": 12, "FIT-CPL2": 20, "FIT-TEE34": 10, "FAS-ROD": 10, "ELE-EMT": 10, "PPE-VST": 6, "PPE-HAT": 4, "PIP-PVC4": 4,
        "PIP-BLK2": 3, "FAS-HEX": 3, "PPE-GLV": 3}
MARKUP = {"Pipe & fittings": 0.36, "Valves": 0.40, "Fasteners": 0.55, "Safety & PPE": 0.42, "Electrical": 0.30, "Tools": 0.33,
          "MRO & janitorial": 0.45, "HVAC/R supplies": 0.32}
SQUEEZE_LINE = "Safety & PPE"     # planted: the vendor raised costs; prices didn't follow
NO_COST = {"TOL-BIT"}

VENDORS = [  # key, name, category, terms days, lead days, chance late, yearly price drift
    ("gulfway", "Gulfway Pipe & Valve", "Pipe & fittings", 30, 3, 0.08, 0.04),
    ("redbud", "Redbud Valve Company", "Valves", 45, 7, 0.36, 0.04),
    ("loneprairie", "Lone Prairie Fasteners", "Fasteners", 30, 4, 0.07, 0.03),
    ("shieldline", "Shieldline Safety Products", "Safety & PPE", 30, 5, 0.09, 0.10),
    ("brazos", "Brazos Electrical Wholesale", "Electrical", 30, 2, 0.06, 0.03),
    ("trinity", "Trinity Tool Supply", "Tools", 30, 6, 0.10, 0.03),
    ("pecos", "Pecos Janitorial Supply", "MRO & janitorial", 30, 4, 0.07, 0.02),
    ("coastal", "Coastal HVAC/R Distributors", "HVAC/R supplies", 30, 4, 0.10, 0.04),
    ("gulfway_dup", "GULFWAY PIPE AND VALVE", "Pipe & fittings", 30, 3, 0.08, 0.04),
]
RESTOCK_KIND = "Stock"

# Orders: per business day per unit of branch size. Fill and shipping by branch; planted problems.
ORDERS_PER_DAY = 16
CHANNELS = [("Counter", 0.30), ("Inside sales", 0.35), ("Web / EDI", 0.20), ("Outside sales", 0.15)]
FILL = 0.955
FILL_BRANCH = {"CRP-05": 0.84}          # Corpus Christi is short-staffed and runs out of stock
FILL_LINE = {"Valves": -0.04}            # the valve vendor delivers late
LATE_SHIP = {"CRP-05": 0.22}             # chance an order ships a day or more after the customer asked; others 0.06
DISCOUNTER = ("DAL-02", 2)               # planted: one Dallas rep discounts heavily
SLOW_PAYER_FROM = dt.date(2026, 4, 1)    # planted: the biggest Houston customer started paying slowly

PEOPLE = {
    "head_office": [("Director of Operations", "Operations", "Salary"), ("Controller", "Finance", "Salary"),
                    ("Credit Manager", "Finance", "Salary"), ("AP Specialist", "Finance", "Hourly"),
                    ("Purchasing Manager", "Purchasing", "Salary"), ("Pricing Analyst", "Purchasing", "Salary"),
                    ("HR Generalist", "People", "Salary")],
    "roles": [
        {"title": "Warehouse Associate", "department": "Warehouse & Delivery", "seats": 5, "quit": 0.022, "fill_days": 30,
         "lead": "Warehouse Lead"},
        {"title": "Delivery Driver", "department": "Warehouse & Delivery", "seats": 2.5, "quit": 0.015, "fill_days": 50},
        {"title": "Counter Sales", "department": "Branch Sales", "seats": 2, "quit": 0.012, "fill_days": 35},
        {"title": "Inside Sales", "department": "Branch Sales", "seats": 1.5, "quit": 0.01, "fill_days": 40},
    ],
    "frontline": "Warehouse & Delivery",
    "short": ("CRP-05", [1, 2]),
    "growth": [("AUS-04", dt.date(2025, 10, 6))],
    "quit_branch": {"CRP-05": 1.6},
    "certs": [("Commercial driver's license (CDL B)", 4, "Delivery Driver"), ("DOT medical card", 2, "Delivery Driver"),
              ("Forklift operator", 3, "Warehouse Associate"), ("Forklift operator", 3, "Warehouse Lead"),
              ("OSHA 10", None, "Warehouse Lead")],
    "license": "Commercial driver's license (CDL B)",
    "overtime": {"frontline": 2.5, "summer": 1.5, "busy_months": (3, 4, 5), "short_factor": 22, "branch": {"CRP-05": 1.5}},
}
