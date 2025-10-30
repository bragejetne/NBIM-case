
from anthropic import Anthropic
import importlib
import check_errors
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")
#Loading agents
gaq_estimation_client = Anthropic(api_key=api_key)
tax_estimation_client = Anthropic(api_key=api_key)
tax_applied_client = Anthropic(api_key=api_key)
tax_calculation_client = Anthropic(api_key=api_key)

gaq_error = check_errors.check_gaq_errors()
wrong_tax_applied, wrong_tax_calculation = check_errors.check_naq_errors()
tax_difference = check_errors.check_tax_difference()



def agent_gaq_feedback():
    response_gaq = ''

    if gaq_error:

        response_gaq = gaq_estimation_client.messages.create(
            model="claude-haiku-4-5",        
            max_tokens=300,
            messages=[
            {"role": "user",
            "content": f"""
    You are a reconciliation analyst. You are given only this Python dict of GAQ errors:
    {gaq_error}

    Meaning per entry (tuple):
    (DPS_rate, Nominal_basis, Reported_GAQ) for the side that failed the check
    — rule: GAQ_expected = DPS_rate * Nominal_basis.

    TASK:
    1) For each item, compute GAQ_expected and compare to Reported_GAQ.
    2) State which side (NBIM or Custodian) violates GAQ = NB * DPS.
    3) Give a short, precise explanation why it's wrong.
    4) Suggest 1-3 concrete checks to resolve (prioritize deterministic: unit/rounding/currency).

    OUTPUT (Markdown):
    - One-line summary.
    - A table with columns:
    row_id | side | DPS | Nominal | GAQ_reported | GAQ_expected | delta | diagnosis | suggested_fix

    CONSTRAINTS:
    - Do not invent rows or fields beyond the dict.
    - If a value is missing, write "N/A" and proceed.
    - Keep explanations concise and actionable.
    """}
        ]
        )
        

    if response_gaq:
        return response_gaq.content[0].text
    

def agent_tax_difference_feedback():
    response_tax = ''

    if tax_difference:

        response_tax = tax_estimation_client.messages.create(
            model="claude-haiku-4-5",        
            max_tokens=300,
            messages=[
            {"role": "user",
            "content": f"""
    You are a reconciliation analyst. You are given only this dict of rows where NBIM and Custodian have different tax rates:
    {tax_difference}

    Each entry notes the two rates and the row id.

    TASK:
    1) For each row, list NBIM_rate, Custody_rate, and the difference in percentage points.
    2) Give a short hypothesis (max 2 bullets) why rates differ (e.g., treaty rate vs standard, relief-at-source vs reclaim, ADR ratio, residency cutoff date, instrument type).
    3) List the minimal evidence needed to resolve (1-2 items: WHT documentation, market/ticker check, residency on record date).

    OUTPUT (Markdown):
    - One-line summary.
    - Table columns:
    row_id | NBIM_rate_% | Custody_rate_% | diff_pp | hypothesis | evidence_needed


    CONSTRAINTS:
    - Do not assert which is correct unless the dict explicitly proves it.
    - Keep hypotheses generic and operationally useful.
    """}
        ]
        )

    if response_tax:
        return response_tax.content[0].text


def agent_tax_applied_error_feedback():
    response_tax_applied = None

    if wrong_tax_applied:
        response_tax_applied = tax_applied_client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=450,
            temperature=0,
            messages=[{
                "role": "user",
                "content": f"""
    You are a reconciliation analyst. You are given only this dict of rows where NET appears inconsistent:
    {wrong_tax_applied}

    Meaning per entry (tuple):
    (GROSS_amount, TAX_amount, NET_reported)
    — rule: NET_expected = GROSS_amount - TAX_amount.

    TASK:
    1) For each item, compute NET_expected and compare to NET_reported.
    2) State which side is incorrect (NBIM or Custodian).
    3) Brief diagnosis and what to check next (fees, rounding, wrong sign, currency mix).

    OUTPUT (Markdown):
    - One-line summary.
    - Table columns:
    row_id | side | GROSS | TAX | NET_reported | NET_expected | delta | diagnosis | suggested_fix

    CONSTRAINTS:
    - Do not add assumptions beyond the tuples.
    - Prefer deterministic checks first; keep text concise.
    """
            }]
        )

    if response_tax_applied:
        return response_tax_applied.content[0].text
    

def wrong_tax_calculated():
    if wrong_tax_calculation:

        response_tax = tax_calculation_client.messages.create(
            model="claude-haiku-4-5",        
            max_tokens=500,
            messages=[
            {"role": "user",
            "content": f"""
    You are a reconciliation analyst. You are given only this dict of suspected wrong tax calculations:
    {wrong_tax_calculation}

    Meaning per entry (tuple):
    (GAQ_reported, TAX_rate_percent, TAX_cost_reported)
    — rule: TAX_expected = GAQ_reported * (TAX_rate_percent/100).

    TASK:
    1) For each item, compute TAX_expected and compare with TAX_cost_reported.
    2) State whether NBIM or Custodian miscalculated tax cost.
    3) Provide a terse diagnosis and 1-3 probable root causes (rounding, percent vs decimal, ADR ratio, exempt/relief).
    4) Provide spreadsheet-ready instructions.

    OUTPUT (Markdown):
    - One-line summary.
    - Table columns:
    row_id | side | GAQ | tax_rate_% | TAX_reported | TAX_expected | delta | diagnosis | suggested_fix

    CONSTRAINTS:
    - Use only the provided dict; do not assume FX conversions unless stated.
    - Keep each diagnosis within ~15 words.
    """}
        ]
        )

    if response_tax:
        return response_tax.content[0].text
    

    