import argparse
import copy
import sys
from typing import Any, Dict, List

import requests


CLIENTS: List[Dict[str, Any]] = [
    {
        "name": "Arjun Desai",
        "email": "arjun.desai@prestigetechpark.com",
        "phoneNumber": "+91 98201 55473",
        "company": "Prestige Tech Park Private Limited",
        "gstin": "27AAGCP7712M1ZX",
        "paymentTerms": 15,
        "currency": "INR",
        "notes": "Largest client. IT campus in Pune, 3 buildings. Installed 12 AC chargers Phase 1. Phase 2 (8 DC fast chargers) in discussion. Pays within 15 days. Key contact is Facilities Manager.",
        "status": "ACTIVE",
    },
    {
        "name": "Sunita Rao",
        "email": "sunita.rao@lemontreehotels.com",
        "phoneNumber": "+91 91672 34891",
        "company": "Lemon Tree Hotels Limited",
        "gstin": "27AAACL8563P1ZU",
        "paymentTerms": 40,
        "currency": "INR",
        "notes": "Hospitality client. 3 hotel properties in Pune needing guest EV charging. Brand mandate from HQ to install chargers by June 2026. Slow payer - avg 35-40 days. Always pays eventually.",
        "status": "ACTIVE",
    },
    {
        "name": "Vikram Nair",
        "email": "vikram.nair@bluedartexpress.com",
        "phoneNumber": "+91 95940 12384",
        "company": "BlueDart Express Limited",
        "gstin": "27AAACB0446L1Z6",
        "paymentTerms": 30,
        "currency": "INR",
        "notes": "Fleet client. Transitioning part of delivery fleet to EV. Needs depot charging at Pune warehouse. Large project but procurement is slow - multiple approvals needed. High value, worth the wait.",
        "status": "ACTIVE",
    },
    {
        "name": "Priya Sharma",
        "email": "priya.sharma@infosysbpm.com",
        "phoneNumber": "+91 80956 77231",
        "company": "Infosys BPM Limited",
        "gstin": "29AAACI6720R1ZL",
        "paymentTerms": 15,
        "currency": "INR",
        "notes": "AMC client. 8 chargers installed by previous vendor, now outsourcing maintenance to us. Quarterly AMC billing. Very reliable payment - auto-approved by procurement. SEBI ESG reporting drives their compliance.",
        "status": "ACTIVE",
    },
    {
        "name": "Rohit Kulkarni",
        "email": "rohit.kulkarni@marriottindia.com",
        "phoneNumber": "+91 99213 08845",
        "company": "Marriott Hotels India Pvt. Ltd.",
        "gstin": "27AABCM4418Q1ZS",
        "paymentTerms": 60,
        "currency": "INR",
        "notes": "Premium hospitality. Wants 6 fast chargers across Marriott Pune and Marriott Kolhapur. High-value project. Partial payments - releases 40% on PO, 40% on completion, 20% after 60 days. Has penalty clause for delays beyond April 30.",
        "status": "ACTIVE",
    },
]


