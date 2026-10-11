"""Read-only as-of cash balance selection and evidence warnings."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from matapan.models import Account, AccountBalance


def account_report(session: Session, account: Account, as_of: date) -> dict:
    latest_date = session.scalar(
        select(func.max(AccountBalance.as_of_date)).where(
            AccountBalance.account_id == account.id,
            AccountBalance.currency_code == account.currency_code,
            AccountBalance.as_of_date <= as_of,
        )
    )
    report = {
        "account_id": account.id,
        "currency_code": account.currency_code,
        "as_of_date": as_of,
        "scope": "account_cash",
        "status": "unavailable",
        "amount": None,
        "balance_as_of_date": latest_date,
        "balance_status": "missing",
        "source": None,
        "source_timestamp": None,
        "observation_ids": [],
        "carried_forward": False,
        "issues": [],
    }
    if latest_date is None:
        report["issues"] = ["No balance observation exists on or before the requested date."]
        return report

    observations = session.scalars(
        select(AccountBalance)
        .where(
            AccountBalance.account_id == account.id,
            AccountBalance.currency_code == account.currency_code,
            AccountBalance.as_of_date == latest_date,
        )
        .order_by(AccountBalance.id)
    ).all()
    if not any(observation.source == "manual" for observation in observations):
        latest_timestamp = max(observation.source_timestamp or "" for observation in observations)
        observations = [
            observation
            for observation in observations
            if (observation.source_timestamp or "") == latest_timestamp
        ]
    report["observation_ids"] = [observation.id for observation in observations]
    amounts = {observation.amount for observation in observations}
    if len(amounts) != 1:
        report["balance_status"] = "conflicted"
        report["issues"] = [
            "Conflicting balance observations exist for this date. "
            "The source observations are preserved; no amount has been selected."
        ]
        return report

    report.update(
        status="partial",
        amount=observations[0].amount,
        balance_status=(
            "user_confirmed"
            if any(item.source == "manual" for item in observations)
            else "source_reported"
        ),
        source=("manual" if any(item.source == "manual" for item in observations) else "revolut"),
        source_timestamp=(
            None
            if any(item.source == "manual" for item in observations)
            else observations[0].source_timestamp
        ),
        carried_forward=latest_date < as_of,
        issues=["This report covers this account's cash only; it is not complete net worth."],
    )
    if report["source"] == "revolut":
        report["issues"].append(
            "This is a source-reported running balance at the stated local timestamp, "
            "not a confirmed end-of-day or statement-end balance."
        )
        report["issues"].append("Imported transaction history may be incomplete.")
    if latest_date < as_of:
        report["issues"].append(
            "The balance is carried forward from its observation date; "
            "it has not been confirmed for the requested date."
        )
    return report
