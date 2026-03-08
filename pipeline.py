import os

import click
import logging
from scrapy import Selector
import requests
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('[pipeline.py]')

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

def compile():
    pass

if __name__ == "__main__":
    cli()