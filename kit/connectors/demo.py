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
