"""Mesquite Ridge Constructors: a FICTIONAL commercial general contractor used to demo the kit.

Healthcare, education, office, industrial and public projects from three Texas offices, won by hard bid and
negotiated contracts, run in a job-cost system with monthly pay applications and 10% retainage.
"""
import datetime as dt

SEED = 20261022
START = dt.date(2024, 1, 2)
START_OPS = dt.date(2025, 1, 1)
DOMAIN = "mesquiteridge.example"
EXEC = ("Rowan Esparza", "VP of Preconstruction")

BRANCHES = [  # office code, city, relative size, win-rate nudge
    ("HOU", "Houston", 1.3, 0.02),
    ("SAT", "San Antonio", 1.0, 0.00),
    ("AUS", "Austin", 0.8, -0.02),
]
MISSING_MARGIN_BRANCH = "AUS"
REP_TITLE = "Estimator"
REPS_BASE = 1

SEGMENTS = {
    "Healthcare": (0.20, 1.3, {"Negotiated": 0.06}),
    "K-12 education": (0.22, 1.1, {"Hard bid": 0.03}),
    "Office & tenant finish": (0.20, 0.7, {"Negotiated": 0.04, "Service work": 0.05}),
    "Industrial & warehouse": (0.16, 1.0, {"Hard bid": 0.02}),
    "Retail & hospitality": (0.12, 0.8, {}),
    "Public works": (0.10, 1.2, {"Hard bid": -0.05}),
}
DEAL_TYPES = {  # share, median, sigma, cap, base win, cycle days, margin mean (bid fee %)
    "Hard bid": (0.40, 1_400_000, 0.7, 15_000_000, 0.19, (20, 60), 8),
    "Negotiated": (0.25, 2_300_000, 0.7, 20_000_000, 0.42, (45, 160), 11),
    "Service work": (0.35, 160_000, 0.7, 1_500_000, 0.50, (7, 30), 14),
}
QUICK_TYPES = set()
DESCRIPTORS = {
    "Hard bid": ["New elementary school", "Fire station", "Library renovation", "Warehouse shell", "Middle school addition",
                 "Public works yard"],
    "Negotiated": ["Medical office building", "Hospital wing expansion", "Corporate campus phase 2", "Clinic build-out",
                   "Distribution center", "Hotel renovation"],
    "Service work": ["Tenant improvement, suite 200", "Roof replacement", "Restroom renovations", "Lobby remodel",
                     "Parking lot repairs", "Classroom upgrades"],
}
STAGES = [("Prospecting", 10), ("Qualification", 20), ("Proposal", 50), ("Negotiation", 75)]
LOSS_REASONS = ["Low bid lost", "Owner chose another GC", "Project shelved", "Budget cut", "No decision"]
LEAD_SOURCES = ["Repeat owner", "Architect referral", "Bid board", "Developer relationship", "Public RFQ"]
ACCOUNT_WORDS = {
    "Healthcare": (["St. Anne", "Riverside", "Hill Country", "Trinity Valley", "Northpark"],
                   ["Health", "Medical Center", "Surgical Hospital", "Health System", "Clinics"]),
    "K-12 education": (["Bluebonnet", "Caliche Flats", "Red Oak Valley", "Pecan Grove", "Live Oak Prairie", "Cypress Bend"],
                       ["ISD", "Consolidated ISD", "Collegiate Academy"]),
    "Office & tenant finish": (["Larkspur", "Highline", "Stonebridge", "Riverwalk", "Prairie Gate", "Westbrook"],
                               ["Properties", "Office Partners", "Realty", "Development", "Holdings"]),
    "Industrial & warehouse": (["Tidewater", "Saltgrass", "Harbor Point", "Redfish Bay", "Coral Ridge"],
                               ["Logistics", "Distribution", "Industrial Park", "Fabricators", "Cold Storage"]),
    "Retail & hospitality": (["Mission Plaza", "Old Mill", "Sunset Ridge", "Lakeview", "Market Square"],
                             ["Hospitality", "Retail Partners", "Hotels", "Shopping Center"]),
    "Public works": (["Port Larkin", "Rio Seco", "Cypress Flats", "Mesquite Springs", "Lake Coralline"],
                     ["Public Works", "Parks & Recreation", "Facilities Department", "County Facilities"]),
}
ACCOUNTS_PER_BRANCH = 60
DEALS_PER_DAY = 0.20
SEASON_AMPLITUDE = 0.06

