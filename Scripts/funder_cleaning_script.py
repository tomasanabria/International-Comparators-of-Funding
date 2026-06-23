import argparse
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Optional, Tuple, Dict, Set

import pandas as pd


# ============================================================
# FUNDER NORMALIZATION DICTIONARY
# Format:
# "raw or messy version": "clean standardized version"
# ============================================================

NORMALIZATION_MAP = {
    # --------------------
    # Major US funders
    # --------------------
    "NIH": "National Institutes of Health",
    "National Institute of Health": "National Institutes of Health",
    "National Institutes of Health": "National Institutes of Health",

    "NIMH": "National Institute of Mental Health",
    "National Institute of Mental Health": "National Institute of Mental Health",

    "NIAID": "National Institute of Allergy and Infectious Diseases",
    "National Institute of Allergy and Infectious Diseases": "National Institute of Allergy and Infectious Diseases",

    "NHGRI": "National Human Genome Research Institute",
    "National Human Genome Research Institute": "National Human Genome Research Institute",

    "NHLBI": "National Heart, Lung, and Blood Institute",
    "National Heart Lung and Blood Institute": "National Heart, Lung, and Blood Institute",
    "National Heart, Lung, and Blood Institute": "National Heart, Lung, and Blood Institute",

    "NCI": "National Cancer Institute",
    "National Cancer Institute": "National Cancer Institute",

    "NIA": "National Institute on Aging",
    "National Institute on Aging": "National Institute on Aging",

    "NCATS": "National Center for Advancing Translational Sciences",
    "National Center for Advancing Translational Sciences": "National Center for Advancing Translational Sciences",

    "NSF": "National Science Foundation",
    "National Science Foundation": "National Science Foundation",

    # --------------------
    # UK funders
    # --------------------
    "NIHR": "National Institute for Health and Care Research",
    "National Institute for Health Research": "National Institute for Health and Care Research",
    "National Institute for Health and Care Research": "National Institute for Health and Care Research",
    "National Institute of Health Research": "National Institute for Health and Care Research",

    "MRC": "Medical Research Council",
    "Medical Research Council": "Medical Research Council",
    "MRC-funded": "Medical Research Council",
    "UK Medical Research Council": "Medical Research Council",

    "WT": "Wellcome Trust",
    "Wellcome Trust": "Wellcome Trust",

    "UKRI": "UK Research and Innovation",
    "UK Research and Innovation": "UK Research and Innovation",

    "AHRC": "Arts and Humanities Research Council",
    "Arts and Humanities Research Council": "Arts and Humanities Research Council",
    "UKRI AHRC": "Arts and Humanities Research Council",

    "ESRC": "Economic and Social Research Council",
    "Economic and Social Research Council": "Economic and Social Research Council",

    "BBSRC": "Biotechnology and Biological Sciences Research Council",
    "Biotechnology and Biological Sciences Research Council": "Biotechnology and Biological Sciences Research Council",

    "EPSRC": "Engineering and Physical Sciences Research Council",
    "Engineering and Physical Sciences Research Council": "Engineering and Physical Sciences Research Council",

    "CRUK": "Cancer Research UK",
    "Cancer Research UK": "Cancer Research UK",

    "BHF": "British Heart Foundation",
    "British Heart Foundation": "British Heart Foundation",

    "HTA": "Health Technology Assessment Programme",
    "Health Technology Assessment Programme": "Health Technology Assessment Programme",
    "Health Technology Assessment": "Health Technology Assessment Programme",
    "NIHR HTA": "Health Technology Assessment Programme",

    "RfPB": "Research for Patient Benefit Programme",
    "Research for Patient Benefit Programme": "Research for Patient Benefit Programme",
    "NIHR RfPB": "Research for Patient Benefit Programme",

    "DFID": "Department for International Development",
    "Department for International Development": "Department for International Development",
    "Department for International Development, UK Government": "Department for International Development",

    # --------------------
    # China funders
    # --------------------
    "NSFC": "National Natural Science Foundation of China",
    "National Natural Science Foundation of China": "National Natural Science Foundation of China",
    "National Nature Science Foundation of China": "National Natural Science Foundation of China",

    "NKRDPC": "National Key Research and Development Program of China",
    "National Key Research and Development Program of China": "National Key Research and Development Program of China",
    "National Key Research and Development Plan": "National Key Research and Development Program of China",
    "National Key Research and Development Projects": "National Key Research and Development Program of China",
    "National Key Research and Development Program of China Stem Cell and Translational Research": "National Key Research and Development Program of China",

    "Fundamental Research Funds for the Central Universities": "Fundamental Research Funds for the Central Universities",

    "Chinese Academy of Sciences": "Chinese Academy of Sciences",
    "CAS": "Chinese Academy of Sciences",

    "China Postdoctoral Science Foundation": "China Postdoctoral Science Foundation",
    "China Postdoctoral Science Foundation General Project": "China Postdoctoral Science Foundation",

    # --------------------
    # South Africa funders
    # --------------------
    "SAMRC": "South African Medical Research Council",
    "South African Medical Research Council": "South African Medical Research Council",

    "NRF": "National Research Foundation of South Africa",
    "National Research Foundation": "National Research Foundation of South Africa",
    "National Research Foundation of South Africa": "National Research Foundation of South Africa",

    # --------------------
    # International / philanthropic funders
    # --------------------
    "BMGF": "Bill & Melinda Gates Foundation",
    "Bill and Melinda Gates Foundation": "Bill & Melinda Gates Foundation",
    "Bill & Melinda Gates Foundation": "Bill & Melinda Gates Foundation",

    "WHO": "World Health Organization",
    "World Health Organization": "World Health Organization",

    "European Commission": "European Commission",
    "EC": "European Commission",

    "H2020": "Horizon 2020 Framework Programme",
    "Horizon 2020": "Horizon 2020 Framework Programme",
    "Horizon 2020 Framework Programme": "Horizon 2020 Framework Programme",

    "FP7": "Seventh Framework Programme",
    "Seventh Framework Programme": "Seventh Framework Programme",

    "EDCTP": "European and Developing Countries Clinical Trials Partnership",
    "European and Developing Countries Clinical Trials Partnership": "European and Developing Countries Clinical Trials Partnership",

    "ARC": "Australian Research Council",
    "Australian Research Council": "Australian Research Council",

    "NHMRC": "National Health and Medical Research Council",
    "National Health and Medical Research Council": "National Health and Medical Research Council",

    "CIHR": "Canadian Institutes of Health Research",
    "Canadian Institutes of Health Research": "Canadian Institutes of Health Research",
}


