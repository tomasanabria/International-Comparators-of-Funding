import re
from pathlib import Path
from collections import Counter, defaultdict

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
# COUNTRY-SPECIFIC SHEET SETTINGS
# These are used to identify the keep column for 2020 files
# where each country had its own affiliation flag.
# ============================================================

COUNTRY_SETTINGS_2020 = {
    "China": {
        "keep_column_candidates": ["Chinese Affiliation", "Keep / Remove"],
        "keep_values": ["yes", "keep"],
        "prefix": "china",
    },
    "South Africa": {
        "keep_column_candidates": ["South African Affiliation", "Keep / Remove"],
        "keep_values": ["yes", "keep"],
        "prefix": "south_africa",
    },
    "United Kingdom": {
        "keep_column_candidates": ["British Affiliation", "Keep / Remove"],
        "keep_values": ["yes", "keep"],
        "prefix": "uk",
    },
    "United States": {
        "keep_column_candidates": ["American Affiliation", "Keep / Remove"],
        "keep_values": ["yes", "keep"],
        "prefix": "usa",
    },
}

COUNTRY_SETTINGS_2024 = {
    "China": {
        "keep_column_candidates": ["Keep / Remove", "Chinese Affiliation"],
        "keep_values": ["keep", "yes"],
        "prefix": "china",
    },
    "South Africa": {
        "keep_column_candidates": ["Keep / Remove", "South African Affiliation"],
        "keep_values": ["keep", "yes"],
        "prefix": "south_africa",
    },
    "United Kingdom": {
        "keep_column_candidates": ["Keep / Remove", "British Affiliation"],
        "keep_values": ["keep", "yes"],
        "prefix": "uk",
    },
    "United States": {
        "keep_column_candidates": ["Keep / Remove", "American Affiliation"],
        "keep_values": ["keep", "yes"],
        "prefix": "usa",
    },
}


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

    # Remove all text inside parentheses.
    text = re.sub(r"\([^)]*\)", "", text)

    return text.strip()


def normalize_spaces(text: str) -> str:
    """
    Standardizes whitespace and strips punctuation at edges.
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

    This only removes short uppercase final comma-separated parts.
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
    name = name.replace("-", "-")
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


def split_funders(funding_details: str) -> list[str]:
    """
    Splits Scopus Funding Details into semicolon-separated raw funder entries.
    """
    if pd.isna(funding_details):
        return []

    text = str(funding_details).strip()

    if not text:
        return []

    parts = [p.strip() for p in text.split(";") if p.strip()]

    return parts


def find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """
    Finds a column by exact candidate names.
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


