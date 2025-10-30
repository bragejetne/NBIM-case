import streamlit as st
import check_errors
import agent_evaluation
import os


st.set_page_config(page_title="Dividend Reconciliation Report", layout="wide")

st.title("Dividend Reconciliation Analysis")
st.markdown("This dashboard shows deviations found in correlation to NBIM and Custody dividend bookings")

gaq_error = check_errors.check_gaq_errors()
wrong_tax_applied, wrong_tax_calculation = check_errors.check_naq_errors()
tax_difference = check_errors.check_tax_difference()

st.header("Gross Amount Quotation (GAQ) Errors")
if gaq_error:
    with st.spinner("Recieving explanation from GAQ-agent..."):
        gaq_feedback = agent_evaluation.agent_gaq_feedback()
    st.markdown(gaq_feedback)
else:
    st.success("No GAQ errors found")

st.header("Tax Rate Differences")
if tax_difference:
    with st.spinner("Recieving explanation from Tax Difference-agent..."):
        tax_diff_feedback = agent_evaluation.agent_tax_difference_feedback()
    st.markdown(tax_diff_feedback)
else:
    st.success("No differences in tax rates found.")

st.header("Wrong Tax Applied")
if wrong_tax_applied:
    with st.spinner("Recieving explanation from Tax Applied-agent..."):
        tax_applied_feedback = agent_evaluation.agent_tax_applied_error_feedback()
    st.markdown(tax_applied_feedback)
else:
    st.success("No errors in applied taxes found")

st.header("Wrong Tax Calculations (Tax = Gross * Rate)")
if wrong_tax_calculation:
    with st.spinner("Recieving explanation from Tax Calculation-agent..."):
        tax_calc_feedback = agent_evaluation.wrong_tax_calculated()
    st.markdown(tax_calc_feedback)
else:
    st.success("No error in tax calulations found")