# ============================================================
# YEAR-INDEPENDENT COUNTRY SETTINGS
# These settings assume all datasets use the same country-specific
# affiliation columns across years.
# ============================================================

COUNTRY_SETTINGS = {
    "China": {
        "affiliation_column": "Chinese Affiliation",
        "prefix": "china",
    },
    "South Africa": {
        "affiliation_column": "South African Affiliation",
        "prefix": "south_africa",
    },
    "United Kingdom": {
        "affiliation_column": "British Affiliation",
        "prefix": "uk",
    },
    "United States": {
        "affiliation_column": "American Affiliation",
        "prefix": "usa",
    },
}


# Values that indicate an article should be retained.
KEEP_VALUES = {"yes", "y", "true", "1", "keep"}


# ============================================================
# CLEANING FUNCTIONS
# ============================================================

def remove_parenthetical_grant_codes(text: str) -> str:
    """
    Removes parenthetical grant numbers or codes.

    Example:
    "National Institutes of Health, NIH, (R01MH12345)"
    becomes:
    "National Institutes of Health, NIH"
    """
    if pd.isna(text):
        return ""

    text = str(text)
    text = re.sub(r"\([^)]*\)", "", text)

    return text.strip()


def normalize_spaces(text: str) -> str:
    """
    Standardizes whitespace and strips punctuation at the edges.
    """
    if pd.isna(text):
        return ""

    text = str(text)
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    text = text.strip(" ;,.")

    return text


