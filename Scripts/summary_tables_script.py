import argparse
from pathlib import Path
from typing import Optional

import pandas as pd


FUNDER_TYPE_ORDER = [
    "Government Agency",
    "Foundation/Charity",
    "Public International Agency",
    "Private International Agency",
    "Academic Institution",
    "Hospital System",
    "Corporation",
]


FUNDER_TYPE_ALIASES = {
    "government agency": "Government Agency",
    "government": "Government Agency",
    "foundation/charity": "Foundation/Charity",
    "foundation": "Foundation/Charity",
    "charity": "Foundation/Charity",
    "ngo": "Foundation/Charity",
    "nonprofit": "Foundation/Charity",
    "non profit": "Foundation/Charity",
    "non-profit": "Foundation/Charity",
    "public international agency": "Public International Agency",
    "international public agency": "Public International Agency",
    "private international agency": "Private International Agency",
    "international private agency": "Private International Agency",
    "academic institution": "Academic Institution",
    "academic": "Academic Institution",
    "university": "Academic Institution",
    "hospital system": "Hospital System",
    "hospital": "Hospital System",
    "corporation": "Corporation",
    "company": "Corporation",
    "industry": "Corporation",
}


VALID_ARTICLE_HEADERS = [
    "article mentions",
    "articles funded",
    "articles mentions",
    "publication mentions",
    "publications funded",
    "publications",
]


def normalize_text(value):
    """
    Normalizes text for column matching.
    """
    if pd.isna(value):
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace("#", "")
        .replace("_", " ")
        .replace("-", " ")
    )


def standardize_funder_type(value):
    """
    Standardizes funder type labels into the final category system.
    """
    normalized = normalize_text(value)

    if normalized in FUNDER_TYPE_ALIASES:
        return FUNDER_TYPE_ALIASES[normalized]

    return str(value).strip()


