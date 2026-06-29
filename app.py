# app.py
from flask import Flask, render_template_string, request
import os
import pandas as pd

# import our modules (separate files)
import etl
import dash
import map
import state_rank

app = Flask(__name__)

# ---- Initialisation (runs once on startup) ----
def initialize():
    print("Running ETL...")
    df, summary = etl.run_etl()
    print("ETL done.")

    print("Generating dashboard image...")
    dash.generate_dashboard()
    print("Dashboard image saved.")

    print("Generating map...")
    map.generate_map()
    print("Map saved.")

    # Load ranking data
    global sorted_by_score, sorted_by_state, state_metrics_df
    sorted_by_score, sorted_by_state, state_metrics_df = state_rank.get_rank_data()
    print("Ranking data loaded.")
    return summary

# Check if CSV exists; if not, run full initialisation
if not os.path.exists("crop_census.csv"):
    summary = initialize()
else:
    try:
        sorted_by_score, sorted_by_state, state_metrics_df = state_rank.get_rank_data()
    except Exception:
        summary = initialize()
    else:
        df = pd.read_csv("crop_census.csv")
        summary = {
            'rows': len(df),
            'columns': len(df.columns),
            'states': df['state'].nunique(),
            'crops': df['crop'].nunique(),
            'missing': df.isnull().sum().sum()
        }
        # Ensure images exist
        if not os.path.exists("agri_dashboard.png"):
            dash.generate_dashboard()
        if not os.path.exists("agri_risk_map.html"):
            map.generate_map()

# Move generated files to static folder (for Flask serving)
def move_to_static(files):
    for f in files:
        if os.path.exists(f):
            dest = os.path.join('static', f)
            if os.path.exists(dest):
                os.remove(dest)
            os.rename(f, dest)

if not os.path.exists('static'):
    os.makedirs('static')
move_to_static(['agri_dashboard.png', 'agri_risk_map.html'])

# ---- Routes ----
@app.route('/', methods=['GET', 'POST'])
def index():
    search_result = None
    search_state = None

    # Handle search form submission
    if request.method == 'POST':
        state_name = request.form.get('state', '').strip().title()
        search_state = state_name
        result = state_rank.get_state_rank(state_name, sorted_by_state, sorted_by_score)
        if result:
            rank, state, score = result
            row = state_metrics_df[state_metrics_df['state'] == state].iloc[0]
            # get extra info from original df
            df = pd.read_csv("crop_census.csv")
            state_data = df[df['state'] == state]
            water_stressed = state_data['Water_Stressed'].any() if not state_data.empty else False
            top_crop = state_data.loc[state_data['total_production_tonnes'].idxmax(), 'crop'] if not state_data.empty else 'N/A'
            search_result = {
                'rank': rank,
                'state': state,
                'score': round(score, 4),
                'avg_yield': round(row['avg_yield'], 1),
                'avg_irrigation': round(row['avg_irrigation'], 1),
                'avg_revenue': round(row['avg_revenue'], 2),
                'avg_loss': round(row['avg_loss'], 1),
                'water_stressed': water_stressed,
                'top_crop': top_crop
            }
        else:
            search_result = None   # indicates not found

    # Build the full ranking table (all states)
    all_ranks = []
    for rank, (score, state) in enumerate(sorted_by_score, 1):
        row = state_metrics_df[state_metrics_df['state'] == state].iloc[0]
        all_ranks.append({
            'rank': rank,
            'state': state,
            'score': round(score, 4),
            'avg_yield': round(row['avg_yield'], 1),
            'avg_irrigation': round(row['avg_irrigation'], 1),
            'avg_revenue': round(row['avg_revenue'], 2),
            'avg_loss': round(row['avg_loss'], 1)
        })

    return render_template_string(HTML_TEMPLATE,
                                  summary=summary,
                                  ranks=all_ranks,
                                  search_result=search_result,
                                  search_state=search_state)

