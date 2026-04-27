import os

import click
import logging
from scrapy import Selector
import requests
import pandas as pd
from rich.console import Console
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from gmft.auto import AutoTableDetector, AutoTableFormatter, AutoFormatConfig  # type: ignore[attr-defined]
from gmft_pymupdf import PyMuPDFDocument

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('[githubpipeline.py]')
console = Console()


def create_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(['GET']),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session


session = create_session()


def fetch_text(url: str) -> str:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def fetch_bytes(url: str) -> bytes:
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response.content


def ensure_output_dirs():
    os.makedirs('output/schedule', exist_ok=True)
    os.makedirs('output/pdf', exist_ok=True)
    os.makedirs('output/csv', exist_ok=True)
    os.makedirs('output/tables', exist_ok=True)


@click.group()
def cli():
    pass


@cli.command()
def schedule():
    """Extracts the schedule of grade threshold tables from the Cambridge International website and saves it as a CSV file."""
    ensure_output_dirs()
    logging.info("Starting schedule extraction...")
    output = fetch_text(
        "https://www.cambridgeinternational.org/programmes-and-qualifications/cambridge-advanced/cambridge-international-as-and-a-levels/grade-threshold-tables/"
    )

    links = [
        'https://www.cambridgeinternational.org' + link
        for link in Selector(text=output).css('div.feature > div > ul > li > a::attr(href)').getall()
    ]
    df = pd.DataFrame(links, columns=["links"])
    df['month'] = df['links'].str.extract(r'grade-threshold-tables/([a-zA-Z]+)')
    df['year'] = df['links'].str.extract(r'(20\d{2})')

    list1 = []
    for row in df.itertuples():
        pdflinks = [
            'https://www.cambridgeinternational.org' + link
            for link in Selector(text=fetch_text(str(row.links)))
            .css('div.feature > div > p > a::attr(href)')
            .getall()
        ]
        df1 = pd.DataFrame(pdflinks, columns=["pdf_links"])
        df1['subject_code'] = df1['pdf_links'].str.extract(r'-(\d{4})-')
        df1['month'] = row.month
        df1['month_id'] = df1['month'].map({'november': 'on', 'june': 'mj', 'march': 'fm'})
        df1['year'] = row.year
        df1['id'] = df1['subject_code'] + '_' + df1['month_id'] + '_' + df1['year']
        list1.append(df1)

    df2 = pd.concat(list1)
    df2.set_index('id', inplace=True)
    df2.to_csv('./output/schedule/schedule.csv', index=True)
    logging.info("Schedule extraction completed. Output saved to './output/schedule/schedule.csv'")


@cli.command()
def downtag():
    ensure_output_dirs()
    schedule_df = pd.read_csv('./output/schedule/schedule.csv', index_col='id', dtype={'subject_code': str})
    rows = list(schedule_df.reset_index().itertuples())
    total = len(rows)
    logger.info(f'Starting PDF download step for {total} files.')
    downloaded = 0
    skipped = 0
    for index, row in enumerate(rows, start=1):
        logger.info(f'[{index}/{total}] Processing {row.id}')
        if not os.path.exists(f'./output/pdf/{row.id}.pdf'):
            with open(f'./output/pdf/{row.id}.pdf', 'wb') as f:
                f.write(fetch_bytes(str(row.pdf_links)))
            downloaded += 1
        else:
            logger.info(f"{row.id} already exists, skipping download.")
            skipped += 1
    logger.info(f'PDF download step complete: {downloaded} downloaded, {skipped} skipped.')


@cli.command()
def extract():
    ensure_output_dirs()
    pdfdir = os.listdir('output/pdf')
    pdfpaths = [f'output/pdf/{pdf}' for pdf in pdfdir if pdf.lower().endswith('.pdf')]

    if not pdfpaths:
        raise click.ClickException('No PDF files found in output/pdf.')

    detector = AutoTableDetector()
    config = AutoFormatConfig(verbosity=3, semantic_spanning_cells=True)
    formatter = AutoTableFormatter(config=config)

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


@cli.command()
def compile():
    ensure_output_dirs()
    csvdir = os.listdir('output/csv')
    codes = [code[:4] for code in csvdir if code.lower().endswith('.csv') and len(code) >= 4 and code[:4].isdigit()]
    subj = sorted(set(codes))
    for code in subj:
        subj_csv = []
        for csv in csvdir:
            if csv.startswith(code) and csv.lower().endswith('.csv'):
                df = pd.read_csv(f'output/csv/{csv}')
                df.columns = df.columns.str.lower()
                df['year'] = csv[8:12]
                df['month'] = csv[5:7]
                subj_csv.append(df)
        if subj_csv:
            subj_df = pd.concat(subj_csv, ignore_index=True)
            subj_df.to_csv(f'output/tables/{code}_all.csv', index=False)


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
