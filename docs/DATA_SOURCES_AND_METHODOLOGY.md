# Data Sources and Methodology

## 1. Research Design

The study combines international trade statistics, country-level development indicators, composite index construction, clustering and selected country case studies.

The objective is to identify African countries with relevant conditions for deeper technological cooperation with Russia and to explore potential forms of such cooperation.

## 2. Data Sources

The analysis draws on the following international statistical databases:

| Source | Data used |
|---|---|
| BACI (CEPII) | Bilateral trade flows by country, year and HS product code |
| World Bank – World Development Indicators | GDP per capita (PPP), electricity access, internet use and manufacturing value added |
| Worldwide Governance Indicators | Institutional environment indicators |
| UNESCO Institute for Statistics | Scientific and research capacity indicators |
| UNIDO | Industrial development indicators |
| International Telecommunication Union | Digital infrastructure indicators |
| World Intellectual Property Organization | Innovation-related indicators and supporting context |
| African Development Bank | Additional regional economic context |

Original datasets are not redistributed in this repository. Users should consult the respective providers for access conditions and licensing requirements.

## 3. Bilateral Trade Analysis

The trade analysis covers 2000–2024 and examines:

- Total bilateral trade dynamics;
- Geographical concentration of trade;
- Commodity composition of exports and imports;
- Trade in machinery, equipment and other technology-related goods.

Trade values are analysed in current US dollars. BACI trade values are originally reported in thousands of US dollars.

### Technology-related trade

HS84–HS90 product groups are used as a broad analytical proxy for technologically significant industrial goods. HS6-level data provide a more detailed product perspective.

Trade persistence is measured through country–product–trade direction combinations observed in at least four out of five years during 2020–2024.

This measure captures the recurrence of trade relationships, not their monetary value or technological depth.

## 4. Technology Readiness Index

A composite index assesses five dimensions of the enabling environment for technological development.

| Dimension | Weight | Main indicators |
|---|---:|---|
| Economic potential | 20% | GDP per capita (PPP) |
| Digital infrastructure | 25% | Electricity access, internet use, international bandwidth |
| Scientific and technological capacity | 20% | Scientific publications per capita |
| Industrial base | 20% | Manufacturing value added as a share of GDP |
| Institutional environment | 15% | Worldwide Governance Indicators |

### Data processing

- Skewed variables are transformed using the natural logarithm of one plus the indicator value.
- Indicators are normalized using min–max scaling.
- Missing values are handled at the indicator and dimension level.
- The digital infrastructure dimension requires at least two available indicators out of three.
- The institutional dimension requires at least four available indicators out of six.
- Overall index values are calculated only when all five dimensions are available.

The index is designed to measure enabling conditions rather than actual technological output or definitive technology absorption capacity.

### Sensitivity analysis

Alternative weighting schemes are compared with the baseline index using Spearman rank correlation and top-10 country overlap.

This tests the robustness of country rankings to changes in weights, but does not establish the construct validity of the index.

## 5. Country Clustering

K-means and hierarchical clustering are used to identify groups of African countries with similar technology readiness profiles.

The number of clusters is assessed using silhouette scores, while agreement between clustering approaches is examined using the Adjusted Rand Index.

Cluster labels are assigned through interpretation of the resulting country profiles.

## 6. Cooperation Mapping

The cooperation map combines three dimensions:

- Mean technology readiness index;
- Number of persistent HS84–HS90 trade links;
- Total bilateral trade in HS84–HS90 goods.

The map is used as an exploratory framework for distinguishing potential cooperation patterns. It does not represent a definitive ranking of investment attractiveness or project feasibility.

## 7. Country Case Studies

Three countries are examined in greater detail:

- **South Africa:** diversified industrial and technology-related trade, with potential for multi-sector cooperation.
- **Algeria:** significant specialized equipment trade, with opportunities for longer-term service, maintenance and training arrangements.
- **Angola:** a mining equipment and components niche, with potential for servicing, adaptation and localization.

## 8. Methodological Limitations

Several limitations should be considered when interpreting the results:

1. HS84–HS90 is a broad analytical proxy and does not constitute an official high-technology classification.
2. Trade flows alone do not demonstrate technology transfer, localization or joint production.
3. The composite index measures enabling conditions and is sensitive to indicator availability and methodological choices.
4. Missing observations should not be interpreted as evidence of low technological potential.
5. Country clusters describe similarities within the selected sample and should not be treated as permanent country classifications.
6. The cooperation map identifies analytical opportunities, not confirmed commercial projects.

## 9. Further Research

Further work could incorporate:

- More granular high-technology product classifications;
- Foreign direct investment and production linkages;
- Technology transfer and localization agreements;
- Industrial capacity at the sector level;
- Joint research and development projects;
- Company-level and project-level evidence.

The methodology is exploratory and intended to support further applied research on Russia–Africa technological and industrial cooperation.
