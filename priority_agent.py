from anthropic import Anthropic
import importlib
import check_errors
import os
from dotenv import load_dotenv
import agent_evaluation

load_dotenv()
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
priority_agent = Anthropic(api_key=anthropic_api_key) 

gaq_response = agent_evaluation.agent_gaq_feedback()
tax_response = agent_evaluation.agent_tax_difference_feedback()

gaq_error, statistics_dict = check_errors.check_gaq_errors()
tax_difference, related_dict = check_errors.check_tax_difference()
def agent_priority_feedback():
        response_priority = priority_agent.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=750,
            messages=[
            {"role": "user",
            "content": f"""
        GAQ means Gross Amount Quotation.
        You are a prioritization analyst. You are given two previous analyses:
- GAQ_RESPONSE: {gaq_response}
- TAX_RESPONSE: {tax_response}

You also have raw context with dates and amounts:
- STATISTICS_DICT (GAQ-related): {statistics_dict}
- RELATED_DICT (Tax-related): {related_dict}

Task:  
Decide which discrepancy should be prioritized first: GAQ or TAX.  
You must reason based mainly on financial impact, then recency (time since it happened) and regulatory risk.
Do not use fixed weights instead, explain your reasoning step by step.

---

Output format(Markdown, similar style to the other agents):

1. Short Summary  
State clearly which discrepancy should be prioritized and why.

2. Comparison Table  
| Group | Largest Impact (amount) | Total Impact | Most Recent Date | Regulatory Risk |
|-------|--------------------------|--------------|------------------|-----------------|

3. Decision Path  
Step-by-step explanation (2-5 bullet points) of how you reached the decision.

4. Next Steps  
A short list of recommended follow-ups: what to address immediately, what can be monitored.

---

Constraints
- Write in English.  
- Keep it concise, professional, and operational.  
- If any value is missing, write `"N/A"`.  
- Do not output JSON. Only Markdown text with the sections above.
    """
    }
            ]
        )
        
        return response_priority.content[0].text


