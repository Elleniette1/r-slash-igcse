from pypdf import PdfReader
import pandas as pd
import re

def parse_threshold(paper_path: str):
    reader = PdfReader("thresholds/IGCSE/741349-additional-mathematics-0606-june-2025-grade-threshold-table.pdf")

    text = ""
    # Get all pages into one big string
    for page in reader.pages:
        text += (page.extract_text())
    text = text.replace("""Learn more! For more information please visit www.cambridgeinternational.org/alevel or contact Customer 
    Services on +44 (0)1223 553554 or email info@cambridgeinternational.org""", "")
    text = text.split("\nThe overall thresholds for the different grades were set as follows.  ") # This line always come before the consolidated table
    text = (text[1]
        .replace("Grade thresholds continued ","")
        .replace("A* A B C D E ", "")
        .replace("A*","\nA*")
        .replace(", ", ",")
        .replace("  ", " "))

    # Removing empty lines (parser generated them idk)
    text = text.split("\n")
    text = [i for i in text 
            if i != "" 
            and i != " " 
            and "Cambridge" not in i
            and "Option" not in i
            and "Maximum" not in i
            and "Combination" not in i
            and "components" not in i
            and "weighting" not in i
            and "mark after" not in i]


    # Finding the Date
    date_extractor = reader.pages[0].extract_text()
    try: 
        date_extractor = re.search(r"November \d{4}", date_extractor).group(0)
    except:
        try:
            date_extractor = re.search(r"June \d{4}", date_extractor).group(0)
        except:
            date_extractor = re.search(r"March \d{4}", date_extractor).group(0)

    # Table Headers
    table_header = [
        'option', 
        'max mark', 
        'combination',
        'A*', 'A', 'B', 'C', 'D', 'E']
    data = pd.DataFrame(columns=table_header)
    data.columns = data.columns.str.lower()

    j = 0
    for i in text:
        k = i.split(" ")
        k.remove("")
        print(k)
        data.loc[j] = k
        j += 1

    data.set_index("option", inplace=True)
    data["date"] = date_extractor
    data.replace("–", 0, inplace=True)
    data[['max mark', 'a*', 'a', 'b', 'c', 'd', 'e']] = data[['max mark', 'a*', 'a', 'b', 'c', 'd', 'e']].astype(int)

    a2_table = data.copy().loc[data["max mark"]>= 131,:]
    as_table = data.copy().loc[data["max mark"]< 131,:].replace(0, pd.NA)

    return data, as_table, a2_table