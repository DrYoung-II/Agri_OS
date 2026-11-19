# 🌾 Agri_OS Africa
### The AI Operating System for African Agriculture

> **An offline-capable decision-support platform designed for African smallholders, commercial livestock & crop farmers, and agricultural extension advisors.**

---

## 📖 Overview

Agricultural decision-making across Sub-Saharan Africa is challenged by volatile feed and input costs, localized weather shocks, thin operating margins, and disease pressures. 

**Agri_OS Africa** provides an operational decision-support system tailored to African farming realities. Rather than basic photo diagnostics, Agri_OS connects on-farm records, feed inventory, vaccination calendars, livestock growth models, local commodity price benchmarks, and financial ledgers into actionable recommendations.

The system is engineered to run **offline-first with zero API bills**, utilizing a locally hosted **Llama 3.2** model via [Ollama](https://ollama.com).

---

## 🌟 Core Modules

### 1. 🤖 Context-Aware AI Extension Advisor
- Direct agricultural recommendations grounded in the farmer's live data: active livestock batches, feed inventory levels, upcoming vaccinations, and local market prices.
- WhatsApp-style pragmatic responses: exact numbers (feed kg, selling price floors, cost breakdowns) and immediate physical action steps for today.
- Optional voice note input for farmers who prefer audio descriptions.

### 2. 🐔 Livestock Intelligence
- **Multi-Species Support**: Broilers, Layers, Cattle (beef/dairy), Goats & Sheep, Pigs, and Fish (Catfish & Tilapia).
- **Feed & Growth Curves**: Cumulative feed requirement calculations and growth trajectories aligned with tropical African extension benchmarks.
- **Optimal Selling Age Calculator**: Identifies the exact week where marginal feed cost per kg gained exceeds market live weight selling price.
- **Mortality & Disease Alerts**: Tracks cumulative mortality percentages against age-based benchmarks and identifies keyword matches for common diseases (Newcastle, Gumboro, Coccidiosis, African Swine Fever, PPR).

### 3. 🥣 Home-Made Feed Formulator & Least-Cost Mixer
- In African livestock production, commercial feed represents 65%–75% of total operating expenses.
- Agri_OS includes an interactive home-mixing formulator utilizing accessible regional ingredients: Yellow/White Maize, Soya Bean Meal, Wheat Offal/Bran, Palm Kernel Cake (PKC), Fish Meal, Groundnut Cake (GNC), Bone Meal, Limestone, Premix, Salt, Lysine, and Methionine.
- Balances Crude Protein (% CP) and Metabolizable Energy (ME kcal/kg) across presets (Broiler Starter, Broiler Finisher, Layer Mash, Catfish Pellets, Pig Grower) and projects exact cost savings per 25 kg bag and per batch vs commercial retail feeds.

### 4. 💰 Multi-Variable Profitability Engine & Ledger
- **Unit Economics**: Calculates gross revenue, loss deductions, feed and input costs, labour, and logistics to determine real net margin.
- **Break-Even Analysis**: Determines the minimum selling price needed to prevent cash losses.
- **Multi-Variable Stress Testing**: Simulates simultaneous market shocks (feed price spikes, additional mortality, market price dips) to calculate the required selling price to protect target profit margins.
- **Farm Ledger**: Persistent transaction recording with cumulative cash-flow curves.

### 5. 📲 WhatsApp & SMS Gateway
- Enables farmers in low-connectivity settings to interact with Agri_OS over messaging channels.
- In-app interactive smartphone simulator for testing and demonstrations.
- Fast keyword commands:
  - `STATUS` — Live summary of active batches, remaining animals, and feed stock.
  - `VACCINES` — Upcoming vaccination deadlines.
  - `MORT [count] [batch]` — Quick logging of animal mortality with automatic count deduction.
  - `PRICE [item]` — Real-time price lookups.
- Webhook endpoints architected for Twilio and Meta WhatsApp Business Cloud API.

### 6. 📒 Operational Farm Records & Inventory
- **Persistent SQLite Database (`agri_os.db`)**: Local storage ensuring zero cloud database fees and complete data privacy.
- **Feed Inventory**: Tracks stock in bags and kg, with automated low-stock warnings when inventory drops below safety buffers.
- **Automated Vaccination Calendar**: Generates standard prevention schedules upon poultry batch creation with date-based alerts.
- **Crop Intelligence & Plots**: Acreage, soil types, and NPK fertilizer calculations for staple African crops (Maize, Cassava, Rice, Sorghum, Millet, Cowpea, Tomato, Yam).
- **Harvest Archiving**: Records final sale weights, prices, gross revenue, and realized net returns.

---

## 🗂️ Architecture

```
agri_os/
├── app.py                     # Main Streamlit interface & multi-page navigation
├── requirements.txt           # Core Python dependencies
├── .gitignore                 # Excludes local databases, bytecode, and virtual environments
├── data/
│   └── market_prices_sample.csv # Multi-country African commodity price sheet
└── modules/
    ├── theme.py               # Dark-green responsive UI theme
    ├── database.py            # SQLite schema, migrations & CRUD persistence
    ├── llm_engine.py          # Grounded Llama 3.2 extension prompt & context builder
    ├── livestock.py           # Livestock intelligence, growth curves & mortality logs
    ├── crops.py               # Crop planting, NPK recommendations & yield forecasts
    ├── profitability.py       # Profitability engine, scenario simulator & farm ledger
    ├── feed_formulator.py     # Home-mixed feed formulator (CP% & ME energy balancing)
    ├── gateway.py             # WhatsApp/SMS webhook router & smartphone simulator
    ├── weather.py             # Open-Meteo weather geocoding & farming risk flags
    └── market_data.py         # Local commodity & feed price dataset
```

---

## 🚀 Getting Started

### 1. Install Ollama & Pull the Model
Download and install Ollama from [ollama.com](https://ollama.com). Then pull the Llama 3.2 model:
```bash
ollama pull llama3.2
ollama serve
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch Agri_OS
```bash
streamlit run app.py
```
The application will open in your browser at `http://localhost:8501` (or `http://localhost:8502`).

---

## 💱 Supported Currencies
- Nigerian Naira (`NGN`)
- Kenyan Shilling (`KES`)
- Ghanaian Cedi (`GHS`)
- Tanzanian Shilling (`TZS`)
- Ugandan Shilling (`UGX`)
- Ethiopian Birr (`ETB`)
- South African Rand (`ZAR`)
- West African CFA Franc (`XOF`)
- Rwandan Franc (`RWF`)
- Zambian Kwacha (`ZMW`)
- US Dollar (`USD`)