def remove_trailing_acronym(name: str) -> str:
    """
    Removes acronym at the end of a funder name when the full name appears first.

    Example:
    "National Institutes of Health, NIH"
    becomes:
    "National Institutes of Health"
    """
    name = normalize_spaces(name)

    if not name:
        return ""

    parts = [p.strip() for p in name.split(",") if p.strip()]

    if len(parts) >= 2:
        last = parts[-1]

        # Acronym-like ending: all caps, short, no spaces.
        if len(last) <= 10 and last.upper() == last and re.match(r"^[A-Z0-9&.\-]+$", last):
            return ", ".join(parts[:-1]).strip()

    return name


def clean_funder_name(raw_funder: str) -> str:
    """
    Produces a cleaned funder name before applying the normalization dictionary.
    """
    if pd.isna(raw_funder):
        return ""

    name = str(raw_funder)

    # Remove grant codes.
    name = remove_parenthetical_grant_codes(name)

    # Normalize common unicode punctuation.
    name = name.replace("‐", "-")
    name = name.replace("–", "-")
    name = name.replace("—", "-")
    name = name.replace("’", "'")
    name = name.replace("“", '"')
    name = name.replace("”", '"')

    # Normalize spaces and punctuation.
    name = normalize_spaces(name)

    # Remove trailing acronym after comma.
    name = remove_trailing_acronym(name)

    # Final cleanup.
    name = normalize_spaces(name)

    return name


def normalize_funder(cleaned_name: str) -> str:
    """
    Applies the manually reviewed normalization dictionary.
    If no dictionary rule exists, keeps the cleaned name.
    """
    cleaned_name = normalize_spaces(cleaned_name)

    if not cleaned_name:
        return ""

    # Exact match first.
    if cleaned_name in NORMALIZATION_MAP:
        return NORMALIZATION_MAP[cleaned_name]

    # Case-insensitive fallback.
    lower_map = {k.lower(): v for k, v in NORMALIZATION_MAP.items()}
    if cleaned_name.lower() in lower_map:
        return lower_map[cleaned_name.lower()]

    return cleaned_name


def split_funders(funding_details: str) -> List[str]:
    """
    Splits Scopus Funding Details into semicolon-separated raw funder entries.
    """
    if pd.isna(funding_details):
        return []

    text = str(funding_details).strip()

    if not text:
        return []

    return [p.strip() for p in text.split(";") if p.strip()]


def find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """
    Finds a column by exact name or case-insensitive match.
    """
    existing = list(df.columns)

    # Exact match.
    for candidate in candidates:
        if candidate in existing:
            return candidate

    # Case-insensitive match.
    lower_lookup = {str(c).lower().strip(): c for c in existing}
    for candidate in candidates:
        key = candidate.lower().strip()
        if key in lower_lookup:
            return lower_lookup[key]

    return None


def filter_kept_articles(df: pd.DataFrame, affiliation_column: str) -> pd.DataFrame:
    """
    Filters dataframe to articles marked Yes in the relevant country affiliation column.

    Example:
    China sheet -> Chinese Affiliation = Yes
    United States sheet -> American Affiliation = Yes
    """
    actual_column = find_column(df, [affiliation_column])

    if actual_column is None:
        raise ValueError(
            f"Could not find required affiliation column: {affiliation_column}. "
            f"Available columns: {list(df.columns)}"
        )

    mask = (
        df[actual_column]
        .astype(str)
        .str.lower()
        .str.strip()
        .isin(KEEP_VALUES)
    )

    return df[mask].copy()


def get_article_identifier(row: pd.Series, row_index: int) -> str:
    """
    Creates a stable article identifier using EID, DOI, Title, or row number.
    """
    for col in ["EID", "DOI", "Title", "Document Title"]:
        if col in row.index:
            val = row.get(col)
            if pd.notna(val) and str(val).strip():
                return str(val).strip()

    return f"row_{row_index}"


def get_article_title(row: pd.Series) -> str:
    """
    Retrieves article title if available.
    """
    for col in ["Title", "Document Title"]:
        if col in row.index:
            val = row.get(col)
            if pd.notna(val) and str(val).strip():
                return str(val).strip()

    return ""


