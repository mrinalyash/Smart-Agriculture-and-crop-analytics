# map.py
import pandas as pd
import folium

def generate_map(csv_path="crop_census.csv", out_html="agri_risk_map.html"):
    df = pd.read_csv(csv_path)

    state_metrics = df.groupby('state').agg({
        'yield_kg_ha': 'mean',
        'irrigation_pct': 'mean',
        'farm_revenue_cr': 'mean',
        'loss_pct': 'mean'
    }).reset_index()
    state_metrics.columns = ['state', 'avg_yield', 'avg_irrigation',
                             'avg_revenue', 'avg_loss']

    for col in ['avg_yield', 'avg_irrigation', 'avg_revenue', 'avg_loss']:
        min_val = state_metrics[col].min()
        max_val = state_metrics[col].max()
        if max_val > min_val:
            state_metrics[f'norm_{col}'] = (state_metrics[col] - min_val) / (max_val - min_val)
        else:
            state_metrics[f'norm_{col}'] = 0

    state_metrics['agri_score'] = (
        0.4 * state_metrics['norm_avg_yield'] +
        0.3 * state_metrics['norm_avg_irrigation'] +
        0.2 * state_metrics['norm_avg_revenue'] -
        0.1 * state_metrics['norm_avg_loss']
    )

    STATE_COORDS = {
        'Punjab': [31.1471, 75.3412],
        'Haryana': [29.0588, 76.0856],
        'UP': [26.8467, 80.9462],
        'Bihar': [25.0961, 85.3131],
        'MP': [23.4734, 77.9470],
        'Maharashtra': [19.6633, 75.3003],
        'Gujarat': [22.2587, 71.1924],
        'Rajasthan': [27.0238, 73.3119],
        'Karnataka': [15.3173, 75.7139],
        'AP': [15.9129, 79.7400],
        'Tamil Nadu': [11.1271, 78.6569],
        'Odisha': [20.9517, 85.0985],
        'WB': [22.9868, 87.8550],
        'Assam': [26.2006, 92.9376],
        'Kerala': [10.8505, 76.2711]
    }

    def get_color(score):
        if score > 0.6: return 'green'
        elif score > 0.4: return 'orange'
        return 'red'

    m = folium.Map(location=[22.0, 78.0], zoom_start=5)
    stressed_group = folium.FeatureGroup(name='Water Stressed')
    normal_group = folium.FeatureGroup(name='Not Stressed')

    state_df = state_metrics.copy()
    state_df['lat'] = state_df['state'].map(lambda x: STATE_COORDS.get(x, [0, 0])[0])
    state_df['lon'] = state_df['state'].map(lambda x: STATE_COORDS.get(x, [0, 0])[1])
    state_df = state_df[state_df['lat'] != 0]

    for _, row in state_df.iterrows():
        state = row['state']
        score = row['agri_score']
        color = get_color(score)
        state_data = df[df['state'] == state]
        water_stressed = state_data['Water_Stressed'].any() if not state_data.empty else False
        top_crop = state_data.loc[state_data['total_production_tonnes'].idxmax(), 'crop'] if not state_data.empty else 'N/A'
        revenue = state_data['farm_revenue_cr'].sum() if not state_data.empty else 0

        popup = folium.Popup(
            f"<b>{state}</b><br>Score: {score:.3f}<br>Top Crop: {top_crop}<br>Water Stressed: {water_stressed}<br>Revenue: ₹{revenue:.2f} Cr",
            max_width=300
        )
        marker = folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=score * 20 + 2,
            popup=popup,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            weight=2
        )
        if water_stressed:
            stressed_group.add_child(marker)
        else:
            normal_group.add_child(marker)

    stressed_group.add_to(m)
    normal_group.add_to(m)
    folium.LayerControl().add_to(m)

    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px;
                border:2px solid grey; z-index:9999;
                background-color:white; padding: 10px; border-radius: 5px;">
        <p><b>Risk Legend</b></p>
        <p><span style="color:green;">●</span> Low Risk (>0.6)</p>
        <p><span style="color:orange;">●</span> Medium Risk (0.4-0.6)</p>
        <p><span style="color:red;">●</span> High Risk (<0.4)</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    m.save(out_html)
    return out_html

if __name__ == '__main__':
    generate_map()
    print("Map saved.")