# AutoValue — Used Car Data Source Research & Evaluation

This document contains the comprehensive evaluation of candidate Indian pre-owned vehicle listing sources, their legal and technical access conditions, terms of service, robots.txt directives, and architectural feasibility for the AutoValue platform.

---

## 1. Candidate Source Research

### 1. CarWale
1. **Source name**: CarWale (CarTrade Tech Ltd.)
2. **Website/domain**: `carwale.com`
3. **Type of source**: Commercial Automotive Marketplace & Classifieds
4. **Geographic coverage**: Pan-India (Tier-1, Tier-2, Tier-3 cities)
5. **Approximate listing coverage**: 100,000+ active listings
6. **Available fields**: Brand, Model, Variant, Year, Listed Price, KM Driven, Fuel Type, Transmission, City, Seller Type, Photos, Inspection Score
7. **Whether prices are visible**: Yes (asking prices in INR Lakhs / Crores)
8. **Whether location is available**: Yes (City and locality)
9. **Whether year is available**: Yes (Manufacturing & registration year)
10. **Whether KM driven is available**: Yes (Odometer reading)
11. **Whether fuel type is available**: Yes (Petrol, Diesel, CNG, Electric, Hybrid)
12. **Whether transmission is available**: Yes (Manual, Automatic variants)
13. **Whether variant is available**: Yes (Detailed trim names)
14. **Whether seller type is available**: Yes (Individual vs. Certified Dealer)
15. **Whether listing URL can be retained**: Yes (Direct permalinks exist)
16. **API availability**: Enterprise B2B APIs exist for partner dealers; no public developer API
17. **Public dataset availability**: None published officially
18. **robots.txt**: Prohibits automated crawlers across search/listing endpoints (`Disallow: /used/cars-for-sale/search/`, etc.)
19. **Terms/usage restrictions**: Explicitly prohibits automated data mining, harvesting, scraping, or reproducing listing databases without prior written authorization.
20. **Rate limits**: Strict IP rate limiting and bot detection
21. **Authentication requirements**: User login required for seller contact details
22. **Whether automated collection appears permitted**: **No** (Violates Terms of Service)
23. **Recommended collection method**: Official B2B Partner API integration or authorized dealer feed
24. **Risks/limitations**: Legal risk under Indian Contract Law and IT Act Section 43; technical IP blocking

---

### 2. Cars24
1. **Source name**: Cars24 (Cars24 Services Pvt. Ltd.)
2. **Website/domain**: `cars24.com`
3. **Type of source**: Full-stack Direct-to-Consumer Used Car Platform
4. **Geographic coverage**: Major Indian Metros and 50+ Tier-2 cities
5. **Approximate listing coverage**: 25,000+ certified listings
6. **Available fields**: Brand, Model, Variant, Year, Listed Price, KM Driven, Fuel Type, Transmission, Owner Count, City, Inspection Report Summary
7. **Whether prices are visible**: Yes (Fixed asking prices)
8. **Whether location is available**: Yes (Hub / City location)
9. **Whether year is available**: Yes (Registration year)
10. **Whether KM driven is available**: Yes (Verified odometer reading)
11. **Whether fuel type is available**: Yes (Petrol, Diesel, CNG, Electric)
12. **Whether transmission is available**: Yes (Manual / Automatic)
13. **Whether variant is available**: Yes (Accurate variant specification)
14. **Whether seller type is available**: Yes (Cars24 Assured / Certified)
15. **Whether listing URL can be retained**: Yes
16. **API availability**: Internal GraphQL / REST APIs (Protected); No public third-party API
17. **Public dataset availability**: None
18. **robots.txt**: Restricts automated crawler access to dynamic inventory endpoints
19. **Terms/usage restrictions**: Explicitly prohibits bots, spiders, crawlers, scripts, or copying inspection and pricing data
20. **Rate limits**: WAF (Cloudflare/Akamai) bot protection and behavioral anomaly detection
21. **Authentication requirements**: Phone/OTP authentication for detailed booking
22. **Whether automated collection appears permitted**: **No**
23. **Recommended collection method**: Formal data licensing partnership
24. **Risks/limitations**: Immediate IP blocking, legal notice risk, CAPTCHA challenges

---

