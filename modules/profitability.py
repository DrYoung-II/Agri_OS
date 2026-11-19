"""
profitability.py
AI Farm Profitability Engine with Multi-Variable Scenario Simulation,
Break-Even Analysis, Custom Feed Formulator, and Persistent Farm Ledger.

Revenue - (feed/input cost + labour + transport + losses) = Expected profit
"""

import datetime
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules import theme, database, llm_engine
from modules import feed_formulator


def compute_profit(revenue, feed_cost, labour_cost, transport_cost, other_cost, loss_pct):
    effective_revenue = revenue * (1.0 - (loss_pct / 100.0))
    total_cost = feed_cost + labour_cost + transport_cost + other_cost
    profit = effective_revenue - total_cost
    margin_pct = (profit / effective_revenue * 100.0) if effective_revenue > 0 else 0.0
    return {
        "effective_revenue": round(effective_revenue, 2),
        "total_cost": round(total_cost, 2),
        "profit": round(profit, 2),
        "margin_pct": round(margin_pct, 2),
    }


def required_selling_price_for_margin(total_units, total_cost, target_margin_pct):
    """Given a target profit margin (%) and total cost, find the minimum total revenue
    and per-unit price required."""
    if target_margin_pct >= 99.0:
        target_margin_pct = 99.0
    required_revenue = total_cost / (1.0 - (target_margin_pct / 100.0))
    price_per_unit = required_revenue / total_units if total_units > 0 else 0.0
    return round(required_revenue, 2), round(price_per_unit, 2)


def compute_breakeven_price(total_units, total_cost, loss_pct=0.0):
    effective_units = total_units * (1.0 - (loss_pct / 100.0))
    if effective_units <= 0:
        return 0.0
    return round(total_cost / effective_units, 2)


