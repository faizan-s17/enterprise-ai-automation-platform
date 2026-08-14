"""A single entry point for every AI call in the platform.

Providers are tried in order: OpenAI, then Gemini, then a deterministic local
fallback. The fallback matters more than it looks. It keeps every endpoint
returning a useful, correctly shaped response with no API key configured, so
the platform can be installed, demonstrated, and tested without spending money
or leaking documents to a third party.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.config import settings

log = logging.getLogger(__name__)


@dataclass
class AIResult:
    text: str
    model: str
    provider: str

    @property
    def is_fallback(self) -> bool:
        return self.provider == "local"


def _openai(prompt: str, system: str, json_mode: bool) -> AIResult:
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    resp = client.chat.completions.create(
        model=settings.AI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        **kwargs,
    )
    return AIResult(
        text=(resp.choices[0].message.content or "").strip(),
        model=settings.AI_MODEL,
        provider="openai",
    )


def _gemini(prompt: str, system: str, json_mode: bool) -> AIResult:
    # google-generativeai is fully deprecated with no further updates; this
    # uses its replacement, the unified google-genai SDK.
    from google import genai
    from google.genai import types

    model_name = "gemini-2.0-flash"
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json" if json_mode else "text/plain",
    )
    resp = client.models.generate_content(
        model=model_name, contents=prompt, config=config
    )
    return AIResult(text=(resp.text or "").strip(), model=model_name, provider="gemini")


def complete(prompt: str, system: str = "You are a helpful business assistant.",
             json_mode: bool = False) -> AIResult:
    """Run a completion against whichever provider is configured."""
    if settings.OPENAI_API_KEY:
        try:
            return _openai(prompt, system, json_mode)
        except Exception as exc:
            log.warning("OpenAI call failed, falling through: %s", exc)
    if settings.GEMINI_API_KEY:
        try:
            return _gemini(prompt, system, json_mode)
        except Exception as exc:
            log.warning("Gemini call failed, falling through: %s", exc)
    return AIResult(text="", model="local-fallback", provider="local")


def complete_json(prompt: str, system: str, fallback: dict) -> tuple[dict, AIResult]:
    """Completion that must return an object.

    Models wrap JSON in prose or fences often enough that parsing the first
    balanced object out of the reply is worth doing rather than trusting the
    response format flag alone.
    """
    result = complete(prompt, system, json_mode=True)
    if not result.text:
        return fallback, result

    data = _extract_json(result.text)
    if data is None:
        log.warning("Model did not return parseable JSON; using fallback")
        return fallback, result
    return data, result


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start=start):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(text[start : i + 1])
                    return parsed if isinstance(parsed, dict) else None
                except json.JSONDecodeError:
                    return None
    return None


# --------------------------------------------------------------- local fallback
MONEY = re.compile(
    r"(?:(?P<cur>PKR|USD|EUR|GBP|Rs\.?)\s*)?(?P<amt>\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+\.\d{2})",
    re.IGNORECASE,
)
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Z][a-z]+\s+\d{4})\b")
# A prefix alone is not a reference: "INVOICE" starts with INV but is a word.
# Require either a separator followed by an alphanumeric run, or digits fused
# straight onto the prefix, so INV-2026-0847 and PO-NG-2026-112 match while
# INVOICE and DOCUMENT do not.
REFERENCE = re.compile(
    r"\b((?:INV|PO|REF|DOC)(?:[-/][A-Z0-9]+)+|(?:INV|PO|REF|DOC)\d[A-Z0-9-]*)\b",
    re.IGNORECASE,
)


def extractive_summary(text: str, max_points: int = 5) -> str:
    """Pick the most information-dense lines when no model is available.

    Lines carrying a reference, amount, date, or an action verb are ranked
    above filler, which produces a summary that is genuinely useful rather
    than the first N lines of the document.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "No readable text was extracted from this document."

    scored: list[tuple[int, int, str]] = []
    for idx, line in enumerate(lines):
        score = 0
        if REFERENCE.search(line):
            score += 4
        if MONEY.search(line):
            score += 3
        if DATE.search(line):
            score += 2
        if re.search(r"\b(due|total|action|require|approve|payment|terms)\b",
                     line, re.IGNORECASE):
            score += 2
        if 15 <= len(line) <= 160:
            score += 1
        # A line starting lower-case is usually the tail of a sentence the PDF
        # extractor wrapped, so it reads as a fragment when quoted alone.
        if line[:1].islower():
            score -= 3
        if score > 0:
            scored.append((-score, idx, line))

    scored.sort()
    picked = [line for _, _, line in scored[:max_points]]
    if not picked:
        picked = lines[:max_points]
    return "\n".join(f"- {p}" for p in picked)


def extract_fields(text: str) -> dict:
    """Regex pass for the fields an invoice or contract usually carries."""
    fields: dict = {}

    ref = REFERENCE.search(text)
    if ref:
        fields["reference"] = ref.group(1).strip()

    amounts = []
    currency = None
    for m in MONEY.finditer(text):
        raw = m.group("amt").replace(",", "")
        try:
            amounts.append(float(raw))
        except ValueError:
            continue
        # Take the currency from whichever amount carries one. Reading only the
        # first match misses documents that list bare figures in a table and
        # name the currency once, on the total.
        if currency is None and m.group("cur"):
            currency = m.group("cur").upper().rstrip(".")
    if amounts:
        fields["amounts_found"] = sorted(set(amounts), reverse=True)[:5]
        fields["total_amount"] = max(amounts)
        if currency:
            fields["currency"] = currency

    # PDF extraction wraps lines mid-phrase, so "27\nAugust 2026" is one date
    # split across two lines. Collapse whitespace before de-duplicating,
    # otherwise the same date is reported twice in different shapes.
    dates = [re.sub(r"\s+", " ", d).strip() for d in DATE.findall(text)]
    if dates:
        fields["dates_found"] = list(dict.fromkeys(dates))[:5]

    return fields
