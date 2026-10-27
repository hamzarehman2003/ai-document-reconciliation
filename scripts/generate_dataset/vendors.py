"""The fictional buyer, its vendors and what each vendor sells."""

from decimal import Decimal

from faker import Faker

from scripts.generate_dataset.models import CatalogItem, Company, LayoutStyle, Vendor

BUYER_STYLE = LayoutStyle(
    font="Helvetica",
    accent="#334155",
    header_align="left",
    date_format="%d %B %Y",
    number_label="PO Number",
    amount_format="us",
)

# vendor_id: (name, currency, tax rate, invoice prefix, layout style)
VENDOR_PROFILES: dict[str, tuple[str, str, str, str, LayoutStyle]] = {
    "V001": (
        "Apex Office Supplies",
        "USD",
        "0.08",
        "AOS",
        LayoutStyle(
            font="Helvetica",
            accent="#1f4e79",
            header_align="left",
            date_format="%Y-%m-%d",
            number_label="Invoice No.",
            amount_format="us",
        ),
    ),
    "V002": (
        "Northfield Packaging Co.",
        "GBP",
        "0.20",
        "NPC",
        LayoutStyle(
            font="Times-Roman",
            accent="#7a1f1f",
            header_align="right",
            date_format="%d/%m/%Y",
            number_label="Invoice #",
            amount_format="us",
        ),
    ),
    "V003": (
        "Bluewater Electronics",
        "USD",
        "0.08",
        "BWE",
        LayoutStyle(
            font="Helvetica",
            accent="#0f766e",
            header_align="right",
            date_format="%B %d, %Y",
            number_label="Bill Number",
            amount_format="us",
        ),
    ),
    "V004": (
        "Cedar & Pine Furniture",
        "EUR",
        "0.19",
        "CPF",
        LayoutStyle(
            font="Times-Roman",
            accent="#5b4636",
            header_align="left",
            date_format="%d.%m.%Y",
            number_label="Invoice Number",
            amount_format="eu",
        ),
    ),
    "V005": (
        "Summit Industrial Parts",
        "USD",
        "0.08",
        "SIP",
        LayoutStyle(
            font="Courier",
            accent="#333333",
            header_align="left",
            date_format="%m/%d/%Y",
            number_label="INVOICE NO",
            amount_format="us",
        ),
    ),
    "V006": (
        "Greenleaf Cleaning Products",
        "EUR",
        "0.21",
        "GCP",
        LayoutStyle(
            font="Helvetica",
            accent="#3f6212",
            header_align="right",
            date_format="%d %b %Y",
            number_label="Inv. No.",
            amount_format="eu",
        ),
    ),
}

