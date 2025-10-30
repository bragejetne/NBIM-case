from anthropic import Anthropic
import check_errors
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")
gaq_estimation_client = Anthropic(api_key=api_key)
tax_estimation_client = Anthropic(api_key=api_key)

gaq_error, statistics_dict = check_errors.check_gaq_errors()
tax_difference, related_dict = check_errors.check_tax_difference()


def agent_gaq_feedback():
    response_gaq = ''

    if gaq_error:
        response_gaq = gaq_estimation_client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=600,
            messages=[
            {"role": "user",
            "content": f"""
You are a reconciliation analyst. You are given this Python dict of Gross Amount Quotation errors:
{gaq_error}, and these are statistics regarding columns that affects calculation of Gross Amount Quotation (gaq): {statistics_dict}.
Find out what has happened and why the gaq is different

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
- Two tables with columns:
  Table 1: row_id | side | DPS | Nominal | Holding Quantity | GAQ_reported | GAQ_expected | delta 
  Table 2: diagnosis AND suggested_fixes. Include BOTH.
  Make them look good for visibility and reading
CONSTRAINTS:
- Do not invent rows or fields beyond the dict.
- If a value is missing, write "N/A" and proceed.
- Keep explanations concise, deterministic, and actionable.
                """ }
            ]
        )
        
    if response_gaq:
        return response_gaq.content[0].text
    



def agent_tax_difference_feedback():
    response_tax = ''

    if tax_difference:

        response_tax = tax_estimation_client.messages.create(
            model="claude-sonnet-4-5",        
            max_tokens=600,
            
            messages=[
            {"role": "user",
            "content": f"""
You are a reconciliation analyst. You are given this dict of rows where NBIM and Custodian have different tax rates. {tax_difference}.Use web research in order 
to find information on different tax rates in which the countries the compies operates in. here is related context from dataset you should use to find out why NBIM has a higher total tax than custody: {related_dict}.

TASK:
1) Detect and calculate the difference in percentage points (diff_pp = NBIM_rate - Custody_rate).
2) Suggest up to 3  hypotheses why rates differ (e.g., treaty vs standard, relief-at-source vs reclaim, local tax vs no local tax).
3) Recommend minimal evidence needed to resolve (1-2 items).
4) Rate severity on a 1-10 scale (1 = negligible, 10 = critical).
5) Assign remediation priority: "Escalate" (if severity ≥ 5) or "Monitor" (if < 5).

OUTPUT (Markdown) VERY IMPORTANT:
- Short summary: total breaks, severity range, and overall status.
- Two detailed tables with these columns:
  table 1: row_id | NBIM_rate_% | Custody_rate_% | diff_pp 
  table 2: hypothesis | evidence_needed |
  make them fit the screen good for visibility
- End with a short "Next Steps" list summarizing what actions to take and notes you found out.

CONSTRAINTS:
- Keep text concise, deterministic, and operational.
- Do not assert which side is correct unless the data proves it.
"""

}
        ]
        )

    if response_tax:
        return response_tax.content[0].text