INVOICES: List[Dict[str, Any]] = [
    {
        "lookup_email": "arjun.desai@prestigetechpark.com",
        "invoiceNumber": "VN-2026-001",
        "issueDate": "2026-01-15",
        "dueDate": "2026-01-30",
        "status": "PAID",
        "notes": "Prestige Tech Park Phase 1 complete. Paid in full.",
        "items": [
            {"type": "PRODUCT", "description": "AC EV Charger Supply & Installation (7.2kW)", "quantity": 12, "rate": 38500, "gstPercent": 18},
            {"type": "SERVICE", "description": "Site Survey & Electrical Feasibility Report", "quantity": None, "rate": 18000, "gstPercent": 18},
            {"type": "PRODUCT", "description": "Civil Work & Cable Ducting (per charger)", "quantity": 12, "rate": 6200, "gstPercent": 18},
        ],
        "payments": [
            {"amount": 647112, "transactionDate": "2026-01-28", "description": "Prestige Tech Park full payment", "paymentMethod": "BANK_TRANSFER", "referenceNumber": "VN-PRESTIGE-001"},
        ],
    },
    {
        "lookup_email": "priya.sharma@infosysbpm.com",
        "invoiceNumber": "VN-2026-002",
        "issueDate": "2026-02-01",
        "dueDate": "2026-02-15",
        "status": "PAID",
        "notes": "Quarterly AMC invoice for Infosys BPM.",
        "items": [
            {"type": "SERVICE", "description": "Quarterly AMC - 8 AC Chargers (Jan-Mar 2026)", "quantity": None, "rate": 42000, "gstPercent": 18},
            {"type": "SERVICE", "description": "Remote Monitoring & Fault Alert Service (Q1)", "quantity": None, "rate": 8500, "gstPercent": 18},
        ],
        "payments": [
            {"amount": 59590, "transactionDate": "2026-02-11", "description": "Infosys BPM AMC payment", "paymentMethod": "BANK_TRANSFER", "referenceNumber": "VN-INFOSYS-002"},
        ],
    },
    {
        "lookup_email": "sunita.rao@lemontreehotels.com",
        "invoiceNumber": "VN-2026-003",
        "issueDate": "2026-02-10",
        "dueDate": "2026-02-25",
        "status": "OVERDUE",
        "notes": "Lemon Tree Hotels rollout. Slow payer, still pending.",
        "items": [
            {"type": "PRODUCT", "description": "AC EV Charger Supply & Installation (7.2kW)", "quantity": 6, "rate": 38500, "gstPercent": 18},
            {"type": "SERVICE", "description": "Hotel Lobby Charging Bay Design & Setup", "quantity": None, "rate": 35000, "gstPercent": 18},
            {"type": "SERVICE", "description": "Site Survey - 3 Properties", "quantity": None, "rate": 24000, "gstPercent": 18},
        ],
        "payments": [],
    },
    {
        "lookup_email": "rohit.kulkarni@marriottindia.com",
        "invoiceNumber": "VN-2026-004",
        "issueDate": "2026-02-20",
        "dueDate": "2026-03-15",
        "status": "SENT",
        "notes": "Advance invoice. Forty percent received against PO.",
        "items": [
            {"type": "PRODUCT", "description": "DC Fast Charger Supply & Installation (30kW)", "quantity": 4, "rate": 112000, "gstPercent": 18},
            {"type": "PRODUCT", "description": "AC Charger Supply & Installation (7.2kW)", "quantity": 2, "rate": 38500, "gstPercent": 18},
            {"type": "SERVICE", "description": "Project Management & Commissioning Fee", "quantity": None, "rate": 45000, "gstPercent": 18},
            {"type": "SERVICE", "description": "FAME III Subsidy Application Assistance", "quantity": None, "rate": 22000, "gstPercent": 18},
        ],
        "payments": [
            {"amount": 274704, "transactionDate": "2026-02-22", "description": "Marriott PO advance payment", "paymentMethod": "BANK_TRANSFER", "referenceNumber": "VN-MARRIOTT-004"},
        ],
    },
    {
        "lookup_email": "vikram.nair@bluedartexpress.com",
        "invoiceNumber": "VN-2026-005",
        "issueDate": "2026-03-05",
        "dueDate": "2026-03-31",
        "status": "SENT",
        "notes": "BlueDart warehouse charging project. Raised this month, payment pending.",
        "items": [
            {"type": "SERVICE", "description": "Depot Charging Infrastructure Design & Planning", "quantity": None, "rate": 55000, "gstPercent": 18},
            {"type": "PRODUCT", "description": "DC Fast Charger Supply & Installation (60kW)", "quantity": 3, "rate": 185000, "gstPercent": 18},
            {"type": "SERVICE", "description": "Smart Load Management System Setup", "quantity": None, "rate": 68000, "gstPercent": 18},
            {"type": "SERVICE", "description": "Electrical Panel Upgrade & Safety Compliance", "quantity": None, "rate": 42000, "gstPercent": 18},
        ],
        "payments": [],
    },
]


def build_headers(args: argparse.Namespace) -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Org-Id": args.org_id,
        "X-User-Id": args.user_id,
    }
    if args.auth_token:
        headers["Authorization"] = f"Bearer {args.auth_token}"
    return headers


