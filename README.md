# The Future of Bioethics - International Comparators of Funding

## Search Strategy
The dataset was constructed using Scopus Advanced Search to identify publications that explicitly self-identify with bioethics or closely related named ethics subfields. The search focused on terms such as bioethic*, medical ethic*, clinical ethic*, research ethic*, public health ethic*, global health ethic*, and neuroethic* in the title, abstract, or keywords.

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
After each Scopus search was completed, the search results were exported with the metadata fields required for bibliometric, affiliation, keyword, and funding analysis. The selected export fields included citation information, bibliographic information, abstracts and keywords, and funding details.

The exported citation fields included author names, document title, year, EID, source title, DOI, citation count, source/document type, publication stage, and open access status. Bibliographic fields included affiliations, serial identifiers, publisher, editor information, language of the original document, and correspondence address. Abstract and keyword fields included the abstract, author keywords, and indexed keywords. Funding fields included funding number, funding acronym, funding sponsor, and funding text.

These fields were exported so that the downstream Python workflows could identify first- and last-author affiliations, screen country-specific records, extract and normalize funder names, and support later bibliometric or keyword-based analyses.

## Preliminary Selection
The preliminary first- and last-author affiliation screening workflow is stored in:

scripts/affiliation_screening_script.py

This script reads raw Scopus export files, identifies the first and last authors, extracts their institutional affiliation information, and flags whether either author is affiliated with an institution in the country of interest. The output is a compact screening file with five columns: first author, first-author affiliation, last author, last-author affiliation, and the relevant country-specific affiliation indicator, such as Chinese Affiliation, American Affiliation, British Affiliation, or South African Affiliation.

This step was used to create a more focused country-specific dataset before downstream funding analysis.

## Funder Mentions

The funder cleaning and normalization workflow is stored in:

scripts/funder_cleaning_script.py

This script takes the screened country-year datasets, filters to retained articles, extracts Scopus funding details, standardizes funder names, removes repeated acronym variants, deduplicates funders within each article, and generates article-level funder counts.

The main output is an Excel file for each country-year dataset. The primary sheet contains three columns:
    Raw Variants Normalized
    Funder
    Articles Funded

The script also produces supporting sheets for auditability, including article-level funder transformations, normalization review, summary statistics, and method notes.