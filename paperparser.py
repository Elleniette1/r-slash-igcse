from pypdf import PdfReader
import pandas as pd
import re

Test = False

def parse_threshold(paper_path: str):
    reader = PdfReader(paper_path)
    ascheck = ('as-level' in paper_path.lower() 
            or '8681' in paper_path)

    if 'IGCSE' in paper_path and "9-1" not in paper_path:
        IGCSE = 2
    elif "9-1" in paper_path:
        IGCSE = 3
    else:
        IGCSE = 0
    if 'additional-mathematics' in paper_path.lower():
        IGCSE -= 2
    text = ""
    # Get all pages into one big string
    for page in reader.pages:
        text += (page.extract_text())
    text = text.split("\n")


    # Removing empty lines (parser generated them idk)
    text = [i.strip() for i in text 
            if i != "" 
            and i != " " 
            and "Cambridge" not in i
            and "Option" not in i
            and "Maximum" not in i
            and "Combination" not in i
            and "components" not in i
            and "weighting" not in i
            and "mark after" not in i
            and "Grade" not in i
            and "Component" not in i
            and "Learn" not in i
            and "Services" not in i
            and "A Level" not in i
            and "refer" not in i
            and "raw" not in i
            and "mark" not in i
            and "available" not in i
            and "A B C D E" not in i
            and "threshold" not in i
            and "exam" not in i
            and "A2-only" not in i
            and "email" not in i
            and "for" not in i
            and "dis" not in i
            and "AS Level" not in i]
    text = [i for i in text if i != ""]
    if not text[0][0].isalpha() and text[0][0] != "–":
        text = text[1:]
    if text[0][0].isdigit():
        text = text[1:]
        
        
    for i in range(len(text)):
        if len(text[i]) < 20:
            try:
                text[i-1] = text[i-1] + " " + text[i] + " " + text[i+1]
            except:
                pass


    text  = [i for i in text if i not in ["", " "]]
    for i in range(len(text)):
        if text[i][0].isdigit():
            text[i-1] = text[i-1] + " " + text[i]
    text = [item for item in text if re.search(r'[A-Za-z]', item)]



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
    if IGCSE and not "9-1" in paper_path:
        table_header = [
            'option', 
            'max mark', 
            'combination',
            'a*', 'a', 'b', 'c', 'd', 'e', 'f','g']
    elif "9-1" in paper_path:
        table_header = [
            'option', 
            'max mark', 
            'combination',
            '9', '8', '7', '6', '5', '4','3','2','1']
    else:
        table_header = [
            'option', 
            'max mark', 
            'combination',
            'A*', 'A', 'B', 'C', 'D', 'E']
    data = pd.DataFrame(columns=table_header)
    data.columns = data.columns.str.lower()

    text = [i.replace(' / ','/') for i in text if len(i) > 7 and not i[0].isdigit()]

    j = 0
    for i in text:
        if i[0].isdigit() or i[0].isspace():
            text.remove(i)
            continue
        i = i.replace(", ", ",")
        i = i.split(" ")
        i = [k for k in i if k != ""]
        if "(" in str(i[1]) or ")" in str(i[1]):
            i[0] = i[0] + " " + i[1]
            i.pop(1)
        if i[3] in i[2]:
            i.pop(3)
            
        try:
            i[1] = int(i[1])
        except:
            pass   
            
        if ascheck:
            i = i[:3] + [0] + i[3:]
        try:
            if i[8+IGCSE] in i[1]:
                i = i[:8+IGCSE]
        except:
            pass
        untrimmed = True
        while untrimmed:
            if not i[-1].isdigit():
                i = i[:-1]
            else:
                untrimmed = False
        if len(i) < 9+IGCSE:
            i = i[:1] + [0] + i[1:]
        
        if len(i) > 9+IGCSE:
            i = i[:9+IGCSE]
    
        data.loc[j] = i
        j += 1
        
    data["option"] = data["option"].astype(str) + " " + data["combination"].astype(str)
    data.drop(columns=["combination"], inplace=True)
    data.set_index("option", inplace=True)
    data["date"] = date_extractor
    data.replace("–", 0, inplace=True)
    try:
        data.iloc[:, :-2] = data.iloc[:, :-2].astype(int)
    except:
        data.iloc[:, :-2] = data.iloc[:, :-2].astype(int)
    if IGCSE != 3:
        a2_table = data.copy().loc[(data["max mark"] >= 131) | (data["a*"] >= 131), :]
    else:
        a2_table = data.copy().loc[(data["max mark"] >= 131) | (data["9"] >= 131), :]
    as_table = data.copy().loc[data["max mark"]< 131,:]

    return data, 1, a2_table