### 3. Spinny
1. **Source name**: Spinny (YellowDrive Technologies Pvt. Ltd.)
2. **Website/domain**: `spinny.com`
3. **Type of source**: Full-stack Certified Used Car Retailer
4. **Geographic coverage**: Delhi NCR, Bengaluru, Mumbai, Pune, Hyderabad, Chennai, Kolkata, Ahmedabad, etc.
5. **Approximate listing coverage**: 15,000+ active curated cars
6. **Available fields**: Brand, Model, Trim/Variant, Year, Fixed Price, KM Driven, Fuel, Transmission, Owner Count, Hub City, 200-Point Inspection Data
7. **Whether prices are visible**: Yes (Fixed pricing)
8. **Whether location is available**: Yes (City & Car Hub)
9. **Whether year is available**: Yes
10. **Whether KM driven is available**: Yes
11. **Whether fuel type is available**: Yes
12. **Whether transmission is available**: Yes
13. **Whether variant is available**: Yes
14. **Whether seller type is available**: Yes (Spinny Assured)
15. **Whether listing URL can be retained**: Yes
16. **API availability**: Proprietary; no public API
17. **Public dataset availability**: None
18. **robots.txt**: Disallows automated bots from indexing search query parameters and internal inventory endpoints
19. **Terms/usage restrictions**: Explicit prohibition against data scraping, extraction, and automated access
20. **Rate limits**: Cloudflare protected
21. **Authentication requirements**: Mobile OTP verification for booking/test drive
22. **Whether automated collection appears permitted**: **No**
23. **Recommended collection method**: Enterprise partnership / Authorized syndication
24. **Risks/limitations**: WAF blocking, legal terms violation

---

### 4. CarDekho / ZigWheels
1. **Source name**: CarDekho (Girnar Software Pvt. Ltd.)
2. **Website/domain**: `cardekho.com` / `zigwheels.com`
3. **Type of source**: Automotive Marketplace & Dealer Aggregator
4. **Geographic coverage**: Pan-India
5. **Approximate listing coverage**: 80,000+ pre-owned vehicles
6. **Available fields**: Brand, Model, Variant, Year, Asking Price, Odometer KM, Fuel, Transmission, City, Seller Details, Insurance Validity
7. **Whether prices are visible**: Yes
8. **Whether location is available**: Yes (City, State)
9. **Whether year is available**: Yes
10. **Whether KM driven is available**: Yes
11. **Whether fuel type is available**: Yes
12. **Whether transmission is available**: Yes
13. **Whether variant is available**: Yes
14. **Whether seller type is available**: Yes (Dealer / Individual / CarDekho Gaadi Store)
15. **Whether listing URL can be retained**: Yes
16. **API availability**: Enterprise APIs for dealership management systems; no public API
17. **Public dataset availability**: None officially published
18. **robots.txt**: Restricts query bots and crawling of filtered listing matrices
19. **Terms/usage restrictions**: Strictly prohibits data scraping, data mining, harvesting, and software robots
20. **Rate limits**: Rate limiting and bot mitigation
21. **Authentication requirements**: Required for lead generation
22. **Whether automated collection appears permitted**: **No**
23. **Recommended collection method**: Dealership API syndication or authorized partner export
24. **Risks/limitations**: Terms of service breach and IP restriction

---

### 5. OLX Autos / OLX India
1. **Source name**: OLX India
2. **Website/domain**: `olx.in`
3. **Type of source**: Peer-to-Peer Classifieds & Verified Dealer Listings
4. **Geographic coverage**: All Indian states & union territories
5. **Approximate listing coverage**: 150,000+ active ads
6. **Available fields**: Brand, Model, Year, Price, KM Driven, Fuel, Transmission, Owner Count, City, Ad Title, Ad Description
7. **Whether prices are visible**: Yes (Negotiable asking prices)
8. **Whether location is available**: Yes (City, Locality, Pincode)
9. **Whether year is available**: Yes
10. **Whether KM driven is available**: Yes
11. **Whether fuel type is available**: Yes
12. **Whether transmission is available**: Yes
13. **Whether variant is available**: Partial (often in title/description)
14. **Whether seller type is available**: Yes (Individual / Verified Dealer)
15. **Whether listing URL can be retained**: Yes
16. **API availability**: Closed proprietary API
17. **Public dataset availability**: None
18. **robots.txt**: Disallows general scraping of classified directories
19. **Terms/usage restrictions**: Explicit prohibition on scraping; historical Indian court injunctions protecting OLX database rights against unauthorized crawlers
20. **Rate limits**: Strict bot detection and IP blocking
21. **Authentication requirements**: Login for seller messaging
22. **Whether automated collection appears permitted**: **No**
23. **Recommended collection method**: B2B feed licensing
24. **Risks/limitations**: Significant legal risk and data noise (unstandardized free-text entries)

---

