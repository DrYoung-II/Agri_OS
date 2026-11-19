"""
gateway.py
Agri_OS Africa - WhatsApp, SMS & USSD Gateway Engine.

Enables farmers to interact with Agri_OS over messaging channels (WhatsApp, SMS, USSD):
- Natural language agricultural extension via local Llama 3.2.
- Quick keyword commands for low-bandwidth / SMS (STATUS, MORTALITY, FEED, PRICE).
- Webhook endpoints ready for Twilio WhatsApp API and Meta WhatsApp Business Cloud API.
- Interactive in-app smartphone simulation for testing and demonstrations.
"""

import datetime
import re
import streamlit as st
from modules import database, llm_engine, market_data, theme


def process_incoming_message(sender_phone: str, message_text: str, default_farm_id: int = None, model: str = llm_engine.DEFAULT_MODEL, host: str = llm_engine.DEFAULT_HOST):
    """
    Core messaging router for WhatsApp/SMS.
    sender_phone: e.g. '+2348012345678'
    message_text: text query or command
    Returns: response_text (WhatsApp/SMS formatted)
    """
    clean_msg = message_text.strip()
    upper_msg = clean_msg.upper()

    # 1. Resolve Farm
    farm = database.get_farm_by_phone(sender_phone)
    if not farm and default_farm_id:
        farm = database.get_farm(default_farm_id)
    
    currency = farm["currency"] if farm else "NGN"
    farm_name = farm["name"] if farm else "Agri_OS Farm"

    # 2. Check for Instant Fast Commands (SMS / Low-Bandwidth mode)
    if upper_msg in ["HELP", "MENU", "START", "HELLO", "HI"]:
        return (
            f"🌾 *Welcome to Agri_OS Africa ({farm_name})*\n\n"
            f"Reply with your question or send any command:\n"
            f"• *STATUS* : Live summary of active batches & feed\n"
            f"• *VACCINES* : Pending vaccinations due\n"
            f"• *PRICE [item]* : Check market price (e.g. PRICE maize)\n"
            f"• *MORT [count] [batch_id]* : Log loss (e.g. MORT 3 1)\n"
            f"• Or type any farming question (feed, disease, profit)."
        )

    if upper_msg == "STATUS":
        if not farm:
            return "⚠️ No active farm found for your phone number. Register your farm on Agri_OS web."
        batches = database.get_livestock_batches(farm["id"], status="active")
        low_feed = database.get_low_feed_alerts(farm["id"])
        vacs = database.get_upcoming_vaccinations_for_farm(farm["id"], days_ahead=5)

        lines = [f"📊 *Farm Status: {farm_name}*"]
        if batches:
            lines.append("\n*Active Livestock:*")
            for b in batches:
                mort = database.get_batch_mortality_summary(b["id"])
                lines.append(f"• Batch #{b['id']} ({b['species']}): {b['count']} birds/head (Lost: {mort['total_dead']})")
        else:
            lines.append("• No active batches.")

        if low_feed:
            lines.append("\n*⚠️ Feed Alerts:*")
            for f in low_feed:
                lines.append(f"• {f['feed_name']}: Only {f['quantity_bags']} bags left!")

        if vacs:
            lines.append(f"\n*⏰ Vaccines Due ({len(vacs)}):*")
            for v in vacs[:3]:
                lines.append(f"• {v['vaccine_name']} by {v['due_date']}")

        return "\n".join(lines)

    if upper_msg == "VACCINES":
        if not farm:
            return "No farm registered."
        vacs = database.get_upcoming_vaccinations_for_farm(farm["id"], days_ahead=14)
        if not vacs:
            return "✅ *No pending vaccinations due in the next 14 days.* All batches are up to date."
        res = ["💉 *Upcoming Vaccinations for your Farm:*"]
        for v in vacs:
            res.append(f"• *{v['vaccine_name']}* for Batch #{v['batch_id']}\n  Due: {v['due_date']} (Disease: {v['target_disease']})")
        return "\n\n".join(res)

    # Quick log mortality: e.g. "MORT 4" or "MORT 4 1"
    if upper_msg.startswith("MORT"):
        parts = clean_msg.split()
        if len(parts) >= 2 and parts[1].isdigit():
            count_dead = int(parts[1])
            batch_id = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None
            
            # Find batch
            if not batch_id and farm:
                batches = database.get_livestock_batches(farm["id"], status="active")
                if batches:
                    batch_id = batches[0]["id"]

            if batch_id:
                today = datetime.date.today().isoformat()
                database.log_mortality(batch_id, today, count_dead, "Reported via WhatsApp/SMS", "Auto-logged")
                return f"✅ *Logged:* {count_dead} dead animals recorded for Batch #{batch_id}. Active count updated in Agri_OS."
            else:
                return "⚠️ Could not identify batch. Format: *MORT [count] [batch_id]* (e.g. MORT 3 1)"

    # Price lookup: e.g. "PRICE maize"
    if upper_msg.startswith("PRICE"):
        item = clean_msg[5:].strip()
        if item:
            df = market_data.load_market_df()
            country = farm["country"] if farm else "Nigeria"
            p, u, c = market_data.get_price(df, country, item.title())
            if p:
                return f"🏷️ *Market Price for {item.title()} ({country}):*\n• Price: *{c} {p:,.0f}* per {u}\n_Source: Agri_OS Market Intelligence_"
            else:
                return f"Price for '{item}' not found for {country}. Update via Market Prices page."

    # 3. Natural Language Extension Query via Local Llama 3.2
    farm_id = farm["id"] if farm else default_farm_id
    success, reply = llm_engine.generate_extension_advice(
        question=clean_msg,
        farm_id=farm_id,
        model=model,
        host=host,
        channel="whatsapp"
    )
    
    if not success:
        return f"⚠️ *Agri_OS Notice:*\n{reply}"
    
    return reply


