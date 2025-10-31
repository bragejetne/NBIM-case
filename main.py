import streamlit as st
import check_errors
import agent_evaluation as ae
import priority_agent as pa


st.set_page_config(page_title="Dividend Reconciliation Report", layout="wide")

st.title("Dividend Reconciliation Analysis")
st.caption("This dashboard shows deviations found between NBIM and Custody dividend bookings.")

gaq_error = check_errors.check_gaq_errors()[0] if isinstance(check_errors.check_gaq_errors(), tuple) else check_errors.check_gaq_errors()
tax_difference = check_errors.check_tax_difference()[0] if isinstance(check_errors.check_tax_difference(), tuple) else check_errors.check_tax_difference()

def _count_items(d, kind: str | None = None):
    if not d:
        return 0

    #Special for tax
    if kind == "taxdiff":
        if isinstance(d, dict):
            if {"nbim", "custody"}.issubset(d.keys()):
                return 1

            if all(isinstance(v, dict) and {"nbim", "custody"}.issubset(v.keys()) for v in d.values()):
                return len(d)
        return 1
    total = 0
    if isinstance(d, dict):
        for v in d.values():
            if isinstance(v, list):
                total += len(v)
            elif isinstance(v, dict):
                if any(isinstance(x, list) for x in v.values()):
                    total += sum(len(x) if isinstance(x, list) else 1 for x in v.values())
                else:
                    total += 1
            else:
                total += 1
        return total

    return len(d) if isinstance(d, (list, tuple, set)) else 1


issues = []
if gaq_error:
    issues.append({"key": "gaq", "title": "GAQ mismatches (Gross Amount Quotation)",
                "subtitle": "Breaks in GAQ = DPS x Nominal", "count": _count_items(gaq_error)})

if tax_difference:
    issues.append({"key": "taxdiff", "title": "Tax rate differences",
                "subtitle": "NBIM WHT rate ≠ Custody WHT rate", "count": _count_items(tax_difference, kind="taxdiff")})

if not issues:
    st.success("No deviations found. All checks passed.")
    st.stop()

# Cache alle agentrapporter ved sidelast 
@st.cache_data(show_spinner=False, ttl=900)
def _render_report(key: str) -> str:
    try:
        if key == "gaq":
            return ae.agent_gaq_feedback() or "No GAQ errors."
        if key == "taxdiff":
            return ae.agent_tax_difference_feedback() or "No tax rate differences."
        if key == "taxapplied":
            return ae.agent_tax_applied_error_feedback() or "No wrong-tax-applied breaks."
        if key == "taxcalc":
            return ae.wrong_tax_calculated() or "No wrong tax calculations."
    except Exception as e:
        return f"**Error while generating report:** {e}"
    return "No report."

@st.cache_data(show_spinner=False, ttl=900)
def _render_priority_report() -> str:
    return pa.agent_priority_feedback()

# Compute everything up-front so both views are instant
with st.spinner("Computing analyst reports..."):
    reports = {it["key"]: _render_report(it["key"]) for it in issues}
with st.spinner("Computing priority..."):
    priority_report = _render_priority_report()

labels = [f"{i['title']} • {i['count']} found" for i in issues]
keys = [i["key"] for i in issues]

tab_detected, tab_priority = st.tabs([
    "Detected deviations",
    "Order of priority"
])

with tab_detected:
    st.subheader("Detected deviations", divider="gray")

    selection = st.radio(
        "Choose a deviation type to review",
        options=keys,
        format_func=lambda k: labels[keys.index(k)],
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("---")
    sel = next(i for i in issues if i["key"] == selection)
    st.subheader(sel["title"])
    st.caption(sel["subtitle"])
    st.markdown(reports[selection], unsafe_allow_html=True)

with tab_priority:
    st.subheader("Order of priority", divider="gray")
    st.markdown(priority_report, unsafe_allow_html=True)