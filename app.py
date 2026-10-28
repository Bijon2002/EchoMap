"""
app.py - EchoMap Main Application
Your World, Remembered.
AI-Powered Spatial Memory Assistant for Blind & Low-Vision Users
Team PythonCharlie | University of Bedfordshire HCI + AI + XR Hackathon
"""

import io
from datetime import datetime
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

import commands
import memory
from spatial import compare_scans, region
import vision
import voice

# Initialize Database
memory.initialise()

# Page configuration
st.set_page_config(
    page_title="EchoMap | Your World, Remembered",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Accessibility & High Contrast
st.markdown(
    """
    <style>
        .main-header {
            font-size: 2.2rem;
            font-weight: 800;
            color: #58a6ff;
            margin-bottom: 2px;
        }
        .sub-header {
            font-size: 1.15rem;
            color: #8b949e;
            margin-bottom: 16px;
        }
        .team-badge {
            display: inline-block;
            background: linear-gradient(90deg, #1f6feb, #238636);
            color: white;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 12px;
        }
        .response-card {
            background-color: #0d1117;
            border: 2px solid #58a6ff;
            border-radius: 10px;
            padding: 18px;
            margin-top: 15px;
            font-size: 1.25rem;
            line-height: 1.6;
            color: #ffffff;
            box-shadow: 0 4px 14px rgba(88, 166, 255, 0.2);
        }
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            font-size: 1rem;
            padding: 8px 16px;
        }
        .status-pill {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        .pill-same { background-color: #238636; color: white; }
        .pill-moved { background-color: #d29922; color: black; }
        .pill-missing { background-color: #da3633; color: white; }
        .pill-new { background-color: #1f6feb; color: white; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session States
if "last_response" not in st.session_state:
    st.session_state.last_response = ""
if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True
if "processed_image" not in st.session_state:
    st.session_state.processed_image = None
if "pending_query" not in st.session_state:
    st.session_state.pending_query = ""

# Sidebar: Controls, Diagnostics & Hackathon Identity
with st.sidebar:
    st.markdown("### 🗺️ EchoMap Identity")
    st.markdown('<div class="team-badge">Team PythonCharlie</div>', unsafe_allow_html=True)
    st.caption("University of Bedfordshire HCI + AI + XR Hackathon")
    st.write("**Tagline:** *Your World, Remembered.*")
    st.write("**Target:** Assistive Spatial Memory for Visually Impaired")

    st.markdown("---")
    st.markdown("### ⚙️ System Status")
    
    api_ready = vision.is_api_configured()
    if api_ready:
        st.success(f"🟢 Gemini API: Connected ({vision.MODEL_NAME})")
    else:
        st.warning("🟡 Gemini API: Demo/Mock Mode Active")
        st.caption("Add your `GEMINI_API_KEY` in `.env` for live Google AI Studio vision.")

    st.session_state.voice_enabled = st.checkbox(
        "🔊 Voice Audio Output (TTS)",
        value=st.session_state.voice_enabled,
        help="When enabled, EchoMap reads answers aloud using browser speech synthesis.",
    )

    st.markdown("---")
    st.markdown("### 🧪 Quick Demo Setup")
    if st.button("🚀 Load Sample Desk Memory", width="stretch", help="Load a pre-configured realistic desk for judging/testing"):
        sample_objects = [
            {"name": "phone", "x": 0.28, "y": 0.52, "confidence": 0.96, "region_desc": "left side of the desk"},
            {"name": "keys", "x": 0.35, "y": 0.48, "confidence": 0.91, "region_desc": "centre of the desk"},
            {"name": "coffee mug", "x": 0.82, "y": 0.25, "confidence": 0.94, "region_desc": "top-right area of the desk"},
            {"name": "notebook", "x": 0.55, "y": 0.70, "confidence": 0.89, "region_desc": "bottom centre of the desk"},
            {"name": "pen", "x": 0.45, "y": 0.68, "confidence": 0.87, "region_desc": "bottom centre of the desk"},
            {"name": "laptop", "x": 0.50, "y": 0.28, "confidence": 0.98, "region_desc": "top centre of the desk"},
            {"name": "water bottle", "x": 0.86, "y": 0.55, "confidence": 0.92, "region_desc": "right side of the desk"},
        ]
        scan_id = memory.save_scan(sample_objects, scene="hackathon_desk", summary="Sample desk layout with 7 items")
        st.session_state.last_response = f"Loaded sample desk layout with {len(sample_objects)} items into memory."
        if st.session_state.voice_enabled:
            voice.speak(st.session_state.last_response)
        st.success("Sample desk loaded into SQLite!")
        st.rerun()

    if st.button("🗑️ Reset All Memory", width="stretch"):
        memory.clear_memory()
        st.session_state.last_response = "Memory cleared."
        st.warning("All scans and corrections cleared.")
        st.rerun()


# Main Application Header
st.markdown('<div class="main-header">🗺️ EchoMap</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Your World, Remembered — Spatial Memory Assistant for Blind and Low-Vision Users</div>',
    unsafe_allow_html=True,
)

# Fetch latest memory
latest = memory.latest_scan()
prev = memory.previous_scan()

current_scan_meta = latest[0] if latest else None
current_objects = latest[1] if latest else []
prev_objects = prev[1] if prev else []

# Application Tabs
tab_voice, tab_scan, tab_map, tab_diff, tab_corrections = st.tabs([
    "🗣️ Ask & Voice Assistant",
    "📸 Scan Desk (Vision)",
    "🗺️ Spatial Desk Map",
    "🔄 Movement & Scan Diffs",
    "✍️ User Corrections"
])

# -------------------------------------------------------------
# TAB 1: ASK & VOICE ASSISTANT
# -------------------------------------------------------------
with tab_voice:
    col_v1, col_v2 = st.columns([1, 1], gap="large")

    with col_v1:
        st.markdown("### 🎙️ Voice Interaction")
        st.caption("Click the microphone below to speak your question directly, or type into the box.")
        voice.voice_input_widget()

        st.markdown("#### Quick Question Prompts (Click to test):")
        q_cols = st.columns(2)
        sample_queries = [
            "Where are my keys?",
            "What is beside my phone?",
            "What is on my desk?",
            "Did my keys move?",
            "Where is my coffee mug?",
            "Hey EchoMap, help"
        ]
        for idx, q_text in enumerate(sample_queries):
            c = q_cols[idx % 2]
            if c.button(q_text, key=f"quick_q_{idx}", width="stretch"):
                st.session_state.pending_query = q_text

    with col_v2:
        st.markdown("### 💬 Ask EchoMap")
        query_input = st.text_input(
            "Speak or type your question:",
            value=st.session_state.pending_query,
            placeholder="e.g. 'Where are my keys?' or 'What is beside my laptop?'",
            key="user_query_input",
            help="Queries your saved spatial memory without turning on the camera."
        )

        col_ask, col_read = st.columns([1, 1])
        with col_ask:
            ask_pressed = st.button("🔍 Answer from Memory", type="primary", width="stretch")
        with col_read:
            repeat_pressed = st.button("🔊 Repeat Spoken Answer", width="stretch")

        if ask_pressed and query_input.strip():
            answer = commands.answer_question(
                query_input,
                current_objects,
                scan_meta=current_scan_meta,
                previous_objects=prev_objects
            )
            st.session_state.last_response = answer
            if st.session_state.voice_enabled:
                voice.speak(answer)

        if repeat_pressed and st.session_state.last_response:
            voice.speak(st.session_state.last_response)

        # Show Output Box
        if st.session_state.last_response:
            st.markdown(
                f'<div class="response-card" role="region" aria-live="assertive">'
                f'<strong>EchoMap:</strong><br>{st.session_state.last_response}'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.info("Ask a question above or scan your desk to get started.")

        if current_scan_meta:
            st.caption(f"ℹ️ Answering based on scan from: `{current_scan_meta['created_at']}` ({len(current_objects)} objects remembered).")


# -------------------------------------------------------------
# TAB 2: SCAN DESK (AI VISION)
# -------------------------------------------------------------
with tab_scan:
    st.markdown("### 📸 On-Demand Desk Scanning")
    st.markdown(
        "Privacy-First Design: The camera stays **OFF** until you explicitly request a scan. "
        "Gemini identifies everyday items and calculates their approximate coordinates on your desk."
    )

    scan_col1, scan_col2 = st.columns([1, 1], gap="large")

    with scan_col1:
        scan_mode = st.radio(
            "Select Image Source:",
            ["📷 Webcam Snapshot", "📁 Upload Desk Photo", "🧪 Demo Image"],
            horizontal=True
        )

        image_to_process = None

        if scan_mode == "📷 Webcam Snapshot":
            camera_snap = st.camera_input("Capture Desk View", help="Takes a single snapshot on click. The camera is not streamed continuously.")
            if camera_snap:
                image_to_process = Image.open(camera_snap)

        elif scan_mode == "📁 Upload Desk Photo":
            uploaded = st.file_uploader("Upload an image of your desk", type=["jpg", "jpeg", "png", "webp"])
            if uploaded:
                image_to_process = Image.open(uploaded)

        elif scan_mode == "🧪 Demo Image":
            st.info("Demonstration Mode: Generates a synthetic desk workspace with everyday objects for evaluation.")
            if st.button("🖼️ Generate Mock Desk Scene", width="stretch"):
                # Create a simple synthetic desk image
                img = Image.new("RGB", (800, 600), color=(235, 230, 220))
                draw = ImageDraw.Draw(img)
                draw.rectangle([50, 50, 750, 550], fill=(210, 180, 140), outline=(139, 69, 19), width=4)
                draw.text((320, 270), "EchoMap Test Desk", fill=(80, 40, 10))
                image_to_process = img
                st.session_state.processed_image = img

        if image_to_process:
            st.image(image_to_process, caption="Captured Image Preview", width="stretch")
            
            if st.button("🧠 Scan & Remember Desk with Gemini", type="primary", width="stretch"):
                with st.spinner("Analyzing image spatial relationships with Google Gemini..."):
                    try:
                        detected = vision.scan_desk(image_to_process)
                        if detected:
                            scan_id = memory.save_scan(
                                detected,
                                scene="desk",
                                summary=f"Scan with {len(detected)} objects detected"
                            )
                            st.success(f"Successfully identified and remembered {len(detected)} objects!")
                            st.session_state.last_response = f"I have scanned your desk and recorded {len(detected)} objects into memory."
                            if st.session_state.voice_enabled:
                                voice.speak(st.session_state.last_response)
                            st.rerun()
                        else:
                            st.warning("No clear everyday objects were detected in the image.")
                    except Exception as e:
                        st.error(f"Vision Scan Error: {str(e)}")
                        st.info("Note: You can also use 'Load Sample Desk Memory' in the sidebar for offline testing.")

    with scan_col2:
        st.markdown("### 📋 Remembered Objects in Current Scan")
        if current_objects:
            df = pd.DataFrame(current_objects)
            df_display = df[["name", "region_desc", "confidence", "x", "y"]].copy()
            df_display.columns = ["Object", "Region", "Confidence", "X (norm)", "Y (norm)"]
            df_display["Confidence"] = df_display["Confidence"].apply(lambda v: f"{int(v*100)}%")
            st.dataframe(df_display, width="stretch", hide_index=True)
        else:
            st.write("No objects recorded in memory yet. Perform a scan or load sample memory.")


# -------------------------------------------------------------
# TAB 3: SPATIAL DESK MAP (VISUALIZATION)
# -------------------------------------------------------------
with tab_map:
    st.markdown("### 🗺️ Visual Spatial Desk Map")
    st.caption("A bird's-eye 9-grid representation of the workspace for judges, carers, and sighted peers.")

    if not current_objects:
        st.info("No spatial objects to plot. Please scan your desk first.")
    else:
        # Create a visual 2D representation
        map_width = 800
        map_height = 500
        map_img = Image.new("RGB", (map_width, map_height), color=(22, 27, 34))
        draw = ImageDraw.Draw(map_img)

        # Draw 9-grid boundary lines
        grid_color = (48, 54, 61)
        w1, w2 = map_width / 3, (2 * map_width) / 3
        h1, h2 = map_height / 3, (2 * map_height) / 3
        draw.line([(w1, 0), (w1, map_height)], fill=grid_color, width=2)
        draw.line([(w2, 0), (w2, map_height)], fill=grid_color, width=2)
        draw.line([(0, h1), (map_width, h1)], fill=grid_color, width=2)
        draw.line([(0, h2), (map_width, h2)], fill=grid_color, width=2)

        # Draw grid labels
        grid_labels = [
            ("Top-Left", 20, 15), ("Top-Centre", w1 + 20, 15), ("Top-Right", w2 + 20, 15),
            ("Left", 20, h1 + 15), ("Centre", w1 + 20, h1 + 15), ("Right", w2 + 20, h1 + 15),
            ("Bottom-Left (Near)", 20, h2 + 15), ("Bottom-Centre (Near)", w1 + 20, h2 + 15), ("Bottom-Right (Near)", w2 + 20, h2 + 15),
        ]
        for label, lx, ly in grid_labels:
            draw.text((lx, ly), label, fill=(110, 118, 129))

        # Color palette for objects
        palette = [
            (88, 166, 255),  # blue
            (126, 231, 135), # green
            (210, 153, 34),  # orange
            (248, 81, 73),   # red
            (188, 140, 255), # purple
            (240, 136, 62),  # gold
            (86, 212, 221),  # cyan
            (255, 123, 114), # coral
        ]

        # Draw proximity connections between nearby objects
        from spatial import distance
        for i in range(len(current_objects)):
            for j in range(i + 1, len(current_objects)):
                d = distance(current_objects[i], current_objects[j])
                if d < 0.28:
                    px1 = int(current_objects[i]["x"] * map_width)
                    py1 = int(current_objects[i]["y"] * map_height)
                    px2 = int(current_objects[j]["x"] * map_width)
                    py2 = int(current_objects[j]["y"] * map_height)
                    draw.line([(px1, py1), (px2, py2)], fill=(65, 75, 90), width=2)

        # Plot objects
        for idx, obj in enumerate(current_objects):
            color = palette[idx % len(palette)]
            px = int(obj["x"] * map_width)
            py = int(obj["y"] * map_height)
            radius = 16

            # Outer ring & inner dot
            draw.ellipse([px - radius, py - radius, px + radius, py + radius], fill=color, outline=(255, 255, 255), width=2)
            # Label
            draw.text((px + 18, py - 8), obj["name"].title(), fill=(255, 255, 255))

        st.image(map_img, caption="Spatial 9-Grid Layout (Coordinates normalized relative to desk boundaries)", width="stretch")

        # Grid Cards Summary
        st.markdown("#### 📍 Objects by Spatial Sector:")
        sectors = {
            "Top Area (Far)": [o["name"] for o in current_objects if o["y"] < 1/3],
            "Middle Area": [o["name"] for o in current_objects if 1/3 <= o["y"] < 2/3],
            "Bottom Area (Near User)": [o["name"] for o in current_objects if o["y"] >= 2/3],
        }
        sec_cols = st.columns(3)
        for i, (sec_name, sec_items) in enumerate(sectors.items()):
            with sec_cols[i]:
                st.write(f"**{sec_name}**")
                if sec_items:
                    for item in sec_items:
                        st.markdown(f"- `{item}`")
                else:
                    st.caption("Empty")


# -------------------------------------------------------------
# TAB 4: MOVEMENT & SCAN DIFFS
# -------------------------------------------------------------
with tab_diff:
    st.markdown("### 🔄 Object Movement & Verification")
    st.caption("EchoMap tracks changes across scans, distinguishing between confirmed location, movement, and missing items.")

    if not latest or not prev:
        st.info("Scan diffing requires at least two scans in memory. Capture another scan or test simulated movement below.")
        if st.button("🧪 Simulate Moved Keys & Missing Mug", width="content"):
            # Save a second scan with moved items
            simulated_new = [
                {"name": "phone", "x": 0.28, "y": 0.52, "confidence": 0.96, "region_desc": "left side of the desk"},
                {"name": "keys", "x": 0.78, "y": 0.75, "confidence": 0.90, "region_desc": "bottom-right area of the desk"}, # Moved!
                {"name": "notebook", "x": 0.55, "y": 0.70, "confidence": 0.89, "region_desc": "bottom centre of the desk"},
                {"name": "pen", "x": 0.45, "y": 0.68, "confidence": 0.87, "region_desc": "bottom centre of the desk"},
                {"name": "laptop", "x": 0.50, "y": 0.28, "confidence": 0.98, "region_desc": "top centre of the desk"},
                {"name": "glasses", "x": 0.15, "y": 0.20, "confidence": 0.88, "region_desc": "top-left area of the desk"}, # New item!
                # coffee mug missing!
            ]
            memory.save_scan(simulated_new, scene="simulated_scan_2", summary="Simulated movement test")
            st.rerun()
    else:
        diffs = compare_scans(prev_objects, current_objects)
        
        st.markdown(f"Comparing **Scan #{prev[0]['id']}** ({prev[0]['created_at']}) with **Scan #{latest[0]['id']}** ({latest[0]['created_at']}):")
        
        for item in diffs:
            status = item["status"]
            if status == "possibly_moved":
                pill = '<span class="status-pill pill-moved">POSSIBLY MOVED</span>'
            elif status == "same":
                pill = '<span class="status-pill pill-same">SAME LOCATION</span>'
            elif status == "not_detected":
                pill = '<span class="status-pill pill-missing">NOT DETECTED</span>'
            else:
                pill = '<span class="status-pill pill-new">NEW ITEM</span>'

            st.markdown(
                f"- {pill} **{item['name'].title()}**: {item['description']}",
                unsafe_allow_html=True
            )


# -------------------------------------------------------------
# TAB 5: USER CORRECTIONS
# -------------------------------------------------------------
with tab_corrections:
    st.markdown("### ✍️ User-Taught Corrections & Spatial Facts")
    st.markdown(
        "Accessibility Feature: When a blind user places an item or knows a tactile fact, "
        "they can teach EchoMap directly. User corrections are stored safely alongside visual observations."
    )

    with st.form("correction_form", clear_on_submit=True):
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            obj_name = st.text_input("Object Name:", placeholder="e.g. keys")
        with col_c2:
            rel_type = st.selectbox(
                "Relationship:",
                ["beside", "near", "left of", "right of", "in front of", "behind", "on top of"]
            )
        with col_c3:
            ref_name = st.text_input("Reference Object:", placeholder="e.g. phone")

        notes = st.text_input("Additional Note (Optional):", placeholder="e.g. In the leather tray")
        submit_corr = st.form_submit_button("💾 Save Spatial Fact")

        if submit_corr and obj_name and ref_name:
            memory.save_correction(obj_name, rel_type, ref_name, note=notes)
            st.success(f"Saved: {obj_name} is {rel_type} {ref_name}!")
            st.rerun()

    st.markdown("#### 📖 Recorded User Corrections:")
    saved_corrs = memory.get_corrections()
    if saved_corrs:
        corr_df = pd.DataFrame(saved_corrs)[["id", "object_name", "relation_type", "reference_object", "note", "created_at"]]
        st.dataframe(corr_df, width="stretch", hide_index=True)
    else:
        st.caption("No user corrections recorded yet.")

# Footer
st.markdown("---")
st.caption("EchoMap Assistive Spatial System | Built for University of Bedfordshire HCI + AI + XR Hackathon by Team PythonCharlie")
