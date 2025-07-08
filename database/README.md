# Database

## Overview
This database follows a medallion architecture with three layers: Bronze (raw/staging), Silver (conformed/relationships), and Gold (business-ready). The system includes committee member management with SCD2 patterns and user fact tracking.

## Bronze Layer
Bronze is a data pipeline framework that handles raw data ingestion and staging in PostgreSQL. It provides a structured way to extract data from various sources, transform it into a consistent format, and load it into staging tables.

## Silver Layer
Silver contains cleaned and validated data with proper relationships and constraints. Includes fact data, committee member data and personal checkup history using SCD2 patterns.

## Gold Layer
Gold contains business-ready aggregated data optimized for specific custom_tools.
