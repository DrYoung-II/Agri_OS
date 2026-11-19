"""
livestock.py
AI Livestock Intelligence: poultry (broiler/layer), cattle, goats/sheep, pigs, fish (catfish/tilapia).

Features:
- Accurate growth curves and feed consumption schedules.
- Mortality tracking, benchmark comparisons, and disease symptom diagnostics.
- Optimal selling week calculator based on marginal cost of feed.
- Direct integration with Feed Inventory, Vaccination Calendars, and Batch Harvesting.
"""

import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules import theme, database, llm_engine

# Reference benchmarks for African poultry production
BROILER_DAILY_INTAKE_G = {1: 18, 2: 35, 3: 62, 4: 92, 5: 118, 6: 132, 7: 142, 8: 148}
BROILER_WEIGHT_KG = {0: 0.042, 1: 0.18, 2: 0.45, 3: 0.85, 4: 1.30, 5: 1.75, 6: 2.20, 7: 2.60, 8: 2.90}
BROILER_BENCHMARK_MORTALITY = {1: 1.0, 2: 1.8, 3: 2.5, 4: 3.2, 5: 3.8, 6: 4.3, 7: 4.8, 8: 5.2}

GENERIC_INTAKE_PCT_BW = {
    "Cattle (beef/dairy)": 0.025,
    "Goat/Sheep": 0.030,
    "Pig": 0.035,
    "Fish (Catfish/Tilapia, pond)": 0.035,
    "Poultry - Layer": 0.060,
}

GENERIC_ADG_KG = {
    "Cattle (beef/dairy)": 0.55,
    "Goat/Sheep": 0.09,
    "Pig": 0.45,
    "Fish (Catfish/Tilapia, pond)": 0.015,
    "Poultry - Layer": 0.005,
}

DISEASE_KEYWORDS = {
    "Newcastle Disease": ["twisted neck", "greenish diarrhea", "gasping", "sudden death", "drop in egg", "torticollis"],
    "Coccidiosis": ["bloody droppings", "blood in stool", "pale comb", "ruffled feathers", "huddled"],
    "Gumboro (IBD)": ["vent pecking", "trembling", "whitish diarrhea", "young bird deaths", "dehydration"],
    "Fowl Typhoid / Pullorum": ["yellow-green droppings", "swollen joints", "high fever", "pasty vent"],
    "Fowl Pox": ["warts on comb", "scabs on wattles", "difficulty swallowing", "nodules"],
    "African Swine Fever (ASF)": ["high pig mortality", "red blotches on belly/ears", "sudden pig death", "bloody diarrhea"],
    "Foot and Mouth Disease (FMD)": ["mouth blisters", "drooling saliva", "lameness cattle", "blisters on hooves"],
    "PPR (Peste des Petits Ruminants)": ["crusty nasal discharge", "mouth sores goat", "diarrhea goat sheep", "pneumonia"],
    "Catfish Columnaris / Fin Rot": ["fin rot", "white patches on head/skin", "sluggish fish swimming at surface"],
}


def estimate_broiler_feed(current_age_weeks: float, num_birds: int, duration_days: int):
    total_kg = 0.0
    age = current_age_weeks
    days_left = duration_days
    while days_left > 0:
        wk = min(8, max(1, round(age)))
        daily_g = BROILER_DAILY_INTAKE_G.get(wk, BROILER_DAILY_INTAKE_G[8])
        days_this_week = min(7, days_left)
        total_kg += (daily_g * days_this_week * num_birds) / 1000.0
        age += 1
        days_left -= days_this_week
    return round(total_kg, 1)


def projected_broiler_weight(age_weeks: float):
    wk_low = int(age_weeks)
    wk_high = min(8, wk_low + 1)
    frac = age_weeks - wk_low
    w_low = BROILER_WEIGHT_KG.get(wk_low, BROILER_WEIGHT_KG[8])
    w_high = BROILER_WEIGHT_KG.get(wk_high, BROILER_WEIGHT_KG[8])
    return round(w_low + (w_high - w_low) * frac, 3)


def broiler_growth_curve(max_week=8):
    weeks = list(range(0, max_week + 1))
    weights = [BROILER_WEIGHT_KG.get(w, BROILER_WEIGHT_KG[8]) for w in weeks]
    return weeks, weights


def assess_mortality_risk(species, current_age_weeks, observed_mortality_pct, heat_risk=False):
    if species == "Poultry - Broiler":
        wk = min(8, max(1, round(current_age_weeks)))
        benchmark = BROILER_BENCHMARK_MORTALITY.get(wk, 5.2)
    else:
        benchmark = 4.0

    delta = observed_mortality_pct - benchmark
    if heat_risk:
        delta += 1.5

    if delta <= 0.5:
        return "Low", benchmark, "good"
    elif delta <= 2.5:
        return "Moderate", benchmark, "warn"
    else:
        return "High", benchmark, "bad"


