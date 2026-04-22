import os

import click
import logging
from scrapy import Selector
import requests
import pandas as pd
from rich.console import Console

from gmft.auto import CroppedTable, AutoTableDetector, AutoTableFormatter,  AutoFormatConfig
from gmft_pymupdf import PyMuPDFDocument

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('[pipeline.py]')
console = Console()

@click.group()
def cli():
    pass

@cli.command()
def schedule():
    """Extracts the schedule of grade threshold tables from the Cambridge International website and saves it as a CSV file."""
    logging.info("Starting schedule extraction...")
    output = requests.get("https://www.cambridgeinternational.org/programmes-and-qualifications/cambridge-advanced/cambridge-international-as-and-a-levels/grade-threshold-tables/").content

    links = ['https://www.cambridgeinternational.org' + link for link in Selector(text=output).css('div.feature > div > ul > li > a::attr(href)').getall()]
    df = pd.DataFrame(links, columns=["links"])
    df['month'] = df['links'].str.extract(r'grade-threshold-tables/([a-zA-Z]+)')
    df['year'] = df['links'].str.extract(r'(20\d{2})')
    
    list1 = []
    for row in df.itertuples():
        pdflinks = ['https://www.cambridgeinternational.org' + link for link in Selector(text=requests.get(row.links).content).css('div.feature > div > p > a::attr(href)').getall()]
        df1 = pd.DataFrame(pdflinks, columns=["pdf_links"])
        df1['subject_code'] = df1['pdf_links'].str.extract(r'-(\d{4})-')
        df1['month'] = row.month
        df1['month_id'] = df1['month'].map({'november': 'on', 'june': 'mj', 'march':'fm'})
        df1['year'] = row.year
        df1['id'] = df1['subject_code'] + '_' + df1['month_id'] + '_' + df1['year']
        list1.append(df1)
    df2 = pd.concat(list1)
    df2.set_index('id', inplace=True)
    df2.to_csv('./output/schedule/schedule.csv', index=True)
    logging.info("Schedule extraction completed. Output saved to './output/schedule/schedule.csv'")

@cli.command()
def downtag():
    schedule = pd.read_csv('./output/schedule/schedule.csv', index_col='id', dtype={'subject_code': str})
    for row in schedule.reset_index().itertuples():
        if not os.path.exists(f'./output/pdf/{row.id}.pdf'):
            with open(f'./output/pdf/{row.id}.pdf', 'wb') as f:
                f.write(requests.get(row.pdf_links).content)
        else:
            logger.info(f"{row.id} already exists, skipping download.")

@cli.command()
def extract():
    pdfdir = os.listdir('output/pdf')
    pdfpaths = [f'output/pdf/{pdf}' for pdf in pdfdir]
    detector = AutoTableDetector()
    config = AutoFormatConfig(verbosity=3, semantic_spanning_cells=True)
    formatter = AutoTableFormatter(config=config)

    doc = PyMuPDFDocument(pdfpaths[0])

    with console.status("Processing PDFs..."):
        for pdfpath in pdfpaths:
            csv_path = f'output/csv/{os.path.basename(pdfpath).replace(".pdf", ".csv")}'

            if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
                doc = PyMuPDFDocument(pdfpath)
                tablefragments = []
                for page in doc:
                    tablefragments += detector.extract(page)
                rows = []
                for tf in tablefragments:
                    df = formatter.format(tf).df()
                    sig = tuple(str(c).strip().lower() for c in df.columns)
                    rows.append({"sig": sig, "df": df})

                index = pd.DataFrame(rows)
                tables = [
                    pd.concat(group["df"].tolist(), ignore_index=True)
                    for _, group in index.groupby("sig", sort=False)
                ]
                tables = [table for table in tables if len(table.columns) > 1]
                option_tables = [
                    table for table in tables
                    if any(str(col).strip().lower() == "option" for col in table.columns)
                ]
                if option_tables:
                    option_tables[-1].to_csv(csv_path, index=False)
                else:
                    console.log(f"[yellow]No grade tables found in {pdfpath}.[/yellow]")
    pass

@cli.command()
def compile():
    csvdir = os.listdir('output/csv')
    codes = [code[:4] for code in csvdir]
    subj = sorted(set(codes))
    for code in subj:
        subj_csv = []
        for csv in csvdir:
            if csv.startswith(code):
                df = pd.read_csv(f'output/csv/{csv}')
                df.columns = df.columns.str.lower()
                df['year'] = csv[8:12]
                df['month'] = csv[5:7]
                subj_csv.append(df)
        subj_df = pd.concat(subj_csv, ignore_index=True)
        subj_df.to_csv(f'output/table/{code}_all.csv', index=False)

@cli.command()
@click.pass_context
def run_all(ctx):
    """Run all steps in the pipeline."""

    ctx.invoke(schedule)
    ctx.invoke(downtag)
    ctx.invoke(extract)
    ctx.invoke(compile)

if __name__ == "__main__":
    cli()