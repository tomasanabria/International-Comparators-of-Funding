import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ============================================================
# COUNTRY SCREENING SETTINGS
# ============================================================

COUNTRY_SETTINGS = {
    "China": {
        "affiliation_column": "Chinese Affiliation",
        "country_aliases": [
            "China",
            "People's Republic of China",
            "PR China",
            "P.R. China",
            "Mainland China",
        ],
    },
    "South Africa": {
        "affiliation_column": "South African Affiliation",
        "country_aliases": [
            "South Africa",
            "Republic of South Africa",
        ],
    },
    "United Kingdom": {
        "affiliation_column": "British Affiliation",
        "country_aliases": [
            "United Kingdom",
            "UK",
            "U.K.",
            "England",
            "Scotland",
            "Wales",
            "Northern Ireland",
            "Belfast",
        ],
        "exclude_aliases": [
            "Republic of Ireland",
            "Ireland",
            "Dublin",
            "Cork",
            "Galway",
            "Limerick",
            "New England",
            "New South Wales",
        ],
    },
    "United States": {
        "affiliation_column": "American Affiliation",
        "country_aliases": [
            "United States",
            "United States of America",
            "USA",
            "U.S.A.",
            "U.S.",
            "U.S",
            "US",
        ],
    },
}


AUTHOR_AFFILIATION_COLUMN_CANDIDATES = [
    "Authors with affiliations",
    "Author full names with affiliations",
    "Author(s) with affiliation(s)",
    "Authors Affiliations",
]

AUTHOR_COLUMN_CANDIDATES = [
    "Authors",
    "Author(s)",
    "Author Names",
]


# ============================================================
# BASIC HELPERS
# ============================================================

def normalize_text(text: str) -> str:
    """
    Normalizes spacing for safer matching.
    """
    if pd.isna(text):
        return ""

    text = str(text)
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """
    Finds a column by exact or case-insensitive match.
    """
    existing = list(df.columns)

    for candidate in candidates:
        if candidate in existing:
            return candidate

    lower_lookup = {str(c).lower().strip(): c for c in existing}

    for candidate in candidates:
        key = candidate.lower().strip()
        if key in lower_lookup:
            return lower_lookup[key]

    return None


def safe_sheet_name(name: str) -> str:
    """
    Excel sheet names must be 31 characters or fewer and cannot contain certain characters.
    """
    name = re.sub(r"[\[\]\:\*\?\/\\]", "-", name)
    return name[:31]


# ============================================================
# RAW SCOPUS FILE LOADING
# ============================================================

def detect_header_row(input_path: Path, sheet_name: str) -> int:
    """
    Scopus exports sometimes place the export filename in row 1
    and the real headers in row 2.

    This function detects the row containing the actual Scopus headers.
    """
    preview = pd.read_excel(
        input_path,
        sheet_name=sheet_name,
        header=None,
        nrows=20,
        dtype=str,
    )

    for row_index, row in preview.iterrows():
        values = [normalize_text(v).lower() for v in row.tolist()]
        joined = " | ".join(values)

        if "authors with affiliations" in joined and "title" in joined:
            return int(row_index)

        if "authors" in values and "title" in values and "affiliations" in values:
            return int(row_index)

    raise ValueError(
        "Could not detect the Scopus header row. "
        "Expected a row containing columns like 'Authors', 'Title', and 'Authors with affiliations'."
    )


