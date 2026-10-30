#!/usr/bin/env python3

import argparse
import logging
import re
import sys
from difflib import SequenceMatcher

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_argparse():
    """
    Sets up the argument parser for the CLI.
    Returns:
        argparse.ArgumentParser: The argument parser object.
    """
    parser = argparse.ArgumentParser(
        description="Analyzes project dependencies for typosquatting risks."
    )
    parser.add_argument(
        "requirements_file",
        nargs="?",  # Make it optional
        default="requirements.txt",
        help="Path to the requirements.txt file (default: requirements.txt)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.8,
        help="Similarity threshold (default: 0.8).  Values between 0 and 1, higher values are stricter.",
    )
    parser.add_argument(
        "--top-packages",
        type=int,
        default=20,
        help="Number of top PyPI packages to compare against. Higher numbers mean better coverage but slower execution. (default: 20)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )
    return parser


def calculate_similarity(a, b):
    """
    Calculates the similarity ratio between two strings.
    Args:
        a (str): The first string.
        b (str): The second string.
    Returns:
        float: The similarity ratio between 0 and 1.
    """
    return SequenceMatcher(None, a, b).ratio()


def get_top_pypi_packages(top_n=20):
    """
    Fetches the names of the most downloaded packages from PyPI.
    This is a placeholder.  In a real implementation, this would
    query a PyPI stats API (which don't currently really exist) or
    scrape the PyPI website (fragile).

    Args:
      top_n (int): Number of top packages to return.
    Returns:
        list: A list of strings representing top packages
    """
    # Placeholder list of popular packages.  In a real implementation,
    # this would dynamically fetch this data.  This ensures the tool
    # is functional and testable without external dependencies or unreliable web scraping.
    popular_packages = [
        "requests",
        "numpy",
        "pandas",
        "django",
        "flask",
        "tensorflow",
        "torch",
        "scikit-learn",
        "matplotlib",
        "beautifulsoup4",
        "pytest",
        "sqlalchemy",
        "celery",
        "scrapy",
        "tornado",
        "aiohttp",
        "gunicorn",
        "psycopg2",
        "redis",
        "boto3",
    ]
    return popular_packages[:top_n] # Ensure we only return 'top_n' packages

def analyze_dependencies(requirements_file, threshold, top_packages):
    """
    Analyzes the dependencies in the requirements file for typosquatting risks.
    Args:
        requirements_file (str): Path to the requirements.txt file.
        threshold (float): Similarity threshold.
    Returns:
        list: A list of tuples containing the dependency and the potential typosquatting target.
    """
    try:
        with open(requirements_file, "r") as f:
            raw_lines = f.readlines()
    except FileNotFoundError:
        logging.error(f"Requirements file not found: {requirements_file}")
        return None
    except Exception as e:
        logging.error(f"Error reading requirements file: {e}")
        return None

    dependencies = []
    for line in raw_lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # A requirement is more than a name: version pins, extras and
        # environment markers all follow it. Splitting only on "==" left
        # "requesrs>=0.1" as the supposed package name, and the similarity
        # test then compared that whole string and found nothing.
        name = re.split(r"[<>=!~;\[\s]", line, maxsplit=1)[0]
        name = re.sub(r"\[.*\]$", "", name).strip()
        if name:
            dependencies.append(name)

    popular_packages = get_top_pypi_packages(top_packages)

    typosquatting_risks = []
    for dependency in dependencies:
        for popular_package in popular_packages:
            # Compare in PEP 503 normalized form so case and separator
            # style (requests vs Requests, scikit-learn vs scikit_learn)
            # do not hide or invent a match.
            dep_norm = re.sub(r"[-_.]+", "-", dependency.lower())
            pop_norm = re.sub(r"[-_.]+", "-", popular_package.lower())
            if dep_norm == pop_norm:
                # A package is not a typosquat of itself. Without this
                # skip the exact, legitimate dependency scored 1.00 and
                # was the first "risk" the tool reported.
                continue
            similarity = calculate_similarity(dep_norm, pop_norm)
            if similarity >= threshold:
                typosquatting_risks.append((dependency, popular_package, similarity))

    return typosquatting_risks

def main():
    """
    Main function to execute the typosquatting risk analyzer.
    """
    parser = setup_argparse()
    args = parser.parse_args()

    # Configure logging level
    logging.getLogger().setLevel(args.log_level)

    # Input validation
    if not 0 <= args.threshold <= 1:
        logging.error("Threshold must be between 0 and 1.")
        sys.exit(1)

    if args.top_packages <= 0:
        logging.error("Number of top packages must be positive.")
        sys.exit(1)

    logging.info(f"Analyzing dependencies in {args.requirements_file} with threshold {args.threshold} and top {args.top_packages} packages.")

    risks = analyze_dependencies(args.requirements_file, args.threshold, args.top_packages)

    if risks is None:
        # The file could not be read. Reporting "no risks" here would
        # read as a clean scan of a file that was never opened.
        sys.exit(1)

    if risks:
        print("Potential typosquatting risks found:")
        for dependency, target, similarity in risks:
            print(f"  Dependency: {dependency}, Similar to: {target}, Similarity: {similarity:.2f}")
    else:
        print("No potential typosquatting risks found.")


if __name__ == "__main__":
    main()