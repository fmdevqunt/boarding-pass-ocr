import streamlit as st
import requests
import json
import os
API_BASE = os.getenv("API_BASE")
st.set_page_config(page_title="Boarding Pass Advisor", layout="centered")
# --- Sidebar ---
with st.sidebar:
    st.header("✈️ Priority Pass Advisor")
    st.markdown("""
    Welcome to the **Priority Pass Lounge Advisor**. This tool helps you find the best airport lounge for your departure based on your boarding pass information.
    
    ### How to use:
    1. **Upload** a boarding pass image (JPEG/PNG) or use the demo data.
    2. **Review** the automatically parsed information.
    3. **Edit** any fields if the OCR confidence is low.
    4. Click **Recommend** to get personalized lounge suggestions.
    
    The system considers:
    - Your current time and departure/boarding time
    - Lounge opening hours
    - Terminal proximity
    - Amenities
    
    ### About Priority Pass
    Priority Pass is the world's largest independent airport lounge access program, offering access to over 1,800+ lounges worldwide.
    
    [🌐 Visit Priority Pass](https://www.prioritypass.com)
    
    ---
    *Note:  For full better functionality, integrate with your own OCR and Gemini API. It only consider departure airports in UK and USA airports*
    """)




st.title("Boarding Pass Advisor — Demo")

# Initialize session state
if 'parsed_data' not in st.session_state:
    st.session_state.parsed_data = None
if 'needs_edit' not in st.session_state:
    st.session_state.needs_edit = False
if 'form_counter' not in st.session_state:
    st.session_state.form_counter = 0

uploaded = st.file_uploader("Upload boarding pass image", type=["jpg","jpeg","png"])

if st.button("Parse"):
    files = {}
    if uploaded:
        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
    try:
        resp = requests.post(f"{API_BASE}/parse", files=files if files else None)
    except Exception as e:
        st.error(f"Error contacting backend: {e}")
        st.stop()
    if resp.status_code != 200:
        st.error(resp.text)
    else:
        parsed = resp.json()
        st.session_state.parsed_data = parsed["boarding_pass"]
        st.session_state.needs_edit = parsed["needs_manual_edit"]
        st.session_state.form_counter += 1
        st.rerun()