def filter_kept_articles(
    df: pd.DataFrame,
    keep_column_candidates: list[str],
    keep_values: list[str],
) -> pd.DataFrame:
    """
    Filters dataframe to kept articles using a country-specific keep column.
    """
    keep_column = find_column(df, keep_column_candidates)

    if keep_column is None:
        raise ValueError(
            f"Could not find a keep column. Tried: {keep_column_candidates}. "
            f"Available columns: {list(df.columns)}"
        )

    keep_values_lower = [v.lower().strip() for v in keep_values]

    mask = (
        df[keep_column]
        .astype(str)
        .str.lower()
        .str.strip()
        .isin(keep_values_lower)
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


def process_country_sheet(
    df: pd.DataFrame,
    country_name: str,
    year: int,
    keep_column_candidates: list[str],
    keep_values: list[str],
    funding_column_candidates: list[str] = ["Funding Details", "Funding Sponsor", "Funding Text"],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """
    Processes one country sheet and returns:
    1. counts_df
    2. mention_audit_df
    3. normalization_dictionary_df
    4. summary dictionary
    """

    funding_column = find_column(df, funding_column_candidates)

    if funding_column is None:
        raise ValueError(
            f"Could not find funding column. Tried: {funding_column_candidates}. "
            f"Available columns: {list(df.columns)}"
        )

    kept_df = filter_kept_articles(
        df=df,
        keep_column_candidates=keep_column_candidates,
        keep_values=keep_values,
    )

    funded_df = kept_df[
        kept_df[funding_column].notna()
        & (kept_df[funding_column].astype(str).str.strip() != "")
    ].copy()

    mention_counter = Counter()
    raw_occurrence_counter = Counter()
    raw_variants_normalized = defaultdict(set)
    raw_variants_as_found = defaultdict(set)

    audit_rows = []
    normalization_rows = []

    for row_index, row in funded_df.iterrows():
        article_id = get_article_identifier(row, row_index)

        title = ""
        for title_col in ["Title", "Document Title"]:
            if title_col in row.index and pd.notna(row.get(title_col)):
                title = str(row.get(title_col)).strip()
                break

        raw_funders = split_funders(row[funding_column])
        normalized_funders_this_article = []

        for raw_funder in raw_funders:
            cleaned = clean_funder_name(raw_funder)
            normalized = normalize_funder(cleaned)

            if not normalized:
                continue

            raw_occurrence_counter[normalized] += 1
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

        # Deduplicate within article.
        unique_normalized_funders = set(normalized_funders_this_article)

        for funder in unique_normalized_funders:
            mention_counter[funder] += 1

    counts_rows = []

    for funder in sorted(mention_counter.keys()):
        counts_rows.append(
            {
                "Funder Clean": funder,
                "Mention Count": mention_counter[funder],
                "Raw Occurrence Count": raw_occurrence_counter[funder],
                "Raw Variants Normalized": "; ".join(sorted(raw_variants_normalized[funder])),
                "Raw Variants As Found": "; ".join(sorted(raw_variants_as_found[funder])),
            }
        )

    counts_df = pd.DataFrame(counts_rows)

    if not counts_df.empty:
        counts_df = counts_df.sort_values(
            by=["Mention Count", "Raw Occurrence Count", "Funder Clean"],
            ascending=[False, False, True],
        ).reset_index(drop=True)

    audit_df = pd.DataFrame(audit_rows)

    normalization_df = pd.DataFrame(normalization_rows).drop_duplicates()

    if not normalization_df.empty:
        normalization_df = normalization_df.sort_values(
            by=["Normalized Funder", "Cleaned Variant", "Raw Variant As Found"]
        ).reset_index(drop=True)

    summary = {
        "Country": country_name,
        "Year": year,
        "Total rows in sheet": len(df),
        "Kept articles": len(kept_df),
        "Kept articles with funding details": len(funded_df),
        "Raw semicolon-separated funder entries": sum(
            len(split_funders(x)) for x in funded_df[funding_column]
        ),
        "Cleaned article-level funder mentions": int(sum(mention_counter.values())),
        "Unique cleaned funders": len(mention_counter),
        "Funding column used": funding_column,
    }

    return counts_df, audit_df, normalization_df, summary


def write_country_outputs(
    counts_df: pd.DataFrame,
    audit_df: pd.DataFrame,
    normalization_df: pd.DataFrame,
    summary: dict,
    output_dir: Path,
    file_prefix: str,
    year: int,
):
    """
    Writes Excel, CSV, and TXT outputs for one country.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"{file_prefix}{year}_funder_counts_raw_variants"

    excel_path = output_dir / f"{base_name}.xlsx"
    csv_path = output_dir / f"{base_name}.csv"
    txt_path = output_dir / f"{base_name}.txt"

    summary_df = pd.DataFrame([summary])

    method_text = pd.DataFrame(
        {
            "Method Notes": [
                "Only retained articles were included in the funder-counting analysis.",
                "Rows without Scopus Funding Details were excluded from funder-count calculations but should not be interpreted as unfunded.",
                "Funding Details were split using semicolons.",
                "Grant numbers and parenthetical award identifiers were removed for name cleaning.",
                "Acronym-only repetitions were removed when attached to full funder names.",
                "Funder names were normalized using a manually reviewed dictionary.",
                "Mention Count counts each normalized funder once per article.",
                "Raw Occurrence Count counts every raw appearance before article-level deduplication.",
                "Raw Variants Normalized records cleaned variants grouped under each funder.",
                "Raw Variants As Found records original Scopus strings grouped under each funder.",
            ]
        }
    )

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        counts_df.to_excel(writer, sheet_name="Funder Counts", index=False)
        audit_df.to_excel(writer, sheet_name="Mention Audit", index=False)
        normalization_df.to_excel(writer, sheet_name="Normalization Dictionary", index=False)
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        method_text.to_excel(writer, sheet_name="Method", index=False)

    counts_df.to_csv(csv_path, index=False)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"Funder counts for {summary['Country']} {year}\n")
        f.write("=" * 80 + "\n\n")

        for key, value in summary.items():
            f.write(f"{key}: {value}\n")

        f.write("\n" + "=" * 80 + "\n\n")

        if counts_df.empty:
            f.write("No funders found.\n")
        else:
            for _, row in counts_df.iterrows():
                f.write(
                    f"{row['Funder Clean']} | "
                    f"Mention Count: {row['Mention Count']} | "
                    f"Raw Occurrence Count: {row['Raw Occurrence Count']}\n"
                )
                f.write(f"Raw Variants Normalized: {row['Raw Variants Normalized']}\n")
                f.write(f"Raw Variants As Found: {row['Raw Variants As Found']}\n")
                f.write("-" * 80 + "\n")

    return excel_path, csv_path, txt_path


def process_workbook(input_file: str, output_dir: str, year: int):
    """
    Processes all country sheets in a workbook.
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)

    if year == 2020:
        country_settings = COUNTRY_SETTINGS_2020
    elif year == 2024:
        country_settings = COUNTRY_SETTINGS_2024
    else:
        raise ValueError("Year must be either 2020 or 2024.")

    all_summaries = []

    xls = pd.ExcelFile(input_path)

    for country_name, settings in country_settings.items():
        if country_name not in xls.sheet_names:
            print(f"Skipping {country_name}: sheet not found.")
            continue

        print(f"Processing {country_name}...")

        df = pd.read_excel(input_path, sheet_name=country_name)

        counts_df, audit_df, normalization_df, summary = process_country_sheet(
            df=df,
            country_name=country_name,
            year=year,
            keep_column_candidates=settings["keep_column_candidates"],
            keep_values=settings["keep_values"],
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
    summary_path = output_path / f"funder_processing_summary_{year}.csv"
    summary_df.to_csv(summary_path, index=False)

    print("\nDone.")
    print(f"Summary saved to: {summary_path}")


# ============================================================
# RUN SCRIPT
# Edit these paths before running.
# ============================================================

if __name__ == "__main__":
    INPUT_FILE = "Data Set 2024.xlsx"
    OUTPUT_DIR = "funder_outputs_2024"
    YEAR = 2024

    process_workbook(
        input_file=INPUT_FILE,
        output_dir=OUTPUT_DIR,
        year=YEAR,
    )