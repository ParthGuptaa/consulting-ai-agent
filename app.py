# app.py (Version 2.0)

import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os

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
        /* Main app background */
        .stApp {
            background-color: #0E1117;
        }
        /* Sidebar styling */
        .css-1d391kg {
            background-color: #1a1a2e;
        }
        /* Button styling */
        .stButton>button {
            border: 2px solid #4A4A4A;
            border-radius: 20px;
            color: #FFFFFF;
            background-color: #262730;
            padding: 10px 24px;
            font-weight: bold;
            transition: all 0.3s ease-in-out;
        }
        .stButton>button:hover {
            border-color: #00A8E8;
            color: #00A8E8;
        }
        /* Title styling */
        h1 {
            color: #FFFFFF;
            text-align: center;
            padding-bottom: 20px;
        }
        /* Header styling */
        .st-emotion-cache-18ni7ap {
             background: linear-gradient(90deg, #1a1a2e, #16213e, #0f3460);
        }
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
    st.error("🚨 API keys are not configured correctly in Streamlit secrets. Please add them before proceeding.")

# --- AGENT'S TOOLS (BACKEND FUNCTIONS) ---

def perform_search(query, use_elite_sources=False, max_results=5):
    search_query = query
    if use_elite_sources:
        # Construct a query that prioritizes top consulting firms and research outlets
        search_query += " site:mckinsey.com OR site:bcg.com OR site:bain.com OR site:deloitte.com OR site:ey.com OR site:pwc.com OR site:hbr.org OR site:gartner.com"
    
    try:
        response = tavily.search(query=search_query, search_depth="advanced", max_results=max_results)
        return response['results']
    except Exception as e:
        return f"Error during search: {e}"

def scrape_and_extract(url, information_to_extract, status_placeholder):
    status_placeholder.write(f"   ↳  🧠 Analyzing {url}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True)[:15000]
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""Based *only* on the text below, find the value for: "{information_to_extract}". If not found, respond *only* with "Information Not Found". Do not add commentary. Text: --- {text_content} ---"""
        ai_response = model.generate_content(prompt)
        result = ai_response.text.strip()
        return result
    except Exception as e:
        return "Extraction Failed"

def generate_elaborate_summary(data_df, research_topic):
    try:
        data_string = data_df.to_string(index=False)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        As a Principal Consultant at a top-tier firm, your task is to synthesize the following research data into an insightful executive summary. The research was conducted on "{research_topic}".

        Your summary must be structured into three sections:
        1.  **Key Insights:** What are the most critical, high-level findings from the data? Use bullet points.
        2.  **Potential Implications:** Based on the insights, what are the potential strategic implications for a business operating in this space? Use bullet points.
        3.  **Identified Gaps & Next Steps:** What information seems to be missing? What should be the logical next steps for a deeper analysis? Use bullet points.

        Do not invent information. Your analysis must be derived *only* from the data provided below.

        **Research Data:**
        ---
        {data_string}
        ---
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating summary: {e}"

# --- FRONT-END UI (STREAMLIT) ---

st.sidebar.header("✨ CogniSynth AI")
st.sidebar.markdown("_Your AI Consulting Partner_")

with st.sidebar.form("research_form"):
    topic = st.text_input("🎯 **Research Topic**", "The impact of AI on the global banking sector")
    data_points_text = st.text_area("📋 **Key Questions / Data Points** (one per line)", 
                                    "Projected market size of AI in banking by 2030\nKey areas of AI adoption (e.g., fraud detection, customer service)\nMain challenges for AI implementation in banks\nRegulatory hurdles for AI in finance",
                                    height=150)
    
    use_elite_sources = st.toggle("🔎 Prioritize elite consulting sources?", value=True)
    submitted = st.form_submit_button("🚀 Start Synthesis")

# Main content area
st.title("🤖 CogniSynth AI Agent")

if submitted:
    if not topic or not data_points_text:
        st.error("Please provide both a topic and at least one data point.")
    else:
        data_points_to_find = [line.strip() for line in data_points_text.split('\n') if line.strip()]
        
        st.info(f"Synthesizing insights for: **{topic}**")
        status_placeholder = st.empty()
        
        results_list = []

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
                            found_info = True
                            break
                
                if not found_info:
                    results_list.append({"Data Point": point, "Finding": "Could not find in top search results", "Source URL": "N/A"})
        
        status_placeholder.empty()
        st.success("✅ Synthesis Complete!")
        
        results_df = pd.DataFrame(results_list)
        results_df["👍 Helpful"] = False # Add the interactive checkbox column

        st.subheader("📊 Raw Findings")
        st.markdown("Here is the raw data collected by the agent. Please rate the findings.")
        edited_df = st.data_editor(results_df, use_container_width=True, height=300)

        with st.spinner('💡 Generating strategic summary...'):
            summary = generate_elaborate_summary(edited_df, topic)
            st.subheader("📝 Executive Summary")
            st.markdown(summary)
else:
    st.markdown("Enter your research topic and key questions in the sidebar to begin.")
