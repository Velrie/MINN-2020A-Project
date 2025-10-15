# MINN-2020A-Project
African Critical Minerals App is a Flask-based web application designed to visualize and analyze mineral data across Africa. It combines interactive mapping, user management, and data visualization to support exploration, research, and decision-making in the mining sector.

# Features
Interactive Map: Displays mineral locations across African countries using Folium.

User Authentication: Secure login system with password hashing and session management.

Data Visualization: Charts and graphs for mineral prices, trends, and country-specific data using Matplotlib and Pandas.

Database Integration: Uses SQLite for storing user data and mineral information.

Responsive Design: HTML templates for login, dashboard, and map views.

# Technologies Used
Flask – Web framework
SQLite – Lightweight database
Folium – Map visualization
Matplotlib & Pandas – Data analysis and charting
Werkzeug – Password security

#Project Structure
AfricanCriticalMineralsApp/
│
├── app.py
├── templates/
│   ├── login.html
│   ├── dashboard.html
│   └── map.html
├── static/
│   └── (CSS/JS files)
├── data/
│   └── minerals.db
└── .venv/
## Setup

1. **Install dependencies:**
    ```
    pip install -r requirements.txt
    ```

2. **Run the app:**
    ```
    python app.py
    ```

3. **Access in browser:**
    ```
    http://127.0.0.1:5000
    
  # License
This project is open-source and available under the MIT License.