def load_scopus_export(input_file: str, sheet_name: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
    """
    Loads a raw Scopus Excel export.

    Works for files where:
    - there is only one sheet with a Scopus-generated name
    - the first row is an export title
    - the second row contains the real headers
    """
    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    xls = pd.ExcelFile(input_path)

    if sheet_name is None:
        selected_sheet = xls.sheet_names[0]
    else:
        if sheet_name not in xls.sheet_names:
            raise ValueError(
                f"Sheet '{sheet_name}' not found. Available sheets: {xls.sheet_names}"
            )
        selected_sheet = sheet_name

    header_row = detect_header_row(input_path, selected_sheet)

    df = pd.read_excel(
        input_path,
        sheet_name=selected_sheet,
        header=header_row,
    )

    df = df.dropna(how="all").copy()

    # Clean column names.
    cleaned_columns = []
    for i, col in enumerate(df.columns):
        col_name = normalize_text(col)
        if not col_name or col_name.lower().startswith("unnamed"):
            col_name = f"Unnamed Column {i + 1}"
        cleaned_columns.append(col_name)

    df.columns = cleaned_columns

    return df, selected_sheet


# ============================================================
# AUTHOR AND AFFILIATION PARSING
# ============================================================

def split_authors(authors_text: str) -> List[str]:
    """
    Splits the Scopus Authors field.

    In the raw Scopus file you showed, authors are separated by semicolons:
    "Palk A.; Illes J.; Thompson P.M.; Stein D.J."
    """
    text = normalize_text(authors_text)

    if not text:
        return []

    if ";" in text:
        return [p.strip() for p in text.split(";") if p.strip()]

    # Fallback if another export uses commas.
    return [p.strip() for p in text.split(",") if p.strip()]


def split_author_affiliation_blocks(affiliation_text: str) -> List[str]:
    """
    Splits Scopus 'Authors with affiliations' into author-affiliation blocks.

    Example:
    Author A., affiliation...; Author B., affiliation...
    """
    text = normalize_text(affiliation_text)

    if not text:
        return []

    return [b.strip() for b in text.split(";") if b.strip()]


def author_key(author_name: str) -> str:
    """
    Converts an author string to a simplified key for matching.

    Example:
    "Palk A." -> "palka"
    """
    text = normalize_text(author_name).lower()
    text = re.sub(r"[^a-z0-9]", "", text)
    return text


def extract_author_prefix_from_block(block: str) -> str:
    """
    Extracts the author name at the start of an author-affiliation block.

    Example:
    "Palk A., Department of Philosophy..." -> "Palk A."
    """
    block = normalize_text(block)

    if "," in block:
        return block.split(",", 1)[0].strip()

    return block.strip()


def get_author_blocks(
    author_name: str,
    affiliation_blocks: List[str],
    fallback_position: str,
) -> List[str]:
    """
    Finds all affiliation blocks corresponding to a given author.

    This is important because a first or last author can have multiple affiliations.
    """
    target_key = author_key(author_name)

    matched_blocks = []

    if target_key:
        for block in affiliation_blocks:
            block_author = extract_author_prefix_from_block(block)
            if author_key(block_author) == target_key:
                matched_blocks.append(block)

    if matched_blocks:
        return matched_blocks

    # Fallback if author names cannot be matched.
    if not affiliation_blocks:
        return []

    if fallback_position == "first":
        return [affiliation_blocks[0]]

    if fallback_position == "last":
        return [affiliation_blocks[-1]]

    return []


def extract_first_last_authors(row: pd.Series, author_column: Optional[str]) -> Tuple[str, str]:
    """
    Extracts first and last author names from the Authors column.
    """
    if author_column is None:
        return "", ""

    authors = split_authors(row.get(author_column, ""))

    if not authors:
        return "", ""

    return authors[0], authors[-1]


def extract_first_last_affiliation_blocks(
    row: pd.Series,
    author_column: Optional[str],
    author_affiliation_column: str,
) -> Tuple[str, str, List[str], List[str]]:
    """
    Extracts first and last author affiliation blocks.

    Returns:
    - first author name
    - last author name
    - first author affiliation block(s)
    - last author affiliation block(s)
    """
    first_author, last_author = extract_first_last_authors(row, author_column)

    affiliation_text = row.get(author_affiliation_column, "")
    affiliation_blocks = split_author_affiliation_blocks(affiliation_text)

    first_blocks = get_author_blocks(
        author_name=first_author,
        affiliation_blocks=affiliation_blocks,
        fallback_position="first",
    )

    last_blocks = get_author_blocks(
        author_name=last_author,
        affiliation_blocks=affiliation_blocks,
        fallback_position="last",
    )

    return first_author, last_author, first_blocks, last_blocks


# ============================================================
# COUNTRY MATCHING
# ============================================================

def contains_alias(text: str, aliases: List[str]) -> bool:
    """
    Checks if any country alias appears in text.

    Uses stricter matching for short aliases like US, UK, U.S., etc.,
    so that 'US' does not accidentally match words like 'University'.
    """
    text = normalize_text(text)

    if not text:
        return False

    for alias in aliases:
        alias = normalize_text(alias)

        if not alias:
            continue

        # For short abbreviations, require non-letter boundaries.
        if len(alias.replace(".", "")) <= 3:
            pattern = r"(?<![A-Za-z])" + re.escape(alias) + r"(?![A-Za-z])"
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True
        else:
            if re.search(re.escape(alias), text, flags=re.IGNORECASE):
                return True

    return False


def country_match_text(text: str, country_name: str) -> bool:
    """
    Checks whether an affiliation text matches the country of interest.
    """
    settings = COUNTRY_SETTINGS[country_name]

    text = normalize_text(text)

    if not text:
        return False

    # Special caution for UK:
    # Avoid counting Republic of Ireland, New England, or New South Wales as UK.
    if country_name == "United Kingdom":
        exclude_aliases = settings.get("exclude_aliases", [])
        protected_uk_aliases = ["Northern Ireland", "Belfast"]

        if contains_alias(text, exclude_aliases) and not contains_alias(text, protected_uk_aliases):
            return False

    return contains_alias(text, settings["country_aliases"])


def country_match_blocks(blocks: List[str], country_name: str) -> bool:
    """
    Checks whether any affiliation block matches the country of interest.
    """
    return any(country_match_text(block, country_name) for block in blocks)


# ============================================================
# SCREENING
# ============================================================

def screen_scopus_dataframe(df: pd.DataFrame, country_name: str) -> pd.DataFrame:
    """
    Screens a raw Scopus dataframe using first- and last-author affiliations.

    Final output only includes:
    - First Author
    - Affiliation (FA)
    - Last Author
    - Affiliation (LA)
    - Country-specific affiliation column
    """
    if country_name not in COUNTRY_SETTINGS:
        raise ValueError(
            f"Unsupported country: {country_name}. "
            f"Choose from: {list(COUNTRY_SETTINGS.keys())}"
        )

    settings = COUNTRY_SETTINGS[country_name]
    output_affiliation_column = settings["affiliation_column"]

    author_affiliation_column = find_column(df, AUTHOR_AFFILIATION_COLUMN_CANDIDATES)
    author_column = find_column(df, AUTHOR_COLUMN_CANDIDATES)

    if author_affiliation_column is None:
        raise ValueError(
            "Could not find an author-affiliation column. "
            f"Tried: {AUTHOR_AFFILIATION_COLUMN_CANDIDATES}. "
            f"Available columns: {list(df.columns)}"
        )

    output_rows = []

    for _, row in df.iterrows():
        first_author, last_author, first_blocks, last_blocks = extract_first_last_affiliation_blocks(
            row=row,
            author_column=author_column,
            author_affiliation_column=author_affiliation_column,
        )

        first_match = country_match_blocks(first_blocks, country_name)
        last_match = country_match_blocks(last_blocks, country_name)

        keep_article = first_match or last_match

        output_rows.append(
            {
                "First Author": first_author,
                "Affiliation (FA)": " || ".join(first_blocks),
                "Last Author": last_author,
                "Affiliation (LA)": " || ".join(last_blocks),
                output_affiliation_column: "Yes" if keep_article else "No",
            }
        )

    output_df = pd.DataFrame(output_rows)

    return output_df

def process_file(
    input_file: str,
    output_file: str,
    country_name: str,
    sheet_name: Optional[str] = None,
):
    """
    Processes one raw Scopus Excel export for one country.

    The output workbook will contain:
    - one country-named sheet, e.g. China
    - Screening Summary sheet
    """
    input_path = Path(input_file)
    output_path = Path(output_file)

    df, source_sheet = load_scopus_export(
        input_file=input_file,
        sheet_name=sheet_name,
    )

    screened_df = screen_scopus_dataframe(
        df=df,
        country_name=country_name,
    )

    affiliation_column = COUNTRY_SETTINGS[country_name]["affiliation_column"]

    kept = int((screened_df[affiliation_column] == "Yes").sum())
    removed = int((screened_df[affiliation_column] == "No").sum())

    summary_df = pd.DataFrame(
        [
            {
                "Country": country_name,
                "Input file": str(input_path),
                "Source sheet": source_sheet,
                "Total records": len(screened_df),
                "Kept": kept,
                "Removed": removed,
                "Affiliation column": affiliation_column,
                "Rule": "Keep if first author or last author has country-of-interest institutional affiliation.",
            }
        ]
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        screened_df.to_excel(
            writer,
            sheet_name=safe_sheet_name(country_name),
            index=False,
        )
        summary_df.to_excel(
            writer,
            sheet_name="Screening Summary",
            index=False,
        )

    print("\nDone.")
    print(f"Input file: {input_path}")
    print(f"Source sheet: {source_sheet}")
    print(f"Country screened: {country_name}")
    print(f"Kept: {kept}")
    print(f"Removed: {removed}")
    print(f"Screened workbook saved to: {output_path}")


# ============================================================
# COMMAND-LINE INTERFACE
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Screen a raw Scopus Excel export using first- and last-author country affiliations."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to the raw Scopus Excel workbook, e.g. 'Data/China - Raw Data - 2020.xlsx'.",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Path for the screened Excel workbook, e.g. 'Data/China - Screened Data - 2020.xlsx'.",
    )

    parser.add_argument(
        "--country",
        required=True,
        choices=list(COUNTRY_SETTINGS.keys()),
        help="Country of interest.",
    )

    parser.add_argument(
        "--sheet",
        required=False,
        default=None,
        help="Optional sheet name. If omitted, the first sheet is used.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    process_file(
        input_file=args.input,
        output_file=args.output,
        country_name=args.country,
        sheet_name=args.sheet,
    )
