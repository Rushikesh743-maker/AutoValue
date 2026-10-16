import sqlite3
import pandas as pd

conn = sqlite3.connect("data/autovalue.db")
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print(f"Tables in data/autovalue.db: {tables}")

for t in tables:
    cursor.execute(f"SELECT count(*) FROM {t};")
    cnt = cursor.fetchone()[0]
    print(f"Table '{t}': {cnt} records")

# Inspect sources
if "sources" in tables:
    df_src = pd.read_sql_query("SELECT * FROM sources;", conn)
    print("\nSources table:")
    print(df_src)

# Inspect collection_runs
if "collection_runs" in tables:
    df_runs = pd.read_sql_query("SELECT * FROM collection_runs;", conn)
    print("\nCollection runs table:")
    print(df_runs)

# Inspect car_listings
if "car_listings" in tables:
    df_listings = pd.read_sql_query("SELECT id, listing_id, source, brand, model, year, listed_price, is_duplicate_candidate, date_collected, listing_url FROM car_listings LIMIT 5;", conn)
    print("\nCar listings sample (first 5):")
    print(df_listings)

    cursor.execute("SELECT count(DISTINCT source) FROM car_listings;")
    print("Unique sources in car_listings:", cursor.fetchone()[0])
    cursor.execute("SELECT source, count(*) FROM car_listings GROUP BY source;")
    print("Counts by source:")
    for r in cursor.fetchall():
        print(f"  {r[0]}: {r[1]}")

conn.close()