def request_json(method: str, url: str, headers: Dict[str, str], payload: Dict[str, Any] | None = None) -> Any:
    response = requests.request(method, url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    if not response.text:
        return None
    return response.json()


def safe_request_json(method: str, url: str, headers: Dict[str, str], payload: Dict[str, Any] | None = None) -> Any | None:
    response = requests.request(method, url, headers=headers, json=payload, timeout=30)
    if response.status_code >= 400:
        return None
    if not response.text:
        return None
    return response.json()


def line_total(item: Dict[str, Any]) -> Dict[str, Any]:
    quantity = item["quantity"] if item["type"] == "PRODUCT" else 1
    subtotal = round(item["rate"] * quantity, 2)
    gst = round(subtotal * item["gstPercent"] / 100, 2)
    total = round(subtotal + gst, 2)
    return {
        **item,
        "lineSubtotal": subtotal,
        "lineGst": gst,
        "lineTotal": total,
    }


def update_invoice_status(base_url: str, headers: Dict[str, str], invoice: Dict[str, Any], status: str) -> Dict[str, Any]:
    payload = copy.deepcopy(invoice)
    payload["status"] = status
    return request_json("PUT", f"{base_url}/api/invoices/{invoice['id']}", headers, payload)


def fetch_existing_clients(base_url: str, headers: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    clients = request_json("GET", f"{base_url}/api/clients?limit=200", headers) or []
    return {client["email"].lower(): client for client in clients if client.get("email")}


def fetch_existing_invoices(base_url: str, headers: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    invoices = request_json("GET", f"{base_url}/api/invoices", headers) or []
    return {invoice["invoiceNumber"]: invoice for invoice in invoices if invoice.get("invoiceNumber")}


def seed_clients(base_url: str, headers: Dict[str, str], team_code: str) -> Dict[str, Dict[str, Any]]:
    existing_by_email = fetch_existing_clients(base_url, headers)
    created: Dict[str, Dict[str, Any]] = {}
    for client in CLIENTS:
        payload = {**client, "teamActionCode": team_code, "source": "MANUAL"}
        email_key = client["email"].lower()
        existing = existing_by_email.get(email_key)
        if existing:
            result = request_json("PUT", f"{base_url}/api/clients/{existing['id']}", headers, payload)
            print(f"Updated client: {result['name']}")
        else:
            result = request_json("POST", f"{base_url}/api/clients", headers, payload)
            print(f"Created client: {result['name']}")
        created[client["email"]] = result
    return created


def seed_invoices(base_url: str, headers: Dict[str, str], team_code: str, clients_by_email: Dict[str, Dict[str, Any]]) -> None:
    existing_by_number = fetch_existing_invoices(base_url, headers)
    for spec in INVOICES:
        client = clients_by_email[spec["lookup_email"]]
        items = [line_total(item) for item in spec["items"]]
        payload = {
            "invoiceNumber": spec["invoiceNumber"],
            "clientId": client["id"],
            "issueDate": spec["issueDate"],
            "dueDate": spec["dueDate"],
            "currency": "INR",
            "notes": spec["notes"],
            "items": items,
            "teamActionCode": team_code,
            "source": "MANUAL",
        }
        created = existing_by_number.get(spec["invoiceNumber"])
        if created:
            print(f"Reusing invoice: {created['invoiceNumber']}")
        else:
            created = request_json("POST", f"{base_url}/api/invoices", headers, payload)
            print(f"Created invoice: {created['invoiceNumber']}")
            existing_by_number[created["invoiceNumber"]] = created

        if spec["status"] != "DRAFT":
            created = update_invoice_status(base_url, headers, created, spec["status"])

        for payment in spec["payments"]:
            reference_number = payment.get("referenceNumber")
            existing_payment = safe_request_json(
                "GET",
                f"{base_url}/api/invoices/{created['id']}/payments",
                headers,
            ) or []
            if reference_number and any(p.get("referenceNumber") == reference_number for p in existing_payment):
                print(f"  Reusing payment {reference_number} for {created['invoiceNumber']}")
                continue
            request_json("POST", f"{base_url}/api/invoices/{created['id']}/payment", headers, payment)
            print(f"  Recorded payment of {payment['amount']} for {created['invoiceNumber']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the VoltNest client and invoice universe.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--org-id", required=True, help="Organization ID")
    parser.add_argument("--user-id", required=True, help="User ID")
    parser.add_argument("--team-code", required=True, help="Team security code")
    parser.add_argument("--auth-token", help="Optional bearer token")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    headers = build_headers(args)
    try:
        clients_by_email = seed_clients(args.base_url.rstrip("/"), headers, args.team_code)
        seed_invoices(args.base_url.rstrip("/"), headers, args.team_code, clients_by_email)
        print("VoltNest universe seeded successfully.")
        return 0
    except requests.HTTPError as exc:
        body = exc.response.text[:500] if exc.response is not None else ""
        print(f"HTTP error: {exc}\n{body}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
