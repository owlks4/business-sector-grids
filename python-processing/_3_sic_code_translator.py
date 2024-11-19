import time
import csv
from _util_SIC_lookup import translate_sic_code, translate_sector_prefixes_of_sic_codes
import os

def process():

    path = 'files/2_COMPARE/output.csv'

    if not os.path.isfile(path):
        print("Will not carry out step 3 because the required file was not there! Did step 2 complete correctly?")
        return

    print("Starting step 3... preparing to amend step 2's output with text-based SIC code labels...\n")

    with open(path, newline='', encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        rows = []
        for row in reader:
            rows.append(row)

    company_name_column_index = rows[0].index("CompanyName")
    sic_code_column_indices = [rows[0].index("SICCode.SicText_1"),rows[0].index("SICCode.SicText_2"),rows[0].index("SICCode.SicText_3"),rows[0].index("SICCode.SicText_4")]

    do_not_preserve_columns_of_this_index_or_greater = 99999999

    for i in range(len(rows[0])):
        if rows[0][i].strip() == "":
            if i < do_not_preserve_columns_of_this_index_or_greater:
                do_not_preserve_columns_of_this_index_or_greater = i

    for row in rows:
        while len(row) > do_not_preserve_columns_of_this_index_or_greater: #this is here just to kill off any invisible extra columns at the end of the data (that would otherwise potentially desync the new columns we're about to add from their headers)
            row.pop(-1)

    if "industry" in rows[0] or "sector" in rows[0]:
        print ("Step 3 will now complete early, because the columns we were going to add using this program - industry and sector - were already there.")
        return;

    rows[0].append("sector")
    rows[0].append("industry")

    for i in range(len(rows)):
        if i == 0: #don't process header
            continue
        row = rows[i]

        if "\"" in row[company_name_column_index]:
            print("WARNING: The company name in this row had a double quotation character in it. If you receive an error immediately after seeing this message, this is probably why - as it runs a high risk of throwing the columns of this csv row out of sync.")
            print("The company name was: "+row[company_name_column_index])

        #print("Now processing "+row[company_name_column_index])

        sector_codes = map(lambda x : row[x].split(" - ")[0].zfill(5)[:3] if len(row[x]) > 0 else None, sic_code_column_indices)
        sector_codes = list(filter(None, sector_codes))
        row.append(";".join(sector_codes))

        industry_codes = map(lambda x : row[x].split(" - ")[0].zfill(5) if len(row[x]) > 0 else None, sic_code_column_indices)
        industry_codes = list(filter(None, industry_codes))
        row.append(";".join(industry_codes))

    with open(path, newline='', encoding="utf-8", mode="w") as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerows(rows)
        print ("\nSuccessfully appended the new columns -- 'industry' and 'sector' -- to the input CSV file, which has been modified in-place.")

process()