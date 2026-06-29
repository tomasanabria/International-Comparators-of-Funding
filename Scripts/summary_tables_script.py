import argparse
from pathlib import Path

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


def read_input_file(input_file: str) -> pd.DataFrame:
    """
    Reads Excel, CSV, TSV, or TXT file.

    Expected input columns can be:
    - Funder
    - Articles Funded
    - Type
    - Country of Origin

    The script also accepts:
    - Funder Type
    - Funder Country

    It can handle a title row above the real header row.
    """
    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if input_path.suffix.lower() in [".xlsx", ".xls"]:
        raw_df = pd.read_excel(input_path, header=None)
    elif input_path.suffix.lower() == ".csv":
        raw_df = pd.read_csv(input_path, header=None)
    elif input_path.suffix.lower() in [".tsv", ".txt"]:
        raw_df = pd.read_csv(input_path, sep="\t", header=None)
    else:
        raise ValueError("Input file must be .xlsx, .xls, .csv, .tsv, or .txt")

    header_row_index = None

    for i in range(min(20, len(raw_df))):
        row_values = [normalize_text(x) for x in raw_df.iloc[i].tolist()]

        has_funder = "funder" in row_values
        has_articles = "articles funded" in row_values
        has_type = "type" in row_values or "funder type" in row_values
        has_country = (
            "country of origin" in row_values
            or "country" in row_values
            or "funder country" in row_values
        )

        if has_funder and has_articles and has_type and has_country:
            header_row_index = i
            break

    if header_row_index is None:
        raise ValueError(
            "Could not find a header row with Funder, Articles Funded, Type, and Country of Origin."
        )

    headers = raw_df.iloc[header_row_index].tolist()
    df = raw_df.iloc[header_row_index + 1 :].copy()
    df.columns = [str(col).strip() for col in headers]

    column_map = {}

    for col in df.columns:
        normalized = normalize_text(col)

        if normalized == "funder":
            column_map[col] = "Funder"

        elif normalized == "articles funded":
            column_map[col] = "Articles Funded"

        elif normalized in ["type", "funder type"]:
            column_map[col] = "Funder Type"

        elif normalized in ["country of origin", "country", "funder country"]:
            column_map[col] = "Funder Country"

    df = df.rename(columns=column_map)

    required_columns = [
        "Funder",
        "Articles Funded",
        "Funder Type",
        "Funder Country",
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    return df[required_columns].copy()


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans spacing, standardizes funder types, and converts Articles Funded to numeric.
    """
    df = df.copy()

    df["Funder"] = df["Funder"].astype(str).str.strip()
    df["Funder Type"] = df["Funder Type"].apply(standardize_funder_type)
    df["Funder Country"] = df["Funder Country"].astype(str).str.strip()

    df["Articles Funded"] = pd.to_numeric(
        df["Articles Funded"],
        errors="coerce",
    )

    df = df[df["Articles Funded"].notna()]
    df["Articles Funded"] = df["Articles Funded"].astype(int)

    df = df[
        df["Funder"].notna()
        & (df["Funder"].str.strip() != "")
        & (df["Funder"].str.lower().str.strip() != "nan")
    ]

    return df


def combine_duplicate_funders(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combines exact duplicate funder names by summing Articles Funded.
    """
    combined_df = (
        df.groupby("Funder", as_index=False)
        .agg(
            {
                "Articles Funded": "sum",
                "Funder Type": "first",
                "Funder Country": "first",
            }
        )
        .sort_values(
            by=["Articles Funded", "Funder"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    return combined_df


def make_top_5_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates Top 5 funders by Articles Funded.
    All remaining funders are grouped into Other.
    """
    df = df.sort_values(
        by=["Articles Funded", "Funder"],
        ascending=[False, True],
    ).reset_index(drop=True)

    top_5_df = df.head(5)[["Funder", "Articles Funded"]].copy()

    other_count = df.iloc[5:]["Articles Funded"].sum()

    if other_count > 0:
        other_row = pd.DataFrame(
            [
                {
                    "Funder": "Other",
                    "Articles Funded": other_count,
                }
            ]
        )

        top_5_df = pd.concat(
            [top_5_df, other_row],
            ignore_index=True,
        )

    total = top_5_df["Articles Funded"].sum()

    if total > 0:
        top_5_df["Share"] = top_5_df["Articles Funded"] / total
    else:
        top_5_df["Share"] = 0

    return top_5_df


def make_funder_type_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates summary table by funder type using the specified category order.
    """
    grouped = (
        df.groupby("Funder Type", as_index=True)["Articles Funded"]
        .sum()
    )

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
        .rename(columns={"index": "Funder Type"})
    )

    total = type_df["Articles Funded"].sum()

    if total > 0:
        type_df["Share"] = type_df["Articles Funded"] / total
    else:
        type_df["Share"] = 0

    return type_df


def make_funder_country_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates summary table by funder country.
    """
    country_df = (
        df.groupby("Funder Country", as_index=False)["Articles Funded"]
        .sum()
        .sort_values(
            by=["Articles Funded", "Funder Country"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    total = country_df["Articles Funded"].sum()

    if total > 0:
        country_df["Share"] = country_df["Articles Funded"] / total
    else:
        country_df["Share"] = 0

    return country_df


def format_percentages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts Share column to readable percentage format.
    """
    df = df.copy()

    if "Share" in df.columns:
        df["Share"] = (df["Share"] * 100).round(1).astype(str) + "%"

    if "Articles Funded" in df.columns:
        df["Articles Funded"] = df["Articles Funded"].astype(int)

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
            sheet_name="By Funder Country",
            index=False,
        )

        combined_df.to_excel(
            writer,
            sheet_name="Cleaned Combined Data",
            index=False,
        )

    print("\nDone.")
    print(f"Summary tables saved to: {output_path}")


def process_summary_tables(input_file: str, output_file: str):
    """
    Full processing workflow.
    """
    df = read_input_file(input_file)
    df = clean_data(df)

    print(f"\nRows after cleaning: {len(df)}")
    print(f"Total Articles Funded counted: {df['Articles Funded'].sum()}")

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

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    process_summary_tables(
        input_file=args.input,
        output_file=args.output,
    )