def read_input_file(input_file: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """
    Reads Excel, CSV, TSV, or TXT file.

    Expected cleaned table columns:
    - Funder
    - Article Mentions
    - Type
    - Country of Origin

    This script also supports files where the cleaned table appears on the
    right side of the worksheet after the raw/manual classification table.
    If there are two matching blocks, it selects the rightmost block.
    """
    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if input_path.suffix.lower() in [".xlsx", ".xls"]:
        excel_file = pd.ExcelFile(input_path)

        if sheet_name is None:
            selected_sheet = excel_file.sheet_names[0]
            print(f"\nNo sheet specified. Using first sheet: {selected_sheet}")
        else:
            selected_sheet = sheet_name

        if selected_sheet not in excel_file.sheet_names:
            raise ValueError(
                f"Sheet '{selected_sheet}' not found. "
                f"Available sheets: {excel_file.sheet_names}"
            )

        raw_df = pd.read_excel(input_path, sheet_name=selected_sheet, header=None)

    elif input_path.suffix.lower() == ".csv":
        raw_df = pd.read_csv(input_path, header=None)

    elif input_path.suffix.lower() in [".tsv", ".txt"]:
        raw_df = pd.read_csv(input_path, sep="\t", header=None)

    else:
        raise ValueError("Input file must be .xlsx, .xls, .csv, .tsv, or .txt")

    candidate_blocks = []

    for row_index in range(min(30, len(raw_df))):
        row_values = [normalize_text(x) for x in raw_df.iloc[row_index].tolist()]

        for col_index in range(len(row_values) - 3):
            has_funder = row_values[col_index] == "funder"
            has_articles = row_values[col_index + 1] in VALID_ARTICLE_HEADERS
            has_type = row_values[col_index + 2] in ["type", "funder type"]
            has_country = row_values[col_index + 3] in [
                "country of origin",
                "country",
                "funder country",
            ]

            if has_funder and has_articles and has_type and has_country:
                candidate_blocks.append((row_index, col_index))

    if not candidate_blocks:
        raise ValueError(
            "Could not find a cleaned table with columns: "
            "Funder, Article Mentions, Type, Country of Origin."
        )

    # If multiple matching tables exist, select the rightmost one.
    # This chooses the cleaned/consolidated table on the right side.
    header_row_index, start_col_index = max(candidate_blocks, key=lambda x: x[1])

    print(
        f"\nDetected cleaned table at row {header_row_index + 1}, "
        f"column {start_col_index + 1}"
    )

    df = raw_df.iloc[
        header_row_index + 1 :,
        start_col_index : start_col_index + 4,
    ].copy()

    df.columns = [
        "Funder",
        "Article Mentions",
        "Type",
        "Country of Origin",
    ]

    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans spacing, standardizes funder types, and converts Article Mentions to numeric.
    """
    df = df.copy()

    df["Funder"] = df["Funder"].astype(str).str.strip()
    df["Type"] = df["Type"].apply(standardize_funder_type)

    df["Country of Origin"] = (
        df["Country of Origin"]
        .fillna("Not specified")
        .astype(str)
        .str.strip()
    )

    df.loc[
        df["Country of Origin"].str.lower().isin(["", "nan", "none"]),
        "Country of Origin",
    ] = "Not specified"

    df["Article Mentions"] = pd.to_numeric(
        df["Article Mentions"],
        errors="coerce",
    )

    df = df[df["Article Mentions"].notna()]
    df["Article Mentions"] = df["Article Mentions"].astype(int)

    df = df[
        df["Funder"].notna()
        & (df["Funder"].str.strip() != "")
        & (df["Funder"].str.lower().str.strip() != "nan")
    ]

    return df


def combine_duplicate_funders(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combines exact duplicate funder names by summing Article Mentions.

    Keeps the first observed Type and Country of Origin.
    """
    combined_df = (
        df.groupby("Funder", as_index=False)
        .agg(
            {
                "Article Mentions": "sum",
                "Type": "first",
                "Country of Origin": "first",
            }
        )
        .sort_values(
            by=["Article Mentions", "Funder"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    return combined_df


def make_top_5_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates Top 5 funders by Article Mentions.
    All remaining funders are grouped into Other.
    """
    df = df.sort_values(
        by=["Article Mentions", "Funder"],
        ascending=[False, True],
    ).reset_index(drop=True)

    top_5_df = df.head(5)[["Funder", "Article Mentions"]].copy()
    other_count = df.iloc[5:]["Article Mentions"].sum()

    if other_count > 0:
        other_row = pd.DataFrame(
            [
                {
                    "Funder": "Other",
                    "Article Mentions": other_count,
                }
            ]
        )

        top_5_df = pd.concat(
            [top_5_df, other_row],
            ignore_index=True,
        )

    total = top_5_df["Article Mentions"].sum()

    if total > 0:
        top_5_df["Share"] = top_5_df["Article Mentions"] / total
    else:
        top_5_df["Share"] = 0

    return top_5_df


def make_funder_type_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates summary table by funder type using the specified category order.
    """
    grouped = df.groupby("Type", as_index=True)["Article Mentions"].sum()

    unknown_types = [
        funder_type
        for funder_type in grouped.index
        if funder_type not in FUNDER_TYPE_ORDER
    ]

    if unknown_types:
        print("\nWarning: These funder types are not in the predefined category order:")
        for funder_type in unknown_types:
            print(f"- {funder_type}")

    final_order = FUNDER_TYPE_ORDER + sorted(unknown_types)

    type_df = (
        grouped
        .reindex(final_order, fill_value=0)
        .reset_index()
        .rename(columns={"index": "Type"})
    )

    total = type_df["Article Mentions"].sum()

    if total > 0:
        type_df["Share"] = type_df["Article Mentions"] / total
    else:
        type_df["Share"] = 0

    return type_df


def make_funder_country_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates Top 5 funder countries by Article Mentions.
    All remaining countries are grouped into Other.
    """
    country_df = (
        df.groupby("Country of Origin", as_index=False)["Article Mentions"]
        .sum()
        .sort_values(
            by=["Article Mentions", "Country of Origin"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    top_5_country_df = country_df.head(5).copy()
    other_count = country_df.iloc[5:]["Article Mentions"].sum()

    if other_count > 0:
        other_row = pd.DataFrame(
            [
                {
                    "Country of Origin": "Other",
                    "Article Mentions": other_count,
                }
            ]
        )

        top_5_country_df = pd.concat(
            [top_5_country_df, other_row],
            ignore_index=True,
        )

    total = top_5_country_df["Article Mentions"].sum()

    if total > 0:
        top_5_country_df["Share"] = (
            top_5_country_df["Article Mentions"] / total
        )
    else:
        top_5_country_df["Share"] = 0

    return top_5_country_df


def format_percentages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts Share column to readable percentage format.
    """
    df = df.copy()

    if "Share" in df.columns:
        df["Share"] = (df["Share"] * 100).round(1).astype(str) + "%"

    if "Article Mentions" in df.columns:
        df["Article Mentions"] = df["Article Mentions"].astype(int)

    return df


def write_output(
    combined_df: pd.DataFrame,
    top_5_df: pd.DataFrame,
    type_df: pd.DataFrame,
    country_df: pd.DataFrame,
    output_file: str,
):
    """
    Writes summary tables to Excel.
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        format_percentages(top_5_df).to_excel(
            writer,
            sheet_name="Top 5 Funders",
            index=False,
        )

        format_percentages(type_df).to_excel(
            writer,
            sheet_name="By Funder Type",
            index=False,
        )

        format_percentages(country_df).to_excel(
            writer,
            sheet_name="Top 5 Funder Countries",
            index=False,
        )

        combined_df.to_excel(
            writer,
            sheet_name="Cleaned Combined Data",
            index=False,
        )

    print("\nDone.")
    print(f"Summary tables saved to: {output_path}")


def process_summary_tables(
    input_file: str,
    output_file: str,
    sheet_name: Optional[str] = None,
):
    """
    Full processing workflow.
    """
    df = read_input_file(input_file, sheet_name=sheet_name)
    df = clean_data(df)

    print(f"\nRows after cleaning: {len(df)}")
    print(f"Total Article Mentions counted: {df['Article Mentions'].sum()}")

    combined_df = combine_duplicate_funders(df)

    print(f"Unique funders after duplicate combination: {len(combined_df)}")

    top_5_df = make_top_5_table(combined_df)
    type_df = make_funder_type_table(combined_df)
    country_df = make_funder_country_table(combined_df)

    write_output(
        combined_df=combined_df,
        top_5_df=top_5_df,
        type_df=type_df,
        country_df=country_df,
        output_file=output_file,
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create funder summary tables from cleaned funder classification data."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to cleaned funder dataset.",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Path to output Excel file.",
    )

    parser.add_argument(
        "--sheet",
        required=False,
        default=None,
        help="Optional Excel sheet name to process.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    process_summary_tables(
        input_file=args.input,
        output_file=args.output,
        sheet_name=args.sheet,
    )