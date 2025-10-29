"""
NBIM Dividend Reconciliation System
====================================
LLM-Powered intelligent reconciliation system for dividend data
Author: [Ditt navn] (NBIM Summer Internship Case Solution)
"""

import pandas as pd
import numpy as np
import json
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# Fargekoder for konsollutskrift (for CLI-demonstrasjon)
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class BreakType(Enum):
    """Classification of reconciliation breaks"""
    AMOUNT_MISMATCH = "Amount Mismatch"
    TAX_RATE_DIFF = "Tax Rate Difference"
    FX_RATE_ISSUE = "FX Rate Issue"
    DATE_MISMATCH = "Date Mismatch"
    QUANTITY_MISMATCH = "Quantity Mismatch"
    MISSING_RECORD = "Missing Record"
    DUPLICATE_RECORD = "Duplicate Record"
    LENDING_IMPACT = "Securities Lending Impact"

@dataclass
class ReconciliationBreak:
    """Data structure for reconciliation breaks"""
    event_key: str
    break_type: BreakType
    nbim_value: Any
    custody_value: Any
    difference: Any
    severity: str
    suggested_action: str
    confidence: float



# --- Robust parsing & normalization -------------------------------------------------

EPS_AMOUNT = 0.01      # 1 cent tålegrense for beløp
EPS_RATE_BPS = 5       # 5 basispunkter for skatterate (0.0005 i fraksjon)

def _clean_str(x):
    if x is None:
        return ""
    return str(x).strip().replace("\u00A0", "")  # fjern NBSP

def _parse_number(x):
    """
    Prøver å tolke x som flyttall. Tåler '1 234,56', '1,234.56', '1234,56'.
    Returnerer NaN ved fiasko.
    """
    s = _clean_str(x)
    if not s:
        return float('nan')
    s = s.replace(" ", "")
    if "," in s and "." in s:
        # antag: komma er tusenskilletegn
        s = s.replace(",", "")
    else:
        # antag: komma er desimal
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return float('nan')

def _to_fraction_rate(x):
    """
    Konverterer skattesats til fraksjon (0.15 for 15%).
    Godtar '15', '15%', 15, 0.15, '0,15', etc.
    """
    s = _clean_str(x)
    if s.endswith("%"):
        s = s[:-1]
        v = _parse_number(s) / 100.0
        return v
    v = _parse_number(s)
    if v > 1.0:
        v = v / 100.0
    return v

def _num(x):
    return _parse_number(x)

def _abs_diff(a, b):
    import math
    if any([
        a is None, b is None,
        isinstance(a, float) and math.isnan(a),
        isinstance(b, float) and math.isnan(b),
    ]):
        return None
    return abs(a - b)

