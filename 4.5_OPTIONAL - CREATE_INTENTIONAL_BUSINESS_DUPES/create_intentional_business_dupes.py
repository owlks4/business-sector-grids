import time
import csv
import copy

def process():
    with open('input.csv', newline='', encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        rows = []
        for row in reader:
            rows.append(row)

    company_name_column_index = rows[0].index("company_name")
    broad_industry_column_index = rows[0].index("broad_industry")

    outputRows = [rows[0]]

    for i in range(len(rows)):
        if i == 0: #don't process header
            continue
        row = rows[i]

        if "\"" in row[company_name_column_index]:
            print("WARNING: The company name in this row had a double quotation character in it. If you receive an error immediately after seeing this message, this is probably why - as it runs a high risk of throwing the columns of this csv row out of sync.")
            print("The company name was: "+row[company_name_column_index])

        print(str(i/len(rows)*100)+"% complete: Now processing "+row[company_name_column_index])

        unique_sectors_for_row = []

        for sector in row[broad_industry_column_index].strip().split(";"):
            sector = sector.strip().upper()
            if not sector in unique_sectors_for_row:
                unique_sectors_for_row.append(sector)

        for j in range(len(unique_sectors_for_row)):
            new_duplicate_row = copy.deepcopy(row)
            new_duplicate_row[broad_industry_column_index] = unique_sectors_for_row[j]
            outputRows.append(new_duplicate_row)

    with open('OUTPUT_(SECTOR-SEPARATED BUSINESSES).csv', newline='', encoding="utf-8", mode="w") as csvfile:
        writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerows(outputRows)
        print ("\nSuccessfully separated businesses with multiple sectors into multiple copies of said business, with one sector each.")

process()