# ============================================================
# MAIN PROCESSING FUNCTIONS
# ============================================================

def process_country_sheet(
    df: pd.DataFrame,
    country_name: str,
    year: int,
    affiliation_column: str,
    funding_column_candidates: List[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict]:
    """
    Processes one country sheet and returns:
    1. counts_df
    2. mention_audit_df
    3. normalization_dictionary_df
    4. summary dictionary
    """

    if funding_column_candidates is None:
        funding_column_candidates = ["Funding Details", "Funding Sponsor", "Funding Text"]

    funding_column = find_column(df, funding_column_candidates)

    if funding_column is None:
        raise ValueError(
            f"Could not find funding column. Tried: {funding_column_candidates}. "
            f"Available columns: {list(df.columns)}"
        )

    kept_df = filter_kept_articles(
        df=df,
        affiliation_column=affiliation_column,
    )

    funded_df = kept_df[
        kept_df[funding_column].notna()
        & (kept_df[funding_column].astype(str).str.strip() != "")
    ].copy()

    mention_counter = Counter()
    raw_variants_normalized: Dict[str, Set[str]] = defaultdict(set)
    raw_variants_as_found: Dict[str, Set[str]] = defaultdict(set)

    audit_rows = []
    normalization_rows = []

    for row_index, row in funded_df.iterrows():
        article_id = get_article_identifier(row, row_index)
        title = get_article_title(row)

        raw_funders = split_funders(row[funding_column])
        normalized_funders_this_article = []

        for raw_funder in raw_funders:
            cleaned = clean_funder_name(raw_funder)
            normalized = normalize_funder(cleaned)

            if not normalized:
                continue

            raw_variants_normalized[normalized].add(cleaned)
            raw_variants_as_found[normalized].add(str(raw_funder).strip())
            normalized_funders_this_article.append(normalized)

            audit_rows.append(
                {
                    "Country": country_name,
                    "Year": year,
                    "Article Row Index": row_index,
                    "Article ID": article_id,
                    "Title": title,
                    "Funder Raw As Found": str(raw_funder).strip(),
                    "Funder Cleaned Before Dictionary": cleaned,
                    "Funder Normalized": normalized,
                }
            )

            normalization_rows.append(
                {
                    "Raw Variant As Found": str(raw_funder).strip(),
                    "Cleaned Variant": cleaned,
                    "Normalized Funder": normalized,
                }
            )

        # Deduplicate within the same article.
        unique_normalized_funders = set(normalized_funders_this_article)

        for funder in unique_normalized_funders:
            mention_counter[funder] += 1

    # Final output table with only three columns.
    counts_rows = []

    for funder in sorted(mention_counter.keys()):
        counts_rows.append(
            {
                "Raw Variants Normalized": "; ".join(sorted(raw_variants_normalized[funder])),
                "Funder": funder,
                "Articles Funded": mention_counter[funder],
            }
        )

    counts_df = pd.DataFrame(counts_rows)

    if not counts_df.empty:
        counts_df = counts_df.sort_values(
            by=["Articles Funded", "Funder"],
            ascending=[False, True],
        ).reset_index(drop=True)

    audit_df = pd.DataFrame(audit_rows)

    normalization_df = pd.DataFrame(normalization_rows)

    if not normalization_df.empty:
        normalization_df = (
            normalization_df
            .drop_duplicates()
            .sort_values(by=["Normalized Funder", "Cleaned Variant", "Raw Variant As Found"])
            .reset_index(drop=True)
        )

    summary = {
        "Country": country_name,
        "Year": year,
        "Total rows in sheet": len(df),
        "Affiliation column used": affiliation_column,
        "Kept articles": len(kept_df),
        "Kept articles with funding details": len(funded_df),
        "Raw semicolon-separated funder entries": sum(
            len(split_funders(x)) for x in funded_df[funding_column]
        ),
        "Article-level funder mentions": int(sum(mention_counter.values())),
        "Unique cleaned funders": len(mention_counter),
        "Funding column used": funding_column,
    }

    return counts_df, audit_df, normalization_df, summary


def write_country_outputs(
    counts_df: pd.DataFrame,
    audit_df: pd.DataFrame,
    normalization_df: pd.DataFrame,
    summary: Dict,
    output_dir: Path,
    file_prefix: str,
    year: int,
):
    """
    Writes only an Excel output for one country.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"{file_prefix}{year}_funder_counts_raw_variants"
    excel_path = output_dir / f"{base_name}.xlsx"

    summary_df = pd.DataFrame([summary])

    method_text = pd.DataFrame(
        {
            "Method Notes": [
                "This script is year-independent and uses standardized country-specific affiliation columns.",
                "Only articles marked Yes in the relevant country affiliation column were included in the funder-counting analysis.",
                "For China, the inclusion column is Chinese Affiliation.",
                "For South Africa, the inclusion column is South African Affiliation.",
                "For the United Kingdom, the inclusion column is British Affiliation.",
                "For the United States, the inclusion column is American Affiliation.",
                "Rows without Scopus Funding Details were excluded from funder-count calculations but should not be interpreted as unfunded.",
                "Funding Details were split using semicolons.",
                "Grant numbers and parenthetical award identifiers were removed for name cleaning.",
                "Acronym-only repetitions were removed when attached to full funder names.",
                "Funder names were normalized using a manually reviewed dictionary.",
                "Articles Funded counts each normalized funder once per article.",
                "Raw Variants Normalized records cleaned variants grouped under each funder.",
                "No assumption was made that the first listed funder was the primary funder.",
            ]
        }
    )

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        counts_df.to_excel(writer, sheet_name="Funder Counts", index=False)
        audit_df.to_excel(writer, sheet_name="Mention Audit", index=False)
        normalization_df.to_excel(writer, sheet_name="Normalization Dictionary", index=False)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        method_text.to_excel(writer, sheet_name="Method", index=False)

    return excel_path

def process_workbook(input_file: str, output_dir: str, year: int):
    """
    Processes all country sheets in a workbook.

    The workbook should contain sheets named:
    - China
    - South Africa
    - United Kingdom
    - United States

    Each sheet should contain the relevant affiliation column:
    - Chinese Affiliation
    - South African Affiliation
    - British Affiliation
    - American Affiliation
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    all_summaries = []

    xls = pd.ExcelFile(input_path)

    for country_name, settings in COUNTRY_SETTINGS.items():
        if country_name not in xls.sheet_names:
            print(f"Skipping {country_name}: sheet not found.")
            continue

        print(f"Processing {country_name}...")

        df = pd.read_excel(input_path, sheet_name=country_name)

        counts_df, audit_df, normalization_df, summary = process_country_sheet(
            df=df,
            country_name=country_name,
            year=year,
            affiliation_column=settings["affiliation_column"],
        )

        write_country_outputs(
            counts_df=counts_df,
            audit_df=audit_df,
            normalization_df=normalization_df,
            summary=summary,
            output_dir=output_path,
            file_prefix=settings["prefix"],
            year=year,
        )

        all_summaries.append(summary)

    summary_df = pd.DataFrame(all_summaries)
    output_path.mkdir(parents=True, exist_ok=True)

    summary_path = output_path / f"funder_processing_summary_{year}.xlsx"
    summary_df.to_excel(summary_path, index=False)

    print("\nDone.")
    print(f"Summary saved to: {summary_path}")


# ============================================================
# COMMAND-LINE INTERFACE
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Clean and count Scopus funder metadata across country-year datasets."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to the Excel workbook, e.g. 'data/Data Set 2024.xlsx'.",
    )

    parser.add_argument(
        "--year",
        required=True,
        type=int,
        help="Dataset year, e.g. 2020, 2024, or 2026.",
    )

    parser.add_argument(
        "--output",
        required=False,
        default=None,
        help="Output directory. If omitted, defaults to funder_outputs_YEAR.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    output_dir = args.output
    if output_dir is None:
        output_dir = f"funder_outputs_{args.year}"

    process_workbook(
        input_file=args.input,
        output_dir=output_dir,
        year=args.year,
    )