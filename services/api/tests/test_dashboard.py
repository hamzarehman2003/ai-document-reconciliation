"""The dashboard numbers.

The dev database already has documents, so these tests check how the numbers
change when known documents are added.
"""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.matching import update_matches
from app.services.review import Decision, decide
from factories import add_three_way_set


def dashboard(client: TestClient) -> dict:
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    return response.json()


def eur(amounts: list[dict]) -> tuple[Decimal, int]:
    """(amount, invoices) for EUR, or zeros."""
    for item in amounts:
        if item["currency"] == "EUR":
            return Decimal(item["amount"]), item["invoices"]
    return Decimal("0"), 0


def problem_count(numbers: dict, code: str) -> int:
    return next((p["count"] for p in numbers["top_problems"] if p["code"] == code), 0)


def test_a_problem_invoice_counts_as_money_at_risk_until_approved(
    client: TestClient, session: Session
) -> None:
    before = dashboard(client)

    _, _, invoice = add_three_way_set(session, ordered="10", received="8", billed="10")
    update_matches(session, invoice)  # billed 10, received 8: needs review, 50.00 EUR
    session.flush()
    with_problem = dashboard(client)

    assert eur(with_problem["money_at_risk"]) == (
        eur(before["money_at_risk"])[0] + Decimal("50.00"),
        eur(before["money_at_risk"])[1] + 1,
    )
    assert (
        with_problem["invoices"]["by_match_status"]["needs_review"]
        == before["invoices"]["by_match_status"]["needs_review"] + 1
    )
    assert problem_count(with_problem, "QTY_EXCEEDS_RECEIVED") == (
        problem_count(before, "QTY_EXCEEDS_RECEIVED") + 1
    )
    assert with_problem["documents"]["by_type"]["invoice"] == (
        before["documents"]["by_type"]["invoice"] + 1
    )

    decide(session, invoice.match_case, Decision.APPROVE, "Sara", "Rest arrives Monday")
    session.flush()
    after_approval = dashboard(client)

    assert eur(after_approval["money_at_risk"]) == eur(before["money_at_risk"])
    assert eur(after_approval["approved_amount"])[0] == (
        eur(before["approved_amount"])[0] + Decimal("50.00")
    )
    assert (
        after_approval["daily"][-1]["approved"] == before["daily"][-1]["approved"] + 1
    )


def test_daily_activity_covers_fourteen_days(client: TestClient) -> None:
    daily = dashboard(client)["daily"]

    assert len(daily) == 14
    days = [item["day"] for item in daily]
    assert days == sorted(days)  # oldest first, no gaps in between


def test_match_rate_is_a_share(client: TestClient) -> None:
    rate = dashboard(client)["invoices"]["match_rate"]

    assert rate is None or 0 <= rate <= 1
