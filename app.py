# app.py (Version 3.0 - The Multi-Modal Agent)

import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os
from PIL import Image
from io import BytesIO
import urllib.parse

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="CogniSynth | AI Consulting Agent",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS FOR "GEN-Z" UI ---
def load_css():
    st.markdown("""
    <style>
        .stApp { background-color: #0E1117; }
        .st-emotion-cache-1d391kg { background-color: #1a1a2e; }
        .stButton>button {
            border: 2px solid #4A4A4A; border-radius: 20px; color: #FFFFFF;
            background-color: #262730; padding: 10px 24px; font-weight: bold;
            transition: all 0.3s ease-in-out;
        }
        .stButton>button:hover { border-color: #00A8E8; color: #00A8E8; }
        h1 { color: #FFFFFF; text-align: center; padding-bottom: 20px; }
        .st-emotion-cache-18ni7ap { background: linear-gradient(90deg, #1a1a2e, #16213e, #0f3460); }
    </style>
    """, unsafe_allow_html=True)

load_css()

# --- API CONFIGURATION ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
    tavily = TavilyClient(api_key=TAVILY_API_KEY)
except Exception as e:
    st.error("🚨 API keys are not configured correctly. Please add them in Streamlit secrets.")

# --- AGENT'S TOOLS (BACKEND FUNCTIONS) ---

def perform_search(query, use_elite_sources=False, max_results=3):
    search_query = query
    if use_elite_sources:
        search_query += " site:mckinsey.com OR site:bcg.com OR site:bain.com OR site:deloitte.com OR site:ey.com OR site:pwc.com OR site:hbr.org OR site:gartner.com"
    try:
        response = tavily.search(query=search_query, search_depth="advanced", max_results=max_results)
        return response['results']
    except Exception:
        return []

def scrape_and_extract(url, information_to_extract, status_placeholder):
    status_placeholder.write(f"   ↳ 🧠 Analyzing text from {url[:70]}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True)[:15000]
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""Based *only* on the text below, find the value for: "{information_to_extract}". If not found, respond *only* with "Information Not Found". Do not add commentary. Text: --- {text_content} ---"""
        ai_response = model.generate_content(prompt)
        return ai_response.text.strip()
    except Exception:
        return "Extraction Failed"

# NEW: Tool to find and validate relevant images
def find_relevant_images(url, topic, status_placeholder):
    status_placeholder.write(f"   ↳ 🖼️ Scanning for visuals at {url[:70]}...")
    relevant_images = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        images = soup.find_all('img')
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        for img in images[:5]: # Limit to first 5 images to be efficient
            img_url = img.get('src')
            if not img_url:
                continue
            
            # Make sure URL is absolute
            img_url = urllib.parse.urljoin(url, img_url)
            
            try:
                # Get image bytes
                img_response = requests.get(img_url, stream=True, timeout=5)
                img_response.raise_for_status()
                img_bytes = img_response.content
                image = Image.open(BytesIO(img_bytes))

                # Use Gemini 1.5 Flash to analyze the image
                prompt = [
                    f"Is this image a relevant chart, graph, or data visualization for the topic: '{topic}'? Answer with only 'Yes' or 'No'.",
                    image
                ]
                response = model.generate_content(prompt)
                
                if 'yes' in response.text.lower():
                    relevant_images.append(img_url)
                    status_placeholder.write(f"   ↳ ✅ Found relevant visual: {img_url}")
                    if len(relevant_images) >= 2: # Stop after finding 2 relevant images per source
                        break
            except Exception:
                continue # Skip if image is broken or inaccessible
    except Exception:
        return []
    return relevant_images

def generate_elaborate_summary(data_df, research_topic):
    # This function remains the same
    try:
        data_string = data_df.to_string(index=False)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""As a Principal Consultant, synthesize the following data for "{research_topic}" into a summary with three sections: Key Insights, Potential Implications, and Identified Gaps & Next Steps. Use bullet points for each. Base your analysis *only* on the data provided. Data: --- {data_string} ---"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating summary: {e}"

# --- FRONT-END UI (STREAMLIT) ---

st.sidebar.header("✨ CogniSynth AI")
st.sidebar.markdown("_Your Multi-Modal AI Partner_")

with st.sidebar.form("research_form"):
    topic = st.text_input("🎯 **Research Topic**", "The impact of AI on the global banking sector")
    data_points_text = st.text_area("📋 **Key Questions / Data Points** (one per line)", 
                                    "Projected market size of AI in banking by 2030\nKey areas of AI adoption (e.g., fraud detection, customer service)\nMain challenges for AI implementation in banks\nRegulatory hurdles for AI in finance",
                                    height=150)
    
    use_elite_sources = st.toggle("🔎 Prioritize elite consulting sources?", value=True)
    submitted = st.form_submit_button("🚀 Start Synthesis")

st.title("🤖 CogniSynth AI Agent")

if submitted:
    if not topic or not data_points_text:
        st.error("Please provide both a topic and at least one data point.")
    else:
        data_points_to_find = [line.strip() for line in data_points_text.split('\n') if line.strip()]
        
        st.info(f"Synthesizing insights for: **{topic}**")
        status_placeholder = st.empty()
        
        results_list = []
        all_visuals = []

        with st.spinner('Agent is working... This may take a few minutes.'):
            for i, point in enumerate(data_points_to_find):
                status_placeholder.text(f"({i+1}/{len(data_points_to_find)}) 🔎 Searching for: '{point}'")
                search_results = perform_search(f"{topic} {point}", use_elite_sources)
                
                found_info = False
                if isinstance(search_results, list) and search_results:
                    for result in search_results:
                        url = result['url']
                        extracted_info = scrape_and_extract(url, point, status_placeholder)
                        
                        if "Information Not Found" not in extracted_info and "Extraction Failed" not in extracted_info:
                            results_list.append({"Data Point": point, "Finding": extracted_info, "Source URL": url})
                            # Now, look for images on this successful source
                            visuals = find_relevant_images(url, topic, status_placeholder)
                            all_visuals.extend(visuals)
                            found_info = True
                            break
                
                if not found_info:
                    results_list.append({"Data Point": point, "Finding": "Could not find in top search results", "Source URL": "N/A"})
        
        status_placeholder.empty()
        st.success("✅ Synthesis Complete!")
        
        results_df = pd.DataFrame(results_list)

        # --- Display Results ---
        st.subheader("📝 Executive Summary")
        with st.spinner('💡 Generating strategic summary...'):
            summary = generate_elaborate_summary(results_df, topic)
            st.markdown(summary)

        if all_visuals:
            st.subheader("📊 Relevant Charts & Graphs")
            unique_visuals = list(set(all_visuals)) # Remove duplicate images
            cols = st.columns(len(unique_visuals) if len(unique_visuals) < 4 else 3)
            for i, visual_url in enumerate(unique_visuals):
                with cols[i % 3]:
                    st.image(visual_url, caption=f"Source: {visual_url[:50]}...", use_column_width=True)
        
        st.subheader("📋 Raw Findings")
        st.markdown("Here is the raw data collected by the agent.")
        st.data_editor(results_df, use_container_width=True, height=210) # Reduced height
else:
    st.markdown("Enter your research topic and key questions in the sidebar to begin.")
