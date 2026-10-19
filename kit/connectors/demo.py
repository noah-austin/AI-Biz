"""Demo connectors: read the fake Bluestem systems from JSON files.

They map source field names (Salesforce-style and QuickBooks-style) into the
standard tables exactly as a real connector would, so everything downstream is
the same code a client gets.
"""
import json
from pathlib import Path

from ..config import get_settings
from .base import Connector, ObjectSpec


def _load(rel: str, options: dict) -> list[dict]:
    base = Path(options.get("path", "source"))
    if not base.is_absolute():
        base = get_settings().client_dir / base
    return json.loads((base / rel).read_text())


class DemoCRM(Connector):
    source = "demo CRM"

    def objects(self):
        o = self.options
        return [
            ObjectSpec("crm.users", "crm.users", ["id", "name", "email", "title", "branch_code", "active"],
                       lambda: ({"id": r["Id"], "name": r["Name"], "email": r["Email"], "title": r["Title"],
                                 "branch_code": r["BranchCode"], "active": r["IsActive"]}
                                for r in _load("crm/users.json", o))),
            ObjectSpec("crm.accounts", "crm.accounts",
                       ["id", "name", "segment", "city", "state", "branch_code", "created_at"],
                       lambda: ({"id": r["Id"], "name": r["Name"], "segment": r["Segment"], "city": r["City"],
                                 "state": r["State"], "branch_code": r["BranchCode"],
                                 "created_at": r["CreatedDate"]}
                                for r in _load("crm/accounts.json", o))),
            ObjectSpec("crm.opportunities", "crm.opportunities",
                       ["id", "name", "account_id", "owner_id", "branch_code", "deal_type", "stage", "is_closed",
                        "is_won", "probability", "amount", "margin_pct", "close_date", "created_at",
                        "modified_at", "loss_reason", "lead_source", "exclude_from_reporting"],
                       lambda: ({"id": r["Id"], "name": r["Name"], "account_id": r["AccountId"],
                                 "owner_id": r["OwnerId"], "branch_code": r["BranchCode"],
                                 "deal_type": r["RecordType"], "stage": r["StageName"],
                                 "is_closed": r["IsClosed"], "is_won": r["IsWon"],
                                 "probability": r["Probability"], "amount": r["Amount"],
                                 "margin_pct": r["MarginPct"], "close_date": r["CloseDate"],
                                 "created_at": r["CreatedDate"], "modified_at": r["LastModifiedDate"],
                                 "loss_reason": r["LossReason"], "lead_source": r["LeadSource"],
                                 "exclude_from_reporting": r["ExcludeFromReporting"]}
                                for r in _load("crm/opportunities.json", o))),
            ObjectSpec("crm.opportunity_history", "crm.opportunity_history",
                       ["id", "opportunity_id", "field", "old_value", "new_value", "changed_at"],
                       lambda: ({"id": r["Id"], "opportunity_id": r["OpportunityId"], "field": r["Field"],
                                 "old_value": r["OldValue"], "new_value": r["NewValue"],
                                 "changed_at": r["CreatedDate"]}
                                for r in _load("crm/opportunity_history.json", o)),
                       mode="history"),
        ]


class DemoAccounting(Connector):
    source = "demo accounting"

    def objects(self):
        o = self.options
        return [
            ObjectSpec("acct.customers", "acct.customers", ["id", "name", "crm_account_id", "terms_days"],
                       lambda: ({"id": r["Id"], "name": r["DisplayName"], "crm_account_id": r["CrmAccountId"],
                                 "terms_days": r["TermsDays"]}
                                for r in _load("accounting/customers.json", o))),
            ObjectSpec("acct.invoices", "acct.invoices",
                       ["id", "number", "customer_id", "invoice_date", "due_date", "amount", "amount_paid",
                        "paid_date", "reference", "memo"],
                       lambda: ({"id": r["Id"], "number": r["DocNumber"], "customer_id": r["CustomerId"],
                                 "invoice_date": r["TxnDate"], "due_date": r["DueDate"], "amount": r["TotalAmt"],
                                 "amount_paid": r["AmountPaid"], "paid_date": r["PaidDate"],
                                 "reference": r["Reference"], "memo": r["Memo"]}
                                for r in _load("accounting/invoices.json", o))),
        ]


def _spec(name, rel, fields, options, mode="snapshot"):
    """One object whose source fields map one-to-one onto table columns: fields is {column: SourceField}."""
    return ObjectSpec(name, name, list(fields),
                      lambda: ({col: r[src] for col, src in fields.items()} for r in _load(rel, options)), mode=mode)


