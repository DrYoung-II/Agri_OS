"""
crops.py
AI Crop Intelligence: planting decisions, fertilizer recommendations, weather risk,
pest/disease alerts, yield forecasting, and harvest timing for major Sub-Saharan
African staple and cash crops.

Yield, duration and NPK figures are typical extension-service averages (estimates for
decision support), and should be adapted with local agronomist advice where possible.
"""

import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules import theme, llm_engine, database, weather as weather_mod

CROP_DB = {
    "Maize": {
        "yield_t_per_ha": 2.5, "duration_days": 120,
        "npk_kg_per_ha": (120, 60, 60),
        "planting_window": {"West Africa": "April - June", "East Africa": "March - May / Oct - Dec",
                             "Southern Africa": "Nov - Dec"},
        "risks": ["Fall Armyworm (vegetative stage, warm/wet weather)", "Maize streak virus",
                  "Drought stress at tasseling"],
    },
    "Cassava": {
        "yield_t_per_ha": 12.0, "duration_days": 300,
        "npk_kg_per_ha": (50, 25, 100),
        "planting_window": {"West Africa": "March - May", "East Africa": "March - May",
                             "Southern Africa": "Oct - Dec"},
        "risks": ["Cassava mosaic disease", "Cassava mealybug", "Waterlogging at establishment"],
    },
    "Rice (Lowland)": {
        "yield_t_per_ha": 3.5, "duration_days": 120,
        "npk_kg_per_ha": (100, 40, 40),
        "planting_window": {"West Africa": "June - July", "East Africa": "March - May",
                             "Southern Africa": "Nov - Dec"},
        "risks": ["Rice blast", "Stem borers", "Water stress during flowering"],
    },
    "Sorghum": {
        "yield_t_per_ha": 1.8, "duration_days": 110,
        "npk_kg_per_ha": (60, 30, 30),
        "planting_window": {"West Africa": "May - July", "East Africa": "March - May",
                             "Southern Africa": "Nov - Dec"},
        "risks": ["Striga weed", "Birds at grain-fill", "Anthracnose"],
    },
    "Millet": {
        "yield_t_per_ha": 1.2, "duration_days": 90,
        "npk_kg_per_ha": (40, 20, 20),
        "planting_window": {"West Africa": "May - July", "East Africa": "March - May", "Southern Africa": "Nov - Dec"},
        "risks": ["Downy mildew", "Head smut", "Birds at grain-fill"],
    },
    "Groundnut": {
        "yield_t_per_ha": 1.5, "duration_days": 100,
        "npk_kg_per_ha": (20, 40, 40),
        "planting_window": {"West Africa": "May - June", "East Africa": "March - May", "Southern Africa": "Nov - Dec"},
        "risks": ["Groundnut rosette virus", "Leaf spot", "Aflatoxin risk if harvest delayed in wet weather"],
    },
    "Cowpea": {
        "yield_t_per_ha": 1.0, "duration_days": 75,
        "npk_kg_per_ha": (20, 30, 30),
        "planting_window": {"West Africa": "June - August", "East Africa": "March - May", "Southern Africa": "Dec - Jan"},
        "risks": ["Pod borer/Maruca", "Aphids", "Bacterial blight in wet conditions"],
    },
    "Tomato": {
        "yield_t_per_ha": 20.0, "duration_days": 90,
        "npk_kg_per_ha": (150, 100, 150),
        "planting_window": {"West Africa": "Year-round (irrigated) / Oct - Dec (rain-fed)",
                             "East Africa": "Year-round (irrigated)", "Southern Africa": "Aug - Oct"},
        "risks": ["Tuta absoluta (leaf miner)", "Bacterial wilt", "Blossom end rot in dry spells"],
    },
    "Yam": {
        "yield_t_per_ha": 10.0, "duration_days": 270,
        "npk_kg_per_ha": (60, 40, 100),
        "planting_window": {"West Africa": "Feb - April", "East Africa": "March - May", "Southern Africa": "n/a"},
        "risks": ["Yam anthracnose", "Nematodes", "Tuber rot in waterlogged soil"],
    },
}

REGIONS = ["West Africa", "East Africa", "Southern Africa"]

SOIL_QUALITY_FACTOR = {"Poor / degraded": 0.7, "Average": 1.0, "Good / fertile": 1.2}
FERTILIZER_USE_FACTOR = {"None": 0.75, "Partial (below recommendation)": 0.9, "Full recommended rate": 1.15}


def yield_forecast(crop, area_ha, soil_quality, fertilizer_use, rainfall_adequate=True):
    base_kg = CROP_DB[crop]["yield_t_per_ha"] * 1000
    factor = SOIL_QUALITY_FACTOR[soil_quality] * FERTILIZER_USE_FACTOR[fertilizer_use]
    if not rainfall_adequate:
        factor *= 0.75
    est_yield_per_ha = round(base_kg * factor, 0)
    total_yield = round(est_yield_per_ha * area_ha, 0)
    return est_yield_per_ha, total_yield


def fertilizer_recommendation(crop, area_ha):
    n, p, k = CROP_DB[crop]["npk_kg_per_ha"]
    return {"N (kg)": round(n * area_ha, 1), "P (kg)": round(p * area_ha, 1), "K (kg)": round(k * area_ha, 1)}