# vendor_id: [(sku, description, unit price), ...]
CATALOGS: dict[str, list[tuple[str, str, str]]] = {
    "V001": [
        ("AOS-1001", "A4 copy paper, 80gsm (box of 5 reams)", "24.50"),
        ("AOS-1002", "Ballpoint pens, blue (pack of 50)", "12.90"),
        ("AOS-1003", "Lever arch files, assorted", "3.75"),
        ("AOS-1004", "Sticky notes 76x76mm (pack of 12)", "8.40"),
        ("AOS-1005", "Desk organiser, mesh black", "15.99"),
        ("AOS-1006", "Whiteboard markers (set of 8)", "9.60"),
        ("AOS-1007", "Stapler, heavy duty", "21.00"),
        ("AOS-1008", "Printer toner, black XL", "68.00"),
    ],
    "V002": [
        ("NPC-201", "Corrugated box 40x30x30cm", "1.35"),
        ("NPC-202", "Corrugated box 60x40x40cm", "2.10"),
        ("NPC-203", "Packing tape, clear 48mm x 66m", "1.80"),
        ("NPC-204", "Bubble wrap roll 750mm x 50m", "18.25"),
        ("NPC-205", "Pallet stretch film 500mm", "14.60"),
        ("NPC-206", "Void fill paper roll", "22.40"),
        ("NPC-207", "Mailing bags, grey (pack of 100)", "11.95"),
        ("NPC-208", "Fragile labels (roll of 500)", "6.50"),
    ],
    "V003": [
        ("BWE-3301", "USB-C charging cable 2m", "7.80"),
        ("BWE-3302", "Wireless mouse", "19.50"),
        ("BWE-3303", "Mechanical keyboard, UK layout", "64.00"),
        ("BWE-3304", "27-inch IPS monitor", "189.00"),
        ("BWE-3305", "HDMI cable 3m", "6.20"),
        ("BWE-3306", "Barcode scanner, handheld", "54.90"),
        ("BWE-3307", "Thermal label printer", "129.00"),
        ("BWE-3308", "Surge protector, 6 outlets", "24.75"),
    ],
    "V004": [
        ("CPF-11", "Office chair, ergonomic", "149.00"),
        ("CPF-12", "Standing desk 140x70cm", "329.00"),
        ("CPF-13", "Filing cabinet, 3 drawers", "119.50"),
        ("CPF-14", "Meeting table, oak veneer", "449.00"),
        ("CPF-15", "Bookshelf, 5 tiers", "89.90"),
        ("CPF-16", "Reception sofa, 2 seats", "399.00"),
        ("CPF-17", "Monitor arm, single", "39.00"),
        ("CPF-18", "Under-desk drawer unit", "79.00"),
    ],
    "V005": [
        ("SIP-5501", "Hex bolt M10x50 (box of 100)", "16.40"),
        ("SIP-5502", "Nylon lock nut M10 (box of 100)", "7.25"),
        ("SIP-5503", "Safety gloves, size L (10 pairs)", "18.90"),
        ("SIP-5504", "Hydraulic hose 1/2in, per metre", "9.80"),
        ("SIP-5505", "Ball bearing 6204-2RS", "4.15"),
        ("SIP-5506", "Cable ties 300mm (pack of 100)", "5.60"),
        ("SIP-5507", "Spray lubricant 400ml", "6.95"),
        ("SIP-5508", "Safety goggles, anti-fog", "7.40"),
    ],
    "V006": [
        ("GCP-01", "Multi-surface cleaner 5L", "12.80"),
        ("GCP-02", "Hand soap refill 5L", "14.20"),
        ("GCP-03", "Paper towels (case of 24 rolls)", "26.50"),
        ("GCP-04", "Microfibre cloths (pack of 20)", "11.40"),
        ("GCP-05", "Bin liners 80L (roll of 50)", "8.90"),
        ("GCP-06", "Floor disinfectant 5L", "17.60"),
        ("GCP-07", "Nitrile gloves, medium (box of 100)", "9.75"),
        ("GCP-08", "Mop head replacement", "6.30"),
    ],
}


def build_buyer(fake: Faker) -> Company:
    """Create the fictional company that places the orders."""
    return Company(
        name="Brightline Retail Ltd",
        address=[fake.street_address(), f"{fake.city()}, {fake.postcode()}"],
        email="accounts@brightline-retail.example",
        style=BUYER_STYLE,
    )


def build_vendors(fake: Faker) -> list[Vendor]:
    """Create the fictional suppliers, each with its own document style."""
    vendors = []
    for vendor_id, profile in VENDOR_PROFILES.items():
        name, currency, tax_rate, prefix, style = profile
        domain = name.lower().split()[0].replace("&", "and")
        vendors.append(
            Vendor(
                vendor_id=vendor_id,
                name=name,
                address=[fake.street_address(), f"{fake.city()}, {fake.postcode()}"],
                email=f"billing@{domain}.example",
                currency=currency,
                tax_rate=Decimal(tax_rate),
                invoice_prefix=prefix,
                style=style,
            )
        )
    return vendors


def build_receiving_staff(fake: Faker, count: int = 5) -> list[str]:
    """Names of the warehouse staff who sign goods receipts."""
    return [fake.name() for _ in range(count)]


def catalog_for(vendor: Vendor) -> list[CatalogItem]:
    return [
        CatalogItem(sku=sku, description=description, unit_price=Decimal(price))
        for sku, description, price in CATALOGS[vendor.vendor_id]
    ]
