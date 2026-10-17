"""Connectors: each one reads a source system and maps it into the standard tables."""
from . import demo

REGISTRY = {
    "demo_crm": demo.DemoCRM,
    "demo_accounting": demo.DemoAccounting,
}
