# Factor Sources

The registry is source-aware and does not substitute across regions, units, scopes, or years.

- UK Government, *Greenhouse gas reporting: conversion factors 2026*, flat file revised July 2026: https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2026
- US EPA, *eGRID detailed data*, eGRID2023 revision 2: https://www.epa.gov/egrid/detailed-data

The UK rows preserve the workbook's aggregate `kg CO2e` values. The eGRID row preserves the `SRL23` subregion acronym and converts the official annual CO2-equivalent output rate from `lb/MWh` to `kg/kWh` using the exact unit conversion `lb * 0.45359237 / 1000`.

The source workbooks are downloaded locally for extraction but are ignored from version control because of their size. The committed registry retains the source URL, year, region, methodology, and factor type for every integrated row.