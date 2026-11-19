"""
feed_formulator.py
Agri_OS Africa - Home-Made Feed Mixing & Least-Cost Formulator.

Feed represents 65%-75% of total production cost in African poultry, livestock and
fish farming. When commercial bag prices surge, home-mixing using locally sourced
feedstuffs (Maize, Soya Meal, Wheat Offal, PKC, Fish Meal, Bone Meal, Premix) is the
most defensible way for farmers to preserve their profit margins.
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from modules import theme

# Common African Feedstuffs with typical nutritional benchmarks (NRC / African Extension Standards)
# cp = Crude Protein %, me = Metabolizable Energy (kcal/kg), ca = Calcium %, p = Available Phosphorus %
FEEDSTUFFS = {
    "Maize (Yellow / White)": {"cp": 8.5, "me": 3350, "ca": 0.02, "p": 0.09, "default_cost_kg": 640.0, "category": "Energy"},
    "Soya Bean Meal (Extruded 44%)": {"cp": 44.0, "me": 2400, "ca": 0.30, "p": 0.25, "default_cost_kg": 1100.0, "category": "Protein"},
    "Wheat Offal / Wheat Bran": {"cp": 16.0, "me": 1900, "ca": 0.12, "p": 0.35, "default_cost_kg": 450.0, "category": "Energy / Fibre"},
    "Palm Kernel Cake (PKC)": {"cp": 17.5, "me": 1850, "ca": 0.25, "p": 0.15, "default_cost_kg": 380.0, "category": "Fibre / Protein"},
    "Fish Meal (Local 65%)": {"cp": 65.0, "me": 2800, "ca": 5.00, "p": 3.00, "default_cost_kg": 2200.0, "category": "Animal Protein"},
    "Groundnut Cake (GNC)": {"cp": 45.0, "me": 2500, "ca": 0.20, "p": 0.20, "default_cost_kg": 1050.0, "category": "Plant Protein"},
    "Bone Meal": {"cp": 0.0, "me": 0, "ca": 24.0, "p": 12.0, "default_cost_kg": 400.0, "category": "Mineral"},
    "Oyster Shell / Limestone": {"cp": 0.0, "me": 0, "ca": 38.0, "p": 0.02, "default_cost_kg": 250.0, "category": "Mineral"},
    "Broiler/Layer Premix (0.25%)": {"cp": 0.0, "me": 0, "ca": 0.0, "p": 0.0, "default_cost_kg": 3500.0, "category": "Premix"},
    "Common Salt (NaCl)": {"cp": 0.0, "me": 0, "ca": 0.0, "p": 0.0, "default_cost_kg": 300.0, "category": "Mineral"},
    "Synthetic Lysine": {"cp": 98.0, "me": 3900, "ca": 0.0, "p": 0.0, "default_cost_kg": 4200.0, "category": "Amino Acid"},
    "Synthetic DL-Methionine": {"cp": 58.0, "me": 4900, "ca": 0.0, "p": 0.0, "default_cost_kg": 5200.0, "category": "Amino Acid"},
}

# Standard targets for Sub-Saharan African production
NUTRITIONAL_TARGETS = {
    "Broiler Starter (0-3 Weeks)": {
        "target_cp": (22.0, 24.0),
        "target_me": (2950, 3100),
        "presets": {
            "Maize (Yellow / White)": 52.0,
            "Soya Bean Meal (Extruded 44%)": 34.0,
            "Wheat Offal / Wheat Bran": 7.0,
            "Fish Meal (Local 65%)": 3.0,
            "Bone Meal": 2.0,
            "Oyster Shell / Limestone": 1.0,
            "Broiler/Layer Premix (0.25%)": 0.25,
            "Common Salt (NaCl)": 0.25,
            "Synthetic Lysine": 0.25,
            "Synthetic DL-Methionine": 0.25,
        }
    },
    "Broiler Finisher (4-8 Weeks)": {
        "target_cp": (19.0, 21.0),
        "target_me": (3050, 3200),
        "presets": {
            "Maize (Yellow / White)": 58.0,
            "Soya Bean Meal (Extruded 44%)": 26.0,
            "Wheat Offal / Wheat Bran": 10.0,
            "Fish Meal (Local 65%)": 2.0,
            "Bone Meal": 2.0,
            "Oyster Shell / Limestone": 1.0,
            "Broiler/Layer Premix (0.25%)": 0.25,
            "Common Salt (NaCl)": 0.25,
            "Synthetic Lysine": 0.25,
            "Synthetic DL-Methionine": 0.25,
        }
    },
    "Layer Mash (Peak Laying)": {
        "target_cp": (16.5, 18.0),
        "target_me": (2700, 2850),
        "presets": {
            "Maize (Yellow / White)": 50.0,
            "Soya Bean Meal (Extruded 44%)": 18.0,
            "Wheat Offal / Wheat Bran": 16.0,
            "Palm Kernel Cake (PKC)": 5.0,
            "Bone Meal": 2.5,
            "Oyster Shell / Limestone": 7.5,
            "Broiler/Layer Premix (0.25%)": 0.25,
            "Common Salt (NaCl)": 0.35,
            "Synthetic DL-Methionine": 0.20,
            "Synthetic Lysine": 0.20,
        }
    },
    "Catfish Grower Pellets": {
        "target_cp": (40.0, 43.0),
        "target_me": (2900, 3200),
        "presets": {
            "Fish Meal (Local 65%)": 35.0,
            "Soya Bean Meal (Extruded 44%)": 30.0,
            "Maize (Yellow / White)": 20.0,
            "Wheat Offal / Wheat Bran": 11.0,
            "Bone Meal": 2.0,
            "Broiler/Layer Premix (0.25%)": 1.0,
            "Common Salt (NaCl)": 0.5,
            "Synthetic DL-Methionine": 0.5,
        }
    },
    "Pig Grower (Grower / Finisher)": {
        "target_cp": (16.0, 18.0),
        "target_me": (3000, 3200),
        "presets": {
            "Maize (Yellow / White)": 45.0,
            "Palm Kernel Cake (PKC)": 25.0,
            "Soya Bean Meal (Extruded 44%)": 15.0,
            "Wheat Offal / Wheat Bran": 11.0,
            "Bone Meal": 2.0,
            "Oyster Shell / Limestone": 1.0,
            "Common Salt (NaCl)": 0.5,
            "Broiler/Layer Premix (0.25%)": 0.5,
        }
    }
}


def compute_feed_mix(proportions: dict, custom_costs: dict):
    """
    proportions: dict of {ingredient_name: kg_in_100kg_batch}
    custom_costs: dict of {ingredient_name: cost_per_kg}
    Returns calculated CP%, ME (kcal/kg), Calcium %, Phosphorus %, total cost per 100kg and per kg.
    """
    total_kg = sum(proportions.values())
    if total_kg <= 0:
        return None

    weighted_cp = 0.0
    weighted_me = 0.0
    weighted_ca = 0.0
    weighted_p = 0.0
    total_cost = 0.0

    for name, kg in proportions.items():
        if kg <= 0 or name not in FEEDSTUFFS:
            continue
        info = FEEDSTUFFS[name]
        cost_kg = custom_costs.get(name, info["default_cost_kg"])
        weighted_cp += (kg * info["cp"])
        weighted_me += (kg * info["me"])
        weighted_ca += (kg * info["ca"])
        weighted_p += (kg * info["p"])
        total_cost += (kg * cost_kg)

    calc_cp = weighted_cp / total_kg
    calc_me = weighted_me / total_kg
    calc_ca = weighted_ca / total_kg
    calc_p = weighted_p / total_kg
    cost_per_kg = total_cost / total_kg
    cost_per_25kg_bag = cost_per_kg * 25.0

    return {
        "total_batch_kg": total_kg,
        "calc_cp": round(calc_cp, 2),
        "calc_me": round(calc_me, 1),
        "calc_ca": round(calc_ca, 2),
        "calc_p": round(calc_p, 2),
        "total_cost": round(total_cost, 2),
        "cost_per_kg": round(cost_per_kg, 2),
        "cost_per_25kg_bag": round(cost_per_25kg_bag, 2),
    }


def render_feed_formulator(farm, currency="NGN"):
    st.markdown("#### 🥣 Custom Feed Formulator & Home-Mixing Calculator")
    st.caption(
        "Commercial feed accounts for 70%+ of production cost. Formulate your own balanced rations "
        "using local ingredients to reduce feed bills while safeguarding animal performance."
    )

    preset_name = st.selectbox(
        "Select Ration Preset / Target",
        list(NUTRITIONAL_TARGETS.keys()),
        index=0
    )
    preset_data = NUTRITIONAL_TARGETS[preset_name]
    target_cp_min, target_cp_max = preset_data["target_cp"]
    target_me_min, target_me_max = preset_data["target_me"]

    st.markdown(f"**Target Requirements for {preset_name}:** Crude Protein: `{target_cp_min}% - {target_cp_max}%` | Energy: `{target_me_min} - {target_me_max} kcal/kg`")

    st.markdown("##### 1. Formulation Proportions (per 100 kg Batch)")
    
    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        user_proportions = {}
        user_costs = {}

        # Show ingredients in an organized 2-column grid
        all_ingredients = list(FEEDSTUFFS.keys())
        p_cols = st.columns(2)
        
        for i, ing in enumerate(all_ingredients):
            col_target = p_cols[i % 2]
            with col_target:
                default_qty = preset_data["presets"].get(ing, 0.0)
                qty = st.number_input(
                    f"{ing} (kg)",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(default_qty),
                    step=0.5,
                    key=f"feed_qty_{ing}_{preset_name}"
                )
                user_proportions[ing] = qty
                user_costs[ing] = FEEDSTUFFS[ing]["default_cost_kg"]

    total_kg_input = sum(user_proportions.values())

    with col_right:
        theme.card_open()
        st.markdown("##### 2. Benchmark Commercial Bag Price")
        commercial_bag_price = st.number_input(
            f"Local Commercial 25kg Bag Price ({currency})",
            min_value=100.0,
            value=21500.0 if currency == "NGN" else 4500.0,
            step=250.0
        )
        total_animals = st.number_input("Number of animals to feed", min_value=1, value=500, step=50)
        days_horizon = st.number_input("Feeding period (days)", min_value=1, value=14, step=1)
        theme.card_close()

    result = compute_feed_mix(user_proportions, user_costs)

    if not result:
        st.warning("Please enter valid positive ingredient quantities.")
        return

    st.divider()

    # Alert if total batch is not 100 kg
    if abs(result["total_batch_kg"] - 100.0) > 0.01:
        st.warning(f"⚠️ Current total formulation batch is **{result['total_batch_kg']:.1f} kg** (standard formulation is 100 kg). Ratios are normalized to actual weight.")
    else:
        st.success("✅ Batch total is exactly **100.0 kg**.")

    # Nutritional Metrics
    m1, m2, m3, m4 = st.columns(4)
    cp_ok = target_cp_min <= result["calc_cp"] <= target_cp_max
    cp_status = "✅ Optimal" if cp_ok else ("⚠️ Too Low" if result["calc_cp"] < target_cp_min else "⚠️ Too High")
    m1.metric("Crude Protein (CP)", f"{result['calc_cp']}%", delta=cp_status, delta_color="normal" if cp_ok else "inverse")

    me_ok = target_me_min <= result["calc_me"] <= target_me_max
    me_status = "✅ Optimal" if me_ok else ("⚠️ Low Energy" if result["calc_me"] < target_me_min else "⚠️ High Energy")
    m2.metric("Metabolizable Energy", f"{result['calc_me']:,.0f} kcal", delta=me_status, delta_color="normal" if me_ok else "inverse")

    m3.metric("Home-Mixed Cost / kg", f"{currency} {result['cost_per_kg']:,.2f}")
    
    home_bag_cost = result["cost_per_25kg_bag"]
    bag_saving = commercial_bag_price - home_bag_cost
    pct_saved = (bag_saving / commercial_bag_price * 100) if commercial_bag_price > 0 else 0
    m4.metric(
        "Cost per 25kg Bag",
        f"{currency} {home_bag_cost:,.2f}",
        delta=f"Save {currency} {bag_saving:,.0f}/bag ({pct_saved:.1f}%)" if bag_saving > 0 else "More expensive than bag",
        delta_color="normal" if bag_saving > 0 else "inverse"
    )

    # Total savings projection
    theme.card_open()
    st.markdown("##### 💰 Batch Savings & Economic Impact")
    # Est feed intake for broiler/livestock
    daily_kg_bird = 0.12  # avg
    total_feed_needed_kg = total_animals * daily_kg_bird * days_horizon
    total_bags_needed = total_feed_needed_kg / 25.0
    commercial_total_cost = total_bags_needed * commercial_bag_price
    home_mix_total_cost = total_feed_needed_kg * result["cost_per_kg"]
    net_savings = commercial_total_cost - home_mix_total_cost

    st.markdown(
        f"For **{total_animals:,} animals** over **{days_horizon} days**, you need approx. "
        f"**{total_feed_needed_kg:,.0f} kg ({total_bags_needed:.1f} bags of 25kg)**.\n\n"
        f"- Commercial feed total cost: **{currency} {commercial_total_cost:,.0f}**\n"
        f"- Home-mixed total cost: **{currency} {home_mix_total_cost:,.0f}**\n"
        f"- **Projected Net Savings:** `{currency} {net_savings:,.0f}` (reducing your feed bill by **{pct_saved:.1f}%**)"
    )
    theme.card_close()

    # Ingredient breakdown chart
    active_ings = {k: v for k, v in user_proportions.items() if v > 0}
    fig = go.Figure(data=[go.Pie(
        labels=list(active_ings.keys()),
        values=list(active_ings.values()),
        hole=0.45,
        textinfo='label+percent',
    )])
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title="Formulation Ingredient Composition (100 kg batch)",
        height=380
    )
    st.plotly_chart(fig, use_container_width=True)
