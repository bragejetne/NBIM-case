import streamlit as st
import check_errors
import agent_evaluation as ae

st.set_page_config(page_title="Dividend Reconciliation Report", layout="wide")

st.title("📊 Dividend Reconciliation Analysis")
st.caption("This dashboard shows deviations found between NBIM and Custody dividend bookings.")

# --- 1) Break detection (for telling og meny) --------------------------------
gaq_error = check_errors.check_gaq_errors()[0] if isinstance(check_errors.check_gaq_errors(), tuple) else check_errors.check_gaq_errors()
naq = check_errors.check_naq_errors()
wrong_tax_applied = naq[0] if isinstance(naq, tuple) else (naq.get("wrong_tax_applied") if isinstance(naq, dict) else {})
wrong_tax_calculation = naq[1] if isinstance(naq, tuple) else (naq.get("wrong_tax_calculation") if isinstance(naq, dict) else {})
tax_difference = check_errors.check_tax_difference()

def _count_items(d):
    if not d:
        return 0
    total = 0
    for v in d.values():
        if isinstance(v, list):
            total += len(v)
        elif isinstance(v, dict):
            # f.eks. {'nbim': [...], 'custody': [...]}
            if any(isinstance(x, list) for x in v.values()):
                total += sum(len(x) if isinstance(x, list) else 1 for x in v.values())
            else:
                total += 1
        else:
            total += 1
    return total

issues = []
if gaq_error:
    issues.append({"key": "gaq", "title": "GAQ mismatches (Gross Amount Quotation)",
                   "subtitle": "Breaks in GAQ = DPS × Nominal", "count": _count_items(gaq_error)})
if tax_difference:
    issues.append({"key": "taxdiff", "title": "Tax rate differences",
                   "subtitle": "NBIM WHT rate ≠ Custody WHT rate", "count": _count_items(tax_difference)})
if wrong_tax_applied:
    issues.append({"key": "taxapplied", "title": "Wrong tax applied (NET ≠ GROSS − TAX)",
                   "subtitle": "Net amount does not reconcile to gross minus tax", "count": _count_items(wrong_tax_applied)})
if wrong_tax_calculation:
    issues.append({"key": "taxcalc", "title": "Wrong tax calculation (TAX ≠ GROSS × rate)",
                   "subtitle": "Tax cost is not GAQ × rate", "count": _count_items(wrong_tax_calculation)})

if not issues:
    st.success("✅ No deviations found. All checks passed.")
    st.stop()

# --- 2) Precompute & cache alle agentrapporter ved sidelast -------------------
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

with st.spinner("Precomputing analyst reports..."):
    reports = {it["key"]: _render_report(it["key"]) for it in issues}

# --- 3) UI: midtstilt meny og detalj uten nye API-kall -----------------------
left, center, right = st.columns([1, 2, 1])
with center:
    st.subheader("Detected deviations", divider="gray")

    labels = [f"{i['title']} • {i['count']} found" for i in issues]
    keys = [i["key"] for i in issues]
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

    # Hent ferdig generert rapport fra cache
    st.markdown(reports[selection], unsafe_allow_html=True)
