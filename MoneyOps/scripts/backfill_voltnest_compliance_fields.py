from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re

from pymongo import MongoClient


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
TARGET_ORG_NAME = "VoltNest Energy Solutions Pvt. Ltd."


def read_env_value(key: str) -> str:
    pattern = re.compile(rf"^\s*{re.escape(key)}=(.*)$")
    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    raise RuntimeError(f"Missing {key} in {ENV_PATH}")


def to_decimal(value) -> Decimal:
    return Decimal(str(value or "0"))


def quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def inclusive_gst(amount: Decimal, rate: Decimal = Decimal("0.18")) -> tuple[Decimal, Decimal]:
    gst = quantize(amount * rate / (Decimal("1.00") + rate))
    taxable = quantize(amount - gst)
    return taxable, gst


@dataclass(frozen=True)
class VendorProfile:
    vendor_name: str
    vendor_gstin: str = ""
    vendor_pan: str = ""
    gst_mode: str = "18_inclusive"  # 18_inclusive, none
    itc_eligible: bool = True
    has_receipt: bool = True
    bank_matched: bool = True


def infer_profile(category: str, description: str) -> VendorProfile:
    text = (description or "").lower()
    category_key = (category or "").lower()

    if category_key == "rent":
        return VendorProfile(
            vendor_name="Lower Parel Realty LLP",
            vendor_pan="AABFL9210K",
            gst_mode="none",
            itc_eligible=False,
        )
    if category_key == "salaries":
        return VendorProfile(
            vendor_name="VoltNest Payroll",
            gst_mode="none",
            itc_eligible=False,
        )
    if category_key == "fuel":
        return VendorProfile(
            vendor_name="HPCL Mobility Fleet Card",
            gst_mode="none",
            itc_eligible=False,
        )
    if category_key == "software":
        if "cloud monitoring" in text:
            return VendorProfile("ChargeCloud Systems Pvt Ltd", "27AAECC4821J1ZB", "AAECC4821J")
        return VendorProfile("GridPulse Software Solutions Pvt Ltd", "27AADCG1142M1ZT", "AADCG1142M")
    if category_key == "utilities":
        return VendorProfile("Airtel Business Services", "27AACCB2894G1Z5", "AACCB2894G")
    if category_key == "marketing":
        if "tender" in text or "compliance" in text:
            return VendorProfile("TenderFlow Advisory LLP", "27AAJFT5521K1ZV", "AAJFT5521K")
        return VendorProfile("UrbanReach Media Private Limited", "27AACCU2255M1ZU", "AACCU2255M")
    if category_key == "travel":
        return VendorProfile("FastTrack Mobility Services Pvt Ltd", "27AACCF9012L1ZE", "AACCF9012L")
    if category_key == "hardware":
        if "subcontract labour" in text or "civil and electrical" in text:
            return VendorProfile("SparkGrid Electrical Contractors", "27ABHFS4512P1ZK", "ABHFS4512P")
        if "electrical panels" in text or "cabling" in text:
            return VendorProfile("PowerRoute Industrial Supplies Pvt Ltd", "27AACCP3801D1Z6", "AACCP3801D")
        if "consumables" in text or "spares" in text:
            return VendorProfile("Electra Components LLP", "27AAGFE2921C1ZP", "AAGFE2921C")
        return VendorProfile("ChargeGrid Hardware Private Limited", "27AAGCC5124R1ZT", "AAGCC5124R")

    return VendorProfile("VoltNest General Vendor", gst_mode="none", itc_eligible=False)


def compute_amounts(amount: Decimal, profile: VendorProfile) -> tuple[Decimal, Decimal]:
    if profile.gst_mode == "18_inclusive":
        return inclusive_gst(amount)
    return quantize(amount), Decimal("0.00")


def main() -> None:
    mongo_uri = read_env_value("MONGODB_URI")
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=20000)
    db = client["moneyops"]

    org = db["business_organizations"].find_one({"legalName": TARGET_ORG_NAME, "deletedAt": None})
    if not org:
        raise RuntimeError(f"Could not find organization {TARGET_ORG_NAME!r}")
    org_id = str(org["_id"])

    expense_updates = 0
    for txn in db["transactions"].find({"orgId": org_id, "type": "EXPENSE", "deletedAt": None}):
        category = txn.get("category", "")
        description = txn.get("description", "")
        profile = infer_profile(category, description)
        amount = to_decimal(txn.get("amount"))
        taxable_amount, gst_amount = compute_amounts(amount, profile)

        update_doc = {
            "vendorName": profile.vendor_name,
            "vendorGstin": profile.vendor_gstin,
            "vendorPan": profile.vendor_pan,
            "taxableAmount": str(taxable_amount),
            "gstAmount": str(gst_amount),
            "itcEligible": bool(profile.itc_eligible and profile.vendor_gstin and gst_amount > 0),
            "hasReceipt": profile.has_receipt,
            "bankMatched": profile.bank_matched,
        }

        current = {key: txn.get(key) for key in update_doc}
        if current != update_doc:
            db["transactions"].update_one({"_id": txn["_id"]}, {"$set": update_doc})
            expense_updates += 1

    invoice_updates = 0
    for invoice in db["invoices"].find({"orgId": org_id, "status": "PAID", "deletedAt": None}):
        payments = list(
            db["transactions"]
            .find(
                {
                    "orgId": org_id,
                    "invoiceId": str(invoice["_id"]),
                    "type": "INCOME",
                    "deletedAt": None,
                    "transactionDate": {"$exists": True},
                },
                {"transactionDate": 1},
            )
            .sort("transactionDate", 1)
        )
        if not payments:
            continue
        latest_payment_date = payments[-1]["transactionDate"]
        if invoice.get("paymentDate") != latest_payment_date:
            db["invoices"].update_one({"_id": invoice["_id"]}, {"$set": {"paymentDate": latest_payment_date}})
            invoice_updates += 1

    print(f"VoltNest orgId: {org_id}")
    print(f"Updated expense records: {expense_updates}")
    print(f"Updated paid invoices with paymentDate: {invoice_updates}")


if __name__ == "__main__":
    main()
