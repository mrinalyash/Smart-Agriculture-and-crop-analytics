# etl.py
import pandas as pd
import numpy as np

def run_etl():
    np.random.seed(21)
    states = ['Punjab','Haryana','UP','Bihar','MP','Maharashtra',
              'Gujarat','Rajasthan','Karnataka','AP','Tamil Nadu',
              'Odisha','WB','Assam','Kerala']
    crops = ['Wheat','Rice','Maize','Sugarcane','Cotton','Soybean']
    rng = np.random.default_rng(21)
    rows = []
    for s in states:
        for c in crops:
            rows.append({'state':s,'crop':c,
                'area_ha':np.random.randint(5000,500000),
                'yield_kg_ha':np.random.uniform(800,6000),
                'rainfall_mm':np.random.uniform(300,2000),
                'fertilizer_kg_ha':np.random.uniform(50,400),
                'irrigation_pct':np.random.uniform(10,95),
                'msp_rs_qtl':np.random.uniform(1200,4500),
                'loss_pct':np.random.choice([np.nan,5,10,15,20,25],1)[0]})
    df = pd.DataFrame(rows)

    area = df['area_ha'].values.astype(object)
    yld  = df['yield_kg_ha'].values.astype(object)
    rain = df['rainfall_mm'].values.astype(float)
    irr  = df['irrigation_pct'].values.astype(float)
    st   = df['state'].values.astype(object)
    idx2 = rng.choice(len(df), size=25, replace=False)
    for i in idx2[:6]:   yld[i]  = np.nan
    for i in idx2[6:12]: area[i] = str(int(area[i])) + ' ha'
    for i in idx2[12:18]: rain[i] = -1
    for i in idx2[18:22]: st[i]  = str(st[i]).upper()
    for i in idx2[22:25]: irr[i] = 110
    df['area_ha']=area; df['yield_kg_ha']=yld
    df['rainfall_mm']=rain; df['irrigation_pct']=irr; df['state']=st
    rng2 = np.random.default_rng(200)
    wm = df['crop']=='Wheat'
    df.loc[wm,'crop'] = rng2.choice(['Wheat','wheat','WHEAT'], wm.sum())

    # ---- cleaning functions (keep as given) ----
    def clean_area():
        df['area_ha'] = df['area_ha'].astype(str).str.strip()
        df['area_ha'] = df['area_ha'].str.replace(' ha', '', regex=False)
        df['area_ha'] = pd.to_numeric(df['area_ha'])
    clean_area()

    def clean_rainfall(rainfall_series: pd.Series, df: pd.DataFrame) -> pd.Series:
        rainfall_series = rainfall_series.replace(-1, np.nan)
        state_medians = df.groupby('state')['rainfall_mm'].median()
        for state in df['state'].unique():
            if pd.notna(state_medians.get(state)):
                mask = (df['state'] == state) & (rainfall_series.isna())
                rainfall_series.loc[mask] = state_medians[state]
        return rainfall_series
    df["rainfall_mm"] = clean_rainfall(df['rainfall_mm'], df)

    def clean_irrigation():
        df['irrigation_pct'] = df['irrigation_pct'].clip(upper=100.0)
    clean_irrigation()

    def fill_missing_values(df: pd.DataFrame) -> pd.DataFrame:
        crop_medians_loss = df.groupby('crop')['loss_pct'].median()
        crop_medians_yield = df.groupby('crop')['yield_kg_ha'].median()
        for crop in df['crop'].unique():
            if pd.notna(crop_medians_loss.get(crop)):
                mask = (df['crop'] == crop) & (df['loss_pct'].isna())
                df.loc[mask, 'loss_pct'] = crop_medians_loss[crop]
            if pd.notna(crop_medians_yield.get(crop)):
                mask = (df['crop'] == crop) & (df['yield_kg_ha'].isna())
                df.loc[mask, 'yield_kg_ha'] = crop_medians_yield[crop]
        return df

    def standardize_state_name(state: str) -> str:
        mapping = {
            'punjab':'Punjab','haryana':'Haryana','up':'UP','bihar':'Bihar',
            'mp':'MP','madhya pradesh':'MP','maharashtra':'Maharashtra',
            'gujarat':'Gujarat','rajasthan':'Rajasthan','karnataka':'Karnataka',
            'ap':'AP','andhra pradesh':'AP','tamil nadu':'Tamil Nadu',
            'odisha':'Odisha','wb':'WB','west bengal':'WB','assam':'Assam',
            'kerala':'Kerala'
        }
        normalized = str(state).strip().lower()
        return mapping.get(normalized, normalized.title())

    def standardize_crop_name(crop: str) -> str:
        mapping = {'wheat':'Wheat','rice':'Rice','maize':'Maize',
                   'sugarcane':'Sugarcane','cotton':'Cotton','soybean':'Soybean'}
        normalized = str(crop).strip().lower()
        return mapping.get(normalized, normalized.title())

    df['state'] = df['state'].apply(standardize_state_name)
    df['crop'] = df['crop'].apply(standardize_crop_name)
    df = fill_missing_values(df)

    def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
        df['total_production_tonnes'] = (df['yield_kg_ha'] * df['area_ha']) / 1000
        df['farm_revenue_cr'] = (df['msp_rs_qtl'] * df['total_production_tonnes'] * 10) / 1e7
        df['Water_Stressed'] = ((df['rainfall_mm'] < 800) & (df['irrigation_pct'] < 30)).astype(bool)
        return df
    df = add_derived_columns(df)

    # save
    df.to_csv("crop_census.csv", index=False)

    # return summary for dashboard
    summary = {
        'rows': len(df),
        'columns': len(df.columns),
        'states': df['state'].nunique(),
        'crops': df['crop'].nunique(),
        'missing': df.isnull().sum().sum()
    }
    return df, summary

if __name__ == '__main__':
    df, summary = run_etl()
    print("ETL completed. Summary:", summary)