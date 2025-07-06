# app.py

import streamlit as st
import pandas as pd
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Consulting Agentic AI",
    page_icon="🤖",
    layout="wide"
)

# --- API CONFIGURATION ---
# We will use Streamlit's secrets management
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]
    
    genai.configure(api_key=GOOGLE_API_KEY)
    tavily = TavilyClient(api_key=TAVILY_API_KEY)
except Exception as e:
    st.error("API keys are not configured correctly in Streamlit secrets. Please add them.")

# --- AGENT'S TOOLS (BACKEND FUNCTIONS) ---

def perform_search(query, max_results=3):
    try:
        response = tavily.search(query=query, search_depth="basic", max_results=max_results)
        return response['results']
    except Exception as e:
        return f"Error during search: {e}"

def scrape_and_extract(url, information_to_extract, status_placeholder):
    status_placeholder.text(f"   ↳  Scraping {url}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        text_content = soup.get_text(separator=' ', strip=True)[:15000]
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""Based *only* on the following text, find the value for the query: "{information_to_extract}". If not present, respond with only "Information Not Found". Do not add commentary. Webpage Text: --- {text_content} ---"""
        ai_response = model.generate_content(prompt)
        result = ai_response.text.strip()
        status_placeholder.text(f"   ↳  AI Result: {result[:50]}...")
        return result
    except Exception as e:
        return "Extraction Failed"

def generate_summary_with_gemini(data_df, research_topic):
    try:
        data_string = data_df.to_string(index=False)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""As a top-tier business consultant, write a concise, professional executive summary based *only* on the data provided below about "{research_topic}". Begin with an introductory sentence, present the key findings, and conclude with a brief closing statement. Do not invent any information. Data: --- {data_string} ---"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating summary with Gemini: {e}"

# --- FRONT-END UI (STREAMLIT) ---

st.title("🤖 Consulting Agentic AI")
st.markdown("A basic agent to automate the 'Data Collector' process for consultants. Enter a topic and the key data points you need, and the agent will search the web, extract the information, and generate a summary.")

with st.form("research_form"):
    topic = st.text_input("Enter the main research topic:", "The future of renewable energy in Australia")
    
    data_points_text = st.text_area("Enter the data points to find (one per line):", 
                                    "Projected market size by 2030\nKey government incentives\nLeading companies in the solar energy sector\nMain challenges for wind energy adoption",
                                    height=150)
    
    submitted = st.form_submit_button("Start Research")

if submitted:
    if not topic or not data_points_text:
        st.error("Please provide both a topic and at least one data point.")
    else:
        data_points_to_find = [line.strip() for line in data_points_text.split('\n') if line.strip()]
        
        st.info(f"Starting research for: **{topic}**")
        status_placeholder = st.empty()
        
        results_list = []

        with st.spinner('Agent is working... This may take a few minutes.'):
            for i, point in enumerate(data_points_to_find):
                status_placeholder.text(f"({i+1}/{len(data_points_to_find)}) 🔎 Searching for: '{point}'")
                search_results = perform_search(f"{topic} {point}")
                
                found_info = False
                if isinstance(search_results, list):
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
        st.success("Research complete!")
        
        results_df = pd.DataFrame(results_list)
        
        st.subheader("📊 Research Findings")
        st.dataframe(results_df, use_container_width=True)

        with st.spinner('Generating summary...'):
            summary = generate_summary_with_gemini(results_df, topic)
            st.subheader(" EXECUTIVE SUMMARY")
            st.markdown(summary)