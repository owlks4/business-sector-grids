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

    company_name_column_index = rows[0].index("company_name")
    sic_code_column_index = rows[0].index("nature_of_business")
    sector_prefix_column_index = rows[0].index("sectorCodes")

    do_not_preserve_columns_of_this_index_or_greater = 99999999

    for i in range(len(rows[0])):
        if rows[0][i].strip() == "":
            if i < do_not_preserve_columns_of_this_index_or_greater:
                do_not_preserve_columns_of_this_index_or_greater = i

    for row in rows:
        while len(row) > do_not_preserve_columns_of_this_index_or_greater: #this is here just to kill off any invisible extra columns at the end of the data (that would otherwise potentially desync the new columns we're about to add from their headers)
            row.pop(-1)

    if "specific_industry" in rows[0] or "broad_industry" in rows[0]:
        print ("Step 3 will now complete early, because the columns we were going to add using this program - specific_industry and broad_industry - were already there.")
        return;

    rows[0].append("specific_industry")
    rows[0].append("broad_industry")

    for i in range(len(rows)):
        if i == 0: #don't process header
            continue
        row = rows[i]

        if "\"" in row[company_name_column_index]:
            print("WARNING: The company name in this row had a double quotation character in it. If you receive an error immediately after seeing this message, this is probably why - as it runs a high risk of throwing the columns of this csv row out of sync.")
            print("The company name was: "+row[company_name_column_index])

        #print("Now processing "+row[company_name_column_index])

        row.append(translate_sic_code(row[sic_code_column_index]))
        row.append(translate_sector_prefixes_of_sic_codes(row[sic_code_column_index])) # I've made this derive the sectors anew from the sic codes, despite there probably being a sector column in the source - this is because I've realised we need an extra digit of the SIC to adequately categorise the retail data - otherwise it generates clusters that are cumbersome in size and too vague to be useful

    with open(path, newline='', encoding="utf-8", mode="w") as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerows(rows)
        print ("\nSuccessfully appended the new columns -- 'specific_industry' and 'broad_industry' -- to the input CSV file, which has been modified in-place.")

process()