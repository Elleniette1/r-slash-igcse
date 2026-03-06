import click
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.group()
def cli():
    pass

@cli.command()
def get_list():
    """Creates a csv file containing the list of all the thresholds with subject code, download link and year included."""
    pass

@cli.command()
def pdf_download():
    """Download the thresholds."""
    pass

@cli.command()
def pdf_process():
    """Process PDF files."""
    pass