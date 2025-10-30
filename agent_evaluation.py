
from anthropic import Anthropic
import importlib
import check_errors
import os
from dotenv import load_dotenv
from json import dumps

load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")
#Loading agents
gaq_estimation_client = Anthropic(api_key=api_key)
tax_estimation_client = Anthropic(api_key=api_key)
tax_applied_client = Anthropic(api_key=api_key)
tax_calculation_client = Anthropic(api_key=api_key)

gaq_error, statistics_dict = check_errors.check_gaq_errors()
wrong_tax_applied, wrong_tax_calculation = check_errors.check_naq_errors()
tax_difference, related_dict = check_errors.check_tax_difference()

#Tools for agent
TAX_RESEARCH_TOOLS = [{"type": "web_search_20250305", "name": "web_search"}]

def agent_gaq_feedback():
    response_gaq = ''

    if gaq_error:
        response_gaq = gaq_estimation_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=300,
            messages=[
            {"role": "user",
            "content": f"""
You are a reconciliation analyst. You are given this Python dict of GAQ errors:
{gaq_error}, and these are statistics regarding columns that may affect calculation of Gross Amount Quotation (gaq): {statistics_dict}.

Meaning per entry (tuple):
(DPS_rate, Nominal_basis, Reported_GAQ) for the side that failed the check.
The validation rule is: GAQ_expected = DPS_rate * Nominal_basis.

Main task: use both dictionaries to find out what the root cause of the GAQ discrepancies are.

TASK:
1) **Break Detection**:
   - For each item, compute GAQ_expected and compare to GAQ_reported.
   - Confirm the difference (delta) and identify which side (NBIM or Custodian) is inconsistent.

2) **Automated Remediation Guidance**:
   - Provide a short, precise explanation of why the discrepancy exists (e.g., unit mismatch, rounding error, wrong DPS).
   - Suggest 1-3 concrete checks to resolve (prioritize deterministic checks such as unit scaling, rounding conventions, currency alignment).
   - Assess severity of the discrepancy on a 1-10 scale:
     - 1 = negligible (e.g., $1 difference),
     - 10 = critical (e.g., ≥ $10,000,000 difference).
   - Indicate whether this discrepancy should be escalated immediately or monitored.

OUTPUT (Markdown):
- Short summary of how many GAQ breaks were found and their severity range.
- A table with columns:
  row_id | side | DPS | Nominal | GAQ_reported | GAQ_expected | delta | diagnosis | suggested_fix | severity | remediation_priority

CONSTRAINTS:
- Do not invent rows or fields beyond the dict.
- If a value is missing, write "N/A" and proceed.
- Keep explanations concise, deterministic, and actionable.
                """ }
            ]
        )
        
    if response_gaq:
        return response_gaq.content[0].text
    



# If the research online takes more than one minute, stop the research and reply "i dont know"
# tools = TAX_RESEARCH_TOOLS,
def agent_tax_difference_feedback():
    response_tax = ''

    if tax_difference:

        response_tax = tax_estimation_client.messages.create(
            model="claude-sonnet-4-5",        
            max_tokens=300,
            
            messages=[
            {"role": "user",
            "content": f"""
You are a reconciliation analyst. You are given this dict of rows where NBIM and Custodian have different tax rates. {tax_difference}.Use web research in order 
to find information on different tax rates in which the countries the compies operates in. here is related context from dataset you should use to find out why NBIM has a higher total tax than custody: {related_dict}.

TASK:
1) Detect and calculate the difference in percentage points (diff_pp = NBIM_rate - Custody_rate).
2) Suggest up to 2 generic hypotheses why rates differ (e.g., treaty vs standard, relief-at-source vs reclaim, ADR ratio).
3) Recommend minimal evidence needed to resolve (1–2 items).
4) Rate severity on a 1–10 scale (1 = negligible, 10 = critical).
5) Assign remediation priority: "Escalate" (if severity ≥ 5) or "Monitor" (if < 5).

OUTPUT (Markdown):
- Short summary: total breaks, severity range, and overall status.
- Detailed table with these columns:
  row_id | NBIM_rate_% | Custody_rate_% | diff_pp | hypothesis | evidence_needed | severity | remediation_priority
- End with a short "Next Steps" list (1–3 bullet points) summarizing what actions to take.

CONSTRAINTS:
- Keep text concise, deterministic, and operational.
- Do not assert which side is correct unless the data proves it.
"""

}
        ]
        )

    if response_tax:
        return response_tax.content[0].text


def agent_tax_applied_error_feedback():
    response_tax_applied = None

    if wrong_tax_applied:
        response_tax_applied = tax_applied_client.messages.create(
            model="claude-sonnet-4-5",
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
    4) Assess the severity of the discrepancy on a scale from 1 to 10, where:
       - 1 indicates a negligible discrepancy (e.g., $1 difference),
       - 10 indicates a critical discrepancy (e.g., $10,000 or more).

    OUTPUT (Markdown):
    - Short summary.
    - Table columns:
    row_id | side | GROSS | TAX | NET_reported | NET_expected | delta | diagnosis | suggested_fix | severity

    CONSTRAINTS:
    - Do not add assumptions beyond the tuples.
    - Prefer deterministic checks first; keep text concise.
    """
            }]
        )

    if response_tax_applied:
        return response_tax_applied.content[0].text
    


# tools = TAX_RESEARCH_TOOLS
def wrong_tax_calculated():
    if wrong_tax_calculation:

        response_tax = tax_calculation_client.messages.create(
            model="claude-sonnet-4-5",        
            max_tokens=500,
            tools = TAX_RESEARCH_TOOLS,
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
    4) Assess the severity of the discrepancy on a scale from 1 to 10, where:
       - 1 indicates a negligible discrepancy (e.g., $1 difference),
       - 10 indicates a critical discrepancy (e.g., $10,000 or more).
    5) Provide spreadsheet-ready instructions.

    OUTPUT (Markdown):
    - Short summary.
    - Table columns:
    row_id | side | GAQ | tax_rate_% | TAX_reported | TAX_expected | delta | diagnosis | suggested_fix | severity

    CONSTRAINTS:
    - Use only the provided dict; do not assume FX conversions unless stated.
    - Keep each diagnosis within ~15 words.
    """}
        ]
        )

    if response_tax:
        return response_tax.content[0].text
    

    