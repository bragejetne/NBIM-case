import pandas as pd

nbim_df = pd.read_csv("NBIM_Dividend_Bookings.csv", delimiter=";")
custody_df = pd.read_csv("CUSTODY_Dividend_Bookings.csv", delimiter=";")

df = nbim_df.merge(custody_df,how="inner", left_on="BANK_ACCOUNT", right_on="BANK_ACCOUNTS", suffixes=("_NBIM", "_CUSTODY"))

#NBIM dicts
col = 'EXDATE'
nbim_exdate = {col: df[col].tolist()}

col = 'PAYMENT_DATE'
nbim_payment_date = {col: df[col].tolist()}

col = 'GROSS_AMOUNT_QUOTATION'
nbim_gaq = {col: df[col].tolist()}

col = 'NET_AMOUNT_QUOTATION'
nbim_net = {col: df[col].tolist()}

col = 'WTHTAX_COST_QUOTATION'
nbim_tax_cost = {col: df[col].tolist()}

col = 'WTHTAX_RATE'
nbim_tax_rate = {col: df[col].tolist()}

col = 'ORGANISATION_NAME'
nbim_org = {col: df[col].tolist()}

col = 'QUOTATION_CURRENCY'
nbim_qc = {col: df[col].tolist()}

col = 'GROSS_AMOUNT_QUOTATION'
nbim_gaq = {col: df[col].tolist()}

col = 'NET_AMOUNT_SETTLEMENT'
nbim_nas = {col: df[col].tolist()}

col = 'NOMINAL_BASIS_NBIM'
nbim_nb = {col: df[col].tolist()}

col = 'NET_AMOUNT_SC'
nbim_nas = {col: df[col].tolist()}

col = 'DIVIDENDS_PER_SHARE'
nbim_dps = {col: df[col].tolist()}

col = 'TOTAL_TAX_RATE'
nbim_ttr = {col: df[col].tolist()}

col = 'LOCALTAX_COST_QUOTATION'
nbim_ltc = {col: df[col].tolist()}

# Custody dicts
col = 'EVENT_EX_DATE'
custody_exdate = {col: df[col].tolist()}

col = 'EVENT_PAYMENT_DATE'
custody_payment_date = {col: df[col].tolist()}

col = 'GROSS_AMOUNT'
custody_gaq = {col: df[col].tolist()}

col = 'NET_AMOUNT_QC'
custody_net = {col: df[col].tolist()}

col = 'TAX'
custody_tax = {col: df[col].tolist()}

col = 'TAX_RATE'
custody_tax_rate = {col: df[col].tolist()}

col = 'GROSS_AMOUNT'
custody_gaq = {col: df[col].tolist()}

col = 'DIV_RATE'
custody_dps = {col: df[col].tolist()}

col = 'NOMINAL_BASIS_CUSTODY'
custody_nb = {col: df[col].tolist()}

col = "HOLDING_QUANTITY"
custody_hq = {col: df[col].tolist()}

def check_gaq_errors():
    #Define lists for errors
    wrong_calulations_gaq = {}
    nbim_vals = nbim_gaq['GROSS_AMOUNT_QUOTATION']
    custody_vals = custody_gaq['GROSS_AMOUNT']

    #Check if any GAQ are different
    unequal_row = []
    for i, (n, c) in enumerate(zip(nbim_vals, custody_vals), start=1):
        tolerance = n * 0.01  
        if abs(n - c) <= tolerance:
            continue
        else:
            unequal_row.append(i)

    if unequal_row:
        for i in unequal_row:
            
            statistics_dict = {
                'implied_shares_nbim': nbim_gaq['GROSS_AMOUNT_QUOTATION'][i-1] / nbim_dps['DIVIDENDS_PER_SHARE'][i-1] if nbim_dps['DIVIDENDS_PER_SHARE'][i-1] != 0 else 0,
                'implied_shares_custody': custody_gaq['GROSS_AMOUNT'][i-1] / custody_dps['DIV_RATE'][i-1] if custody_dps['DIV_RATE'][i-1] != 0 else 0,
                'actual_shares_custody': custody_nb['NOMINAL_BASIS_CUSTODY'][i-1],
                'actual_shares_nbim': nbim_nb['NOMINAL_BASIS_NBIM'][i-1],
                'holding_quantity_custody': custody_hq['HOLDING_QUANTITY'][i-1],
                'event_date_nbim': nbim_exdate['EXDATE'][i-1]
}

            if nbim_dps['DIVIDENDS_PER_SHARE'][i-1] * nbim_nb['NOMINAL_BASIS_NBIM'][i-1] != nbim_gaq['GROSS_AMOUNT_QUOTATION'][i-1]:
                wrong_calulations_gaq[f'nbim_{i}'] = nbim_dps['DIVIDENDS_PER_SHARE'][i-1], nbim_nb['NOMINAL_BASIS_NBIM'][i-1], nbim_gaq['GROSS_AMOUNT_QUOTATION'][i-1]
            if custody_dps['DIV_RATE'][i-1] * custody_nb['NOMINAL_BASIS_CUSTODY'][i-1] != custody_gaq['GROSS_AMOUNT'][i-1]:
                wrong_calulations_gaq[f'custody_{i}'] = (f'DPS rate: {custody_dps['DIV_RATE'][i-1]}'), (f'Nominal basis: {custody_nb['NOMINAL_BASIS_CUSTODY'][i-1]}'), (f'{custody_gaq['GROSS_AMOUNT'][i-1]}')

    return wrong_calulations_gaq, statistics_dict

def check_tax_difference():
    
    nbim_vals = nbim_ttr['TOTAL_TAX_RATE']
    custody_vals = custody_tax_rate['TAX_RATE']
    unequal_tax_dict = {}
    tolerance = 0.01

    for i, (n, c) in enumerate(zip(nbim_vals, custody_vals), start=1):
        
        if abs(n - c) < tolerance:
            continue
        else:
            unequal_tax_dict[f'nbim:_{i}'] = [f'tax rate {n}, row {i}']
            unequal_tax_dict[f'custody_{i}'] = [f'tax rate {c}, row {i}']

        related_dict = {
            'implied_tax_amount_nbim': nbim_gaq['GROSS_AMOUNT_QUOTATION'][i-1] * nbim_tax_rate['WTHTAX_RATE'][i-1] / 100 + nbim_ltc['LOCALTAX_COST_QUOTATION'][i-1],
            'implied_tax_amount_custody': custody_gaq['GROSS_AMOUNT'][i-1] * custody_tax_rate['TAX_RATE'][i-1] / 100,
            'organisation_name': nbim_org['ORGANISATION_NAME'][i-1],
            'quotation_currency_nbim': nbim_qc['QUOTATION_CURRENCY'][i-1],
            'nbim_gross_amount_quotation': nbim_gaq['GROSS_AMOUNT_QUOTATION'][i-1],
            'custody_gross_amount': custody_gaq['GROSS_AMOUNT'][i-1],
            'localtax_cost_quotation_nbim': nbim_ltc['LOCALTAX_COST_QUOTATION'][i-1],
            'wthtax_cost_quotation_nbim': nbim_tax_cost['WTHTAX_COST_QUOTATION'][i-1],
            'wthtax_rate_nbim': nbim_tax_rate['WTHTAX_RATE'][i-1],
            'net_amount_qoutation_nbim': nbim_net['NET_AMOUNT_QUOTATION'][i-1],
            'net_amount_qoutation_custody': custody_net['NET_AMOUNT_QC'][i-1],
            'event_ex_date_nbim': nbim_exdate['EXDATE'][i-1]
            


            



        }
    return unequal_tax_dict, related_dict