class DemoHR(Connector):
    source = "demo HR and payroll"

    def objects(self):
        o = self.options
        employees = ObjectSpec(
            "hr.employees", "hr.employees",
            ["id", "name", "email", "title", "department", "branch_code", "hire_date", "termination_date",
             "termination_type", "manager_id", "pay_type", "employment_type"],
            lambda: ({"id": r["Id"], "name": f'{r["FirstName"]} {r["LastName"]}', "email": r["Email"], "title": r["JobTitle"],
                      "department": r["Department"], "branch_code": r["LocationCode"], "hire_date": r["HireDate"],
                      "termination_date": r["TerminationDate"], "termination_type": r["TerminationType"],
                      "manager_id": r["ManagerId"], "pay_type": r["PayType"], "employment_type": r["EmploymentType"]}
                     for r in _load("hr/employees.json", o)))
        return [
            employees,
            _spec("hr.certifications", "hr/certifications.json",
                  {"id": "Id", "employee_id": "EmployeeId", "name": "Certification", "issued_date": "IssuedDate",
                   "expires_date": "ExpiresDate"}, o),
            _spec("hr.timesheets", "hr/timesheets.json",
                  {"id": "Id", "employee_id": "EmployeeId", "week_start": "WeekStart", "regular_hours": "RegularHours",
                   "overtime_hours": "OvertimeHours", "pto_hours": "PtoHours", "approved": "Approved"}, o),
            _spec("hr.requisitions", "hr/requisitions.json",
                  {"id": "Id", "title": "Title", "department": "Department", "branch_code": "LocationCode",
                   "opened_date": "OpenedDate", "filled_date": "FilledDate", "status": "Status", "reason": "Reason",
                   "applicants": "Applicants"}, o),
        ]


class DemoFieldService(Connector):
    source = "demo field service"

    def objects(self):
        o = self.options
        return [
            _spec("fsm.work_orders", "fieldservice/work_orders.json",
                  {"id": "Id", "number": "JobNumber", "account_id": "AccountId", "branch_code": "BranchCode",
                   "job_type": "JobType", "priority": "Priority", "status": "Status", "created_at": "CreatedAt",
                   "scheduled_date": "ScheduledDate", "arrived_at": "ArrivedAt", "completed_at": "CompletedAt",
                   "technician_id": "TechnicianId", "labor_hours": "LaborHours", "billable": "Billable",
                   "billable_amount": "BillableAmount", "invoice_number": "InvoiceNumber", "is_callback": "IsCallback",
                   "parent_id": "ParentWorkOrderId"}, o),
            _spec("fsm.work_order_parts", "fieldservice/work_order_parts.json",
                  {"id": "Id", "work_order_id": "WorkOrderId", "sku": "Sku", "qty": "Qty", "location_id": "LocationId",
                   "used_date": "UsedDate"}, o),
        ]


class DemoInventory(Connector):
    source = "demo inventory"

    def objects(self):
        o = self.options
        return [
            _spec("inv.items", "inventory/items.json",
                  {"id": "Sku", "description": "Description", "category": "Category", "standard_cost": "StandardCost",
                   "preferred_vendor_id": "PreferredVendorId", "critical": "Critical", "active": "Active"}, o),
            _spec("inv.locations", "inventory/locations.json",
                  {"id": "Id", "name": "Name", "kind": "Kind", "branch_code": "BranchCode"}, o),
            _spec("inv.stock", "inventory/stock.json",
                  {"id": "Id", "location_id": "LocationId", "sku": "Sku", "on_hand": "OnHand", "reorder_point": "ReorderPoint",
                   "reorder_qty": "ReorderQty", "last_issued_date": "LastIssuedDate", "last_counted_date": "LastCountedDate"}, o),
            _spec("inv.adjustments", "inventory/adjustments.json",
                  {"id": "Id", "adj_date": "Date", "location_id": "LocationId", "sku": "Sku", "qty": "Qty", "reason": "Reason"},
                  o, mode="history"),
        ]


class DemoPurchasing(Connector):
    source = "demo purchasing"

    def objects(self):
        o = self.options
        return [
            _spec("ap.vendors", "purchasing/vendors.json",
                  {"id": "Id", "name": "Name", "category": "Category", "terms_days": "TermsDays"}, o),
            _spec("ap.purchase_orders", "purchasing/purchase_orders.json",
                  {"id": "Id", "number": "PONumber", "vendor_id": "VendorId", "branch_code": "BranchCode", "kind": "Kind",
                   "ordered_date": "OrderedDate", "expected_date": "ExpectedDate", "received_date": "ReceivedDate",
                   "status": "Status", "amount": "Amount", "billed_amount": "BilledAmount", "deal_id": "DealId"}, o),
            _spec("ap.po_lines", "purchasing/po_lines.json",
                  {"id": "Id", "po_id": "POId", "sku": "Sku", "description": "Description", "qty": "Qty",
                   "unit_price": "UnitPrice"}, o),
        ]


class DemoOrders(Connector):
    source = "demo orders (ERP)"

    def objects(self):
        o = self.options
        return [
            _spec("ord.orders", "orders/orders.json",
                  {"id": "Id", "number": "OrderNumber", "account_id": "AccountId", "branch_code": "BranchCode", "rep_id": "RepId",
                   "channel": "Channel", "order_date": "OrderDate", "requested_date": "RequestedDate", "status": "Status",
                   "first_ship_date": "FirstShipDate", "last_ship_date": "LastShipDate", "invoice_number": "InvoiceNumber"}, o),
            _spec("ord.order_lines", "orders/order_lines.json",
                  {"id": "Id", "order_id": "OrderId", "sku": "Sku", "qty_ordered": "QtyOrdered",
                   "qty_first_shipment": "QtyFirstShipment", "qty_shipped": "QtyShipped", "unit_price": "UnitPrice",
                   "unit_cost": "UnitCost"}, o),
        ]
