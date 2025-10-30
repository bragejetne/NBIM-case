# Dividend Reconciliation System  
**NBIM Summer Internship Case Solution – Documentation of Prompts and Approach**

## Overview  
This project implements a **dividend reconciliation tool** that compares dividend bookings from **NBIM** and **Custody** records.  
It leverages **deterministic checks** for discrepancies and supplements them with **LLM-based prioritization** to analyze and rank the breaks.  

The solution is structured around:  
1. **Data ingestion** (CSV files for NBIM and Custody bookings)  
2. **Error detection** (deterministic rules to identify mismatches)  
3. **Agent-based evaluation** (LLM prompts for structured reasoning)  
4. **Prioritization engine** (deciding which discrepancy should be addressed first, based on financial impact, recency, and regulatory risk)  
5. **Dashboard** (Streamlit app to visualize reconciliation results)  

---

## Project Structure  
```
├── main.py                        # Streamlit dashboard – UI for reconciliation reports
├── check_errors.py                # Deterministic error detection (GAQ, TAX, date/amount mismatches)
├── priority_agent.py              # LLM-based prioritization agent for breaks
├── agent_evaluation.py            # Evaluation helper for LLM responses
├── NBIM_Dividend_Bookings.csv     # Sample NBIM dataset
├── CUSTODY_Dividend_Bookings.csv  # Sample Custody dataset
├── requirements.txt               # Dependencies
└── README.md                      # Documentation (this file)
```

---

## Prompting Approach  

The **LLM agents** (Anthropic Claude API via `anthropic>=0.34`) are used for **structured analysis and prioritization**.  
Instead of asking the model open-endedly, the prompts are designed to be:  

### 1. Error Detection Prompts (`check_errors.py`)  
- **Goal**: Deterministically detect breaks (no LLM).  
- **Types of errors identified**:  
  - **GAQ discrepancies** – Gross Amount Quotation mismatches  
  - **TAX discrepancies** – Incorrect tax rate or withholding difference  
  - (Optional) Date mismatches, FX mismatches  

These are passed downstream as structured dictionaries.  

---

### 2. Evaluation Prompts (`agent_evaluation.py`)  
- **Goal**: Ensure responses are complete and follow the required format.  
- **Checks**:  
  - Has the agent found out why the break happened?  
  - Are reasoning steps explicit?  

This ensures that the LLM output is consistent and production-ready.  

---

### 3. Prioritization Prompts (`priority_agent.py`)  
- **Goal**: Decide which discrepancy matters most.  
- **Prompt style**:  
  ```markdown
  You are a prioritization analyst.  
  Given GAQ_RESPONSE, TAX_RESPONSE, and raw context, decide which discrepancy should be prioritized.  
  Base decision on:
  - Financial impact (primary)  
  - Recency of event (secondary)  
  - Regulatory risk (tertiary)  

  Output format (Markdown):
  1. Short Summary
  2. Comparison Table
  3. Decision Path (2–5 bullets)
  4. Next Steps
  ```
- **Reasoning style**: Step-by-step, structured tables, deterministic layout.  
- **Why this works**: It minimizes hallucinations and ensures repeatable, auditable outputs.  

---

## Dashboard (`main.py`)  
The **Streamlit interface** renders:  
- **Detected errors** (GAQ, TAX, etc.)  
- **Prioritization analysis** from the LLM  
- **Final recommendations**  

This provides an interactive reconciliation report, simulating a real-world financial control workflow.  

---

## Installation  
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Running the App  
```bash
streamlit run main.py
```

---

##  Notes on Approach  
- **Deterministic first, LLM second**:  
  Simple mismatches (amount, tax rate) are best detected with code to avoid ambiguity.  
- **LLM adds prioritization & narrative**:  
  Human-like reasoning is applied only where interpretation is needed.  
- **Scalable design**:  
  Additional agents (FX mismatch, payment-date mismatch) can easily be plugged in.  
