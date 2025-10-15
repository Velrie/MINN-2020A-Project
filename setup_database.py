import pandas as pd
import sqlite3
import os

# Create Data folder if missing
os.makedirs("Data", exist_ok=True)

# Required CSV files (must be inside /Data)
required_files = [
    "users.csv", "roles.csv", "minerals.csv",
    "sites.csv", "countries.csv", "production_stats.csv"
]

for file in required_files:
    path = os.path.join("Data", file)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")

# Load CSV files
users_df = pd.read_csv("Data/users.csv")
roles_df = pd.read_csv("Data/roles.csv")
minerals_df = pd.read_csv("Data/minerals.csv")
sites_df = pd.read_csv("Data/sites.csv")
countries_df = pd.read_csv("Data/countries.csv")
production_stats_df = pd.read_csv("Data/production_stats.csv")

# Connect to SQLite database
conn = sqlite3.connect("Data/userdata.db")
cur = conn.cursor()

# Create tables
cur.execute("""
CREATE TABLE IF NOT EXISTS roles (
    RoleID INTEGER PRIMARY KEY,
    RoleName TEXT NOT NULL,
    Permissions TEXT NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    UserID INTEGER PRIMARY KEY,
    Username TEXT NOT NULL UNIQUE,
    PasswordHash TEXT NOT NULL,
    RoleID INTEGER,
    FOREIGN KEY(RoleID) REFERENCES roles(RoleID)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS minerals (
    MineralID INTEGER PRIMARY KEY,
    MineralName TEXT NOT NULL,
    Description TEXT NOT NULL,
    MarketPriceUSD_per_tonne REAL NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS countries (
    CountryID INTEGER PRIMARY KEY,
    CountryName TEXT NOT NULL,
    GDP_BillionUSD REAL NOT NULL,
    MiningRevenue_BillionUSD REAL NOT NULL,
    KeyProjects TEXT NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS sites (
    SiteID INTEGER PRIMARY KEY,
    SiteName TEXT NOT NULL,
    CountryID INTEGER,
    MineralID INTEGER,
    Latitude REAL NOT NULL,
    Longitude REAL NOT NULL,
    Production_tonnes REAL NOT NULL,
    FOREIGN KEY(CountryID) REFERENCES countries(CountryID),
    FOREIGN KEY(MineralID) REFERENCES minerals(MineralID)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS production_stats (
    StatID INTEGER PRIMARY KEY,
    Year INTEGER NOT NULL,
    CountryID INTEGER,
    MineralID INTEGER,
    Production_tonnes REAL NOT NULL,
    ExportValue_BillionUSD REAL NOT NULL,
    FOREIGN KEY(CountryID) REFERENCES countries(CountryID),
    FOREIGN KEY(MineralID) REFERENCES minerals(MineralID)
)
""")

# Insert data if empty
def insert_if_empty(df, table_name, columns):
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cur.fetchone()[0]
    if count == 0:
        placeholders = ','.join(['?'] * len(columns))
        for _, row in df.iterrows():
            cur.execute(
                f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})",
                tuple(row[col] for col in columns)
            )
        print(f"Inserted data into {table_name}.")
    else:
        print(f"Skipped {table_name} — already filled.")

insert_if_empty(roles_df, "roles", ["RoleID", "RoleName", "Permissions"])
insert_if_empty(users_df, "users", ["UserID", "Username", "PasswordHash", "RoleID"])
insert_if_empty(minerals_df, "minerals", ["MineralID", "MineralName", "Description", "MarketPriceUSD_per_tonne"])
insert_if_empty(countries_df, "countries", ["CountryID", "CountryName", "GDP_BillionUSD", "MiningRevenue_BillionUSD", "KeyProjects"])
insert_if_empty(sites_df, "sites", ["SiteID", "SiteName", "CountryID", "MineralID", "Latitude", "Longitude", "Production_tonnes"])
insert_if_empty(production_stats_df, "production_stats", ["StatID", "Year", "CountryID", "MineralID", "Production_tonnes", "ExportValue_BillionUSD"])

conn.commit()
conn.close()

print("✅ Database setup complete! Data loaded into Data/userdata.db.")
