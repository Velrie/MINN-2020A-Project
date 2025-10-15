from flask import Flask, flash, render_template, request, redirect, url_for, session
import sqlite3
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import folium
import io
import base64
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
# -------------------------
# App Setup
# -------------------------
app = Flask(__name__)
app.secret_key = "super_secret_key_123"  # Change this to something unique!

# -------------------------
# Database Connection Helper
# -------------------------
def get_db_connection():
    db_path = os.path.join("Data", "userdata.db")
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


# ----------------------------------------
# Connect to SQLite database
db_path = os.path.join("Data", "userdata.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Drop the old mineral_prices table
cur.execute("DROP TABLE IF EXISTS mineral_prices")

# Create the new table using MineralName
cur.execute("""
    CREATE TABLE mineral_prices (
        PriceID INTEGER PRIMARY KEY AUTOINCREMENT,
        MineralName TEXT NOT NULL,
        Year INTEGER NOT NULL,
        PriceUSD_per_tonne REAL NOT NULL
    )
""")

# ----------------------------------------
# Define historical pricing data
# ----------------------------------------
historical_prices = [
    ("Cobalt",    2023, 50229.0),
    ("Cobalt",    2024, 49822.0),
    ("Cobalt",    2025, 52000.0),
    ("Graphite",  2023, 729.0),
    ("Graphite",  2024, 821.0),
    ("Graphite",  2025, 800.0),
    ("Lithium",   2023, 64093.0),
    ("Lithium",   2024, 69273.0),
    ("Lithium",   2025, 70000.0),
    ("Manganese", 2023, 1980.0),
    ("Manganese", 2024, 2300.0),
    ("Manganese", 2025, 2200.0)
]

# ----------------------------------------
# Insert data while preventing duplicates
# ----------------------------------------
for name, year, price in historical_prices:
    cur.execute("""
        SELECT 1 FROM mineral_prices
        WHERE MineralName = ? AND Year = ?
    """, (name, year))
    
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO mineral_prices (MineralName, Year, PriceUSD_per_tonne)
            VALUES (?, ?, ?)
        """, (name, year, price))

# ----------------------------------------
# Finalize and close connection
# ----------------------------------------
conn.commit()
conn.close()


# -------------------------
# Routes
# -------------------------

# --- ROLE-BASED HOME ---
@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))

    role_id = session.get('role_id')
    username = session['username']

    if role_id == 1:
        return render_template('admin_home.html', username=username)
    elif role_id == 2:
        return render_template('investor_home.html', username=username, role='investor')
    elif role_id == 3:
        return render_template('researcher_home.html', username=username, role='researcher')
    else:
        return render_template('error.html', message="Unknown role.")
    

@app.route('/register', methods=['POST'])
def register_user():
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    confirm_password = request.form['confirm_password'].strip()
    role_name = request.form['role'].strip()

    # Validate password length
    if len(password) < 8:
        return render_template('login.html',
                               error="Password must be at least 8 characters.",
                               timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Confirm password match
    if password != confirm_password:
        return render_template('login.html',
                               error="Passwords do not match. Please try again.",
                               timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Restrict registration to Investor and Researcher only
    if role_name not in ['Investor', 'Researcher']:
        return render_template('login.html',
                               error="Only Investors and Researchers can register.",
                               timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Hash the password securely
    password_hash = generate_password_hash(password)

    conn = get_db_connection()
    cur = conn.cursor()

    # Validate role from roles table
    cur.execute("SELECT RoleID FROM roles WHERE RoleName = ?", (role_name,))
    role = cur.fetchone()

    if not role:
        conn.close()
        return render_template('login.html',
                               error="Invalid role selected. Please choose Investor or Researcher.",
                               timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    role_id = role['RoleID']

    try:
        cur.execute("""
            INSERT INTO users (Username, PasswordHash, RoleID)
            VALUES (?, ?, ?)
        """, (username, password_hash, role_id))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return render_template('login.html',
                               error="Username already exists. Please choose a different one.",
                               timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    conn.close()
    return render_template('login.html',
                           success="Registration complete. You may now log in.",
                           timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


# -------------------------
# Admin: Manage Users
# -------------------------
@app.route('/admin/users', methods=['GET'])
def view_users():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template('admin_users_menu.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
def add_user():
    username = request.form['username']
    password = request.form['password']
    role_id = request.form['role_id']
    conn = get_db_connection()
    conn.execute("INSERT INTO users (Username, PasswordHash, RoleID) VALUES (?, ?, ?)", (username, password, role_id))
    conn.commit()
    conn.close()
    flash(f"User '{username}' added successfully.", "success")
    return redirect(url_for('view_users'))

@app.route('/admin/users/edit/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    username = request.form['username']
    password = request.form['password']
    role_id = request.form['role_id']
    conn = get_db_connection()
    conn.execute("UPDATE users SET Username = ?, PasswordHash = ?, RoleID = ? WHERE UserID = ?", (username, password, role_id, user_id))
    conn.commit()
    conn.close()
    flash(f"User '{username}' updated successfully.", "info")
    return redirect(url_for('view_users'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM users WHERE UserID = ?", (user_id,))
        conn.commit()
        flash(f"User deleted successfully.", "success")
    finally:
        conn.close()
    return redirect(url_for('view_users'))


# -------------------------
# Admin: Manage Minerals
# -------------------------
@app.route('/admin/minerals', methods=['GET'])
def view_minerals():
    conn = get_db_connection()
    minerals = conn.execute("SELECT * FROM minerals").fetchall()
    conn.close()
    return render_template('admin_minerals_menu.html', minerals=minerals)

@app.route('/admin/minerals/add', methods=['POST'])
def add_mineral():
    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO minerals (MineralName, Description, MarketPriceUSD_per_tonne) VALUES (?, ?, ?)",
        (name, description, price)
    )
    conn.commit()
    conn.close()
    flash(f"Mineral '{name}' added successfully.", "success")
    return redirect(url_for('view_minerals'))

@app.route('/admin/minerals/edit/<int:mineral_id>', methods=['POST'])
def edit_mineral(mineral_id):
    name = request.form['name']
    description = request.form['description']
    price = request.form['price']
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE minerals SET MineralName = ?, Description = ?, MarketPriceUSD_per_tonne = ? WHERE MineralID = ?",
            (name, description, price, mineral_id)
        )
        conn.commit()
        flash(f"Mineral '{name}' updated successfully.", "info")
    return redirect(url_for('view_minerals'))

@app.route('/admin/minerals/delete/<int:mineral_id>', methods=['POST'])
def delete_mineral(mineral_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM minerals WHERE MineralID = ?", (mineral_id,))
    conn.commit()
    conn.close()
    flash(f"Mineral deleted successfully.", "success")
    return redirect(url_for('view_minerals'))

# -------------------------
# Admin: Manage Countries
# -------------------------

@app.route('/admin/countries', methods=['GET'])
def view_countries():
    conn = get_db_connection()
    countries = conn.execute("SELECT * FROM countries").fetchall()
    conn.close()
    return render_template('admin_countries_menu.html', countries=countries)

@app.route('/admin/countries/add', methods=['POST'])
def add_country():
    name = request.form['name']
    gdp = request.form['gdp']
    revenue = request.form['revenue']
    projects = request.form['projects']
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO countries (CountryName, GDP_BillionUSD, MiningRevenue_BillionUSD, KeyProjects) VALUES (?, ?, ?, ?)",
        (name, gdp, revenue, projects)
    )
    conn.commit()
    conn.close()
    flash(f"Country '{name}' added successfully.", "success")
    return redirect(url_for('view_countries'))

@app.route('/admin/countries/edit/<int:country_id>', methods=['POST'])
def edit_country(country_id):
    name = request.form['name']
    gdp = request.form['gdp']
    revenue = request.form['revenue']
    projects = request.form['projects']
    conn = get_db_connection()
    conn.execute(
        "UPDATE countries SET CountryName = ?, GDP_BillionUSD = ?, MiningRevenue_BillionUSD = ?, KeyProjects = ? WHERE CountryID = ?",
        (name, gdp, revenue, projects, country_id)
    )
    conn.commit()
    conn.close()
    flash(f"Country '{name}' updated successfully.", "info")
    return redirect(url_for('view_countries'))

@app.route('/admin/countries/delete/<int:country_id>', methods=['POST'])
def delete_country(country_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM countries WHERE CountryID = ?", (country_id,))
    conn.commit()
    conn.close()
    flash(f"Country deleted successfully.", "success")
    return redirect(url_for('view_countries'))

# -------------------------
# Admin: Manage Sites
# -------------------------

@app.route('/admin/sites', methods=['GET'])
def view_sites():
    with get_db_connection() as conn:
        sites = conn.execute("SELECT * FROM sites").fetchall()
    return render_template('admin_sites_menu.html', sites=sites)

@app.route('/admin/sites/add', methods=['POST'])
def add_site():
    name = request.form['name']
    country_id = request.form['country_id']
    mineral_id = request.form['mineral_id']
    lat = request.form['latitude']
    lon = request.form['longitude']
    production = request.form['production']
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO sites (SiteName, CountryID, MineralID, Latitude, Longitude, Production_tonnes) VALUES (?, ?, ?, ?, ?, ?)",
            (name, country_id, mineral_id, lat, lon, production)
        )
        conn.commit()
        flash(f"Site '{name}' added successfully.", "success")
    return redirect(url_for('view_sites'))

@app.route('/admin/sites/edit/<int:site_id>', methods=['POST'])
def edit_site(site_id):
    name = request.form['name']
    country_id = request.form['country_id']
    mineral_id = request.form['mineral_id']
    lat = request.form['latitude']
    lon = request.form['longitude']
    production = request.form['production']
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE sites SET SiteName = ?, CountryID = ?, MineralID = ?, Latitude = ?, Longitude = ?, Production_tonnes = ? WHERE SiteID = ?",
            (name, country_id, mineral_id, lat, lon, production, site_id)
        )
        conn.commit()
        flash(f"Site '{name}' updated successfully.", "info")
    return redirect(url_for('view_sites'))

@app.route('/admin/sites/delete/<int:site_id>', methods=['POST'])
def delete_site(site_id):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM sites WHERE SiteID = ?", (site_id,))
        conn.commit()
        flash(f"Site deleted successfully.", "success")
    return redirect(url_for('view_sites'))

# -------------------------
# Admin: Manage Production Stats
# -------------------------

@app.route('/admin/production', methods=['GET'])
def view_production_stats():
    with get_db_connection() as conn:
        stats = conn.execute("SELECT * FROM production_stats").fetchall()
    return render_template('admin_production_stats_menu.html', stats=stats)

@app.route('/admin/production/add', methods=['POST'])
def add_production_stat():
    year = request.form['year']
    country_id = request.form['country_id']
    mineral_id = request.form['mineral_id']
    production = request.form['production']
    export_value = request.form['export_value']
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO production_stats (Year, CountryID, MineralID, Production_tonnes, ExportValue_BillionUSD) VALUES (?, ?, ?, ?, ?)",
            (year, country_id, mineral_id, production, export_value)
        )
        conn.commit()
        flash(f"Production stat for year {year} added successfully.", "success")
    return redirect(url_for('view_production_stats'))

@app.route('/admin/production/edit/<int:stat_id>', methods=['POST'])
def edit_production_stat(stat_id):
    year = request.form['year']
    country_id = request.form['country_id']
    mineral_id = request.form['mineral_id']
    production = request.form['production']
    export_value = request.form['export_value']
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE production_stats SET Year = ?, CountryID = ?, MineralID = ?, Production_tonnes = ?, ExportValue_BillionUSD = ? WHERE StatID = ?",
            (year, country_id, mineral_id, production, export_value, stat_id)
        )
        conn.commit()
        flash(f"Production stat for year {year} updated successfully.", "info")
    return redirect(url_for('view_production_stats'))

@app.route('/admin/production/delete/<int:stat_id>', methods=['POST'])
def delete_production_stat(stat_id):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM production_stats WHERE StatID = ?", (stat_id,))
        conn.commit()
        flash(f"Production stat deleted successfully.", "success")
    return redirect(url_for('view_production_stats'))

# -------------------------
# Admin: Manage Mineral Prices
# -------------------------

@app.route('/admin/prices', methods=['GET'])
def view_mineral_prices():
    conn = get_db_connection()
    prices = conn.execute("SELECT * FROM mineral_prices").fetchall()
    conn.close()
    return render_template('admin_mineral_prices_menu.html', prices=prices)

@app.route('/admin/prices/add', methods=['POST'])
def add_mineral_price():
    mineral_name = request.form['mineral_name']
    year = request.form['year']
    price = request.form['price']
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO mineral_prices (MineralName, Year, PriceUSD_per_tonne) VALUES (?, ?, ?)",
        (mineral_name, year, price)
    )
    conn.commit()
    conn.close()
    flash(f"Mineral price for {mineral_name} added successfully.", "success")
    return redirect(url_for('view_mineral_prices'))


@app.route('/admin/prices/edit/<int:price_id>', methods=['POST'])
def edit_mineral_price(price_id):
    mineral_name = request.form['mineral_name']
    year = request.form['year']
    price = request.form['price']
    conn = get_db_connection()
    conn.execute(
        "UPDATE mineral_prices SET MineralName = ?, Year = ?, PriceUSD_per_tonne = ? WHERE PriceID = ?",
        (mineral_name, year, price, price_id)
    )
    conn.commit()
    conn.close()
    flash(f"Mineral price for {mineral_name} updated successfully.", "info")
    return redirect(url_for('view_mineral_prices'))


@app.route('/admin/prices/delete/<int:price_id>', methods=['POST'])
def delete_mineral_price(price_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM mineral_prices WHERE PriceID = ?", (price_id,))
    conn.commit()
    conn.close()
    flash(f"Mineral price deleted successfully.", "success")
    return redirect(url_for('view_mineral_prices'))

# -------------------------
# Admin: Manage Roles
# -------------------------
@app.route('/admin/roles', methods=['GET'])
def view_roles():
    conn = get_db_connection()
    roles = conn.execute("SELECT * FROM roles").fetchall()
    conn.close()
    return render_template('manage_roles.html', roles=roles)

@app.route('/admin/roles/add', methods=['POST'])
def add_role():
    name = request.form['name']
    permissions = request.form['permissions']
    conn = get_db_connection()
    conn.execute("INSERT INTO roles (RoleName, Permissions) VALUES (?, ?)", (name, permissions))
    conn.commit()
    conn.close()
    flash(f"Role '{name}' added successfully.", "success")
    return redirect(url_for('view_roles'))

@app.route('/admin/roles/edit/<int:role_id>', methods=['POST'])
def edit_role(role_id):
    name = request.form['name']
    permissions = request.form['permissions']
    conn = get_db_connection()
    conn.execute("UPDATE roles SET RoleName = ?, Permissions = ? WHERE RoleID = ?", (name, permissions, role_id))
    conn.commit()
    conn.close()
    flash(f"Role '{name}' updated successfully.", "info")
    return redirect(url_for('view_roles'))

@app.route('/admin/roles/delete/<int:role_id>', methods=['POST'])
def delete_role(role_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM roles WHERE RoleID = ?", (role_id,))
    conn.commit()
    conn.close()
    flash(f"Role deleted successfully.", "success")
    return redirect(url_for('view_roles'))

# -------------------------
# Admin: Shared Menus
# -------------------------

@app.route('/<role>/minerals')
def show_minerals(role):
    if role not in ['investor', 'researcher', 'administrator']:
        return render_template('error.html', message="Unknown role.")

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    minerals = conn.execute("SELECT * FROM minerals").fetchall()
    conn.close()

    return render_template('shared_minerals.html', minerals=minerals, role=role)

from flask import send_file
import io

@app.route('/<role>/export-countries', methods=['POST'])
def export_countries(role):
    if role not in ['investor', 'researcher']:
        return render_template('error.html', message="Unknown role.")

    conn = get_db_connection()
    countries = conn.execute("SELECT CountryID, CountryName, GDP_BillionUSD, MiningRevenue_BillionUSD, KeyProjects FROM countries").fetchall()
    conn.close()

    selected_ids = request.form.getlist('country_id')
    export_format = request.form.get('format')

    if not selected_ids:
        return render_template('shared_country_profile.html', role=role, countries=countries,
                               export_success="No countries selected for export.")

    filtered = [c for c in countries if str(c['CountryID']) in selected_ids]
    df = pd.DataFrame(filtered)

    filename = f"{role}_country_export.{export_format}"

    if export_format == 'csv':
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        flash(f"{filename} successfully exported.", "success")
        return send_file(io.BytesIO(buffer.getvalue().encode()), mimetype='text/csv',
                         as_attachment=True, download_name=filename)

    elif export_format == 'json':
        buffer = io.StringIO()
        df.to_json(buffer, orient='records', indent=2)
        buffer.seek(0)
        flash(f"{filename} successfully exported.", "success")
        return send_file(io.BytesIO(buffer.getvalue().encode()), mimetype='application/json',
                         as_attachment=True, download_name=filename)
    
    flash("Invalid export format selected.", "error")
    return render_template('shared_country_profile.html', role=role, countries=countries,
                           export_success="Invalid export format selected.")

@app.route('/<role>/export-minerals', methods=['POST'])
def export_minerals(role):
    if role not in ['investor', 'researcher']:
        return render_template('error.html', message="Unknown role.")

    conn = get_db_connection()
    minerals = conn.execute("SELECT MineralID, MineralName, Description, MarketPriceUSD_per_tonne FROM minerals").fetchall()
    conn.close()

    selected_ids = request.form.getlist('mineral_id')
    export_format = request.form.get('format')

    if not selected_ids:
        return render_template('shared_minerals.html', role=role, minerals=minerals,
                               export_success="No minerals selected for export.")

    filtered = [m for m in minerals if str(m['MineralID']) in selected_ids]
    df = pd.DataFrame(filtered)

    filename = f"{role}_mineral_export.{export_format}"

    if export_format == 'csv':
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        flash(f"{filename} successfully exported.", "success")
        return send_file(io.BytesIO(buffer.getvalue().encode()), mimetype='text/csv',
                         as_attachment=True, download_name=filename)

    elif export_format == 'json':
        buffer = io.StringIO()
        df.to_json(buffer, orient='records', indent=2)
        buffer.seek(0)
        flash(f"{filename} successfully exported.", "success")
        return send_file(io.BytesIO(buffer.getvalue().encode()), mimetype='application/json',
                         as_attachment=True, download_name=filename)
    flash("Invalid export format selected.", "error")
    return render_template('shared_minerals.html', role=role, minerals=minerals,
                           export_success="Invalid export format selected.")

@app.route('/<role>/map')
def show_mineral_sites_map(role):
    # Validate role
    if role not in ['investor', 'researcher']:
        return render_template('error.html', message="Unknown role.")

    conn = get_db_connection()

    # Load lookup tables
    countries = conn.execute("SELECT CountryID, CountryName FROM countries").fetchall()
    minerals = conn.execute("SELECT MineralID, MineralName FROM minerals").fetchall()
    sites = conn.execute("SELECT * FROM sites").fetchall()
    conn.close()

    if not sites:
        return render_template('error.html', message="No mineral sites found.")

    # Build lookup dictionaries
    country_lookup = {c['CountryID']: c['CountryName'] for c in countries}
    mineral_lookup = {m['MineralID']: m['MineralName'] for m in minerals}

    # Create Folium map
    africa_map = folium.Map(location=[-2.0, 23.5], zoom_start=4)

    for site in sites:
        country_name = country_lookup.get(site['CountryID'], "Unknown Country")
        mineral_name = mineral_lookup.get(site['MineralID'], "Unknown Mineral")

        popup_html = f"""
        <div style='font-size:14px'>
          <strong>Site:</strong> {site['SiteName']}<br>
          <strong>Country:</strong> {country_name}<br>
          <strong>Mineral:</strong> {mineral_name}<br>
          <strong>Production:</strong> {site['Production_tonnes']} tonnes
        </div>
        """

        folium.Marker(
            location=[site['Latitude'], site['Longitude']],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(africa_map)

    # Embed map in template
    map_html = africa_map._repr_html_()
    return render_template('shared_map.html', role=role, map_html=map_html)


def generate_pie_chart(gdp, mining_revenue):
    labels = ['Mining Revenue', 'Other GDP']
    values = [mining_revenue, gdp - mining_revenue]
    colors = ['#4F46E5', '#A5B4FC']

    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
    ax.set_title('GDP Composition')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    chart_data = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return chart_data

@app.route('/<role>/country-profile')
def view_country_profile(role):
    if role not in ['investor', 'researcher']:
        return render_template('error.html', message="Unknown role.")

    conn = get_db_connection()
    countries = conn.execute("SELECT * FROM countries").fetchall()

    country_id = request.args.get("country_id", type=int)
    selected_country = None
    chart_data = None

    if country_id:
        selected_country = conn.execute(
            "SELECT * FROM countries WHERE CountryID = ?", (country_id,)
        ).fetchone()

        if selected_country:
            gdp = selected_country['GDP_BillionUSD']
            mining = selected_country['MiningRevenue_BillionUSD']
            chart_data = generate_pie_chart(gdp, mining)

    conn.close()

    return render_template(
        'shared_country_profile.html',
        role=role,
        countries=countries,
        selected_country=selected_country,
        chart_data=chart_data
    )

def generate_comparison_chart(countries):
    """
    Generates a grouped bar chart comparing GDP and Mining Revenue across countries.
    Expects a list of dicts with keys: 'CountryName', 'GDP_BillionUSD', 'MiningRevenue_BillionUSD'
    """
    country_names = [c['CountryName'] for c in countries]
    gdp_values = [c['GDP_BillionUSD'] for c in countries]
    mining_values = [c['MiningRevenue_BillionUSD'] for c in countries]

    x = range(len(countries))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar([i - width/2 for i in x], gdp_values, width, label='GDP', color='#4F46E5')
    ax.bar([i + width/2 for i in x], mining_values, width, label='Mining Revenue', color='#A5B4FC')

    ax.set_xticks(x)
    ax.set_xticklabels(country_names, rotation=45, ha='right')
    ax.set_ylabel('Billion USD')
    ax.set_title('GDP vs Mining Revenue by Country')
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.5)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    chart_data = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return chart_data

@app.route('/<role>/compare-countries')
def compare_countries(role):
    # Validate role
    if role not in ['investor', 'researcher']:
        return render_template('error.html', message="Unknown role.")

    # Load all countries
    conn = get_db_connection()
    countries = conn.execute("SELECT * FROM countries").fetchall()

    # Get selected country IDs from query string
    ids = request.args.getlist("country_id", type=int)
    selected_countries = []

    # Filter selected countries
    if ids:
        for cid in ids:
            country = conn.execute("SELECT * FROM countries WHERE CountryID = ?", (cid,)).fetchone()
            if country:
                selected_countries.append(country)

    # Generate comparison chart
    comparison_chart = generate_comparison_chart(selected_countries)
    conn.close()

    # Render template with all data
    return render_template(
        'shared_compare_countries.html',
        role=role,
        countries=countries,
        selected_countries=selected_countries,
        comparison_chart=comparison_chart
    )


@app.route('/researcher/insights', methods=['GET', 'POST'])
def researcher_insights():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Ensure required tables exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS minerals (
            MineralID INTEGER PRIMARY KEY AUTOINCREMENT,
            MineralName TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mineral_insights (
            InsightID INTEGER PRIMARY KEY AUTOINCREMENT,
            MineralID INTEGER,
            Insight TEXT,
            FOREIGN KEY(MineralID) REFERENCES minerals(MineralID)
        )
    """)

    # Handle new insight submission
    if request.method == 'POST':
        mineral_id = request.form.get('mineral_id')
        insight = request.form.get('insight')
        if mineral_id and insight:
            cur.execute("""
                INSERT INTO mineral_insights (MineralID, Insight)
                VALUES (?, ?)
            """, (mineral_id, insight))
            conn.commit()

    # Fetch minerals for dropdown
    minerals = cur.execute("""
        SELECT MineralID, MineralName
        FROM minerals
        ORDER BY MineralName
    """).fetchall()

    # Fetch all insights with mineral names
    insights = cur.execute("""
        SELECT i.InsightID, i.Insight, m.MineralName
        FROM mineral_insights i
        JOIN minerals m ON i.MineralID = m.MineralID
        ORDER BY i.InsightID DESC
    """).fetchall()

    conn.close()
    return render_template('researcher_insights.html',
                           role='researcher',
                           minerals=minerals,
                           insights=insights)