def render(farm, market_df, ollama_host, ollama_model, currency):
    theme.hero(
        "💰 AI Farm Profitability Engine",
        "Not just 'how do I produce more' - but 'will I actually make money'. "
        "Calculate unit economics, simulate input shocks, formulate cheaper feed, and track farm cash flow.",
        "📈"
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Profit Calculator",
        "🔮 Multi-Variable Scenario Simulator",
        "🥣 Custom Feed Formulator",
        "🧾 Farm Ledger"
    ])

    # ---------------- Tab 1: Profit Calculator ----------------
    with tab1:
        st.markdown("##### Enter your production cycle numbers")
        c1, c2 = st.columns(2)
        with c1:
            output_units = st.number_input("Total output units (e.g. birds, kg live weight, bags)", min_value=1.0, value=500.0, step=50.0)
            price_per_unit = st.number_input(f"Selling price per unit ({currency})", min_value=0.0, value=2800.0, step=50.0)
            loss_pct = st.slider("Expected mortality / post-harvest loss (%)", 0.0, 50.0, 5.0, step=0.5)
        with c2:
            feed_cost = st.number_input(f"Total feed / fertilizer / input cost ({currency})", min_value=0.0, value=750000.0, step=10000.0)
            labour_cost = st.number_input(f"Labour cost ({currency})", min_value=0.0, value=50000.0, step=5000.0)
            transport_cost = st.number_input(f"Transport & logistics cost ({currency})", min_value=0.0, value=25000.0, step=2500.0)
            other_cost = st.number_input(f"Other costs (meds/vet, electricity/water, bedding) ({currency})", min_value=0.0, value=20000.0, step=2500.0)

        revenue = output_units * price_per_unit
        result = compute_profit(revenue, feed_cost, labour_cost, transport_cost, other_cost, loss_pct)
        breakeven_price = compute_breakeven_price(output_units, result["total_cost"], loss_pct)
        safety_margin_pct = ((price_per_unit - breakeven_price) / price_per_unit * 100.0) if price_per_unit > 0 else 0.0

        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Gross Revenue", f"{currency} {revenue:,.0f}")
        m2.metric("Total Production Cost", f"{currency} {result['total_cost']:,.0f}")
        
        profit_delta = f"{result['margin_pct']}% margin"
        m3.metric("Expected Net Profit", f"{currency} {result['profit']:,.0f}", delta=profit_delta, delta_color="normal" if result['profit'] >= 0 else "inverse")
        
        m4.metric("Break-Even Selling Price", f"{currency} {breakeven_price:,.2f}", delta=f"{safety_margin_pct:.1f}% Safety buffer")

        col_w, col_g = st.columns([1.4, 1])
        with col_w:
            fig = go.Figure(go.Waterfall(
                orientation="v",
                measure=["relative", "relative", "relative", "relative", "relative", "total"],
                x=["Gross Revenue", "Mortality/Losses", "Feed/Inputs", "Labour", "Transport+Other", "Net Profit"],
                y=[revenue, -(revenue - result["effective_revenue"]), -feed_cost, -labour_cost, -(transport_cost + other_cost), 0],
                connector={"line": {"color": theme.BORDER}},
                increasing={"marker": {"color": theme.ACCENT}},
                decreasing={"marker": {"color": theme.DANGER}},
                totals={"marker": {"color": theme.GOLD}},
            ))
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              title="Profit & Cost Breakdown Waterfall", height=380)
            st.plotly_chart(fig, use_container_width=True)

        with col_g:
            theme.card_open()
            st.markdown("##### 💡 Farm Economist Assessment")
            if result["profit"] > 0:
                st.markdown(
                    f"✅ **Profitable Operation:** For every unit you produce, you earn a net margin of **{result['margin_pct']}%**.\n\n"
                    f"- Minimum selling price to avoid loss: **{currency} {breakeven_price:,.2f}**\n"
                    f"- You can absorb a price drop of up to **{currency} {max(0.0, price_per_unit - breakeven_price):,.2f}/unit** before losing money."
                )
            else:
                st.markdown(
                    f"⚠️ **Loss-Making Operation:** Current total cost exceeds revenue by **{currency} {abs(result['profit']):,.0f}**.\n\n"
                    f"- You need to raise selling price to at least **{currency} {breakeven_price:,.2f}** to break even, or cut feed/input costs."
                )
            theme.card_close()

        st.session_state["_last_profit_calc"] = {
            "output_units": output_units, "price_per_unit": price_per_unit, "feed_cost": feed_cost,
            "labour_cost": labour_cost, "transport_cost": transport_cost, "other_cost": other_cost,
            "loss_pct": loss_pct, "breakeven_price": breakeven_price, **result,
        }

    # ---------------- Tab 2: Multi-Variable Scenario Simulator ----------------
    with tab2:
        st.markdown("##### 'What-If' Stress Testing: Multi-Variable Shock Simulator")
        base = st.session_state.get("_last_profit_calc")
        if not base:
            st.info("👈 Run the Profit Calculator tab first so the simulator has a baseline to work from.")
        else:
            st.caption("Simulate how simultaneous market shocks affect your bottom line and find the new required selling price.")
            
            sc1, sc2 = st.columns(2)
            with sc1:
                feed_price_change = st.slider("Feed / Input Price Shock (%)", -40, 80, 15, step=5)
                mortality_shock = st.slider("Additional Mortality / Losses (+%)", 0.0, 25.0, 2.0, step=0.5)
            with sc2:
                selling_price_change = st.slider("Market Selling Price Change (%)", -40, 40, 0, step=5)
                target_margin = st.slider("Target Net Margin to Protect (%)", 0, 50, max(0, int(base["margin_pct"])), step=5)

            new_feed_cost = base["feed_cost"] * (1.0 + feed_price_change / 100.0)
            new_loss_pct = min(90.0, base["loss_pct"] + mortality_shock)
            new_selling_price = base["price_per_unit"] * (1.0 + selling_price_change / 100.0)
            
            new_total_cost = new_feed_cost + base["labour_cost"] + base["transport_cost"] + base["other_cost"]
            effective_units = base["output_units"] * (1.0 - new_loss_pct / 100.0)
            
            new_revenue = effective_units * new_selling_price
            new_profit = new_revenue - new_total_cost
            new_margin_pct = (new_profit / new_revenue * 100.0) if new_revenue > 0 else 0.0
            
            required_revenue, required_price = required_selling_price_for_margin(
                effective_units, new_total_cost, target_margin
            )
            price_change_needed = required_price - new_selling_price

            st.divider()
            sm1, sm2, sm3, sm4 = st.columns(4)
            sm1.metric("Simulated Total Cost", f"{currency} {new_total_cost:,.0f}", delta=f"{currency} {new_total_cost - base['total_cost']:+,.0f}")
            sm2.metric("Simulated Revenue", f"{currency} {new_revenue:,.0f}")
            sm3.metric("Simulated Net Profit", f"{currency} {new_profit:,.0f}", delta=f"{new_margin_pct:.1f}% margin", delta_color="normal" if new_profit >= 0 else "inverse")
            sm4.metric(f"Price Needed for {target_margin}% Margin", f"{currency} {required_price:,.2f}", delta=f"{currency} {price_change_needed:+,.2f} vs current")

            theme.card_open()
            st.markdown(
                f"**Scenario Outcome:** Under a **{feed_price_change:+d}% feed shock** and **+{mortality_shock:.1f}% mortality**, "
                f"your cost moves to **{currency} {new_total_cost:,.0f}**.\n\n"
                f"- To preserve your target **{target_margin}% profit margin**, your minimum selling price must be **{currency} {required_price:,.2f} per unit**.\n"
                f"- If local market buyers will not pay `{currency} {required_price:,.2f}`, you must reduce input expenses (e.g. switch to home-mixed rations or sell earlier)."
            )
            theme.card_close()

            # Dynamic Sensitivity Curve
            changes = list(range(-30, 71, 10))
            req_prices = []
            for chg in changes:
                fc = base["feed_cost"] * (1.0 + chg / 100.0)
                tc = fc + base["labour_cost"] + base["transport_cost"] + base["other_cost"]
                _, p = required_selling_price_for_margin(effective_units, tc, target_margin)
                req_prices.append(p)

            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=changes, y=req_prices, mode="lines+markers", line=dict(color=theme.ACCENT, width=3), name="Required Price"))
            fig2.add_hline(y=base["price_per_unit"], line_dash="dash", line_color=theme.GOLD, annotation_text="Baseline Price")
            fig2.update_layout(
                template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                title=f"Sensitivity: Required Selling Price vs. Feed Shock (to protect {target_margin}% margin)",
                xaxis_title="Feed Price Change (%)", yaxis_title=f"Required Price ({currency}/unit)", height=350
            )
            st.plotly_chart(fig2, use_container_width=True)

            if farm:
                with st.expander("🧠 Ask Llama 3.2 to advise on this pricing shock"):
                    if st.button("Generate AI Farm Advice", key="sim_ai_explain"):
                        summary = (
                            f"Farm: {farm['name']}, Country: {farm['country']}. "
                            f"Baseline profit: {currency}{base['profit']:,.0f} ({base['margin_pct']}% margin). "
                            f"Shock: feed changed {feed_price_change}%, mortality +{mortality_shock}%. "
                            f"New cost: {currency}{new_total_cost:,.0f}, simulated profit: {currency}{new_profit:,.0f}. "
                            f"Required price for {target_margin}% margin: {currency}{required_price:,.2f}."
                        )
                        system = llm_engine.SYSTEM_PROMPT_TEMPLATE.format(
                            farm_context=llm_engine.build_farm_context({"Scenario Shock": summary})
                        )
                        messages = [
                            {"role": "system", "content": system},
                            {"role": "user", "content": "What immediate tactical decisions should I make to protect my profit margin against this price shock?"}
                        ]
                        st.write_stream(llm_engine.stream_chat(messages, model=ollama_model, host=ollama_host))

    # ---------------- Tab 3: Custom Feed Formulator ----------------
    with tab3:
        feed_formulator.render_feed_formulator(farm, currency)

    # ---------------- Tab 4: Farm Ledger ----------------
    with tab4:
        if not farm:
            st.info("Create or select an active farm in the sidebar to log transactions.")
        else:
            st.markdown("##### 🧾 Farm Income & Expense Ledger")
            with st.form("tx_form", clear_on_submit=True):
                fc1, fc2, fc3, fc4 = st.columns(4)
                tx_type = fc1.selectbox("Transaction Type", ["income", "expense"])
                category = fc2.selectbox("Category", [
                    "Feed Purchase", "Livestock Sales", "Crop Harvest Sales",
                    "Day-Old Chicks / Stock", "Fertilizer / Agro-chemicals",
                    "Labour & Wages", "Transport & Logistics", "Veterinary & Medication",
                    "Fuel & Utilities", "Equipment & Maintenance", "Other"
                ])
                amount = fc3.number_input(f"Amount ({currency})", min_value=0.0, step=1000.0)
                tx_date = fc4.date_input("Date", value=datetime.date.today())
                notes = st.text_input("Description / Notes (e.g. 10 bags finisher feed from distributor)")
                
                submitted = st.form_submit_button("➕ Record Entry", use_container_width=True)
                if submitted and amount > 0:
                    database.add_transaction(farm["id"], tx_type, category, amount, tx_date.isoformat(), notes)
                    st.success(f"Recorded {tx_type}: {currency} {amount:,.0f} for {category}")
                    st.rerun()

            txs = database.get_transactions(farm["id"])
            if txs:
                df = pd.DataFrame(txs)
                income = df[df["tx_type"] == "income"]["amount"].sum()
                expense = df[df["tx_type"] == "expense"]["amount"].sum()
                net = income - expense

                lm1, lm2, lm3 = st.columns(3)
                lm1.metric("Total Inflow (Income)", f"{currency} {income:,.0f}")
                lm2.metric("Total Outflow (Expense)", f"{currency} {expense:,.0f}")
                lm3.metric("Net Cash Position", f"{currency} {net:,.0f}", delta_color="normal" if net >= 0 else "inverse")

                # Cumulative cash trajectory
                df_sorted = df.sort_values("tx_date")
                df_sorted["signed_amount"] = df_sorted.apply(
                    lambda r: r["amount"] if r["tx_type"] == "income" else -r["amount"], axis=1
                )
                df_sorted["cumulative"] = df_sorted["signed_amount"].cumsum()

                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(
                    x=df_sorted["tx_date"], y=df_sorted["cumulative"], mode="lines+markers",
                    line=dict(color=theme.ACCENT, width=3), fill="tozeroy"
                ))
                fig3.update_layout(
                    template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    title="Cumulative Net Cash Flow", height=320
                )
                st.plotly_chart(fig3, use_container_width=True)

                st.markdown("##### Recent Transaction History")
                for t in txs[:15]:
                    with st.container():
                        theme.card_open()
                        tc1, tc2, tc3 = st.columns([1.5, 3, 1])
                        sign = "+" if t["tx_type"] == "income" else "-"
                        color = theme.ACCENT if t["tx_type"] == "income" else theme.DANGER
                        tc1.markdown(f"<span style='color:{color}; font-weight:700;'>{sign} {currency} {t['amount']:,.0f}</span>", unsafe_allow_html=True)
                        tc2.markdown(f"**{t['category']}** ({t['tx_date']}) — {t['notes'] or 'No description'}")
                        if tc3.button("🗑️ Delete", key=f"del_tx_{t['id']}"):
                            database.delete_transaction(t["id"])
                            st.rerun()
                        theme.card_close()
            else:
                st.caption("No transactions logged yet. Start recording your income and expenses above.")
