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
        help="Number of entries from the fixed package list in main.py to compare against. The list is fixed in the source and no package index is queried. Higher numbers mean better coverage but slower execution, up to the size of that list; asking for more than the list holds prints a warning and uses the whole list. (default: 20)",
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
    # I use the general string ratio, which rewards shared runs of
    # characters in order. It knows nothing about keyboards, so a
    # swapped letter pair that a human spots at once can score
    # lower than a longer name that merely shares a prefix.
    return SequenceMatcher(None, a, b).ratio()


def get_top_pypi_packages(top_n=20):
    """
    Returns the first top_n names from a fixed list of widely
    downloaded PyPI packages held in this file. No package index
    is queried and nothing is fetched; the list changes only when
    this source file is edited.

    Args:
      top_n (int): Number of top packages to return.
    Returns:
        list: A list of strings representing top packages
    """
    # Fixed list of widely downloaded packages, in rough download
    # order. It is deliberately not fetched at run time, so a run
    # offline compares against exactly the names written here.
    popular_packages = [
        "boto3",
        "urllib3",
        "certifi",
        "idna",
        "requests",
        "charset-normalizer",
        "setuptools",
        "pip",
        "wheel",
        "packaging",
        "six",
        "python-dateutil",
        "pytz",
        "typing-extensions",
        "botocore",
        "s3transfer",
        "jmespath",
        "numpy",
        "pandas",
        "pillow",
        "pyyaml",
        "click",
        "attrs",
        "cryptography",
        "pyparsing",
        "filelock",
        "platformdirs",
        "tqdm",
        "fsspec",
        "colorama",
        "importlib-metadata",
        "zipp",
        "more-itertools",
        "pluggy",
        "iniconfig",
        "pytest",
        "tomli",
        "pygments",
        "rich",
        "markdown-it-py",
        "mdurl",
        "psutil",
        "lxml",
        "beautifulsoup4",
        "soupsieve",
        "django",
        "flask",
        "werkzeug",
        "jinja2",
        "markupsafe",
        "itsdangerous",
        "blinker",
        "sqlalchemy",
        "alembic",
        "greenlet",
        "mako",
        "celery",
        "redis",
        "kombu",
        "amqp",
        "billiard",
        "vine",
        "pymongo",
        "elasticsearch",
        "requests-oauthlib",
        "oauthlib",
        "pyjwt",
        "python-jose",
        "passlib",
        "pydantic",
        "pydantic-core",
        "annotated-types",
        "fastapi",
        "starlette",
        "uvicorn",
        "anyio",
        "sniffio",
        "h11",
        "httpx",
        "httpcore",
        "tornado",
        "aiohttp",
        "multidict",
        "yarl",
        "frozenlist",
        "aiosignal",
        "async-timeout",
        "gunicorn",
        "psycopg2",
        "psycopg2-binary",
        "pymysql",
        "marshmallow",
        "scrapy",
        "twisted",
        "pyopenssl",
        "service-identity",
        "protobuf",
        "grpcio",
        "google-auth",
        "google-api-core",
        "google-cloud-storage",
        "azure-core",
        "azure-storage-blob",
        "azure-identity",
        "docker",
        "websocket-client",
        "websockets",
        "sentry-sdk",
        "prometheus-client",
        "coverage",
        "mock",
        "faker",
        "freezegun",
        "tox",
        "virtualenv",
        "distlib",
        "build",
        "installer",
        "hatchling",
        "poetry-core",
        "black",
        "flake8",
        "mccabe",
        "pycodestyle",
        "pyflakes",
        "isort",
        "pylint",
        "astroid",
        "wrapt",
        "mypy",
        "bandit",
        "gitpython",
        "gitdb",
        "smmap",
        "paramiko",
        "bcrypt",
        "pynacl",
        "invoke",
        "scikit-learn",
        "scipy",
        "joblib",
        "threadpoolctl",
        "matplotlib",
        "contourpy",
        "cycler",
        "fonttools",
        "kiwisolver",
        "tensorflow",
        "torch",
        "transformers",
        "huggingface-hub",
        "tokenizers",
        "safetensors",
        "regex",
        "sympy",
        "networkx",
        "mpmath",
        "opencv-python",
        "nltk",
        "spacy",
        "xgboost",
        "lightgbm",
        "statsmodels",
        "patsy",
        "seaborn",
        "plotly",
        "bokeh",
        "streamlit",
        "openpyxl",
        "xlrd",
        "xlsxwriter",
        "python-docx",
        "pypdf",
        "reportlab",
        "chardet",
        "defusedxml",
        "selenium",
        "playwright",
        "djangorestframework",
        "django-cors-headers",
        "drf-yasg",
        "coreapi",
        "coreschema",
    ]
    if top_n > len(popular_packages):
        logging.warning(
            f"Requested the top {top_n} packages, but the fixed list in this file holds {len(popular_packages)} names; using all {len(popular_packages)}."
        )
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
                # I do not stop at the closest popular name. One dependency
                # can be reported against several entries in the list, and the
                # reader has to decide which one it was aiming at, if any.
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
        # I print the risks and exit normally. A requirements file with
        # a likely typosquat and a clean one both exit 0, so the list
        # above is the only place the answer lives.
        print("Potential typosquatting risks found:")
        for dependency, target, similarity in risks:
            print(f"  Dependency: {dependency}, Similar to: {target}, Similarity: {similarity:.2f}")
    else:
        print("No potential typosquatting risks found.")


if __name__ == "__main__":
    main()