@app.route('/researcher/insights/edit/<int:insight_id>', methods=['POST'])
def edit_insight(insight_id):
    updated_text = request.form.get('updated_insight')
    if updated_text:
        with sqlite3.connect("userdata.db") as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE mineral_insights
                SET Insight = ?
                WHERE InsightID = ?
            """, (updated_text, insight_id))
            conn.commit()
    return redirect(url_for('researcher_insights'))

@app.route('/researcher/insights/delete/<int:insight_id>', methods=['POST'])
def delete_insight(insight_id):
    with sqlite3.connect("userdata.db") as conn:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM mineral_insights
            WHERE InsightID = ?
        """, (insight_id,))
        conn.commit()
    return redirect(url_for('researcher_insights'))



# Investor-only Menus
@app.route('/investor/analyze-prices')
def investor_analyze_prices():
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row

    query = """
    SELECT MineralName, Year, PriceUSD_per_tonne
    FROM mineral_prices
    ORDER BY MineralName, Year
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        return render_template('investor_analyze_prices.html', message="No historical prices available.")

    # Prepare data for charts
    grouped = df.groupby("MineralName")
    latest_df = df.loc[df.groupby("MineralName")["Year"].idxmax()]

    return render_template(
        'investor_analyze_prices.html',
        data=df.to_dict(orient='records'),
        latest=latest_df.to_dict(orient='records'),
        role='investor'
    )


# --- INDEX ---
@app.route('/')
def index():
    # If already logged in, send them to their home
    if 'username' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

# --- LOGIN ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT UserID, Username, PasswordHash, RoleID FROM users WHERE Username=?", (username,))
        user = cur.fetchone()
        conn.close()

        # Secure password check using hash
        if user and check_password_hash(user["PasswordHash"], password):
            session['username'] = user["Username"]
            session['role_id'] = user["RoleID"]

            return redirect(url_for('home')) 
        else:
            error = "Invalid username or password."

    return render_template('login.html',
                           error=error,
                           timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# --- LOGOUT ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -------------------------
# Run the App
# -------------------------
if __name__ == '__main__':
    app.run(debug=True)
    
