import streamlit as st
import pandas as pd
from dividend_reconciliation import find_breaks
from llm_agent_system import ReconciliationAgent, AgentRole
from dotenv import load_dotenv
import os

load_dotenv()

st.set_page_config(page_title="NBIM Dividend Reconciliation", layout="wide")
st.title("🧾 NBIM Dividend Reconciliation Prototype")

st.markdown("""
Dette er en prototype for å identifisere og forklare avvik mellom NBIMs interne dividend-data og Custodian-rapporter.

🔍 **LLM brukes kun for forklaring av avvik**, og kun der det er nødvendig.

Last opp to CSV-filer nedenfor for å begynne:
""")

nbim_file = st.file_uploader("NBIM-fil (CSV)", type="csv")
custody_file = st.file_uploader("Custody-fil (CSV)", type="csv")

if nbim_file and custody_file:
    df_nbim = pd.read_csv(nbim_file, sep=';', dtype=str)
    df_custody = pd.read_csv(custody_file, sep=';', dtype=str)
    
    st.success("Filer lastet inn!")

    # Vis inputdata
    with st.expander("📂 Se NBIM-data"):
        st.dataframe(df_nbim)
    with st.expander("📂 Se Custody-data"):
        st.dataframe(df_custody)

    st.divider()
    st.header("🔎 Avviksanalyse")
    breaks = find_breaks(df_nbim, df_custody)

    if not breaks:
        st.success("Ingen avvik funnet!")
    else:
        st.info(f"Fant {len(breaks)} avvik.")

        for b in breaks:
            with st.expander(f"📌 Avvik for event {b['event_key']}"):
                st.json(b)
                
                if b["break_type"] in ["amount_mismatch", "missing_event"]:
                    agent = ReconciliationAgent(role=AgentRole.ANALYST)
                    with st.spinner("Analyserer med Claude..."):
                        decision = agent.analyze(b)

                    st.subheader("🤖 Claude-analyse")
                    st.write(f"**Beslutning:** {decision.decision}")
                    st.write(f"**Forklaring:** {decision.reasoning}")
                    st.write(f"**Anbefalt handling:** {decision.recommended_action}")
                    st.write(f"**Risikovurdering:** {decision.risk_assessment}")
                else:
                    st.warning("Denne typen avvik håndteres ikke i MVP-en.")

    st.divider()
    st.markdown("🧠 *Bygget med Claude Sonnet og Streamlit – kun for demonstrasjon.*")
else:
    st.warning("Vennligst last opp begge filene for å starte analysen.")