if st.session_state.parsed_data is not None:
    bp = st.session_state.parsed_data
    needs_edit = st.session_state.needs_edit

    # --- Nicer display of parsed boarding pass ---
    st.subheader("📄 Parsed Boarding Pass")

    # Extract fields with fallbacks
    airport_iata = bp.get("airport", {}).get("iata", "N/A")
    airport_city = bp.get("airport", {}).get("city", "N/A")
    dest_iata = bp.get("destination", {}).get("iata", "N/A")
    dest_city = bp.get("destination", {}).get("city", "N/A")
    terminal_val = bp.get("terminal", {}).get("value", "N/A")
    gate_val = bp.get("gate", "N/A")
    flight_val = bp.get("flight_number", "N/A")
    dep_time = bp.get("departure_time_local", "N/A")
    board_time = bp.get("boarding_time_local", "N/A")
    raw_text = bp.get("raw_text", "")

    # Layout in columns
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**🛫 Airport:** {airport_iata} – {airport_city}")
        st.markdown(f"**🛬 Destination:** {dest_iata} – {dest_city}")
        st.markdown(f"**🚪 Gate:** {gate_val}")
    with col2:
        st.markdown(f"**🏷️ Terminal:** {terminal_val}")
        st.markdown(f"**✈️ Flight:** {flight_val}")
        st.markdown(f"**⏰ Departure:** {dep_time}")
        st.markdown(f"**🕒 Boarding:** {board_time}")

    # Optional confidence indicators if available
    if "confidence" in bp.get("destination", {}):
        dest_conf = bp["destination"]["confidence"]
        st.caption(f"Destination confidence: {dest_conf:.0%}")
    if "confidence" in bp.get("terminal", {}):
        term_conf = bp["terminal"]["confidence"]
        st.caption(f"Terminal confidence: {term_conf:.0%}")

    # Raw OCR text in expandable section
    with st.expander("🔍 View raw OCR text"):
        st.text(raw_text if raw_text else "No raw text provided.")

    if needs_edit:
        st.warning("⚠️ OCR confidence low — please edit fields below before recommending.")

    # --- Editable form (same as before) ---
    with st.form(key=f"edit_form_{st.session_state.form_counter}"):
        airport_iata = st.text_input("Airport IATA", value=airport_iata if airport_iata != "N/A" else "")
        airport_city = st.text_input("Airport city", value=airport_city if airport_city != "N/A" else "")
        dest_iata = st.text_input("Destination IATA", value=dest_iata if dest_iata != "N/A" else "")
        dest_city = st.text_input("Destination city", value=dest_city if dest_city != "N/A" else "")
        terminal = st.text_input("Terminal", value=terminal_val if terminal_val != "N/A" else "")
        gate = st.text_input("Gate", value=gate_val if gate_val != "N/A" else "")
        flight = st.text_input("Flight number", value=flight_val if flight_val != "N/A" else "")
        dep_time = st.text_input("Departure time", value=dep_time if dep_time != "N/A" else "")
        board_time = st.text_input("Boarding time", value=board_time if board_time != "N/A" else "")

        submitted = st.form_submit_button("Recommend")

        if submitted:
            payload = {
                "airport": {"iata": airport_iata or None, "city": airport_city or None},
                "destination": {"iata": dest_iata or None, "city": dest_city or None, "confidence": 0.99},
                "terminal": {"value": terminal or None, "source": "printed" if terminal else None, "confidence": 0.99 if terminal else 0.0},
                "gate": gate or None,
                "flight_number": flight or None,
                "departure_time_local": dep_time or None,
                "boarding_time_local": board_time or None,
                "raw_text": raw_text,
                "assumptions": []
            }
            rec = requests.post(f"{API_BASE}/recommend", json=payload)
            if rec.status_code != 200:
                st.error(rec.text)
            else:
                adv = rec.json()
                # --- Display recommendation results (as before) ---
                if adv.get("time_window") and adv["time_window"].get("start"):
                    time_text = f"{adv['time_window']['start']} to {adv['time_window']['end']}"
                    if adv["time_window"].get("overnight"):
                        time_text += " (overnight)"
                    st.caption(f"⏱️ Time window: {time_text}")
                if adv.get("available_terminals"):
                    st.caption(f"🛫 Lounges available in terminals: {', '.join(adv['available_terminals'])}")
                st.subheader("💬 Advisory")
                st.markdown(adv["advisory"])
                if adv.get("recommendations"):
                    st.subheader("🏨 Recommended Lounges")
                    for r in adv["recommendations"]:
                        with st.expander(f"{r['name']} (Terminal {r['terminal']})"):
                            st.write(f"**Opening hours:** {r['opening_hours']}")
                            st.write(f"**Amenities:** {r['amenities']}")
                            st.write(f"[More info]({r['source_url']})")
                            st.caption(f"**Why:** {r['why_recommended']}")
                if adv.get("destination_context"):
                    dest = adv["destination_context"]
                    st.subheader("✈️ Destination Information")
                    cols = st.columns(2)
                    with cols[0]:
                        if dest.get("iata") or dest.get("city"):
                            st.markdown(f"**Airport:** {dest.get('iata', '')} – {dest.get('city', '')}")
                    with cols[1]:
                        if dest.get("flight_duration_estimate"):
                            st.markdown(f"**Flight duration:** {dest['flight_duration_estimate']}")
                    if dest.get("arrival_insight"):
                        st.info(f"🕐 **Arrival insight:** {dest['arrival_insight']}")
                    if dest.get("uncertainty"):
                        st.caption(f"⚠️ Note: {dest['uncertainty']}")
                elif "destination_context" in adv and adv["destination_context"] is None:
                    st.caption("ℹ️ Destination information not available.")