def render_gateway_simulator(farm, currency="NGN", ollama_host=llm_engine.DEFAULT_HOST, ollama_model=llm_engine.DEFAULT_MODEL):
    theme.hero(
        "📲 WhatsApp & SMS Gateway",
        "Empower farmers to consult Agri_OS directly from WhatsApp, SMS or USSD — "
        "even in low-connectivity areas with zero app download required.",
        "📱"
    )

    tab_sim, tab_webhook = st.tabs(["💬 Interactive WhatsApp Simulator", "⚙️ Webhook & API Integration"])

    with tab_sim:
        st.markdown("##### 📱 Live WhatsApp Conversation Simulation")
        st.caption("Test how a farmer experiences Agri_OS on their smartphone via WhatsApp.")

        sim_key = "wa_sim_messages"
        if sim_key not in st.session_state:
            st.session_state[sim_key] = [
                {"role": "assistant", "sender": "Agri_OS Africa", "time": "10:00 AM",
                 "content": f"🌾 *Agri_OS Farm Assistant Online*\n\nHello farmer! I am linked to *{farm['name'] if farm else 'your farm'}*. Ask me any farming question or send *STATUS*, *VACCINES*, or *MORT* to log farm records."}
            ]

        col_phone, col_tools = st.columns([1.5, 1])

        with col_phone:
            # WhatsApp Styled Container
            st.markdown(
                """
                <div style="background-color:#0b141a; border:1px solid #202c33; border-radius:12px; padding:16px; min-height:480px; max-height:550px; overflow-y:auto;">
                """,
                unsafe_allow_html=True
            )

            for msg in st.session_state[sim_key]:
                if msg["role"] == "user":
                    st.markdown(
                        f"""
                        <div style="display:flex; justify-content:flex-end; margin-bottom:10px;">
                            <div style="background-color:#005c4b; color:#e9edef; padding:8px 12px; border-radius:8px 0px 8px 8px; max-width:80%; font-size:0.92rem; box-shadow:0 1px 2px rgba(0,0,0,0.3);">
                                <div>{msg['content']}</div>
                                <div style="text-align:right; font-size:0.7rem; color:#8696a0; margin-top:4px;">{msg['time']} ✓✓</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"""
                        <div style="display:flex; justify-content:flex-start; margin-bottom:10px;">
                            <div style="background-color:#202c33; color:#e9edef; padding:8px 12px; border-radius:0px 8px 8px 8px; max-width:85%; font-size:0.92rem; box-shadow:0 1px 2px rgba(0,0,0,0.3); border-left:3px solid #25d366;">
                                <div style="font-size:0.75rem; color:#25d366; font-weight:700; margin-bottom:2px;">Agri_OS Africa</div>
                                <div style="white-space:pre-wrap;">{msg['content']}</div>
                                <div style="text-align:right; font-size:0.7rem; color:#8696a0; margin-top:4px;">{msg['time']}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            st.markdown("</div>", unsafe_allow_html=True)

            # Chat input form
            with st.form("wa_input_form", clear_on_submit=True):
                wa_msg = st.text_input("Type WhatsApp message...", placeholder="e.g. STATUS, or 'Feed prices jumped 15%, should I sell early?'")
                submitted = st.form_submit_button("Send WhatsApp Message 🟢", use_container_width=True)
                if submitted and wa_msg.strip():
                    now_str = datetime.datetime.now().strftime("%I:%M %p")
                    st.session_state[sim_key].append({
                        "role": "user", "sender": "Farmer", "time": now_str, "content": wa_msg
                    })
                    
                    # Generate response
                    reply = process_incoming_message(
                        sender_phone="+2348000000000",
                        message_text=wa_msg,
                        default_farm_id=farm["id"] if farm else None,
                        model=ollama_model,
                        host=ollama_host
                    )
                    st.session_state[sim_key].append({
                        "role": "assistant", "sender": "Agri_OS Africa", "time": now_str, "content": reply
                    })
                    st.rerun()

        with col_tools:
            theme.card_open()
            st.markdown("##### ⚡ Quick WhatsApp Test Prompts")
            st.caption("Click to test standard African farmer interactions:")

            quick_samples = [
                ("📊 Check Farm Status", "STATUS"),
                ("💉 Check Vaccines Due", "VACCINES"),
                ("💀 Log 4 Bird Mortalities", "MORT 4"),
                ("🏷️ Check Maize Price", "PRICE maize"),
                ("🐔 Broiler Feed Shock Query", "I have 500 broilers at 4 weeks. Feed prices went up by 15%. What should I sell at to remain profitable?"),
                ("🌡️ Heat Stress Emergency", "It is 36°C today and my birds are panting heavily with wings spread. What immediate emergency steps should I take?"),
            ]

            for label, query in quick_samples:
                if st.button(label, key=f"btn_quick_{label}", use_container_width=True):
                    now_str = datetime.datetime.now().strftime("%I:%M %p")
                    st.session_state[sim_key].append({
                        "role": "user", "sender": "Farmer", "time": now_str, "content": query
                    })
                    reply = process_incoming_message(
                        sender_phone="+2348000000000",
                        message_text=query,
                        default_farm_id=farm["id"] if farm else None,
                        model=ollama_model,
                        host=ollama_host
                    )
                    st.session_state[sim_key].append({
                        "role": "assistant", "sender": "Agri_OS Africa", "time": now_str, "content": reply
                    })
                    st.rerun()

            if st.button("🗑️ Reset Chat Simulator", use_container_width=True):
                st.session_state.pop(sim_key, None)
                st.rerun()

            theme.card_close()

    with tab_webhook:
        theme.card_open()
        st.markdown("#### 🔌 Twilio & Meta WhatsApp Cloud API Setup")
        st.markdown(
            """
            Agri_OS is engineered for plug-and-play webhook connectivity:
            
            1. **Twilio WhatsApp Endpoint**:
               Configure your Twilio Sandbox or WhatsApp Business number webhook URL to:
               `https://your-domain.com/api/webhook/whatsapp`
            
            2. **Incoming Webhook Payload Handling**:
               The gateway accepts standard `From` (e.g. `whatsapp:+2348012345678`) and `Body` POST parameters.
            """
        )

        st.code(
            """
# Example Python Webhook Server (FastAPI / Flask)
from flask import Flask, request
from modules.gateway import process_incoming_message

app = Flask(__name__)

@app.route("/api/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    sender = request.form.get("From", "").replace("whatsapp:", "")
    incoming_msg = request.form.get("Body", "")
    
    # Process through Agri_OS local intelligence engine
    reply = process_incoming_message(sender_phone=sender, message_text=incoming_msg)
    
    # Return TwiML or Meta Cloud API response
    return f"<Response><Message>{reply}</Message></Response>", 200, {"Content-Type": "application/xml"}
            """,
            language="python"
        )
        theme.card_close()
