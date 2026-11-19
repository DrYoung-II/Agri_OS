"""
Agri_OS Africa - The AI Operating System for African Agriculture
==================================================================
Main Streamlit entry point.

Run locally with:
    streamlit run app.py --server.port 8502

Features:
- Offline-capable decision support via local Llama 3.2 (Ollama).
- Farm Records: Batches, Feed Inventory, Vaccinations, Plots, Ledger.
- Profitability Engine & Custom Feed Formulator.
- WhatsApp & SMS Gateway with interactive smartphone simulation.
"""

import datetime
import pandas as pd
import streamlit as st

from modules import theme, database, llm_engine, market_data, gateway
from modules import livestock, crops, profitability, weather as weather_mod

# ---------------------------------------------------------------------------
# Page config + theme (must run first)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Agri_OS Africa",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)
theme.apply_theme()
database.init_db()

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
defaults = {
    "ollama_host": llm_engine.DEFAULT_HOST,
    "ollama_model": llm_engine.DEFAULT_MODEL,
    "current_farm_id": None,
    "currency": "NGN",
    "page": "🏠 Dashboard",
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

market_df = market_data.load_market_df()


def current_farm():
    if st.session_state["current_farm_id"] is None:
        farms = database.get_farms()
        if farms:
            st.session_state["current_farm_id"] = farms[0]["id"]
            st.session_state["currency"] = farms[0]["currency"] or "NGN"
            return farms[0]
        return None
    return database.get_farm(st.session_state["current_farm_id"])


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center; padding: 10px 0 4px 0;">
            <div style="font-size: 2.4rem;">🌾</div>
            <div style="font-size:1.35rem; font-weight:800; color:#eafaf1;">Agri_OS <span style="color:#52b788;">Africa</span></div>
            <div style="font-size:0.78rem; color:#9fc9b3;">AI Operating System for African Agriculture</div>
        </div>
        <hr>
        """,
        unsafe_allow_html=True,
    )

    farms = database.get_farms()
    farm_names = ["➕ Create new farm..."] + [f"{f['name']} ({f['country']})" for f in farms]
    default_idx = 0
    if st.session_state["current_farm_id"]:
        for i, f in enumerate(farms):
            if f["id"] == st.session_state["current_farm_id"]:
                default_idx = i + 1
    choice = st.selectbox("🚜 Active Farm", farm_names, index=default_idx)

    if choice == "➕ Create new farm...":
        with st.form("new_farm_form"):
            name = st.text_input("Farm Name (e.g. GreenPastures Farm)")
            country = st.selectbox("Country", market_data.COUNTRIES)
            region = st.selectbox("Region", ["West Africa", "East Africa", "Southern Africa"])
            farm_type = st.selectbox("Primary Focus", ["Mixed", "Poultry", "Crops", "Livestock", "Fish/Aquaculture"])
            phone = st.text_input("WhatsApp Phone (e.g. +2348012345678)", placeholder="+2348000000000")
            if st.form_submit_button("Create Farm", use_container_width=True):
                if name:
                    curr = market_data.CURRENCY_BY_COUNTRY.get(country, "NGN")
                    fid = database.create_farm(name, country, region, farm_type, curr, phone_number=phone)
                    st.session_state["current_farm_id"] = fid
                    st.session_state["currency"] = curr
                    st.rerun()
                else:
                    st.warning("Please enter a farm name.")
    else:
        selected_farm = farms[farm_names.index(choice) - 1]
        st.session_state["current_farm_id"] = selected_farm["id"]
        st.session_state["currency"] = selected_farm["currency"] or "NGN"

    st.markdown("<br>", unsafe_allow_html=True)

    st.session_state["page"] = st.radio(
        "Navigate",
        [
            "🏠 Dashboard",
            "💬 AI Assistant",
            "🐔 Livestock Intelligence",
            "🌾 Crop Intelligence",
            "💰 Profitability Engine",
            "📲 WhatsApp & SMS Gateway",
            "☁️ Weather & Climate",
            "🏷️ Market Prices",
            "📒 Farm Records",
            "⚙️ Settings"
        ],
        label_visibility="collapsed",
    )

    st.markdown("<hr>", unsafe_allow_html=True)
    ok = llm_engine.is_ollama_running(st.session_state["ollama_host"])
    status_badge = theme.badge("● Llama 3.2 Online", "good") if ok else theme.badge("● Llama 3.2 Offline", "bad")
    st.markdown(status_badge, unsafe_allow_html=True)
    if not ok:
        st.caption("Start Ollama (`ollama serve`) and pull `llama3.2` to enable the AI assistant.")

farm = current_farm()
currency = st.session_state["currency"]
ollama_host = st.session_state["ollama_host"]
ollama_model = st.session_state["ollama_model"]
page = st.session_state["page"]

# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------
if page == "🏠 Dashboard":
    theme.hero(
        f"Agri_OS Africa — {farm['name'] if farm else 'Farm Operations'}",
        "Actionable decision support combining your farm records, local feed & market prices, "
        "weather risks, mortality tracking, and farm economics.",
        "🌍",
    )

    if not farm:
        st.info("👈 Create your first farm in the sidebar to unlock personalized recommendations and farm records.")
    else:
        batches = database.get_livestock_batches(farm["id"], status="active")
        plots = database.get_crop_plots(farm["id"], status="active")
        txs = database.get_transactions(farm["id"])
        income = sum(t["amount"] for t in txs if t["tx_type"] == "income")
        expense = sum(t["amount"] for t in txs if t["tx_type"] == "expense")
        net = income - expense

        # Top KPI Metrics
        c1, c2, c3, c4 = st.columns(4)
        total_animals = sum(b["count"] for b in batches)
        c1.metric("Active Livestock", f"{total_animals:,} head/birds", delta=f"{len(batches)} batches")
        c2.metric("Active Crop Plots", f"{len(plots)} plots", delta=f"{sum(p['area_ha'] for p in plots):.1f} ha total")
        c3.metric("Net Cash Position", f"{currency} {net:,.0f}", delta="Inflow vs Outflow", delta_color="normal" if net >= 0 else "inverse")
        c4.metric("Operating Country", f"{farm['country']}", delta=f"{farm['region']}")

        # Urgent Operational Alerts Section
        low_feeds = database.get_low_feed_alerts(farm["id"])
        upcoming_vacs = database.get_upcoming_vaccinations_for_farm(farm["id"], days_ahead=7)

        if low_feeds or upcoming_vacs:
            st.markdown("---")
            if low_feeds:
                for lf in low_feeds:
                    st.error(f"⚠️ **Low Feed Alert:** `{lf['feed_name']}` has only **{lf['quantity_bags']} bags** ({lf['total_kg']:.0f} kg) remaining in store. Order restock soon.")
            if upcoming_vacs:
                for uv in upcoming_vacs:
                    st.warning(f"⏰ **Vaccination Due Soon:** `{uv['vaccine_name']}` for **Batch #{uv['batch_id']} ({uv['species']})** is due on **{uv['due_date']}**.")

        st.markdown("---")
        colA, colB = st.columns([1.4, 1])
        with colA:
            theme.card_open()
            st.markdown("#### 💬 Ask Agri_OS Extension Officer")
            st.caption("Ask specific numeric questions grounded in your live farm data:")
            quick_q = st.text_input(
                "Your question", key="quick_dashboard_q", label_visibility="collapsed",
                placeholder="e.g. My broiler feed cost rose 15%. What should I sell at to protect my margin?"
            )
            if st.button("Consult Extension Advisor", key="dashboard_ask", use_container_width=True) and quick_q:
                st.session_state["_pending_question"] = quick_q
                st.session_state["page"] = "💬 AI Assistant"
                st.rerun()

            st.markdown(
                """
                <div style="font-size:0.82rem; color:#9fc9b3; margin-top:8px;">
                    💡 <b>Popular farmer inquiries:</b><br>
                    • <i>"Estimate feed requirements for my 500 broilers for the next 2 weeks."</i><br>
                    • <i>"It is 35°C outside. How do I prevent heat stroke mortality in my poultry house?"</i><br>
                    • <i>"How much can I save by home-mixing maize and soya bean meal?"</i>
                </div>
                """,
                unsafe_allow_html=True
            )
            theme.card_close()

        with colB:
            theme.card_open()
            st.markdown("#### 📌 Farm Quick Actions")
            qa1, qa2 = st.columns(2)
            if qa1.button("🐔 New Batch", use_container_width=True):
                st.session_state["page"] = "🐔 Livestock Intelligence"
                st.rerun()
            if qa2.button("💰 Calculate Profit", use_container_width=True):
                st.session_state["page"] = "💰 Profitability Engine"
                st.rerun()
            if qa1.button("🥣 Formulate Feed", use_container_width=True):
                st.session_state["page"] = "💰 Profitability Engine"
                st.rerun()
            if qa2.button("📲 Open WhatsApp", use_container_width=True):
                st.session_state["page"] = "📲 WhatsApp & SMS Gateway"
                st.rerun()
            theme.card_close()

        # Active Batches & Plots Overview
        col_b_list, col_p_list = st.columns(2)
        with col_b_list:
            if batches:
                theme.card_open()
                st.markdown("#### 🐔 Active Livestock Batches")
                for b in batches[:4]:
                    mort = database.get_batch_mortality_summary(b["id"])
                    st.markdown(
                        f"- **Batch #{b['id']}: {b['species']}** — {b['count']} birds/head (mortality: {mort['mortality_pct']}%), "
                        f"started {b['start_date']}"
                    )
                theme.card_close()

        with col_p_list:
            if plots:
                theme.card_open()
                st.markdown("#### 🌾 Active Crop Plots")
                for p in plots[:4]:
                    st.markdown(f"- **Plot #{p['id']}: {p['crop']}** — {p['area_ha']} ha, planted {p['planting_date']} ({p['soil_type']})")
                theme.card_close()

# ---------------------------------------------------------------------------
# AI ASSISTANT (chat)
# ---------------------------------------------------------------------------
elif page == "💬 AI Assistant":
    theme.hero(
        "💬 Agri_OS AI Extension Advisor",
        "Natural-language advice grounded in your live farm records, active batches, "
        "feed inventory, and local commodity prices. Powered by your local offline Llama 3.2 model.",
        "🤖"
    )

    if not llm_engine.is_ollama_running(ollama_host):
        st.error(
            "Llama 3.2 is not reachable. Make sure Ollama is running (`ollama serve`) and `ollama pull llama3.2` is complete."
        )

    farm_id_key = farm["id"] if farm else "no_farm"
    history_key = f"chat_history_{farm_id_key}"
    if history_key not in st.session_state:
        if farm:
            st.session_state[history_key] = database.get_chat_history(farm["id"])
        else:
            st.session_state[history_key] = []

    # Voice input (beta)
    with st.expander("🎙️ Voice Input (Beta)"):
        st.caption("Record an audio voice note describing your problem. Uses speech recognition.")
        audio = st.audio_input("Record voice question")
        if audio is not None and st.button("Transcribe & Ask"):
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with sr.AudioFile(audio) as source:
                    audio_data = r.record(source)
                text = r.recognize_google(audio_data)
                st.session_state["_pending_question"] = text
                st.success(f"Heard: \"{text}\"")
            except Exception as e:
                st.warning(f"Speech recognition notice: {e}")

    for msg in st.session_state[history_key]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pending = st.session_state.pop("_pending_question", None)
    user_input = st.chat_input("Ask about feed, selling week, symptoms, NPK rates, or profit...")
    question = pending or user_input

    if question:
        st.session_state[history_key].append({"role": "user", "content": question})
        if farm:
            database.save_chat_message(farm["id"], "user", question, channel="web")
        with st.chat_message("user"):
            st.markdown(question)

        # Build comprehensive farm context
        if farm:
            context_str, curr = llm_engine.build_holistic_farm_context(farm["id"])
        else:
            context_str, curr = "No active farm selected.", currency

        sample_prices = market_df[market_df["country"] == farm["country"]] if farm else market_df.head(6)
        price_snippet = "; ".join(f"{r['commodity']}: {r['price']} {r['currency']}/{r['unit']}" for _, r in sample_prices.iterrows())
        context_str += f"\nLocal Market Benchmarks: {price_snippet}"

        system_prompt = llm_engine.SYSTEM_PROMPT_TEMPLATE.format(currency=curr, farm_context=context_str)
        messages = [{"role": "system", "content": system_prompt}]
        messages += [{"role": m["role"], "content": m["content"]} for m in st.session_state[history_key][-8:]]

        with st.chat_message("assistant"):
            full_response = st.write_stream(
                llm_engine.stream_chat(messages, model=ollama_model, host=ollama_host)
            )
        st.session_state[history_key].append({"role": "assistant", "content": full_response})
        if farm:
            database.save_chat_message(farm["id"], "assistant", full_response, channel="web")

    if st.button("🗑️ Clear Conversation History"):
        st.session_state[history_key] = []
        if farm:
            database.clear_chat_history(farm["id"])
        st.rerun()

# ---------------------------------------------------------------------------
# LIVESTOCK
# ---------------------------------------------------------------------------
elif page == "🐔 Livestock Intelligence":
    livestock.render(farm, market_df, ollama_host, ollama_model, currency)

# ---------------------------------------------------------------------------
# CROPS
# ---------------------------------------------------------------------------
elif page == "🌾 Crop Intelligence":
    crops.render(farm, market_df, ollama_host, ollama_model, currency)

# ---------------------------------------------------------------------------
# PROFITABILITY & FEED FORMULATOR
# ---------------------------------------------------------------------------
elif page == "💰 Profitability Engine":
    profitability.render(farm, market_df, ollama_host, ollama_model, currency)

# ---------------------------------------------------------------------------
# WHATSAPP & SMS GATEWAY
# ---------------------------------------------------------------------------
elif page == "📲 WhatsApp & SMS Gateway":
    gateway.render_gateway_simulator(farm, currency, ollama_host, ollama_model)

# ---------------------------------------------------------------------------
# WEATHER
# ---------------------------------------------------------------------------
elif page == "☁️ Weather & Climate":
    theme.hero("☁️ Weather & Climate Risk", "Free 7-day forecast via Open-Meteo, with plain-language farming risk flags.", "🌦️")
    default_city = "Ibadan, Nigeria" if not farm else f"{farm.get('region', 'Ibadan')}, {farm.get('country', 'Nigeria')}"
    city = st.text_input("Town / City / Region", value=default_city)
    if st.button("Get Agricultural Weather Forecast", type="primary") and city:
        lat, lon, display = weather_mod.geocode_location(city)
        if lat is None:
            st.error("Location not found. Try 'City, Country' format.")
        else:
            st.success(f"Forecast for **{display}**")
            fc = weather_mod.get_forecast(lat, lon)
            if fc:
                current = fc.get("current", {})
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Current Temperature", f"{current.get('temperature_2m', '-')} °C")
                c2.metric("Relative Humidity", f"{current.get('relative_humidity_2m', '-')}%")
                c3.metric("Wind Speed", f"{current.get('wind_speed_10m', '-')} km/h")
                c4.metric("Precipitation Now", f"{current.get('precipitation', '-')} mm")

                daily = fc.get("daily", {})
                df = pd.DataFrame({
                    "Date": daily.get("time", []),
                    "Max °C": daily.get("temperature_2m_max", []),
                    "Min °C": daily.get("temperature_2m_min", []),
                    "Rain (mm)": daily.get("precipitation_sum", []),
                    "Max Wind (km/h)": daily.get("wind_speed_10m_max", []),
                })
                st.dataframe(df, use_container_width=True, hide_index=True)

                theme.card_open()
                st.markdown("**🌾 Farming & Livestock Risk Alerts This Week:**")
                for note in weather_mod.farming_risk_notes(fc):
                    st.markdown(f"- {note}")
                theme.card_close()
            else:
                st.error("Could not fetch forecast — check internet connectivity.")

# ---------------------------------------------------------------------------
# MARKET PRICES
# ---------------------------------------------------------------------------
elif page == "🏷️ Market Prices":
    theme.hero(
        "🏷️ Market & Feed Prices",
        "Editable local price sheet across African markets. The AI Assistant and calculators "
        "use these values directly to evaluate feed costs and profit margins.",
        "💵"
    )
    edited = st.data_editor(market_df, use_container_width=True, num_rows="dynamic", hide_index=True)
    if st.button("💾 Save Market Price Updates", type="primary"):
        market_data.save_market_df(edited)
        st.success("✅ Market prices updated successfully! All models will now compute using these updated prices.")
        st.rerun()

# ---------------------------------------------------------------------------
# FARM RECORDS
# ---------------------------------------------------------------------------
elif page == "📒 Farm Records":
    theme.hero("📒 Farm Records & Inventory", "Comprehensive logs of batches, feed inventory, vaccination schedules, and harvested sales.", "🗂️")
    if not farm:
        st.info("Please create or select an active farm in the sidebar first.")
    else:
        st.markdown(f"### {farm['name']} — {farm['country']} ({farm.get('region', '')})")
        
        tab_b, tab_inv, tab_vac, tab_p, tab_h = st.tabs([
            "🐔 Livestock Batches",
            "📦 Feed Inventory",
            "💉 Vaccination Calendar",
            "🌾 Crop Plots",
            "🏁 Harvested Batches"
        ])

        with tab_b:
            batches = database.get_livestock_batches(farm["id"])
            if batches:
                for b in batches:
                    mort = database.get_batch_mortality_summary(b["id"])
                    with st.container():
                        theme.card_open()
                        c1, c2 = st.columns([4, 1])
                        status_str = f"[{b['status'].upper()}]" if b['status'] != 'active' else "🟢 Active"
                        c1.markdown(
                            f"**Batch #{b['id']}: {b['species']}** ({b['breed'] or 'Local/Standard'}) — "
                            f"{status_str} | **{b['count']}** remaining (Started: {mort['initial_count']}, Dead: {mort['total_dead']} [{mort['mortality_pct']}% mortality]). "
                            f"Started: {b['start_date']}. Feed: {b['feed_type']} @ {currency} {b['feed_price_per_kg'] or 0}/kg."
                        )
                        if c2.button("🗑️ Delete Batch", key=f"del_batch_rec_{b['id']}"):
                            database.delete_livestock_batch(b["id"])
                            st.rerun()
                        theme.card_close()
            else:
                st.caption("No livestock batches recorded yet. Add one in the Livestock Intelligence page.")

        with tab_inv:
            st.markdown("##### 📦 Feed & Ingredient Inventory in Store")
            with st.form("new_inv_form", clear_on_submit=True):
                ic1, ic2, ic3, ic4 = st.columns(4)
                feed_n = ic1.text_input("Feed / Ingredient Name", placeholder="e.g. Broiler Finisher Pellets")
                f_cat = ic2.selectbox("Category", ["Commercial Feed", "Raw Ingredient (Maize, Soya, Offal)", "Premix & Minerals", "Medication"])
                f_bags = ic3.number_input("Quantity (Bags / Units)", min_value=0.5, value=10.0, step=1.0)
                f_bag_wt = ic4.number_input("Weight per Bag (kg)", min_value=1.0, value=25.0, step=5.0)
                
                ic5, ic6 = st.columns(2)
                f_cost = ic5.number_input(f"Cost per Bag ({currency})", min_value=0.0, value=21500.0, step=500.0)
                f_alert = ic6.number_input("Low Stock Alert Threshold (Bags)", min_value=1.0, value=3.0, step=1.0)

                if st.form_submit_button("➕ Add to Inventory", use_container_width=True) and feed_n:
                    database.add_feed_inventory_item(farm["id"], feed_n, f_cat, f_bags, f_bag_wt, f_cost, f_alert)
                    st.success(f"Added {f_bags} bags of {feed_n} to inventory.")
                    st.rerun()

            inv_items = database.get_feed_inventory(farm["id"])
            if inv_items:
                for item in inv_items:
                    theme.card_open()
                    cols = st.columns([3, 2, 1])
                    alert_tag = "⚠️ LOW STOCK" if item["quantity_bags"] <= item["minimum_alert_bags"] else "✅ In Stock"
                    cols[0].markdown(f"**{item['feed_name']}** ({item['category']}) — `{alert_tag}`")
                    cols[1].markdown(f"**{item['quantity_bags']:.1f} bags** ({item['total_kg']:.0f} kg) @ {currency} {item['cost_per_bag']:,.0f}/bag")
                    if cols[2].button("🗑️ Remove", key=f"del_inv_{item['id']}"):
                        database.delete_feed_inventory_item(item["id"])
                        st.rerun()
                    theme.card_close()
            else:
                st.caption("No feed inventory logged yet.")

        with tab_vac:
            st.markdown("##### 💉 Farm-Wide Vaccination & Preventive Health Schedule")
            all_vacs = database.get_upcoming_vaccinations_for_farm(farm["id"], days_ahead=60)
            if all_vacs:
                for v in all_vacs:
                    theme.card_open()
                    vc1, vc2, vc3 = st.columns([3, 2, 1])
                    vc1.markdown(f"**{v['vaccine_name']}** for **Batch #{v['batch_id']} ({v['species']})**")
                    vc2.markdown(f"Target Disease: `{v['target_disease']}` | Due Date: **{v['due_date']}**")
                    if vc3.button("Mark Completed", key=f"vac_m_done_{v['id']}"):
                        database.mark_vaccination_status(v["id"], "completed")
                        st.success("Marked as administered.")
                        st.rerun()
                    theme.card_close()
            else:
                st.caption("No pending vaccinations scheduled for the next 60 days.")

        with tab_p:
            plots = database.get_crop_plots(farm["id"])
            if plots:
                for p in plots:
                    theme.card_open()
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(
                        f"**Plot #{p['id']}: {p['crop']}** — {p['area_ha']} ha, planted {p['planting_date']}. "
                        f"Soil: {p['soil_type']}, Fertilizer: {p['fertilizer_used']}. Notes: {p['notes'] or '-'}"
                    )
                    if c2.button("🗑️ Delete Plot", key=f"del_plot_rec_{p['id']}"):
                        database.delete_crop_plot(p["id"])
                        st.rerun()
                    theme.card_close()
            else:
                st.caption("No crop plots recorded yet. Add one in the Crop Intelligence page.")

        with tab_h:
            st.markdown("##### 🏁 Completed & Harvested Batches (Performance & Net Returns)")
            harvests = database.get_batch_harvests(farm["id"])
            if harvests:
                for h in harvests:
                    theme.card_open()
                    st.markdown(
                        f"**Batch #{h['batch_id']}: {h['species']} ({h['breed'] or 'Standard'})** — Harvested on **{h['harvest_date']}**\n\n"
                        f"- Total Sold: **{h['units_sold']} units** ({h['total_weight_kg']:.1f} kg total live weight, avg {h['avg_weight_kg']:.2f} kg/unit)\n"
                        f"- Selling Price: **{currency} {h['price_per_unit_or_kg']:,.0f}** | Gross Revenue: **{currency} {h['total_revenue']:,.0f}**\n"
                        f"- Net Profit: **{currency} {h['net_profit']:,.0f}**"
                    )
                    theme.card_close()
            else:
                st.caption("No batches marked as harvested yet.")

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
elif page == "⚙️ Settings":
    theme.hero("⚙️ Settings & Integrations", "Configure your local Llama 3.2 connection, WhatsApp phone linkage, and preferences.", "🛠️")

    theme.card_open()
    st.markdown("#### 🤖 Local AI Model Connection (Ollama / Llama 3.2)")
    st.session_state["ollama_host"] = st.text_input("Ollama Host URL", value=st.session_state["ollama_host"])
    models = llm_engine.list_local_models(st.session_state["ollama_host"])
    if models:
        st.session_state["ollama_model"] = st.selectbox(
            "Selected Local Model", models,
            index=models.index(st.session_state["ollama_model"]) if st.session_state["ollama_model"] in models else 0
        )
    else:
        st.session_state["ollama_model"] = st.text_input("Model Name", value=st.session_state["ollama_model"])
        st.caption("No models detected. Pull the model with `ollama pull llama3.2`.")
    theme.card_close()

    if farm:
        theme.card_open()
        st.markdown(f"#### 📲 WhatsApp & Phone Linkage for {farm['name']}")
        p_input = st.text_input("Farm WhatsApp Phone Number", value=farm.get("phone_number") or "", placeholder="+2348012345678")
        if st.button("Save Phone Number"):
            database.update_farm_phone(farm["id"], p_input)
            st.success("Phone number linked. Incoming WhatsApp messages from this number will route to this farm.")
            st.rerun()
        theme.card_close()

    theme.card_open()
    st.markdown("#### 💱 Currency Preferences")
    st.session_state["currency"] = st.selectbox(
        "Default Operating Currency",
        ["NGN", "KES", "GHS", "TZS", "UGX", "ETB", "ZAR", "USD", "XOF", "RWF", "ZMW"],
        index=0 if st.session_state["currency"] not in ["NGN", "KES", "GHS", "TZS", "UGX", "ETB", "ZAR", "USD", "XOF", "RWF", "ZMW"] else
        ["NGN", "KES", "GHS", "TZS", "UGX", "ETB", "ZAR", "USD", "XOF", "RWF", "ZMW"].index(st.session_state["currency"]),
    )
    theme.card_close()

st.markdown(
    f"""
    <div style="text-align:center; color:{theme.TEXT_MUTED}; font-size:0.8rem; margin-top:40px;">
        Agri_OS Africa · Free local-AI decision support · Powered by your own Llama 3.2 model via Ollama
    </div>
    """,
    unsafe_allow_html=True,
)