def assess_disease_risk(symptom_text: str):
    if not symptom_text or not symptom_text.strip():
        return []
    text = symptom_text.lower()
    hits = []
    for disease, keywords in DISEASE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                hits.append(disease)
                break
    return hits


def recommend_broiler_selling_week(feed_price_per_kg: float, market_price_per_kg_live: float):
    rows = []
    for wk in range(1, 9):
        gain = BROILER_WEIGHT_KG.get(wk, BROILER_WEIGHT_KG[8]) - BROILER_WEIGHT_KG.get(wk - 1, 0)
        feed_kg_week = BROILER_DAILY_INTAKE_G.get(wk, BROILER_DAILY_INTAKE_G[8]) * 7.0 / 1000.0
        marginal_cost_per_kg_gain = (feed_kg_week * feed_price_per_kg) / gain if gain > 0 else float("inf")
        profitable = marginal_cost_per_kg_gain < market_price_per_kg_live
        rows.append({
            "Week": wk,
            "Live Weight (kg)": BROILER_WEIGHT_KG.get(wk, BROILER_WEIGHT_KG[8]),
            "Feed that week (kg/bird)": round(feed_kg_week, 2),
            "Marginal cost / kg gain": round(marginal_cost_per_kg_gain, 2),
            "Profitable to feed further?": "✅ Yes" if profitable else "❌ No",
        })
    df = pd.DataFrame(rows)
    profitable_weeks = df[df["Profitable to feed further?"] == "✅ Yes"]["Week"].tolist()
    recommended = max(profitable_weeks) if profitable_weeks else 5
    return recommended, df


def generic_livestock_projection(species, num_animals, avg_weight_kg, feed_price_per_kg, duration_days):
    pct_bw = GENERIC_INTAKE_PCT_BW.get(species, 0.03)
    adg = GENERIC_ADG_KG.get(species, 0.2)
    daily_feed_per_animal = avg_weight_kg * pct_bw
    total_feed_kg = daily_feed_per_animal * duration_days * num_animals
    total_feed_cost = total_feed_kg * feed_price_per_kg
    total_weight_gain = adg * duration_days * num_animals
    final_avg_weight = avg_weight_kg + adg * duration_days
    return {
        "total_feed_kg": round(total_feed_kg, 1),
        "total_feed_cost": round(total_feed_cost, 2),
        "total_weight_gain_kg": round(total_weight_gain, 1),
        "final_avg_weight_kg": round(final_avg_weight, 2),
    }


