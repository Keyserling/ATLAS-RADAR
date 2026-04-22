import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.title("Atlas Radar")

# --- Dummy Data (ersetzt später deine echte Logik wieder) ---
data = [
    {"Title": "Obesity Phase 2 Trial", "Sponsor": "Lilly", "Phase": "Phase 2", "Enrollment": 300},
    {"Title": "Neuro Biomarker Study", "Sponsor": "Roche", "Phase": "Phase 1", "Enrollment": 120},
    {"Title": "Cardio Outcomes Study", "Sponsor": "Novartis", "Phase": "Phase 3", "Enrollment": 5000},
    {"Title": "Metabolic Early Discovery", "Sponsor": "Pfizer", "Phase": "Phase 1", "Enrollment": 80},
]

df = pd.DataFrame(data)

# --- Simple scoring logic (sauber & stabil) ---
def compute_score(row):
    score = 0

    if "Phase 3" in row["Phase"]:
        score += 50
    elif "Phase 2" in row["Phase"]:
        score += 40
    else:
        score += 20

    if row["Enrollment"] > 1000:
        score += 40
    elif row["Enrollment"] > 200:
        score += 20
    else:
        score += 10

    return score

df["TriggerScore"] = df.apply(compute_score, axis=1)

# --- Normalize to 1–10 ---
max_score = df["TriggerScore"].max()

if max_score > 0:
    df["Score"] = (df["TriggerScore"] / max_score * 10).round(1)
else:
    df["Score"] = 0

# --- Color logic ---
def color_score(val):
    if val >= 8:
        return "background-color: #2ecc71; color: white;"
    elif val >= 5:
        return "background-color: #f1c40f; color: black;"
    else:
        return "background-color: #e74c3c; color: white;"

styled_df = df.style.applymap(color_score, subset=["Score"])

# --- Output ---
st.dataframe(styled_df, use_container_width=True)