def harvest_date(planting_date: datetime.date, crop: str):
    return planting_date + datetime.timedelta(days=CROP_DB[crop]["duration_days"])


def render(farm, market_df, ollama_host, ollama_model, currency):
    theme.hero("🌾 AI Crop Intelligence",
               "Planting windows, fertilizer rates, weather risk, pest/disease alerts, "
               "yield forecasting and harvest timing.", "🌱")

    col1, col2 = st.columns(2)
    with col1:
        crop = st.selectbox("Crop", list(CROP_DB.keys()))
        region = st.selectbox("Region", REGIONS)
        area_ha = st.number_input("Farm/plot area (hectares)", min_value=0.1, value=1.0, step=0.1)
    with col2:
        planting_date = st.date_input("Planting date (planned or actual)", value=datetime.date.today())
        soil_quality = st.selectbox("Soil quality", list(SOIL_QUALITY_FACTOR.keys()), index=1)
        fertilizer_use = st.selectbox("Fertilizer use plan", list(FERTILIZER_USE_FACTOR.keys()), index=2)

    city = st.text_input("Nearest town/city (for weather-based risk check)", placeholder="e.g. Kaduna, Nigeria")

    run = st.button("🔍 Analyze Crop Plan", type="primary", use_container_width=True)
    if not run:
        return

    st.divider()
    info = CROP_DB[crop]
    rainfall_ok = True
    weather_notes = []

    if city:
        lat, lon, display = weather_mod.geocode_location(city)
        if lat:
            fc = weather_mod.get_forecast(lat, lon)
            weather_notes = weather_mod.farming_risk_notes(fc)
            if fc:
                total_rain = sum(fc.get("daily", {}).get("precipitation_sum", []) or [0])
                rainfall_ok = total_rain >= 5
        else:
            weather_notes = ["Could not find that location - check spelling or try 'City, Country'."]

    est_yield_per_ha, total_yield = yield_forecast(crop, area_ha, soil_quality, fertilizer_use, rainfall_ok)
    fert = fertilizer_recommendation(crop, area_ha)
    h_date = harvest_date(planting_date, crop)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Recommended planting window", info["planting_window"].get(region, "n/a"))
    m2.metric("Estimated yield/ha", f"{est_yield_per_ha:,.0f} kg")
    m3.metric("Total expected yield", f"{total_yield:,.0f} kg")
    m4.metric("Expected harvest date", h_date.strftime("%d %b %Y"))

    theme.card_open()
    st.markdown("**🧪 Fertilizer recommendation (total for plot):**")
    st.markdown(f"- Nitrogen (N): **{fert['N (kg)']} kg**  \n"
                f"- Phosphorus (P): **{fert['P (kg)']} kg**  \n"
                f"- Potassium (K): **{fert['K (kg)']} kg**")
    theme.card_close()

    theme.card_open()
    st.markdown("**🐛 Pest & disease watch for this crop:**")
    for r in info["risks"]:
        st.markdown(f"- {r}")
    theme.card_close()

    if weather_notes:
        theme.card_open()
        st.markdown("**☁️ Weather risk check:**")
        for n in weather_notes:
            st.markdown(f"- {n}")
        theme.card_close()

    # Simple yield-over-time growth visualization (illustrative S-curve)
    days = list(range(0, info["duration_days"] + 1, max(1, info["duration_days"] // 20)))
    progress = [min(1.0, (d / info["duration_days"]) ** 1.5) * total_yield for d in days]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=days, y=progress, mode="lines", fill="tozeroy",
                              line=dict(color=theme.ACCENT, width=3)))
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                       title="Projected biomass/yield accumulation", xaxis_title="Days after planting",
                       yaxis_title="Kg (cumulative, illustrative)", height=350)
    st.plotly_chart(fig, use_container_width=True)

    if farm and st.button("💾 Save this crop plot to Farm Records"):
        database.add_crop_plot(
            farm["id"], crop=crop, area_ha=area_ha, planting_date=planting_date.isoformat(),
            soil_type=soil_quality, fertilizer_used=fertilizer_use, notes=f"Region: {region}",
        )
        st.success("Crop plot saved to Farm Records.")

    computed_summary = (
        f"Crop: {crop}, {area_ha} ha in {region}. Planting date {planting_date}. "
        f"Soil quality: {soil_quality}, fertilizer plan: {fertilizer_use}. "
        f"Estimated yield: {est_yield_per_ha} kg/ha, total {total_yield} kg. "
        f"Fertilizer needed: {fert}. Expected harvest: {h_date}. "
        f"Weather notes: {weather_notes}. Key risks: {info['risks']}."
    )

    with st.expander("🧠 Ask the AI to explain this in plain language / WhatsApp-style"):
        if st.button("Generate AI explanation", key="crop_ai_explain"):
            system = llm_engine.SYSTEM_PROMPT_TEMPLATE.format(
                farm_context=llm_engine.build_farm_context({
                    "Farm": farm["name"] if farm else "Unnamed farm",
                    "Country": farm["country"] if farm else "",
                    "Computed crop analysis": computed_summary,
                })
            )
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": "Explain this crop plan to me simply, like you're advising "
                                             "me over WhatsApp, and tell me exactly what to do next."},
            ]
            st.write_stream(llm_engine.stream_chat(messages, model=ollama_model, host=ollama_host))
