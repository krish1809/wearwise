"""The owner's email after each Trend Scout run (docs/AGENTS.md, section 4): what it searched
for, what it read, what it kept and dropped and why, and what it cost. Like a lab notebook, so
the owner can see how it worked, not only what it found. A missing report is also how a missed
scheduled run is noticed (D56).
"""

import html
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.email import Email, EmailSender
from app.core.config import get_settings
from app.models import AgentRun, Trend
from app.services import mail, trends

log = logging.getLogger(__name__)

INDIA = ZoneInfo("Asia/Kolkata")
# Why a run stopped early, in words.
STOPPED = {
    "search_credits": "the month's search credits ran out",
    "time": "it reached its time limit",
    "tokens": "it reached its token limit",
    "model_off": "the model is switched off (AI_PROVIDER)",
    "model_unavailable": "the model didn't answer",
    "model_unreadable": "the model's answer couldn't be read",
    "spend_cap": "today's AI spend cap was reached",
    "search_unavailable": "the search service didn't answer",
    "lapsed": "it never said it had finished",
    "batch_cap": "it reached the most emails one run sends",
}


@dataclass(frozen=True)
class Report:
    subject: str
    text: str
    html: str


def _plural(count: int, word: str) -> str:
    if count == 1:
        return f"{count} {word}"
    return f"{count} {word}es" if word.endswith(("s", "sh", "ch", "x")) else f"{count} {word}s"


def scout_report(db: Session, run: AgentRun, now: datetime) -> Report:
    settings = get_settings()
    steps: dict[str, Any] = run.steps
    saved = steps.get("save") or {}
    added: list[str] = saved.get("added") or []
    merged: list[str] = saved.get("merged") or []
    dropped: list[dict[str, str]] = (steps.get("validate") or {}).get("dropped") or []
    waiting = (
        db.scalar(select(func.count()).select_from(Trend).where(Trend.status == "pending")) or 0
    )
    stopped = STOPPED.get(run.stopped_by or "", run.stopped_by or "")

    if run.status == "failed":
        subject = "Trend Scout failed"
    elif run.status == "stopped":
        subject = f"Trend Scout stopped early: {stopped}"
    elif added:
        subject = f"Trend Scout: {_plural(len(added), 'new trend')}" + (
            " to review" if settings.trends_require_approval else ""
        )
    else:
        subject = "Trend Scout: nothing new"

    # Each block is a heading line (or None) and its lines; empty blocks are left out.
    blocks: list[tuple[str | None, list[str]]] = []
    started = run.started_at.astimezone(INDIA).strftime("%d %b %Y, %H:%M")
    how = "on its schedule" if run.trigger == "schedule" else "started by hand"
    took = (run.finished_at or now) - run.started_at
    opening = [
        f"The Trend Scout ran on {started} (India time), {how}, for "
        f"{_plural(round(took.total_seconds()), 'second')}."
    ]
    if run.status == "failed":
        opening.append("It failed: " + (run.errors[-1] if run.errors else "no reason recorded."))
    elif run.status == "stopped":
        opening.append(f"It stopped early: {stopped}.")
    blocks.append((None, opening))

    plan = steps.get("plan_queries") or {}
    queries: list[str] = plan.get("queries") or []
    if queries:
        heading = "It searched for"
        if plan.get("planned_by") == "template":
            heading += " (from templates: the model's queries couldn't be used)"
        blocks.append((heading + ":", [f"- {q}" for q in queries]))

    search = steps.get("search") or {}
    read = steps.get("read") or {}
    if search:
        line = (
            f"It read {_plural(read.get('read', 0), 'page')} from "
            f"{_plural(search.get('searched', 0), 'search')}"
        )
        if search.get("failed"):
            line += f" ({search['failed']} failed)"
        skipped: dict[str, int] = read.get("skipped") or {}
        if skipped:
            # Most first: the database keeps no order.
            ordered = sorted(skipped.items(), key=lambda item: (-item[1], item[0]))
            line += ". Not read: " + ", ".join(f"{why} ({n})" for why, n in ordered)
        blocks.append((None, [line + "."]))

    found: list[str] = []
    if added:
        label = "New, waiting for your approval" if settings.trends_require_approval else "New"
        found.append(f"- {label}: " + ", ".join(added))
    if merged:
        found.append("- Found again (new sources added): " + ", ".join(merged))
    if dropped:
        found.append("- Dropped: " + "; ".join(f"{d['name']} ({d['reason']})" for d in dropped))
    expired = (steps.get("dedupe_merge") or {}).get("expired") or 0
    if expired:
        found.append(f"- Expired: {_plural(expired, 'trend')} not seen for 8 weeks")
    if search:
        blocks.append(("What it found:", found or ["- Nothing new."]))

    month = trends.credits_used(db, now)
    cost = (
        f"{_plural(run.search_credits, 'search credit')} "
        f"({month} of {settings.search_monthly_credit_cap} this month); "
        f"{run.tokens_in:,} tokens in and {run.tokens_out:,} out"
    )
    # Without the model's prices in the settings there's no cost to give.
    if run.cost_micro_usd:
        cost += f", about ${run.cost_micro_usd / 1_000_000:.4f}"
    blocks.append(("What it cost:", [cost + "."]))
    if run.errors and run.status != "failed":
        blocks.append(("Errors:", [f"- {e}" for e in run.errors]))
    closing = []
    if waiting:
        closing.append(
            f"{_plural(waiting, 'trend')} waiting for your approval: "
            f"{settings.app_url}/admin/trends"
        )
    closing.append(f"Every run: {settings.app_url}/admin/runs")
    blocks.append((None, closing))

    text = "\n\n".join(
        "\n".join(([heading] if heading else []) + lines) for heading, lines in blocks
    )
    return Report(subject, text + "\n", _html(blocks))


def _html(blocks: list[tuple[str | None, list[str]]]) -> str:
    parts: list[str] = []
    for heading, lines in blocks:
        if heading:
            parts.append(f"<p><strong>{html.escape(heading)}</strong></p>")
        items = [line.removeprefix("- ") for line in lines if line.startswith("- ")]
        if items:
            parts.append("<ul>" + "".join(f"<li>{html.escape(i)}</li>" for i in items) + "</ul>")
        parts += [f"<p>{html.escape(line)}</p>" for line in lines if not line.startswith("- ")]
    return '<div style="font-family: sans-serif; line-height: 1.5">' + "".join(parts) + "</div>"


def send_scout_report(db: Session, run: AgentRun, sender: EmailSender, now: datetime) -> int:
    """Email the report to each owner in ADMIN_EMAILS. Returns how many were sent."""
    owners = sorted(get_settings().admins)
    if not owners:
        log.warning("No ADMIN_EMAILS, so the Trend Scout's run report wasn't sent")
        return 0
    report = scout_report(db, run, now)
    sent = 0
    for owner in owners:
        event = mail.send(
            db,
            sender,
            Email(
                to=owner,
                subject=report.subject,
                text=report.text,
                html=report.html,
                key=f"run-report-{run.id}-{owner}",
            ),
            kind="run_report",
            now=now,
        )
        sent += event.status == "sent"
    return sent
