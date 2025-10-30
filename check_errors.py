import pandas as pd

nbim_df = pd.read_csv("NBIM_Dividend_Bookings.csv", delimiter=";")
custody_df = pd.read_csv("CUSTODY_Dividend_Bookings.csv", delimiter=";")

df = nbim_df.merge(custody_df,how="inner", left_on="BANK_ACCOUNT", right_on="BANK_ACCOUNTS", suffixes=("_NBIM", "_CUSTODY"))

#NBIM dicts
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

# Custody dicts
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
    
        if n == c:
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
                'holding_quantity_custody': custody_hq['HOLDING_QUANTITY'][i-1]
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

    for i, (n, c) in enumerate(zip(nbim_vals, custody_vals), start=1):
        if n == c:
            continue
        else:
            unequal_tax_dict[f'nbim:_{i}'] = [f'tax rate {n}, row {i}, org {nbim_org['ORGANISATION_NAME'][i-1]}']
            unequal_tax_dict[f'custody_{i}'] = [f'tax rate {c}, row {i}']
    return unequal_tax_dict

def check_naq_errors():
    wrong_tax_calculation = {}
    wrong_tax_applied = {}
    nbim_vals = nbim_net['NET_AMOUNT_QUOTATION']
    custody_vals = custody_net['NET_AMOUNT_QC']
    unequal_row = []

    for i, (n, c) in enumerate(zip(nbim_vals, custody_vals), start=1):
        if n == c:
            continue
        else:
            unequal_row.append(i)

    if unequal_row:
        tax_standardizer = 0.01
        for i in unequal_row:

            if nbim_gaq['GROSS_AMOUNT_QUOTATION'][i-1] * nbim_ttr['TOTAL_TAX_RATE'][i-1] * tax_standardizer != nbim_tax_cost['WTHTAX_COST_QUOTATION'][i-1]:
                    wrong_tax_calculation[f'nbim_{i}'] = nbim_gaq['GROSS_AMOUNT_QUOTATION'][i-1], nbim_tax_rate['WTHTAX_RATE'][i-1], nbim_tax_cost['WTHTAX_COST_QUOTATION'][i-1]


            if custody_gaq['GROSS_AMOUNT'][i-1] * custody_tax_rate['TAX_RATE'][i-1] * tax_standardizer != custody_tax['TAX'][i-1]:
                    wrong_tax_calculation[f'custody_{i}'] = custody_gaq['GROSS_AMOUNT'][i-1], custody_tax_rate['TAX_RATE'][i-1], custody_tax['TAX'][i-1]
        
        for i in unequal_row:
            
            if nbim_gaq['GROSS_AMOUNT_QUOTATION'][i-1] - nbim_tax_cost['WTHTAX_COST_QUOTATION'][i-1] != nbim_net['NET_AMOUNT_QUOTATION'][i-1]:
                    wrong_tax_applied[f'nbim_{i}'] = (f' Gross amount Quotation: {nbim_gaq['GROSS_AMOUNT_QUOTATION'][i-1]}'), (f'Tax cost quotation: {nbim_tax_cost['WTHTAX_COST_QUOTATION'][i-1]}'), (f' Net amount quotation: {nbim_net['NET_AMOUNT_QUOTATION'][i-1]}')


            if custody_gaq['GROSS_AMOUNT'][i-1] - custody_tax['TAX'][i-1] != custody_net['NET_AMOUNT_QC'][i-1]:
                    wrong_tax_applied[f'custody_{i}'] = custody_gaq['GROSS_AMOUNT'][i-1], custody_tax['TAX'][i-1], custody_net['NET_AMOUNT_QC'][i-1]

    return wrong_tax_applied, wrong_tax_calculation
    

    