def render(farm, market_df, ollama_host, ollama_model, currency):
    theme.hero(
        "🐔 AI Livestock Intelligence",
        "Feed planning, cost, growth curves, mortality tracking, disease alerts, and optimal selling age "
        "for poultry, cattle, goats, pigs, and fish.",
        "🐄"
    )

    tab_plan, tab_active = st.tabs(["🔍 Planning & Analysis Engine", "📋 Active Batches Manager"])

    with tab_plan:
        species = st.selectbox(
            "Livestock Type",
            ["Poultry - Broiler", "Poultry - Layer", "Cattle (beef/dairy)", "Goat/Sheep", "Pig",
             "Fish (Catfish/Tilapia, pond)"],
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            num_animals = st.number_input("Number of animals / birds", min_value=1, value=500, step=25)
        with col2:
            if species == "Poultry - Broiler":
                age_weeks = st.number_input("Current age (weeks)", min_value=0.0, max_value=8.0, value=4.0, step=0.5)
            else:
                avg_weight = st.number_input("Current average weight (kg)", min_value=0.05, value=150.0 if "Cattle" in species else (0.4 if "Fish" in species else 25.0))
        with col3:
            duration_days = st.number_input("Planning horizon (days)", min_value=1, value=14, step=1)

        st.markdown("##### Feed & Selling Prices")
        colf1, colf2 = st.columns(2)
        with colf1:
            feed_price = st.number_input(f"Feed price ({currency} per kg)", min_value=0.0, value=850.0, step=25.0,
                                          help="e.g. 25kg bag at 21,250 = 850/kg")
        with colf2:
            market_price = st.number_input(f"Market selling price ({currency} per kg live weight / bird)", min_value=0.0, value=2800.0, step=50.0)

        st.markdown("##### Health, Mortality & Weather Risk")
        colh1, colh2 = st.columns(2)
        with colh1:
            observed_mortality = st.number_input("Observed mortality so far (%)", min_value=0.0, max_value=100.0, value=2.0, step=0.1)
        with colh2:
            symptoms = st.text_input("Symptoms or disease flags observed (optional)",
                                      placeholder="e.g. bloody droppings, gasping, ruffled feathers, twisted neck")

        heat_risk = st.checkbox("Active heat stress conditions (temperature >32°C)", value=False)

        run = st.button("🔍 Run Livestock Analysis", type="primary", use_container_width=True)

        if run:
            st.divider()
            if species == "Poultry - Broiler":
                feed_needed = estimate_broiler_feed(age_weeks, num_animals, duration_days)
                feed_cost = round(feed_needed * feed_price, 2)
                current_weight = projected_broiler_weight(age_weeks)
                future_weight = projected_broiler_weight(age_weeks + duration_days / 7.0)
                total_live_weight_future = round(future_weight * num_animals, 1)
                expected_revenue = round(total_live_weight_future * market_price, 2)
                expected_profit = round(expected_revenue - feed_cost, 2)

                risk_level, benchmark, risk_kind = assess_mortality_risk(species, age_weeks, observed_mortality, heat_risk)
                recommended_week, sell_df = recommend_broiler_selling_week(feed_price, market_price)
                disease_hits = assess_disease_risk(symptoms)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Feed Needed", f"{feed_needed:,.0f} kg ({feed_needed/25.0:.1f} bags)")
                m2.metric("Feed Cost", f"{currency} {feed_cost:,.0f}")
                m3.metric(f"Weight in {duration_days}d", f"{future_weight:.2f} kg/bird")
                m4.metric("Operating Margin", f"{currency} {expected_profit:,.0f}")

                theme.card_open()
                st.markdown(f"**Mortality Risk Status:** {theme.badge(risk_level, risk_kind)} (Benchmark for this age ≈ {benchmark:.1f}%)", unsafe_allow_html=True)
                if disease_hits:
                    st.markdown(f"**⚠️ Suspected Health Issues from Symptoms:** `{', '.join(disease_hits)}`. Contact an extension agent or vet immediately.")
                st.markdown(
                    f"**Optimal Selling Week:** **Week {recommended_week}** (~{BROILER_WEIGHT_KG.get(recommended_week, 2.2):.2f} kg/bird). "
                    f"Beyond week {recommended_week}, the cost of feed per kg gained exceeds your selling price of {currency} {market_price:,.0f}/kg."
                )
                theme.card_close()

                # Visual growth curve
                weeks, weights = broiler_growth_curve()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=weeks, y=weights, mode="lines+markers", name="Live Weight (kg)", line=dict(color=theme.ACCENT, width=3)))
                fig.add_vline(x=recommended_week, line_dash="dash", line_color=theme.GOLD, annotation_text=f"Sell at Week {recommended_week}", annotation_position="top")
                fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  title="Broiler Growth Curve & Recommended Sell Point", xaxis_title="Age (Weeks)", yaxis_title="Weight (kg)", height=350)
                st.plotly_chart(fig, use_container_width=True)

                computed_summary = (
                    f"Broiler batch of {num_animals} birds, currently {age_weeks} weeks old. "
                    f"Feed needed for {duration_days} days: {feed_needed} kg costing {currency} {feed_cost:,.0f}. "
                    f"Projected weight: {future_weight} kg. Selling recommendation: Week {recommended_week}. "
                    f"Mortality risk: {risk_level} ({observed_mortality}% vs benchmark {benchmark}%)."
                )

            else:
                avg_w = avg_weight
                proj = generic_livestock_projection(species, num_animals, avg_w, feed_price, duration_days)
                expected_revenue = round(proj["final_avg_weight_kg"] * num_animals * market_price, 2)
                expected_profit = round(expected_revenue - proj["total_feed_cost"], 2)
                risk_level, benchmark, risk_kind = assess_mortality_risk(species, 0, observed_mortality, heat_risk)
                disease_hits = assess_disease_risk(symptoms)

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Feed Needed", f"{proj['total_feed_kg']:,.0f} kg")
                m2.metric("Feed Cost", f"{currency} {proj['total_feed_cost']:,.0f}")
                m3.metric(f"Projected Avg Weight", f"{proj['final_avg_weight_kg']:.2f} kg")
                m4.metric("Operating Margin", f"{currency} {expected_profit:,.0f}")

                theme.card_open()
                st.markdown(f"**Health & Mortality Status:** {theme.badge(risk_level, risk_kind)}", unsafe_allow_html=True)
                if disease_hits:
                    st.markdown(f"**⚠️ Suspected Condition:** `{', '.join(disease_hits)}`. Consult veterinary officer.")
                st.markdown(f"**Projected Output Value:** **{currency} {expected_revenue:,.0f}** after {duration_days} days.")
                theme.card_close()

                computed_summary = (
                    f"{species} batch: {num_animals} head/stock. Current avg weight {avg_w} kg. "
                    f"Feed needed for {duration_days} days: {proj['total_feed_kg']} kg costing {currency} {proj['total_feed_cost']:,.0f}. "
                    f"Projected final weight: {proj['final_avg_weight_kg']} kg."
                )

            # Save batch to farm records
            if farm:
                if st.button("💾 Save as Active Batch in Farm Records", use_container_width=True):
                    bid = database.add_livestock_batch(
                        farm["id"],
                        species=species,
                        breed="",
                        stage="",
                        count=num_animals,
                        initial_count=num_animals,
                        avg_weight_kg=locals().get("avg_weight", locals().get("current_weight", 0)),
                        age_weeks=locals().get("age_weeks", 0),
                        start_date=datetime.date.today().isoformat(),
                        feed_type="Commercial Feed",
                        feed_price_per_kg=feed_price,
                        notes=symptoms
                    )
                    st.success(f"✅ Batch #{bid} ({species} - {num_animals} count) saved! Standard African vaccination schedule generated automatically.")

    with tab_active:
        if not farm:
            st.info("Select an active farm to manage ongoing batches.")
        else:
            active_batches = database.get_livestock_batches(farm["id"], status="active")
            if not active_batches:
                st.info("No active livestock batches found. Create one in the Planning tab.")
            else:
                for b in active_batches:
                    with st.expander(f"📦 Batch #{b['id']}: {b['species']} ({b['count']} remaining) — Started {b['start_date']}", expanded=True):
                        # Mortality summary
                        mort_summary = database.get_batch_mortality_summary(b["id"])
                        c_info1, c_info2, c_info3, c_info4 = st.columns(4)
                        c_info1.metric("Current Count", f"{b['count']} animals")
                        c_info2.metric("Total Losses", f"{mort_summary['total_dead']} lost")
                        c_info3.metric("Mortality Rate", f"{mort_summary['mortality_pct']}%")
                        c_info4.metric("Age / Stage", f"{b['age_weeks']} weeks" if b['age_weeks'] else "Growing")

                        # Sub-sections: Log Mortality, Vaccination Schedule, Harvest Batch
                        st.markdown("---")
                        col_mort, col_vac = st.columns(2)

                        with col_mort:
                            st.markdown("##### 💀 Log Mortality / Death")
                            with st.form(f"mort_form_{b['id']}", clear_on_submit=True):
                                m_count = st.number_input("Number lost", min_value=1, max_value=max(1, b["count"]), value=1, step=1)
                                m_cause = st.text_input("Observed Symptoms / Suspected Cause", placeholder="e.g. Heat exhaustion, bloody stool")
                                m_action = st.text_input("Action Taken", placeholder="e.g. Administered electrolytes, isolated birds")
                                m_date = st.date_input("Date", value=datetime.date.today(), key=f"m_date_{b['id']}")
                                if st.form_submit_button("Log Mortality"):
                                    database.log_mortality(b["id"], m_date.isoformat(), m_count, m_cause, m_action)
                                    st.success(f"Recorded loss of {m_count} animals. Active count updated.")
                                    st.rerun()

                        with col_vac:
                            st.markdown("##### 💉 Vaccination & Preventive Health")
                            vac_list = database.get_vaccination_schedule(b["id"])
                            if vac_list:
                                for v in vac_list[:5]:
                                    v_icon = "✅" if v["status"] == "completed" else "⏳"
                                    vc1, vc2 = st.columns([3, 1])
                                    vc1.markdown(f"{v_icon} **{v['vaccine_name']}** (Due: {v['due_date']})")
                                    if v["status"] == "pending":
                                        if vc2.button("Done", key=f"vac_done_{v['id']}"):
                                            database.mark_vaccination_status(v["id"], "completed")
                                            st.rerun()
                            else:
                                st.caption("No schedule recorded.")

                        st.markdown("---")
                        st.markdown("##### 🏁 Harvest / Complete Batch Sale")
                        with st.form(f"harvest_form_{b['id']}"):
                            hc1, hc2, hc3 = st.columns(3)
                            units_sold = hc1.number_input("Total animals sold", min_value=1, max_value=max(1, b["count"]), value=b["count"])
                            total_wt = hc2.number_input("Total live weight sold (kg)", min_value=0.0, value=float(b["count"] * 2.2))
                            sell_price = hc3.number_input(f"Average selling price ({currency} per unit/kg)", min_value=0.0, value=2800.0)
                            h_notes = st.text_input("Buyer / Market notes", placeholder="e.g. Sold to local processing off-taker")

                            if st.form_submit_button("Record Batch Harvest & Calculate Profit", type="primary"):
                                est_feed_cost = (b["count"] * 4.2 * (b["feed_price_per_kg"] or 850.0))
                                database.record_batch_harvest(
                                    b["id"], datetime.date.today().isoformat(), units_sold,
                                    total_wt, sell_price, est_feed_cost, 0.0, h_notes
                                )
                                st.success("🎉 Batch harvest successfully logged and archived! Transaction added to Farm Ledger.")
                                st.rerun()