def _ensure_parsed_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Hvis CSV ble lest uten sep=';', blir alt én kolonne med semikolon i headeren."""
    if isinstance(df, pd.DataFrame) and len(df.columns) == 1:
        only = df.columns[0]
        if isinstance(only, str) and ';' in only:
            cols = [c.strip() for c in only.split(';')]
            rows = df.iloc[:, 0].astype(str).str.split(';')
            df = pd.DataFrame(rows.tolist(), columns=cols)
    return df

def _standardize_headers(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().upper() for c in df.columns]
    aliases = {
        'COAC EVENT KEY': 'COAC_EVENT_KEY',
        # legg fler aliaser ved behov
    }
    df = df.rename(columns=aliases)
    return df

def _cast_numeric_columns(df: pd.DataFrame, cols: list[str]) -> None:
    """Kast oppgitte kolonner til numerisk (tåler tusenskilletegn, mellomrom, komma/desimal)."""
    for c in cols:
        if c in df.columns:
            df[c] = df[c].apply(_parse_number)

def _cast_rate_columns(df: pd.DataFrame, cols: list[str]) -> None:
    """Kast skatterate/andel-kolonner til fraksjon (0–1)."""
    for c in cols:
        if c in df.columns:
            df[c] = df[c].apply(_to_fraction_rate)

def _cast_date_columns(df: pd.DataFrame, cols: list[str]) -> None:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True)

NUMERIC_NBIM = [
    'GROSS_AMOUNT_QUOTATION', 'NET_AMOUNT_QUOTATION', 'WTHTAX_AMOUNT_QUOTATION',
    'DIVIDEND_RATE', 'NOMINAL_BASIS', 'QUANTITY',
    # skatterate i NBIM kan ligge i WTHTAX_RATE/TAX_RATE
]

NUMERIC_CUSTODY = [
    'GROSS_AMOUNT', 'NET_AMOUNT', 'TAX_AMOUNT',
    'DIVIDEND_RATE', 'NOMINAL_BASIS', 'QUANTITY',
]

RATE_NBIM = ['WTHTAX_RATE', 'TAX_RATE']
RATE_CUSTODY = ['TAX_RATE']

DATE_NBIM = ['EVENT_EX_DATE', 'EVENT_PAYMENT_DATE', 'EXDATE', 'PAYMENT_DATE']
DATE_CUSTODY = ['EVENT_EX_DATE', 'EVENT_PAYMENT_DATE', 'EX_DATE', 'PAY_DATE', 'RECORD_DATE']



def find_breaks(nbim_df, custody_df):
    system = DividendReconciliationSystem()

    # 1) Robust parsing + header-standardisering
    nbim_df = _ensure_parsed_csv(nbim_df)
    custody_df = _ensure_parsed_csv(custody_df)
    nbim_df = _standardize_headers(nbim_df)
    custody_df = _standardize_headers(custody_df)

    # 2) Nøkler som strenger (unngå 970… -> int)
    if 'COAC_EVENT_KEY' in nbim_df.columns:
        nbim_df['COAC_EVENT_KEY'] = nbim_df['COAC_EVENT_KEY'].astype(str).str.strip()
    if 'COAC_EVENT_KEY' in custody_df.columns:
        custody_df['COAC_EVENT_KEY'] = custody_df['COAC_EVENT_KEY'].astype(str).str.strip()

    # 3) Kast tall-, rate- og datokolonner
    _cast_numeric_columns(nbim_df, NUMERIC_NBIM)
    _cast_numeric_columns(custody_df, NUMERIC_CUSTODY)
    _cast_rate_columns(nbim_df, RATE_NBIM)       # NEW
    _cast_rate_columns(custody_df, RATE_CUSTODY) # NEW
    _cast_date_columns(nbim_df, DATE_NBIM)
    _cast_date_columns(custody_df, DATE_CUSTODY)

    # 4) Inn i systemet
    system.nbim_data = nbim_df
    system.custody_data = custody_df

    # 5) Kjør analyse
    system.analyze_events()

    # 6) Returner serialiserbart
    return [vars(b) for b in getattr(system, "breaks", [])]



class DividendReconciliationSystem:
    """Main reconciliation system logic"""
    def __init__(self):
        self.nbim_data = None
        self.custody_data = None
        self.breaks: List[ReconciliationBreak] = []
        self.matched_records: List[str] = []
        
    def load_data(self, nbim_path: str, custody_path: str):
        """Load and preprocess data from CSV files"""
        print(f"{Colors.HEADER}📊 Loading dividend data...{Colors.ENDC}")
        # Load NBIM and Custody CSVs
        self.nbim_data = pd.read_csv(nbim_path, sep=';', encoding='utf-8-sig')
        print(f"  ✓ Loaded {len(self.nbim_data)} NBIM records")
        self.custody_data = pd.read_csv(custody_path, sep=';', encoding='utf-8-sig')
        print(f"  ✓ Loaded {len(self.custody_data)} Custody records")
        # Clean column names (strip whitespace)
        self.nbim_data.columns = [col.strip() for col in self.nbim_data.columns]
        self.custody_data.columns = [col.strip() for col in self.custody_data.columns]
        # Convert date columns to datetime objects for consistency
        self._convert_dates()
    
    def _convert_dates(self):
        """Convert relevant columns to datetime for NBIM and Custody dataframes"""
        # NBIM date columns
        date_cols_nbim = ['EXDATE', 'PAYMENT_DATE']
        for col in date_cols_nbim:
            if col in self.nbim_data.columns:
                self.nbim_data[col] = pd.to_datetime(self.nbim_data[col], format='%d.%m.%Y', errors='coerce')
        # Custody date columns (several)
        date_cols_custody = ['EVENT_EX_DATE', 'EVENT_PAYMENT_DATE', 'EX_DATE', 'PAY_DATE', 'RECORD_DATE']
        for col in date_cols_custody:
            if col in self.custody_data.columns:
                self.custody_data[col] = pd.to_datetime(self.custody_data[col], format='%d.%m.%Y', errors='coerce')
    
    def analyze_events(self):
        """Analyze all dividend events and identify breaks"""
        print(f"\n{Colors.CYAN}🔍 Analyzing dividend events...{Colors.ENDC}")
        # Determine unique event keys in each dataset
        nbim_events = set(self.nbim_data['COAC_EVENT_KEY'].unique())
        custody_events = set(self.custody_data['COAC_EVENT_KEY'].unique())
        print(f"\n📌 Events found:")
        print(f"  • NBIM: {nbim_events}")
        print(f"  • Custody: {custody_events}")
        # Find missing events on each side
        missing_in_custody = nbim_events - custody_events
        missing_in_nbim = custody_events - nbim_events
        if missing_in_custody:
            print(f"  {Colors.RED}⚠ Missing in Custody: {missing_in_custody}{Colors.ENDC}")
            for event in missing_in_custody:
                # Create a break for missing custodian record
                self.breaks.append(ReconciliationBreak(
                    event_key=str(event),
                    break_type=BreakType.MISSING_RECORD,
                    nbim_value="Present in NBIM",
                    custody_value="MISSING",
                    difference=None,
                    severity="HIGH",
                    suggested_action="Follow up with custodian, event not received",
                    confidence=0.99
                ))
        if missing_in_nbim:
            print(f"  {Colors.RED}⚠ Missing in NBIM: {missing_in_nbim}{Colors.ENDC}")
            for event in missing_in_nbim:
                self.breaks.append(ReconciliationBreak(
                    event_key=str(event),
                    break_type=BreakType.MISSING_RECORD,
                    nbim_value="MISSING",
                    custody_value="Present in Custody",
                    difference=None,
                    severity="HIGH",
                    suggested_action="Investigate why NBIM lacks this event",
                    confidence=0.99
                ))
        # Analyze each event present in both
        common_events = nbim_events & custody_events
        for event_key in common_events:
            self._analyze_single_event(event_key)
    
    def _analyze_single_event(self, event_key):
        """Analyze and compare records for a single dividend event (across accounts)"""
        nbim_event = self.nbim_data[self.nbim_data['COAC_EVENT_KEY'] == event_key]
        custody_event = self.custody_data[self.custody_data['COAC_EVENT_KEY'] == event_key]
        print(f"\n{Colors.BOLD}Event {event_key}: {nbim_event.iloc[0]['INSTRUMENT_DESCRIPTION']}{Colors.ENDC}")
        # Group by bank account (NBIM uses BANK_ACCOUNT, Custody uses BANK_ACCOUNTS)
        nbim_by_account = nbim_event.groupby('BANK_ACCOUNT')
        custody_by_account = custody_event.groupby('BANK_ACCOUNTS')
        # Compare each NBIM account entry to matching custody account entry
        for account in nbim_event['BANK_ACCOUNT'].unique():
            custody_match = custody_event[custody_event['BANK_ACCOUNTS'].astype(str) == str(account)]
            if not custody_match.empty:
                # We assume one record per account per event in both datasets
                nbim_rec = nbim_event[nbim_event['BANK_ACCOUNT'] == account].iloc[0]
                custody_rec = custody_match.iloc[0]
                self._compare_records(nbim_rec, custody_rec, event_key)
            else:
                # NBIM has an entry for this account, but Custody does not
                print(f"  {Colors.RED}⚠ No custody record for NBIM account {account}{Colors.ENDC}")
                self.breaks.append(ReconciliationBreak(
                    event_key=str(event_key),
                    break_type=BreakType.MISSING_RECORD,
                    nbim_value=f"Account {account} present",
                    custody_value="Account missing",
                    difference=None,
                    severity="HIGH",
                    suggested_action="Custodian record missing for NBIM account",
                    confidence=0.95
                ))
        # Also check if custody has an account entry NBIM lacks
        for account in custody_event['BANK_ACCOUNTS'].unique():
            nbim_match = nbim_event[nbim_event['BANK_ACCOUNT'].astype(str) == str(account)]
            if nbim_match.empty:
                print(f"  {Colors.RED}⚠ No NBIM record for Custody account {account}{Colors.ENDC}")
                self.breaks.append(ReconciliationBreak(
                    event_key=str(event_key),
                    break_type=BreakType.MISSING_RECORD,
                    nbim_value="Account missing",
                    custody_value=f"Account {account} present",
                    difference=None,
                    severity="HIGH",
                    suggested_action="NBIM record missing for this custody account",
                    confidence=0.95
                ))
    

    def _compare_records(self, nbim_rec, custody_rec, event_key):
        """Compare NBIM and Custody records for a single account, appending any breaks found."""
        breaks_found = []
        # 1. Check gross amounts (quotation currency)
        ga_nbim = _num(nbim_rec.get('GROSS_AMOUNT_QUOTATION'))
        ga_cust = _num(custody_rec.get('GROSS_AMOUNT'))
        diff = _abs_diff(ga_nbim, ga_cust)
        if diff is not None and diff > EPS_AMOUNT:
            breaks_found.append(ReconciliationBreak(
            event_key=str(event_key),
            break_type=BreakType.AMOUNT_MISMATCH,
            nbim_value=ga_nbim,
            custody_value=ga_cust,
            difference=diff,
            severity="HIGH",
            suggested_action="Review calculation methodology and dividend rate",
            confidence=0.95
    ))

            
        # 2. Check withholding tax rates (compare as fraction 0..1)
        if ('WTHTAX_RATE' in nbim_rec.index or 'TAX_RATE' in nbim_rec.index) and ('TAX_RATE' in custody_rec.index):
            # NBIM kan ha WTHTAX_RATE eller TAX_RATE – prøv begge, prioriter WTHTAX_RATE
            nbim_rate_raw = nbim_rec.get('WTHTAX_RATE')
            if pd.isna(nbim_rate_raw):
                nbim_rate_raw = nbim_rec.get('TAX_RATE')
            nbim_tax_rate = _to_fraction_rate(nbim_rate_raw)
            custody_tax_rate = _to_fraction_rate(custody_rec.get('TAX_RATE'))

            rate_diff = _abs_diff(nbim_tax_rate, custody_tax_rate)
            if rate_diff is not None and rate_diff > (EPS_RATE_BPS / 10000.0):
                breaks_found.append(ReconciliationBreak(
            event_key=str(event_key),
            break_type=BreakType.TAX_RATE_DIFF,
            nbim_value=nbim_tax_rate,
            custody_value=custody_tax_rate,
            difference=rate_diff,  # i fraksjon
            severity="MEDIUM",
            suggested_action="Verify treaty withholding rate and update configuration if needed",
            confidence=0.90
        ))

        # 3. Check quantities (NOMINAL_BASIS)
        nbim_qty = _num(nbim_rec.get('NOMINAL_BASIS'))
        cust_qty = _num(custody_rec.get('NOMINAL_BASIS'))
        qdiff = _abs_diff(nbim_qty, cust_qty)
        if qdiff is not None and qdiff != 0:
            lending_pct = _to_fraction_rate(custody_rec.get('LENDING_PERCENTAGE'))
            loan_qty = _num(custody_rec.get('LOAN_QUANTITY'))
            holding_qty = _num(custody_rec.get('HOLDING_QUANTITY'))

            if (not pd.isna(lending_pct)) and (not pd.isna(loan_qty)) and (not pd.isna(holding_qty)):
                if _abs_diff(nbim_qty, holding_qty) == 0:
                    # Ulikhet skyldes utlån – informer
                    breaks_found.append(ReconciliationBreak(
                        event_key=str(event_key),
                        break_type=BreakType.LENDING_IMPACT,
                        nbim_value=nbim_qty,
                        custody_value=cust_qty,
                        difference=qdiff,
                        severity="LOW",
                        suggested_action=(
                            f"Securities lending impact: Custody shows loan of {loan_qty} "
                            f"shares ({round(lending_pct*100, 2)}%). Adjust positions for lending."
                        ),
                        confidence=0.85
                    ))
                else:
                    breaks_found.append(ReconciliationBreak(
                        event_key=str(event_key),
                        break_type=BreakType.QUANTITY_MISMATCH,
                        nbim_value=nbim_qty,
                        custody_value=cust_qty,
                        difference=qdiff,
                        severity="HIGH",
                        suggested_action="Reconcile position quantities with custody records",
                        confidence=0.92
                    ))
            else:
                breaks_found.append(ReconciliationBreak(
                    event_key=str(event_key),
                    break_type=BreakType.QUANTITY_MISMATCH,
                    nbim_value=nbim_qty,
                    custody_value=cust_qty,
                    difference=qdiff,
                    severity="HIGH",
                    suggested_action="Reconcile position quantities with custody records",
                    confidence=0.92
                ))

                    
        # 4. Check payment dates
        nbim_date = pd.to_datetime(nbim_rec.get('PAYMENT_DATE'))
        custody_date = pd.to_datetime(custody_rec.get('EVENT_PAYMENT_DATE') or custody_rec.get('PAY_DATE'))
        if pd.notna(nbim_date) and pd.notna(custody_date):
            if nbim_date.date() != custody_date.date():
                breaks_found.append(ReconciliationBreak(
                    event_key=str(event_key),
                    break_type=BreakType.DATE_MISMATCH,
                    nbim_value=nbim_date.strftime('%Y-%m-%d'),
                    custody_value=custody_date.strftime('%Y-%m-%d'),
                    difference="Date difference",
                    severity="MEDIUM",
                    suggested_action="Verify payment date with corporate actions team",
                    confidence=0.88
                ))
        # Append any breaks found for this record
        self.breaks.extend(breaks_found)
        if not breaks_found:
            # No discrepancies for this account record
            self.matched_records.append(f"{event_key}-Acct{nbim_rec['BANK_ACCOUNT']}")
            print(f"  {Colors.GREEN}✅ Perfect match for account {nbim_rec['BANK_ACCOUNT']}{Colors.ENDC}")
        else:
            print(f"  {Colors.YELLOW}⚠ Found {len(breaks_found)} break(s) for account {nbim_rec['BANK_ACCOUNT']}{Colors.ENDC}")
    
    def generate_report(self):
        """Output a summary report of reconciliation results to console"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}📝 RECONCILIATION REPORT{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        if not self.breaks:
            print(f"\n{Colors.GREEN}✅ No reconciliation breaks found!{Colors.ENDC}")
            return
        # Group breaks by type for summary
        breaks_by_type: Dict[BreakType, List[ReconciliationBreak]] = {}
        for brk in self.breaks:
            breaks_by_type.setdefault(brk.break_type, []).append(brk)
        # Print each break type group
        for break_type, breaks_list in breaks_by_type.items():
            severity_color = Colors.RED if any(b.severity == "HIGH" for b in breaks_list) else Colors.YELLOW
            print(f"\n{severity_color}🔸 {break_type.value} ({len(breaks_list)} instances){Colors.ENDC}")
            for brk in breaks_list:
                print(f"  Event {brk.event_key}:")
                print(f"    NBIM: {brk.nbim_value}")
                print(f"    Custody: {brk.custody_value}")
                print(f"    Difference: {brk.difference}")
                print(f"    {Colors.CYAN}→ Action: {brk.suggested_action}{Colors.ENDC}")
                print(f"    Confidence: {brk.confidence:.0%}")
        # Summary statistics
        total_breaks = len(self.breaks)
        high_severity = sum(1 for b in self.breaks if b.severity == "HIGH")
        medium_severity = sum(1 for b in self.breaks if b.severity == "MEDIUM")
        low_severity = sum(1 for b in self.breaks if b.severity == "LOW")
        print(f"\n{Colors.BOLD}📊 Summary Statistics:{Colors.ENDC}")
        print(f"  Total breaks: {total_breaks}")
        print(f"  {Colors.RED}High severity: {high_severity}{Colors.ENDC}")
        print(f"  {Colors.YELLOW}Medium severity: {medium_severity}{Colors.ENDC}")
        print(f"  {Colors.GREEN}Low severity: {low_severity}{Colors.ENDC}")
    
    def export_for_llm(self):
        """Export breaks data as JSON for LLM input"""
        if not self.breaks:
            return None
        export_data = []
        for brk in self.breaks:
            export_data.append({
                'event_key': brk.event_key,
                'break_type': brk.break_type.value,
                'nbim_value': str(brk.nbim_value),
                'custody_value': str(brk.custody_value),
                'difference': str(brk.difference),
                'severity': brk.severity,
                'suggested_action': brk.suggested_action,
                'confidence': brk.confidence
            })
        return json.dumps(export_data, indent=2, default=str)
    


def main():
    """Main execution flow"""
    # Initialize system and load data
    system = DividendReconciliationSystem()
    system.load_data('NBIM_Dividend_Bookings.csv', 'CUSTODY_Dividend_Bookings.csv')
    # Analyze events for discrepancies
    system.analyze_events()
    # Generate summary report
    system.generate_report()
    # Export breaks for LLM agent analysis
    llm_data = system.export_for_llm()
    if llm_data:
        with open('breaks_for_llm.json', 'w') as f:
            f.write(llm_data)
        print(f"\n{Colors.GREEN}✓ Exported breaks data for LLM analysis (breaks_for_llm.json){Colors.ENDC}")
    return system

if __name__ == "__main__":
    system = main()
