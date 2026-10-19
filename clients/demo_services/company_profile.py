"""Kestrel Ridge Engineering: a FICTIONAL engineering and consulting firm used to demo the kit.

Civil, structural and building-systems engineering for public agencies, school districts, developers and health
systems, from four Texas offices. Work is sold as fixed-fee design projects, hourly studies and on-call retainers,
and run in a project and time system (PSA).
"""
import datetime as dt

SEED = 20261021
START = dt.date(2024, 1, 2)
START_OPS = dt.date(2025, 1, 1)
DOMAIN = "kestrelridge.example"
EXEC = ("Harper Delgado", "Principal, Business Development")

BRANCHES = [  # office code, city, relative size, win-rate nudge
    ("HOU", "Houston", 1.3, 0.03),
    ("DFW", "Dallas", 1.1, 0.00),
    ("AUS", "Austin", 0.9, -0.03),
    ("SAT", "San Antonio", 0.7, 0.02),
]
MISSING_MARGIN_BRANCH = "SAT"
REP_TITLE = "Business Development Manager"
REPS_BASE = 1

SEGMENTS = {
    "Municipal": (0.26, 1.0, {"On-call retainer": 0.08}),
    "School district": (0.20, 1.1, {"Design services": 0.04}),
    "Developer": (0.20, 0.9, {"Study / assessment": 0.05, "Design services": -0.04}),
    "Health system": (0.14, 1.3, {"Design services": 0.05}),
    "Industrial": (0.12, 1.2, {"Study / assessment": 0.03}),
    "State agency": (0.08, 1.4, {"On-call retainer": -0.05, "Design services": -0.06}),
}
DEAL_TYPES = {  # share, median, sigma, cap, base win, cycle days, margin mean
    "Design services": (0.48, 85_000, 0.8, 1_500_000, 0.33, (30, 120), 24),
    "Study / assessment": (0.37, 28_000, 0.7, 250_000, 0.45, (10, 45), 30),
    "On-call retainer": (0.15, 120_000, 0.5, 600_000, 0.38, (45, 150), 27),
}
QUICK_TYPES = set()
DESCRIPTORS = {
    "Design services": ["Drainage improvements design", "Roadway reconstruction design", "MEP design, new wing",
                        "Structural design, parking garage", "Water main replacement design", "School renovation MEP design"],
    "Study / assessment": ["Facility condition assessment", "Traffic impact study", "Stormwater master plan update",
                           "Energy audit", "Structural assessment", "Utility capacity study"],
    "On-call retainer": ["On-call engineering services", "On-call inspection services", "General engineering retainer"],
}
STAGES = [("Prospecting", 10), ("Qualification", 20), ("Proposal", 50), ("Negotiation", 75)]
LOSS_REASONS = ["Fee too high", "Qualifications ranked lower", "Chose incumbent", "Project shelved", "No decision"]
LEAD_SOURCES = ["Existing client", "RFQ / public bid", "Referral", "Conference", "Website"]
ACCOUNT_WORDS = {
    "Municipal": (["Port Larkin", "Rio Seco", "Cypress Flats", "Mesquite Springs", "Lake Coralline", "Cedar Bluff", "Oak Hollow"],
                  ["Public Works", "Water Utility", "Streets Department", "Parks & Recreation", "Drainage District"]),
    "School district": (["Bluebonnet", "Caliche Flats", "Red Oak Valley", "Pecan Grove", "Live Oak Prairie"],
                        ["ISD", "Consolidated ISD", "Collegiate Academy", "Community College"]),
    "Developer": (["Larkspur", "Highline", "Stonebridge", "Riverwalk", "Prairie Gate", "Westbrook"],
                  ["Development", "Partners", "Land Company", "Properties", "Communities"]),
    "Health system": (["St. Anne", "Riverside", "Hill Country", "Trinity Valley", "Northpark"],
                      ["Health", "Medical Center", "Children's Hospital", "Health System"]),
    "Industrial": (["Tidewater", "Saltgrass", "Harbor Point", "Redfish Bay", "Coral Ridge"],
                   ["Terminal", "Polymers", "Fabricators", "Packaging", "Logistics Park"]),
    "State agency": (["Texas Coastal", "Gulf Region", "Central Texas", "Hill Country"],
                     ["Transit Authority", "River Authority", "Water Development Board", "Port Authority"]),
}
ACCOUNTS_PER_BRANCH = 70
DEALS_PER_DAY = 0.42
SEASON_AMPLITUDE = 0.08

# People: engineers are the frontline; their PE license is the legal must.
ROLES = {  # title: (department, standard bill rate, cost rate per hour)
    "Senior Engineer": ("Engineering", 215, 92),
    "Project Engineer": ("Engineering", 165, 64),
    "CAD Designer": ("Design", 115, 41),
    "Construction Inspector": ("Field Services", 105, 38),
    "Project Manager": ("Project Management", 190, 80),
}
TARGET_UTIL = {"Senior Engineer": 0.70, "Project Engineer": 0.82, "CAD Designer": 0.85, "Construction Inspector": 0.88,
               "Project Manager": 0.55}
AUSTIN_DROP = 0.78                              # planted: Austin lost its biggest client in February; same people, less work
STAFFING = {"HOU": 0.88}                        # planted: Houston is staffed about 12% short of its work
OVERRUN_PM_INDEX = 1                            # planted: this Dallas PM's fixed-fee projects run over budget
STALLED_OFFICE = "HOU"                          # planted: one big hourly project there hasn't been billed in months
WRITE_DOWN_SEGMENT = "State agency"             # planted: hours on these clients get written down at billing

PEOPLE = {
    "head_office": [("Chief Operating Officer", "Operations", "Salary"), ("Controller", "Finance", "Salary"),
                    ("Billing Specialist", "Finance", "Hourly"), ("HR Manager", "People", "Salary"),
                    ("Marketing Coordinator", "Business Development", "Salary"), ("IT Manager", "Operations", "Salary")],
    "frontline_head_dept": "Operations",
    "roles": [
        {"title": "Project Engineer", "department": "Engineering", "seats": 5, "quit": 0.011, "fill_days": 60,
         "pay": "Salary", "lead": "Senior Engineer"},
        {"title": "Senior Engineer", "department": "Engineering", "seats": 2, "quit": 0.006, "fill_days": 80, "pay": "Salary"},
        {"title": "CAD Designer", "department": "Design", "seats": 3, "quit": 0.015, "fill_days": 40},
        {"title": "Construction Inspector", "department": "Field Services", "seats": 2, "quit": 0.014, "fill_days": 45},
        {"title": "Project Manager", "department": "Project Management", "seats": 1.5, "quit": 0.008, "fill_days": 70,
         "pay": "Salary"},
        {"title": "Office Administrator", "department": "Administration", "seats": 1, "quit": 0.01, "fill_days": 30},
    ],
    "frontline": "Engineering",
    "short": (None, []),
    "growth": [("HOU", dt.date(2026, 2, 2))],
    "certs": [("Professional Engineer (PE) license", 2, "Senior Engineer"), ("Professional Engineer (PE) license", 2, "Project Engineer"),
              ("ICC building inspector", 3, "Construction Inspector"), ("OSHA 30", None, "Construction Inspector"),
              ("PMP", 3, "Project Manager")],
    "license": "Professional Engineer (PE) license",
    "overtime": {"base": 1.5, "frontline": 0, "busy_months": (), "branch": {}, "branch_all": {"HOU": 4.5}},
}