LOSS_JOB_OFFICE = "SAT"    # planted: one big job there is now projected to lose money
UNDERBILL_OFFICE = "AUS"   # planted: one job there bills two months behind its progress
PENDING_CO_OFFICE = "HOU"  # planted: a pile of change orders waiting on the owner for months

VENDORS = [  # key, name, category, terms days, lead days, chance late, yearly drift
    ("concrete", "Alamo Ready-Mix", "Materials", 30, 3, 0.08, 0.05),
    ("steel", "Lone Star Rebar & Steel", "Materials", 30, 14, 0.20, 0.06),
    ("lumber", "Pecos Lumber & Supply", "Materials", 30, 5, 0.10, 0.04),
    ("mep", "Gulfway Mechanical Subcontractors", "Subcontract", 45, 20, 0.15, 0.04),
    ("electric", "Brazos Electric Contractors", "Subcontract", 45, 20, 0.12, 0.04),
    ("drywall", "Hill Country Drywall & Paint", "Subcontract", 45, 15, 0.10, 0.03),
    ("roofing", "Redbud Roofing", "Subcontract", 45, 15, 0.18, 0.03),
    ("site", "Caliche Site Work", "Subcontract", 45, 10, 0.12, 0.03),
    ("rental", "Trinity Equipment Rental", "Equipment", 30, 2, 0.05, 0.04),
    ("concrete_dup", "ALAMO READY MIX INC", "Materials", 30, 3, 0.08, 0.05),
]
ITEMS = []

PEOPLE = {
    "head_office": [("Chief Operating Officer", "Operations", "Salary"), ("Controller", "Finance", "Salary"),
                    ("Project Accountant", "Finance", "Hourly"), ("AP Specialist", "Finance", "Hourly"),
                    ("Safety Director", "Safety", "Salary"), ("HR Manager", "People", "Salary"),
                    ("Chief Estimator", "Preconstruction", "Salary")],
    "frontline_head_dept": "Operations",
    "roles": [
        {"title": "Carpenter", "department": "Field Operations", "seats": 10, "quit": 0.025, "fill_days": 30, "lead": "Foreman"},
        {"title": "Laborer", "department": "Field Operations", "seats": 8, "quit": 0.035, "fill_days": 20},
        {"title": "Equipment Operator", "department": "Field Operations", "seats": 3, "quit": 0.015, "fill_days": 40},
        {"title": "Superintendent", "department": "Field Operations", "seats": 3, "quit": 0.008, "fill_days": 75, "pay": "Salary"},
        {"title": "Project Manager", "department": "Project Management", "seats": 3, "quit": 0.008, "fill_days": 70, "pay": "Salary"},
        {"title": "Project Engineer", "department": "Project Management", "seats": 2, "quit": 0.012, "fill_days": 45, "pay": "Salary"},
    ],
    "frontline": "Field Operations",
    "short": ("SAT", [2, 5]),
    "growth": [("HOU", dt.date(2026, 3, 2))],
    "certs": [("NCCCO crane operator certification", 5, "Equipment Operator"), ("OSHA 30", None, "Superintendent"),
              ("OSHA 30", None, "Foreman"), ("OSHA 10", None, "Carpenter"), ("OSHA 10", None, "Laborer"),
              ("First aid and CPR", 2, "Foreman"), ("First aid and CPR", 2, "Superintendent")],
    "license": "NCCCO crane operator certification",
    "overtime": {"frontline": 3.5, "summer": 2.5, "busy_months": (5, 6, 7, 8), "short_factor": 24, "branch": {"SAT": 2}},
}