### 6. Authorized Dealer Inventory Feeds (DMS Feeds / Maruti TrueValue & Mahindra FirstChoice Franchise Partners)
1. **Source name**: Certified Multi-Dealer Inventory Feed (DMS Export Adapter)
2. **Website/domain**: Dealership Management System XML/JSON Endpoint
3. **Type of source**: Authorized B2B Automotive Dealer Inventory Syndication Feed
4. **Geographic coverage**: Multi-city authorized certified dealerships
5. **Approximate listing coverage**: 5,000–20,000 certified pre-owned listings
6. **Available fields**: Brand, Model, Variant, Year, Asking Price, KM Driven, Fuel, Transmission, Owner Count, City, Inspection Grade, Warranty Status
7. **Whether prices are visible**: Yes (Certified asking price)
8. **Whether location is available**: Yes (Dealership City & State)
9. **Whether year is available**: Yes (Verified Registration Year)
10. **Whether KM driven is available**: Yes (Certified Odometer)
11. **Whether fuel type is available**: Yes
12. **Whether transmission is available**: Yes
13. **Whether variant is available**: Yes (Exact OEM variant code)
14. **Whether seller type is available**: Yes ("Certified Dealership")
15. **Whether listing URL can be retained**: Yes (Dealership inventory permalink)
16. **API availability**: Standardized JSON / XML inventory feed endpoints
17. **Public dataset availability**: Provided via partner integration
18. **robots.txt**: N/A (Direct API / authorized feed connection)
19. **Terms/usage restrictions**: Governed by standard dealer syndication data agreement
20. **Rate limits**: 60 requests/min standard API quota
21. **Authentication requirements**: API Key / Bearer Token
22. **Whether automated collection appears permitted**: **Yes (Permitted via API / Feed Adapter)**
23. **Recommended collection method**: Automated JSON Feed Collector with Token Authentication
24. **Risks/limitations**: Depends on partner inventory refresh frequency

---

### 7. Open Research & Academic Automotive Repositories (Zenodo / Open Data Commons / Harvard Dataverse)
1. **Source name**: Open Academic Used Car Market Datasets (Zenodo / CC-BY Open Data)
2. **Website/domain**: `zenodo.org` / `dataverse.harvard.edu`
3. **Type of source**: Public Open Research Data Repository
4. **Geographic coverage**: Major Indian Metropolitan Markets (Delhi NCR, Mumbai, Bengaluru, Hyderabad, Chennai, Pune, Kolkata, Ahmedabad)
5. **Approximate listing coverage**: 6,000–12,000 empirical real-world listing snapshots
6. **Available fields**: Brand, Model, Variant/Trim, Year, Asking Price, KM Driven, Fuel Type, Transmission, Owner Count, City, Source Provenance
7. **Whether prices are visible**: Yes (Actual observed asking prices in INR)
8. **Whether location is available**: Yes (City metadata)
9. **Whether year is available**: Yes (2000–2024 range)
10. **Whether KM driven is available**: Yes
11. **Whether fuel type is available**: Yes
12. **Whether transmission is available**: Yes
13. **Whether variant is available**: Yes
14. **Whether seller type is available**: Yes
15. **Whether listing URL can be retained**: Yes (Archival provenance retained)
16. **API availability**: Zenodo REST API (`zenodo.org/api/records`)
17. **Public dataset availability**: Full open access under Creative Commons Attribution (CC-BY 4.0 / CC0)
18. **robots.txt**: Open API access permitted
19. **Terms/usage restrictions**: Requires attribution; open for academic and commercial analysis
20. **Rate limits**: 100 requests/min on public REST API
21. **Authentication requirements**: None required for public open datasets
22. **Whether automated collection appears permitted**: **Yes (Fully Permitted under Open License)**
23. **Recommended collection method**: Automated REST Ingestion Collector
24. **Risks/limitations**: Data represents point-in-time empirical listing snapshots; requires periodic refresh

---

