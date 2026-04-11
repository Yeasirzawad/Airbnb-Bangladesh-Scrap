# Airbnb Market Analysis in Bangladesh

This project explores the Airbnb market in Bangladesh by building a custom web scraping pipeline to collect listing, host, and review data directly from Airbnb. The goal was to turn a fragmented marketplace into a structured dataset that could be analyzed for pricing behavior, host patterns, guest experience, and short-term rental market dynamics.

## Why this project matters

Airbnb listings contain rich information, but it is scattered across search pages, listing pages, host profiles, and reviews. This project brings those sources together into a single analysis-ready dataset to answer questions like:

- How are listings priced across Bangladesh?
- What amenities and listing features appear most often?
- How concentrated is supply among hosts?
- What host characteristics and review signals may influence guest perception?

Rather than analyzing a few listings manually, I built a repeatable scraping workflow that captures market data at scale.

## Project impact

This project produced a multi-source Airbnb dataset for Bangladesh by combining:

- **1,578 host links** extracted from listing data
- **879 host-level records** scraped from Airbnb host pages
- **1,853 merged listing-host records**
- **28 variables** in the merged dataset
- **735 distinct host names** after consolidation

These outputs made it possible to move from raw web pages to structured market analysis and host-level profiling.

## What I built

I developed a Selenium-based scraping pipeline in Python that collects data in stages:

1. **Listing discovery**
   - Searches Airbnb locations in Bangladesh
   - Collects listing URLs across result pages

2. **Listing-level extraction**
   - Price per night
   - Review count and review links
   - Host profile link
   - Listing description
   - Category-level ratings such as cleanliness, accuracy, communication, location, and value
   - Google Maps location link
   - Facilities and amenities

3. **Host-level extraction**
   - Host name
   - Host rating
   - Number of reviews
   - Hosting duration
   - Number of listings
   - Host about section
   - Confirmed host information

4. **Review-level extraction**
   - Reviewer name
   - Reviewer profile link
   - Review metadata
   - Review text and extra rating context

5. **Data merging**
   - Joined listing and host data into a consolidated analysis dataset

The core scraping logic is implemented in `functions/scrap_main.py`, which contains functions for listing scraping, listing-detail extraction, host scraping, and review scraping.

## Technical approach

The scraper is implemented with:

- **Python**
- **Selenium**
- **pandas**
- **NumPy**
- **Power BI**
- **DAX**

## Example analysis questions this dataset supports

- Which hosts control the largest share of listings?
- How do listing ratings vary across properties?
- What amenities are most common in the Bangladesh Airbnb market?
- How do host experience and hosting duration relate to listing supply?
- What can review data reveal about customer experience?


## What I learned

This project strengthened my ability to:

- build end-to-end scraping pipelines for dynamic websites
- work with multi-step web extraction across listings, hosts, and reviews
- clean and merge data from multiple scraped sources
- design datasets for downstream market analysis
- troubleshoot brittle scraping logic in changing page structures


## Future improvements

- Refactor scraping modules into smaller files
- Remove merge conflicts and duplicate functions
- Add logging and error reporting
- Parameterize locations and output paths
- Build a dashboard on top of the merged dataset
- Add sentiment analysis on reviews

## Authors

- [@Yeasirzawad](https://github.com/Yeasirzawad)
- [@mominulislam2001](https://github.com/mominulislam2001)
