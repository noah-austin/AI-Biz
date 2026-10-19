"""Connectors: each one reads a source system and maps it into the standard tables."""
from . import demo

REGISTRY = {
    "demo_crm": demo.DemoCRM,
    "demo_accounting": demo.DemoAccounting,
    "demo_hr": demo.DemoHR,
    "demo_field_service": demo.DemoFieldService,
    "demo_inventory": demo.DemoInventory,
    "demo_purchasing": demo.DemoPurchasing,
    "demo_orders": demo.DemoOrders,
    "demo_projects": demo.DemoProjects,
}