# ---- HTML template (includes full ranking table and search) ----
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Agri Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: auto; background: white; padding: 20px; border-radius: 8px; }
        h1 { text-align: center; color: #2c3e50; }
        .summary { display: flex; flex-wrap: wrap; justify-content: space-around; background: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .summary-item { margin: 5px 15px; }
        .dashboard-image { text-align: center; margin: 20px 0; }
        .dashboard-image img { max-width: 100%; border: 1px solid #ddd; border-radius: 5px; }
        .map-container { width: 100%; height: 500px; margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }
        .map-container iframe { width: 100%; height: 100%; border: none; }
        .rank-section { display: flex; flex-wrap: wrap; }
        .rank-table { flex: 2; min-width: 300px; margin-right: 20px; }
        .rank-table table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .rank-table th, .rank-table td { padding: 6px; border: 1px solid #ddd; text-align: left; }
        .rank-table th { background-color: #34495e; color: white; position: sticky; top: 0; }
        .rank-table-container { max-height: 400px; overflow-y: auto; }
        .search-box { flex: 1; min-width: 250px; background: #f8f9fa; padding: 15px; border-radius: 5px; }
        .search-box input[type=text] { width: 100%; padding: 8px; margin: 8px 0; border: 1px solid #ccc; border-radius: 4px; }
        .search-box input[type=submit] { background: #2c3e50; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
        .search-box input[type=submit]:hover { background: #1a252f; }
        .result-card { background: #e8f4f8; padding: 10px; border-radius: 4px; margin-top: 10px; }
        .result-card h4 { margin: 0 0 8px 0; }
        .not-found { background: #fdd; padding: 10px; border-radius: 4px; margin-top: 10px; }
        hr { margin: 30px 0; }
        .footer { text-align: center; color: #7f8c8d; margin-top: 30px; }
    </style>
</head>
<body>
<div class="container">
    <h1>🌾 Agricultural Analytics Dashboard</h1>

    <div class="summary">
        <div class="summary-item"><b>Rows:</b> {{ summary.rows }}</div>
        <div class="summary-item"><b>Columns:</b> {{ summary.columns }}</div>
        <div class="summary-item"><b>States:</b> {{ summary.states }}</div>
        <div class="summary-item"><b>Crops:</b> {{ summary.crops }}</div>
        <div class="summary-item"><b>Missing Values:</b> {{ summary.missing }}</div>
    </div>

    <div class="dashboard-image">
        <h2>Dashboard Visualization</h2>
        <img src="{{ url_for('static', filename='agri_dashboard.png') }}" alt="Agri Dashboard">
    </div>

    <div class="map-container">
        <h2>State Risk Map</h2>
        <iframe src="{{ url_for('static', filename='agri_risk_map.html') }}"></iframe>
    </div>

    <hr>
    <h2>State Rankings</h2>
    <div class="rank-section">
        <div class="rank-table">
            <div class="rank-table-container">
                <table>
                    <thead><tr><th>Rank</th><th>State</th><th>Score</th><th>Avg Yield</th><th>Irrigation %</th><th>Revenue (Cr)</th><th>Loss %</th></tr></thead>
                    <tbody>
                    {% for r in ranks %}
                    <tr>
                        <td>{{ r.rank }}</td>
                        <td>{{ r.state }}</td>
                        <td>{{ r.score }}</td>
                        <td>{{ r.avg_yield }}</td>
                        <td>{{ r.avg_irrigation }}</td>
                        <td>{{ r.avg_revenue }}</td>
                        <td>{{ r.avg_loss }}</td>
                    </tr>
                    {% endfor %}
                    </tbody>
                </table>
            </div>
            <p><small>Total {{ ranks|length }} states ranked.</small></p>
        </div>
        <div class="search-box">
            <h3>🔍 Search State</h3>
            <form method="POST" action="/">
                <input type="text" name="state" placeholder="Enter state name (e.g., Punjab)" value="{{ search_state or '' }}" required>
                <input type="submit" value="Get Rank">
            </form>
            {% if search_result %}
            <div class="result-card">
                <h4>{{ search_result.state }}</h4>
                <p><b>Rank:</b> #{{ search_result.rank }}</p>
                <p><b>Score:</b> {{ search_result.score }}</p>
                <p><b>Avg Yield:</b> {{ search_result.avg_yield }} kg/ha</p>
                <p><b>Avg Irrigation:</b> {{ search_result.avg_irrigation }}%</p>
                <p><b>Avg Revenue:</b> ₹{{ search_result.avg_revenue }} Cr</p>
                <p><b>Avg Loss:</b> {{ search_result.avg_loss }}%</p>
                <p><b>Top Crop:</b> {{ search_result.top_crop }}</p>
                <p><b>Water Stressed:</b> {{ "Yes" if search_result.water_stressed else "No" }}</p>
            </div>
            {% elif search_state is not none %}
            <div class="not-found">
                <p>State "<b>{{ search_state }}</b>" not found. Please check spelling.</p>
            </div>
            {% endif %}
        </div>
    </div>
    <div class="footer">Data processed by ETL • Visuals with Matplotlib & Folium</div>
</div>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True, port=5000)