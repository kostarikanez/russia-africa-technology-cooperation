# Project Workflow and Reproducibility

## 1. Overview

The research project combines bilateral trade analysis, technology readiness assessment, country clustering and country-sector case studies to identify opportunities for Russia–Africa technology cooperation.

The analytical workflow consists of five interconnected stages:

1. Data collection and preparation.
2. Russia–Africa trade analysis.
3. Technology readiness assessment.
4. Identification of country-sector cooperation opportunities.
5. Final cooperation mapping and interpretation.

The scripts are organized by analytical function under the `scripts/` directory.

## 2. Data Collection

**Directory:** `scripts/data_collection/`

The data collection stage prepares country-level and bilateral trade datasets.

Main scripts:

- `extract_baci.py` — extracts Russia–Africa bilateral trade flows and product-level trade data.
- `prepare_baci_countries.py` — prepares the country reference dataset.
- `extract_wdi.py` — processes World Development Indicators.
- `extract_wgi.py` — processes Worldwide Governance Indicators.
- `extract_itu.py` — processes digital infrastructure indicators.
- `extract_unesco.py` — processes science and education indicators.
- `extract_unido.py` — processes industrial development indicators.
- `extract_wipo.py` — processes intellectual property indicators.
- `extract_afdb.py` — processes African Development Bank indicators.

The BACI extraction script produces:

- `baci_russia_africa_annual.csv`
- `baci_russia_africa_products.csv`

Other extraction scripts generate corresponding processed datasets in `data/processed/`.

Original source datasets are not distributed with this repository. Their availability and required file paths must be checked before executing the extraction scripts.

## 3. Russia–Africa Trade Analysis

**Directory:** `scripts/trade_analysis/`

This stage examines bilateral trade dynamics, commodity composition, technology-related product flows and the persistence of trade relationships.

Main scripts:

- `build_russia_africa_trade_analysis.py` — calculates aggregate trade indicators, country and product structures, and concentration measures.
- `build_russia_africa_trade_visuals.py` — generates trade visualizations.
- `analyze_technology_trade_products.py` — analyzes trade in HS84–90 product categories.
- `audit_technology_trade_stability.py` — evaluates the persistence of selected technology-related product flows.
- `build_trade_technology_matrix.py` — combines trade data with country clusters and technology gaps.
- `build_trade_technology_slide.py` — generates additional presentation-oriented visualizations.

The analysis relies primarily on the processed BACI datasets.

## 4. Technology Readiness Assessment

**Directory:** `scripts/technology_index/`

This stage constructs a country-year panel and evaluates enabling conditions for technological development.

Recommended analytical sequence:

1. `build_country_year_panel.py` — constructs the raw country-year panel from processed indicator datasets.
2. `build_technology_readiness_index.py` — normalizes indicators and calculates the composite index.
3. `cluster_african_countries.py` — groups countries according to their technology readiness profiles.
4. `build_technology_gap_matrix.py` — identifies the weakest dimensions of technological development.
5. `visualize_africa_technology_index.py` — produces visual representations of the results.

Key outputs include:

- `country_year_panel_raw.csv`
- `country_year_panel_normalized.csv`
- `country_clusters.csv`
- `country_technology_gaps.csv`
- `cluster_profiles.csv`
- `clustering_metrics.csv`

The index measures enabling conditions for technological development rather than actual technological output or demonstrated technology transfer.

## 5. Country-Sector Cooperation Analysis

**Directory:** `scripts/cooperation_cases/`

This stage connects trade evidence with country-level technological and institutional profiles.

The workflow includes:

- `mnts_top15_case_selection.py` — selects priority country-sector combinations from the casebook.
- `build_mnts_country_sector_casebook.py` — constructs a country-sector casebook using a priority shortlist, product-level evidence and technology classification data.
- `audit_technology_product_persistence.py` — evaluates the persistence of selected technology-related product relationships.
- `final_cases.py` — prepares the final case matrix and supporting product evidence.
- `build_final_cooperation_map_log.py` — generates the final logarithmic cooperation map.

The casebook construction script expects intermediate datasets, including:

- `mnts_priority_shortlist.csv` or an enriched version of this shortlist;
- `candidate_product_evidence_2002_2023.csv`;
- `candidate_product_evidence_2019_2023.csv`;
- `mnts_candidates_technology_classified.csv`.

These files are expected under the `reports/mnts_cooperation_priority/` directory structure.

They are intermediate research outputs and are not guaranteed to be available in a clean repository checkout.

## 6. Final Cooperation Mapping

The final cooperation map combines:

- technology-related bilateral trade data;
- country technology readiness profiles;
- country clustering results;
- the persistence of trade relationships.

The map is designed as an analytical tool for identifying differentiated cooperation opportunities rather than as a definitive ranking of investment attractiveness.

Its interpretation should account for the differences between trade intensity, persistence of trade links and national technological capabilities.

## 7. Reproducibility and Data Limitations

Full reproduction of the research requires access to original source datasets and certain intermediate analytical outputs.

The repository provides selected Python scripts, processed analytical outputs, visualizations and methodological documentation. It does not contain every original dataset or every intermediate file generated during the research process.

Users attempting to reproduce the analysis should:

1. Install the dependencies listed in `requirements.txt`.
2. Obtain the required original datasets from their respective providers.
3. Recreate the expected directory structure.
4. Run the data preparation scripts.
5. Generate the analytical outputs in the appropriate sequence.
6. Check the availability of intermediate files required by the country-sector casebook workflow.

The scripts are organized by analytical stage. Not every script is required to reproduce the final published figures, and some scripts perform additional validation or presentation-oriented tasks.

## 8. Research Scope and Interpretation

The project uses HS84–90 as a broad analytical proxy for technology-related trade. This classification does not constitute an official high-technology product classification.

Trade flows alone cannot demonstrate technology transfer, local production, localization or joint research and development.

The technology readiness index is a composite proxy based on economic, digital, scientific, industrial and institutional indicators. Missing observations should not be interpreted as evidence of low technological potential.

The results should therefore be interpreted as an exploratory quantitative assessment of potential cooperation opportunities.