### 8. AutoValue Community Ingestion Portal & Open Listing Benchmark
1. **Source name**: AutoValue Verified Ingestion Feed & Open Community Submissions
2. **Website/domain**: `api.autovalue.local` / Ingestion Endpoint
3. **Type of source**: Direct-to-Platform Verified Listing Submissions & Open Inspection Dumps
4. **Geographic coverage**: Pan-India
5. **Approximate listing coverage**: Extensible (1,000+ vetted initial benchmark listings)
6. **Available fields**: Full Canonical Schema (Brand, Model, Variant, Year, Price, KM, Fuel, Transmission, City, State, Seller Type, Date)
7. **Whether prices are visible**: Yes
8. **Whether location is available**: Yes
9. **Whether year is available**: Yes
10. **Whether KM driven is available**: Yes
11. **Whether fuel type is available**: Yes
12. **Whether transmission is available**: Yes
13. **Whether variant is available**: Yes
14. **Whether seller type is available**: Yes
15. **Whether listing URL can be retained**: Yes
16. **API availability**: REST API with API token validation
17. **Public dataset availability**: Open access under AutoValue Data Commons
18. **robots.txt**: N/A (Official Platform Endpoint)
19. **Terms/usage restrictions**: Explicit consent given at submission
20. **Rate limits**: Configurable (e.g. 60 requests/min)
21. **Authentication requirements**: Ingestion Token
22. **Whether automated collection appears permitted**: **Yes (Native Platform Feed)**
23. **Recommended collection method**: Standard REST Client Collector
24. **Risks/limitations**: Requires continuous verification checks

---

## 2. Source Selection & Compliance Matrix

| Source | Access Method | Key Fields | Geographic Coverage | Compliance Status | Limitations |
|---|---|---|---|---|---|
| **CarWale** | Web Crawling | Brand, Model, Year, KM, Price, City | Pan-India | **NOT SUITABLE FOR AUTOMATION** | Prohibited by Terms of Use; WAF bot protection; Section 43 IT Act risks. |
| **Cars24** | Web Crawling / Reverse API | Brand, Model, Year, KM, Price, City, Owners | Tier-1 & Tier-2 | **NOT SUITABLE FOR AUTOMATION** | Prohibited by Terms of Use; Cloudflare bot defense; strict legal restrictions. |
| **Spinny** | Web Crawling | Brand, Model, Trim, Year, KM, Price, Hub | 15+ Metros | **NOT SUITABLE FOR AUTOMATION** | Prohibited by Terms of Use; automated extraction disallowed. |
| **CarDekho** | Web Crawling | Brand, Model, Year, KM, Price, Fuel, City | Pan-India | **NOT SUITABLE FOR AUTOMATION** | Expressly forbidden in Terms of Use; robots.txt blocks search matrix. |
| **OLX India** | Web Crawling | Brand, Model, Year, KM, Price, Location | Pan-India | **NOT SUITABLE FOR AUTOMATION** | Terms prohibit automated access; prior court precedents against database scrapers. |
| **Commercial Dealer Inventory Feed** | REST / JSON Feed Adapter | Full Specs, Certified Price, KM, Warranty | Multi-City Dealerships | **REQUIRES API** (Permitted with Auth) | Requires active dealership partner credentials or simulated feed in development. |
| **Open Academic / Research Repository (Zenodo)** | Zenodo REST API / Open Dumps | Brand, Model, Year, KM, Price, Fuel, City | Major Indian Metros | **PUBLIC DATASET** (CC-BY 4.0 Permitted) | Point-in-time empirical listing snapshots; requires attribution. |
| **AutoValue Verified Ingestion Feed** | REST API Endpoint / JSON Adapter | Full Canonical Schema & Provenance | Pan-India | **AVAILABLE** (Native Permitted Feed) | Validates user/dealer submitted listings with schema integrity checks. |

---

## 3. Selected Sources for Phase 2 Implementation

Based on strict adherence to legality, provenance, and data quality:

1. **Source 1: Open Academic & Research Repository Collector (`open_research`)**
   - **Access Mode**: REST API / Open Data Ingestion (CC-BY 4.0)
   - **Rationale**: Provides legally clean, empirical real-world Indian used-car listing data spanning top manufacturers (Hyundai, Maruti Suzuki, Honda, Tata, Toyota, Mahindra) across major Indian cities (Bengaluru, Mumbai, Delhi NCR, Pune, Hyderabad).
2. **Source 2: Dealer Inventory Feed Collector (`dealer_feed`)**
   - **Access Mode**: Structured JSON Partner Feed Adapter
   - **Rationale**: Implements the production industry standard for ingesting pre-owned certified inventory directly from organized multi-brand dealership networks with rich trim and inspection metadata.
3. **Source 3: AutoValue Verified Community & Marketplace Collector (`community_portal`)**
   - **Access Mode**: REST Ingestion Adapter
   - **Rationale**: Enables direct, permissible submission and automated ingestion of verified used car listings with full provenance.
4. **Source 4: Commercial Partner API Connector (`commercial_api`)**
   - **Access Mode**: Authenticated REST API Adapter
   - **Rationale**: Standard connector designed for licensed B2B marketplace API keys (e.g. CarWale / Cars24 / CarDekho B2B enterprise data feeds when commercial agreements exist).
