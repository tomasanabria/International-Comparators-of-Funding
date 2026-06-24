# The Future of Bioethics - International Comparators of Funding

## Running the Code
Before running the scripts, install the required Python packages:
    python -m pip install pandas openpyxl

**All commands should be run from the main repository folder**:
    cd /workspaces/The-Future-of-Bioethics

## Search Strategy
The dataset was constructed using Scopus Advanced Search to identify publications that explicitly self-identify with bioethics or closely related named ethics subfields. The search focused on terms such as "bioethic*", "medical ethic*", "clinical ethic*", "research ethic*", "public health ethic*", "global health ethic*", and "neuroethic*" in the title, abstract, or keywords.

This search strategy was designed to prioritize precision and reproducibility. It captures a conservative baseline of publications that present themselves as part of bioethics or a closely related ethics subfield, rather than all biomedical publications that mention ethics, consent, or review procedures in passing.

The general Scopus query template was:

TITLE-ABS-KEY(
    bioethic* OR "medical ethic*" OR "clinical ethic*" OR "research ethic*"
    OR "public health ethic*" OR "global health ethic*" OR neuroethic*
)
AND PUBYEAR > [YEAR BEFORE YEAR OF INTEREST]
AND PUBYEAR < [YEAR AFTER YEAR OF INTEREST]
AND (
    LIMIT-TO(AFFILCOUNTRY, "[COUNTRY OF INTEREST]")
)

The year and country parameters were changed for each country-year dataset. The Scopus country filter was used to generate an initial candidate set, but because Scopus includes a publication under a country if any author has an affiliation there, an additional screening step was applied after export.

## Exportation Parameters
After each Scopus search was completed, the search results were exported with the metadata fields required for bibliometric, affiliation, keyword, and funding analysis. These were the following parameters

<p align="center">
  <img src="Other/Exportation Parameters.png" alt="Scopus export parameters" width="600">
</p>

These fields were exported so that the downstream Python workflows could identify first- and last-author affiliations, screen country-specific records, extract and normalize funder names, and support later bibliometric or keyword-based analyses.

## Preliminary Selection
The Python code for the preliminary slection is stored in:

**scripts/affiliation_screening_script.py**

This script reads **.xlsx files that need to be reexported from the Scopus .csv export files**. It identifies the first and last authors, extracts their institutional affiliation information, and flags whether either author is affiliated with an institution in the country of interest. The output is a compact screening file with five columns: first author, first-author affiliation, last author, last-author affiliation, and the relevant country-specific affiliation indicator, such as Chinese Affiliation, American Affiliation, British Affiliation, or South African Affiliation.

**General command template**: python Scripts/affiliation_screening_script.py --input "Data/[FILE NAME].xlsx" --output "Data/[COUNTRY] - Screened Data - [YEAR].xlsx" --country "[COUNTRY]"

Example for China 2020: python Scripts/affiliation_screening_script.py --input "Data/China - Raw Data - 2020.xlsx" --output "Data/China - Screened Data - 2020.xlsx" --country China

This step was used to create a more focused country-specific dataset before downstream funding analysis.

## Funder Mentions
The Python code for the funder cleaning and normalization workflow is stored in:

**scripts/funder_cleaning_script.py**

This script takes the screened country-year datasets, filters to retained articles, extracts Scopus funding details, standardizes funder names, removes repeated acronym variants, deduplicates funders within each article, and generates article-level funder counts.

The main output is an Excel file for each country-year dataset. The primary sheet contains three columns: Raw Variants Normalized, Funder, Articles Funded

The script also produces supporting sheets for auditability, including article-level funder transformations, normalization review, summary statistics, and method notes.

**General command template**: python Scripts/funder_cleaning_script.py --input "Data/[FILE NAME].xlsx" --year [YEAR]

Example for 2020: python Scripts/funder_cleaning_script.py --input "Data/Data Set 2020.xlsx" --year 2020