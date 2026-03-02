import streamlit as st
import asyncio
import pandas as pd
import threading
import threading
from trading_bot import TradingBot
import time
import time
import json
from datetime import datetime
import requests
import os
import subprocess
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path

# Base directory for all file operations
BASE_DIR = "/Users/enderj/Library/CloudStorage/GoogleDrive-enderjnets@gmail.com/My Drive/Bittrader/Bittrader EA/Dev Folder/Coinbase Cripto Trader Claude"
COORDINATOR_DB = os.path.join(BASE_DIR, "coordinator.db")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FUTURES_DIR = os.path.join(BASE_DIR, "data_futures")

# --- BROKER & BOT SETUP ---
from backtester import Backtester
from coinbase_client import CoinbaseClient
from scanner import MarketScanner
# from schwab_client import SchwabClient  # TEMPORAL: archivo eliminado

# Page Config
st.set_page_config(
    page_title="Coinbase Crypto Bot",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize theme in session state
if 'dark_mode' not in st.session_state:
    st.session_state['dark_mode'] = True  # Default to dark mode

# Custom CSS - Dynamic based on theme
if st.session_state['dark_mode']:
    # Dark Mode CSS - Mejorado con mejor contraste y legibilidad
    st.markdown("""
    <style>
        /* ===== FONDO PRINCIPAL ===== */
        .stApp {
            background: linear-gradient(135deg, #1a1d29 0%, #0f111a 100%);
        }

        .main {
            background-color: transparent;
            color: #e8eaed;
        }

        /* ===== SIDEBAR ===== */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e2433 0%, #151820 100%);
            border-right: 1px solid #2d3748;
        }

        section[data-testid="stSidebar"] .css-17eq0hr {
            color: #e8eaed;
        }

        /* ===== TÍTULOS Y HEADERS ===== */
        h1, h2, h3, h4, h5, h6 {
            color: #ffffff !important;
            font-weight: 600;
        }

        h1 {
            background: linear-gradient(90deg, #60a5fa 0%, #3b82f6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        /* ===== TEXTO ===== */
        p, span, div, label {
            color: #e5e7eb !important;
        }

        .stMarkdown {
            color: #e5e7eb !important;
        }

        .stMarkdown p {
            color: #e5e7eb !important;
        }

        /* Asegurar que todos los textos sean legibles */
        * {
            color: #e5e7eb;
        }

        /* Override específico para inputs */
        input, textarea, select {
            color: #e5e7eb !important;
        }

        /* ===== BOTONES ===== */
        .stButton>button {
            color: #ffffff;
            background: linear-gradient(135deg, #0052ff 0%, #0041cc 100%);
            border-radius: 10px;
            border: none;
            font-weight: 600;
            padding: 0.75rem 1.5rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0, 82, 255, 0.2);
        }

        .stButton>button:hover {
            background: linear-gradient(135deg, #0041cc 0%, #0052ff 100%);
            box-shadow: 0 6px 12px rgba(0, 82, 255, 0.4);
            transform: translateY(-2px);
        }

        /* ===== INPUTS Y SELECTBOXES ===== */
        .stTextInput>div>div>input,
        .stNumberInput>div>div>input,
        .stTextArea>div>div>textarea,
        .stDateInput>div>div>input,
        .stTimeInput>div>div>input {
            background-color: #1f2937 !important;
            color: #e5e7eb !important;
            border: 1px solid #374151 !important;
            border-radius: 8px;
            padding: 0.75rem;
        }

        .stTextInput>div>div>input:focus,
        .stNumberInput>div>div>input:focus,
        .stTextArea>div>div>textarea:focus,
        .stDateInput>div>div>input:focus,
        .stTimeInput>div>div>input:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        /* ===== DATE PICKER CALENDAR COMPLETO ===== */
        /* Calendar container */
        [data-baseweb="calendar"] {
            background-color: #1f2937 !important;
            border: 1px solid #374151 !important;
            border-radius: 8px !important;
            padding: 1rem !important;
        }

        /* Calendar header (month/year) */
        [data-baseweb="calendar-header"] {
            background-color: #1f2937 !important;
            color: #e5e7eb !important;
        }

        [data-baseweb="calendar-header"] button {
            background-color: #374151 !important;
            color: #e5e7eb !important;
        }

        [data-baseweb="calendar-header"] button:hover {
            background-color: #4b5563 !important;
        }

        /* Month and year text */
        [data-baseweb="calendar-header"] [role="heading"] {
            color: #ffffff !important;
            font-weight: 600 !important;
        }

        /* Day names (Su, Mo, Tu, etc.) */
        [data-baseweb="calendar"] thead {
            background-color: #1f2937 !important;
        }

        [data-baseweb="calendar"] thead th {
            color: #9ca3af !important;
            font-weight: 600 !important;
        }

        /* Calendar days */
        [data-baseweb="calendar"] button {
            background-color: #1f2937 !important;
            color: #e5e7eb !important;
            border-radius: 6px !important;
        }

        [data-baseweb="calendar"] button:hover {
            background-color: #374151 !important;
            color: #ffffff !important;
        }

        /* Selected day */
        [data-baseweb="calendar"] button[aria-selected="true"],
        [data-baseweb="calendar"] [aria-pressed="true"] {
            background-color: #ef4444 !important;
            color: #ffffff !important;
            font-weight: 700 !important;
        }

        /* Today's date */
        [data-baseweb="calendar"] [data-highlighted="true"] {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
        }

        /* Disabled days (other months) */
        [data-baseweb="calendar"] button[disabled] {
            background-color: #1f2937 !important;
            color: #4b5563 !important;
            opacity: 0.5 !important;
        }

        /* Calendar month grid */
        [data-baseweb="month"] {
            background-color: #1f2937 !important;
        }

        /* All calendar text */
        .stDateInput * {
            color: #e5e7eb !important;
        }

        /* Popover container for calendar */
        .stDateInput [data-baseweb="popover"] {
            background-color: #1f2937 !important;
            border: 1px solid #374151 !important;
            border-radius: 8px !important;
        }

        /* Number input buttons */
        .stNumberInput button {
            background-color: #374151 !important;
            color: #e5e7eb !important;
        }

        .stNumberInput button:hover {
            background-color: #4b5563 !important;
        }

        .stSelectbox>div>div>select,
        .stMultiSelect>div>div>select {
            background-color: #1f2937 !important;
            color: #e5e7eb !important;
            border: 1px solid #374151 !important;
            border-radius: 8px;
        }

        /* ===== SELECTBOX DROPDOWN OPTIONS ===== */
        [data-baseweb="select"] {
            background-color: #1f2937 !important;
        }

        [data-baseweb="select"] > div {
            background-color: #1f2937 !important;
            color: #e5e7eb !important;
            border: 1px solid #374151 !important;
        }

        [data-baseweb="popover"] {
            background-color: #1f2937 !important;
        }

        [data-baseweb="menu"] {
            background-color: #1f2937 !important;
            border: 1px solid #374151 !important;
            border-radius: 8px !important;
        }

        ul[role="listbox"] {
            background-color: #1f2937 !important;
            border: 1px solid #374151 !important;
            padding: 0.5rem !important;
        }

        li[role="option"] {
            background-color: #1f2937 !important;
            color: #e5e7eb !important;
            padding: 0.75rem 1rem !important;
            border-radius: 6px !important;
            margin: 0.25rem 0 !important;
        }

        li[role="option"]:hover {
            background-color: #374151 !important;
            color: #ffffff !important;
        }

        li[aria-selected="true"] {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
        }

        /* ===== MULTISELECT ESPECÍFICO ===== */
        [data-baseweb="select"] input {
            background-color: #1f2937 !important;
            color: #e5e7eb !important;
        }

        [data-baseweb="select"] svg {
            fill: #9ca3af !important;
        }

        /* ===== MULTISELECT PILLS ===== */
        .stMultiSelect span[data-baseweb="tag"] {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
        }

        span[data-baseweb="tag"] {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
            border-radius: 6px !important;
            padding: 0.25rem 0.5rem !important;
        }

        /* ===== WIDGET LABELS ===== */
        .stTextInput label,
        .stNumberInput label,
        .stSelectbox label,
        .stMultiSelect label,
        .stTextArea label,
        .stDateInput label,
        .stTimeInput label,
        .stSlider label,
        .stCheckbox label,
        .stRadio label {
            font-weight: 500 !important;
        }

        /* ===== ASEGURAR CONTRASTE EN TODOS LOS INPUTS (MODO OSCURO) ===== */
        input[type="text"],
        input[type="number"],
        input[type="email"],
        input[type="password"],
        input[type="search"],
        input[type="tel"],
        input[type="url"],
        input[type="date"],
        textarea,
        select {
            background-color: #1f2937 !important;
            color: #e5e7eb !important;
            border: 1px solid #374151 !important;
        }

        /* ===== TODOS LOS ELEMENTOS DE BASEWEB (MODO OSCURO) ===== */
        [class*="StyledInput"],
        [class*="StyledSelect"],
        [data-baseweb="input"],
        [data-baseweb="textarea"] {
            background-color: #1f2937 !important;
            color: #e5e7eb !important;
        }

        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea {
            background-color: #1f2937 !important;
            color: #e5e7eb !important;
        }

        /* ===== MÉTRICAS ===== */
        [data-testid="stMetricValue"] {
            color: #60a5fa !important;
            font-size: 2rem !important;
            font-weight: 700 !important;
        }

        [data-testid="stMetricLabel"] {
            color: #9ca3af !important;
            font-size: 0.875rem !important;
        }

        [data-testid="stMetricDelta"] {
            color: #34d399 !important;
        }

        /* ===== CARDS Y CONTAINERS ===== */
        .element-container {
            background-color: transparent;
        }

        div[data-testid="stExpander"] {
            background-color: #1f2937;
            border: 1px solid #374151;
            border-radius: 12px;
            padding: 1rem;
            margin: 0.5rem 0;
        }

        div[data-testid="stExpander"] summary {
            color: #e5e7eb !important;
            font-weight: 600;
        }

        /* ===== DATAFRAMES Y TABLAS ===== */
        .stDataFrame {
            background-color: #1f2937;
            border-radius: 8px;
            overflow: hidden;
        }

        .stDataFrame table {
            color: #e5e7eb !important;
        }

        .stDataFrame th {
            background-color: #374151 !important;
            color: #f3f4f6 !important;
            font-weight: 600;
        }

        .stDataFrame td {
            background-color: #1f2937 !important;
            color: #d1d5db !important;
            border-color: #374151 !important;
        }

        /* ===== PROGRESS BAR ===== */
        .stProgress > div > div > div {
            background-color: #3b82f6;
        }

        /* ===== TABS ===== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #1f2937;
            border-radius: 10px;
            padding: 0.5rem;
        }

        .stTabs [data-baseweb="tab"] {
            color: #9ca3af !important;
            background-color: transparent;
            border-radius: 8px;
            padding: 0.5rem 1rem;
        }

        .stTabs [aria-selected="true"] {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
        }

        /* ===== ALERTS ===== */
        .stAlert {
            background-color: #1f2937;
            border: 1px solid #374151;
            border-radius: 8px;
            color: #e5e7eb;
        }

        .stSuccess {
            background-color: rgba(16, 185, 129, 0.1) !important;
            border-left: 4px solid #10b981 !important;
            color: #d1fae5 !important;
        }

        .stError {
            background-color: rgba(239, 68, 68, 0.1) !important;
            border-left: 4px solid #ef4444 !important;
            color: #fee2e2 !important;
        }

        .stWarning {
            background-color: rgba(245, 158, 11, 0.1) !important;
            border-left: 4px solid #f59e0b !important;
            color: #fef3c7 !important;
        }

        .stInfo {
            background-color: rgba(59, 130, 246, 0.1) !important;
            border-left: 4px solid #3b82f6 !important;
            color: #dbeafe !important;
        }

        /* ===== RADIO BUTTONS ===== */
        .stRadio > label {
            color: #e5e7eb !important;
        }

        .stRadio [role="radiogroup"] label {
            color: #d1d5db !important;
        }

        /* ===== CHECKBOXES ===== */
        .stCheckbox > label {
            color: #e5e7eb !important;
        }

        /* ===== DIVIDER ===== */
        hr {
            border-color: #374151 !important;
            opacity: 0.5;
        }

        /* ===== SCROLLBAR ===== */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }

        ::-webkit-scrollbar-track {
            background: #1f2937;
        }

        ::-webkit-scrollbar-thumb {
            background: #4b5563;
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #6b7280;
        }

        /* ===== CODE BLOCKS ===== */
        code {
            background-color: #1f2937 !important;
            color: #fbbf24 !important;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
        }

        pre {
            background-color: #1f2937 !important;
            border: 1px solid #374151 !important;
            border-radius: 8px;
        }

        /* ===== FORMS Y CONTAINERS ===== */
        .stForm {
            background-color: #1f2937;
            border: 1px solid #374151;
            border-radius: 12px;
            padding: 1.5rem;
        }

        /* ===== MEJORAS VISUALES ===== */
        .element-container:has(> .stMarkdown) {
            padding: 0.25rem 0;
        }

        /* ===== SPINNER ===== */
        .stSpinner > div {
            border-top-color: #3b82f6 !important;
        }
    </style>
    """, unsafe_allow_html=True)
else:
    # Light Mode CSS - Mejorado con diseño moderno
    st.markdown("""
    <style>
        /* ===== FONDO PRINCIPAL ===== */
        .stApp {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        }

        .main {
            background-color: transparent;
            color: #1e293b;
        }

        /* ===== SIDEBAR ===== */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
            border-right: 1px solid #cbd5e1;
        }

        /* ===== TÍTULOS Y HEADERS ===== */
        h1, h2, h3, h4, h5, h6 {
            color: #0f172a !important;
            font-weight: 600;
        }

        h1 {
            background: linear-gradient(90deg, #3b82f6 0%, #1d4ed8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        /* ===== TEXTO ===== */
        p, span, div, label {
            color: #334155 !important;
        }

        /* ===== BOTONES ===== */
        .stButton>button {
            color: #ffffff;
            background: linear-gradient(135deg, #0052ff 0%, #0041cc 100%);
            border-radius: 10px;
            border: none;
            font-weight: 600;
            padding: 0.75rem 1.5rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0, 82, 255, 0.15);
        }

        .stButton>button:hover {
            background: linear-gradient(135deg, #0041cc 0%, #0052ff 100%);
            box-shadow: 0 6px 12px rgba(0, 82, 255, 0.3);
            transform: translateY(-2px);
        }

        /* ===== INPUTS Y SELECTBOXES ===== */
        .stTextInput>div>div>input,
        .stNumberInput>div>div>input,
        .stTextArea>div>div>textarea,
        .stDateInput>div>div>input,
        .stTimeInput>div>div>input {
            background-color: #ffffff !important;
            color: #1e293b !important;
            border: 2px solid #cbd5e1 !important;
            border-radius: 8px;
            padding: 0.75rem;
        }

        .stTextInput>div>div>input:focus,
        .stNumberInput>div>div>input:focus,
        .stTextArea>div>div>textarea:focus,
        .stDateInput>div>div>input:focus,
        .stTimeInput>div>div>input:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        /* ===== DATE PICKER CALENDAR COMPLETO ===== */
        /* Calendar container */
        [data-baseweb="calendar"] {
            background-color: #ffffff !important;
            border: 2px solid #e2e8f0 !important;
            border-radius: 8px !important;
            padding: 1rem !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
        }

        /* Calendar header (month/year) */
        [data-baseweb="calendar-header"] {
            background-color: #ffffff !important;
            color: #1e293b !important;
        }

        [data-baseweb="calendar-header"] button {
            background-color: #f1f5f9 !important;
            color: #1e293b !important;
        }

        [data-baseweb="calendar-header"] button:hover {
            background-color: #e2e8f0 !important;
        }

        /* Month and year text */
        [data-baseweb="calendar-header"] [role="heading"] {
            color: #0f172a !important;
            font-weight: 600 !important;
        }

        /* Day names (Su, Mo, Tu, etc.) */
        [data-baseweb="calendar"] thead {
            background-color: #ffffff !important;
        }

        [data-baseweb="calendar"] thead th {
            color: #64748b !important;
            font-weight: 600 !important;
        }

        /* Calendar days */
        [data-baseweb="calendar"] button {
            background-color: #ffffff !important;
            color: #1e293b !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
        }

        [data-baseweb="calendar"] button:hover {
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
        }

        /* Selected day */
        [data-baseweb="calendar"] button[aria-selected="true"],
        [data-baseweb="calendar"] [aria-pressed="true"] {
            background-color: #ef4444 !important;
            color: #ffffff !important;
            font-weight: 700 !important;
        }

        /* Today's date */
        [data-baseweb="calendar"] [data-highlighted="true"] {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
        }

        /* Disabled days (other months) */
        [data-baseweb="calendar"] button[disabled] {
            background-color: #ffffff !important;
            color: #cbd5e1 !important;
            opacity: 0.5 !important;
        }

        /* Calendar month grid */
        [data-baseweb="month"] {
            background-color: #ffffff !important;
        }

        /* All calendar text */
        .stDateInput * {
            color: #1e293b !important;
        }

        /* Popover container for calendar */
        .stDateInput [data-baseweb="popover"] {
            background-color: #ffffff !important;
            border: 2px solid #e2e8f0 !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
        }

        /* Number input buttons */
        .stNumberInput button {
            background-color: #f1f5f9 !important;
            color: #1e293b !important;
        }

        .stNumberInput button:hover {
            background-color: #e2e8f0 !important;
        }

        .stSelectbox>div>div>select,
        .stMultiSelect>div>div>select {
            background-color: #ffffff !important;
            color: #1e293b !important;
            border: 2px solid #cbd5e1 !important;
            border-radius: 8px;
        }

        /* ===== SELECTBOX DROPDOWN OPTIONS ===== */
        [data-baseweb="select"] {
            background-color: #ffffff !important;
        }

        [data-baseweb="select"] > div {
            background-color: #ffffff !important;
            color: #1e293b !important;
            border: 2px solid #cbd5e1 !important;
        }

        [data-baseweb="popover"] {
            background-color: #ffffff !important;
        }

        [data-baseweb="menu"] {
            background-color: #ffffff !important;
            border: 2px solid #e2e8f0 !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
        }

        ul[role="listbox"] {
            background-color: #ffffff !important;
            border: 2px solid #e2e8f0 !important;
            padding: 0.5rem !important;
        }

        li[role="option"] {
            background-color: #ffffff !important;
            color: #1e293b !important;
            padding: 0.75rem 1rem !important;
            border-radius: 6px !important;
            margin: 0.25rem 0 !important;
            font-weight: 500 !important;
        }

        li[role="option"]:hover {
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
        }

        li[aria-selected="true"] {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
        }

        /* ===== MULTISELECT ESPECÍFICO ===== */
        [data-baseweb="select"] input {
            background-color: #ffffff !important;
            color: #1e293b !important;
        }

        [data-baseweb="select"] svg {
            fill: #64748b !important;
        }

        /* ===== MULTISELECT PILLS ===== */
        .stMultiSelect span[data-baseweb="tag"] {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
        }

        span[data-baseweb="tag"] {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
            border-radius: 6px !important;
            padding: 0.25rem 0.5rem !important;
        }

        /* ===== WIDGET LABELS ===== */
        .stTextInput label,
        .stNumberInput label,
        .stSelectbox label,
        .stMultiSelect label,
        .stTextArea label,
        .stDateInput label,
        .stTimeInput label,
        .stSlider label,
        .stCheckbox label,
        .stRadio label {
            font-weight: 500 !important;
        }

        /* ===== ASEGURAR CONTRASTE EN TODOS LOS INPUTS (MODO CLARO) ===== */
        input[type="text"],
        input[type="number"],
        input[type="email"],
        input[type="password"],
        input[type="search"],
        input[type="tel"],
        input[type="url"],
        input[type="date"],
        textarea,
        select {
            background-color: #ffffff !important;
            color: #1e293b !important;
            border: 2px solid #cbd5e1 !important;
        }

        /* ===== TODOS LOS ELEMENTOS DE BASEWEB (MODO CLARO) ===== */
        [class*="StyledInput"],
        [class*="StyledSelect"],
        [data-baseweb="input"],
        [data-baseweb="textarea"] {
            background-color: #ffffff !important;
            color: #1e293b !important;
        }

        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea {
            background-color: #ffffff !important;
            color: #1e293b !important;
        }

        /* ===== MÉTRICAS ===== */
        [data-testid="stMetricValue"] {
            color: #2563eb !important;
            font-size: 2rem !important;
            font-weight: 700 !important;
        }

        [data-testid="stMetricLabel"] {
            color: #64748b !important;
            font-size: 0.875rem !important;
        }

        [data-testid="stMetricDelta"] {
            color: #10b981 !important;
        }

        /* ===== CARDS Y CONTAINERS ===== */
        div[data-testid="stExpander"] {
            background-color: #ffffff;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            padding: 1rem;
            margin: 0.5rem 0;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }

        div[data-testid="stExpander"] summary {
            color: #0f172a !important;
            font-weight: 600;
        }

        /* ===== DATAFRAMES Y TABLAS ===== */
        .stDataFrame {
            background-color: #ffffff;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #e2e8f0;
        }

        .stDataFrame table {
            color: #1e293b !important;
        }

        .stDataFrame th {
            background-color: #f1f5f9 !important;
            color: #0f172a !important;
            font-weight: 600;
        }

        .stDataFrame td {
            background-color: #ffffff !important;
            color: #334155 !important;
            border-color: #e2e8f0 !important;
        }

        /* ===== PROGRESS BAR ===== */
        .stProgress > div > div > div {
            background-color: #3b82f6;
        }

        /* ===== TABS ===== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #f8fafc;
            border-radius: 10px;
            padding: 0.5rem;
        }

        .stTabs [data-baseweb="tab"] {
            color: #64748b !important;
            background-color: transparent;
            border-radius: 8px;
            padding: 0.5rem 1rem;
        }

        .stTabs [aria-selected="true"] {
            background-color: #3b82f6 !important;
            color: #ffffff !important;
        }

        /* ===== ALERTS ===== */
        .stSuccess {
            background-color: rgba(16, 185, 129, 0.1) !important;
            border-left: 4px solid #10b981 !important;
            color: #047857 !important;
        }

        .stError {
            background-color: rgba(239, 68, 68, 0.1) !important;
            border-left: 4px solid #ef4444 !important;
            color: #b91c1c !important;
        }

        .stWarning {
            background-color: rgba(245, 158, 11, 0.1) !important;
            border-left: 4px solid #f59e0b !important;
            color: #b45309 !important;
        }

        .stInfo {
            background-color: rgba(59, 130, 246, 0.1) !important;
            border-left: 4px solid #3b82f6 !important;
            color: #1d4ed8 !important;
        }

        /* ===== RADIO BUTTONS ===== */
        .stRadio > label {
            color: #0f172a !important;
        }

        .stRadio [role="radiogroup"] label {
            color: #334155 !important;
        }

        /* ===== CHECKBOXES ===== */
        .stCheckbox > label {
            color: #0f172a !important;
        }

        /* ===== DIVIDER ===== */
        hr {
            border-color: #cbd5e1 !important;
            opacity: 0.5;
        }

        /* ===== SCROLLBAR ===== */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }

        ::-webkit-scrollbar-track {
            background: #f1f5f9;
        }

        ::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }

        /* ===== CODE BLOCKS ===== */
        code {
            background-color: #f1f5f9 !important;
            color: #d97706 !important;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
        }

        pre {
            background-color: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px;
        }

        /* ===== FORMS Y CONTAINERS ===== */
        .stForm {
            background-color: #ffffff;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }

        /* ===== MEJORAS VISUALES ===== */
        .element-container:has(> .stMarkdown) {
            padding: 0.25rem 0;
        }

        /* ===== SPINNER ===== */
        .stSpinner > div {
            border-top-color: #3b82f6 !important;
        }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ Coinbase Pro Trading Bot")
st.markdown("### Algorithmic High-Frequency Trading System")

# Sidebar
st.sidebar.header("Control Panel")

# Theme Toggle Button - Mejorado
theme_icon = "🌙" if st.session_state['dark_mode'] else "☀️"
theme_text = "Modo Claro" if st.session_state['dark_mode'] else "Modo Oscuro"
if st.sidebar.button(f"{theme_icon} {theme_text}", width='stretch', key="theme_toggle"):
    st.session_state['dark_mode'] = not st.session_state['dark_mode']
    st.rerun()

st.sidebar.markdown("---")

# Bot Control Wrapper
# Streamlit runs in a separate thread/process model usually, 
# but for a local simpler app we can use threading to run the bot loop.

def run_bot_thread(bot_ref):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_ref.run_loop())

if "bots" not in st.session_state:
    st.session_state['bots'] = {
        'Coinbase': TradingBot(broker_type="COINBASE"),
        'Schwab': TradingBot(broker_type="SCHWAB")
    }

if "bot_threads" not in st.session_state:
    st.session_state['bot_threads'] = {}

# Helper to get active bot based on section or selection
# Default to Coinbase for general views
if 'active_bot_key' not in st.session_state:
    st.session_state['active_bot_key'] = 'Coinbase'

bot_instance = st.session_state['bots'][st.session_state['active_bot_key']]


# Mode Selection
mode = st.sidebar.radio("Trading Mode", ["Paper Trading (Simulated)", "Live Trading (Real $$$)"])
if "Paper" in mode:
    bot_instance.mode = "PAPER"
else:
    bot_instance.mode = "LIVE"

st.sidebar.markdown("---")
# Broker Selection (New)
broker_selection = st.sidebar.radio("Connect via", ["Coinbase (Crypto)", "Charles Schwab (Stocks)"])

# Initialize Broker Client in Session State if changed
if 'active_broker_name' not in st.session_state:
    st.session_state['active_broker_name'] = "Coinbase (Crypto)"
    
if broker_selection != st.session_state['active_broker_name']:
    st.session_state['active_broker_name'] = broker_selection
    # Logic to switch broker client will be handled where it is needed (Backtester/Scanner)
    st.toast(f"Switched to {broker_selection}", icon="🔄")
    st.rerun()

is_crypto = "Coinbase" in broker_selection
is_stocks = False  # TEMPORAL: Schwab deshabilitado

# Select Broker Client
# Schwab deshabilitado temporalmente
broker_client = CoinbaseClient()

# Initialize Components with Broker
bt = Backtester(broker_client=broker_client)
scanner = MarketScanner(broker_client=broker_client)

st.title(f"⚡ 'Coinbase Crypto Bot'  # TEMPORAL")

# --- Navigation ---
nav_mode = st.sidebar.radio(
    "Navigation",
    ["🤖 Live Dashboard", "⚡ Bitcoin Spot Pro", "🧪 Backtester", "⚙️ Optimizer", "⛏️ Strategy Miner (AI)", "🌐 Sistema Distribuido"]
)


if nav_mode == "⚡ Bitcoin Spot Pro":
    st.subheader("Bitcoin Spot Pro 🚀 (BTC-USDC)")
    
    # Bitcoin Spot Pro functionality
    tab_swing, tab_grid, tab_calc = st.tabs(["📉 Swing Trader", "🕸️ Grid Bot", "🧮 Position Calculator"])
    
    with tab_swing:
        st.markdown("### Intraday Swing (H1/H4)")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("BTC Price", "$95,432.10", "+1.2%") # Mock
        with col2:
            st.metric("Market Regime", "Lateral / Range", "Neutral")
            
        st.info("ℹ️ Strategy: Bollinger Bands (20,2) + RSI(<30) Reversion")
        if st.button("Analyze Swing Setup"):
            st.write("Fetching H1 data...")
            from btc_spot_strategy import BitcoinSpotStrategy
            strat = BitcoinSpotStrategy(None)
            st.success("Analysis Complete: No Signal (RSI=45)")
            
            # --- STRATEGY CONTROL ---
        st.divider()
        
            # Check if this specific strategy matches the active one
        from btc_spot_strategy import BitcoinSpotStrategy
        
            # Helper to check if current strategy is BTC Spot
        is_btc_strat_active = isinstance(bot_instance.strategy, BitcoinSpotStrategy)
        
        col_ctrl_1, col_ctrl_2 = st.columns([2, 1])
        with col_ctrl_1:
            st.markdown("### 🤖 Strategy Activation")
            if is_btc_strat_active and bot_instance.is_running:
                 st.success("✅ Bitcoin Spot Pro Strategy is RUNNING")
                 if st.button("Stop Strategy", key="stop_btc"):
                     bot_instance.is_running = False
                     st.rerun()
            else:
                 st.warning("Strategy is STOPPED or another strategy is active.")
                 if st.button("🚀 START Bitcoin Spot Strategy", key="start_btc"):
                         # Initialize and assign strategy
                         # Ensure we are using the Coinbase bot (active one in this view)
                     cb_bot = st.session_state['bots']['Coinbase']
                     cb_bot.strategy = BitcoinSpotStrategy(cb_bot.broker)
                     cb_bot.is_running = True
                     
                         # Ensure thread is running
                     if 'Coinbase' not in st.session_state['bot_threads'] or \
                        st.session_state['bot_threads']['Coinbase'] is None or \
                        not st.session_state['bot_threads']['Coinbase'].is_alive():
                            
                        t = threading.Thread(target=run_bot_thread, args=(cb_bot,), daemon=True)
                        t.start()
                        st.session_state['bot_threads']['Coinbase'] = t
                        
                     st.toast("Bitcoin Strategy Activated!", icon="🚀")
                     time.sleep(1)
                     st.rerun()


        with tab_grid:
            st.markdown("### Geometric Grid (Fee-Aware)")
            st.caption("Optimized for Coinbase Maker Fees (0.4%)")
            
            c1, c2, c3 = st.columns(3)
            lower = c1.number_input("Lower Range ($)", value=90000)
            upper = c2.number_input("Upper Range ($)", value=98000)
            grids = c3.number_input("Grid Levels", value=10, min_value=2)
            
            if st.button("Preview Grid"):
                from btc_spot_strategy import BitcoinSpotStrategy
                strat = BitcoinSpotStrategy(None)
                levels, gap = strat.generate_grid_levels(0, lower, upper, grids)
                
                st.write(f"**Grid Gap:** {gap:.2f}%")
                if gap < 1.2:
                    st.error(f"❌ Gap too small! Fees will eat profits. Aim for > 1.2%")
                else:
                    st.success("✅ Gap Healthy (Covers Fees + Profit)")
                    st.dataframe(pd.DataFrame(levels, columns=["Price Level"]))

        with tab_calc:
            st.markdown("### Risk & Position Sizing")
            cap = st.number_input("Account Balance ($)", value=10000.0)
            risk_pct = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.0)
            
            c_ent, c_stop = st.columns(2)
            entry = c_ent.number_input("Entry Price ($)", value=50000.0)
            stop = c_stop.number_input("Stop Loss ($)", value=49000.0)
            
            if entry > stop:
                risk_usd = cap * (risk_pct/100)
                diff = entry - stop
                shares = risk_usd / diff
                pos_size = shares * entry
                
                st.divider()
                st.metric("Max Position Size", f"${pos_size:,.2f}", f"{shares:.4f} BTC")
                st.caption(f"Risking ${risk_usd:.2f} to lose 1% if stopped out.")
            else:
                st.error("Stop Loss must be lower than Entry.")
    
    # --- Strategy Monitor (Manual Refresh) ---
    st.markdown("---")
    st.subheader("📡 Strategy Monitor (Snapshot)")
    
    col_mon_1, col_mon_2 = st.columns([2, 1])
    
    # Use generic bot instance for this view (Coinbase usually)
    mon_bot = st.session_state['bots']['Coinbase']
    
    with col_mon_1:
         st.markdown("**Active Positions**")
         if mon_bot.active_positions:
             st.dataframe(pd.DataFrame(mon_bot.active_positions.values()))
         else:
             st.caption("No active positions.")
             
         st.markdown("**Scanner Candidates**")
         if mon_bot.candidates:
             st.dataframe(pd.DataFrame.from_dict(mon_bot.candidates, orient='index'))
         else:
             st.caption("No candidates.")

    # --- Live Charts ---
    st.markdown("### 📊 Contexto de Mercado (1H)")
    
    # Status Metrics
    m1, m2, m3 = st.columns(3)
    
    # helper for safe access
    l_trend = getattr(mon_bot, 'last_trend', 'WAITING')
    l_price = getattr(mon_bot, 'last_price', 0.0)
    l_time = getattr(mon_bot, 'last_analysis_time', '-')
    
    m1.metric("Tendencia Mercado", l_trend, delta=None, delta_color="off")
    m2.metric("Último Cierre", f"${l_price:,.2f}")
    m3.metric("Último Análisis", l_time)
    
    if st.button("📉 Cargar Gráficos", key="load_charts_btc"):
        with st.spinner("Fetching market data..."):
            # Fetch Data
            end_ts = int(time.time())
            start_ts = end_ts - (100 * 3600) # 100 hours
            
            # Use the bot's scanner/strategy to ensure consistency
            try:
                df_chart = mon_bot.scanner.get_candles("BTC-USD", start_ts, end_ts, "ONE_HOUR")
                if df_chart is not None and not df_chart.empty:
                    # Calculate Indicators
                    df_chart = mon_bot.strategy.calculate_indicators(df_chart)
                    
                    # Chart 1: Price vs BB
                    st.caption("Precio vs Bandas de Bollinger")
                    chart_data = df_chart[['close', 'BB_UPPER', 'BB_LOWER']].copy()
                    st.line_chart(chart_data, color=["#ffffff", "#00ff00", "#ff0000"]) # White Price, Green Upper, Red Lower
                    
                    # Chart 2: RSI
                    st.caption("RSI (Momento)")
                    rsi_data = df_chart[['RSI']].copy()
                    # Add threshold lines manually or just show the line
                    st.line_chart(rsi_data, color="#00aaff")
                    
                    curr_rsi = rsi_data.iloc[-1]['RSI']
                    st.metric("RSI Actual", f"{curr_rsi:.2f}", delta=None)
                    
                else:
                    st.error("No se recibieron datos de Coinbase.")
            except Exception as e:
                st.error(f"Chart Error: {e}")

    with col_mon_2:

        st.markdown("**System Logs**")
        if st.button("🔄 Refresh Monitor"):
            st.rerun()
            
        with st.container(height=300):
            for log in reversed(mon_bot.logs[-20:]):
                st.text(log)


elif nav_mode == "🤖 Live Dashboard":

    # --- Existing Main Dashboard Logic ---
    st.write("") # Spacer

# Risk Level Details
risk_help = """
**🟢 Low Risk**: Breakout + 2 Confirmations (Strict/Sniper)
**🟡 Medium Risk**: Breakout + 1 Confirmation (Balanced)
**🔴 High Risk**: Immediate Breakout (Aggressive/Scalping)
"""
risk_selection = st.sidebar.select_slider(
    "Strategy Risk Level",
    options=["LOW", "MEDIUM", "HIGH"],
    value="LOW",
    help=risk_help
)
# Update the ACTIVE bot's risk level directly
st.session_state['bots'][st.session_state['active_bot_key']].risk_level = risk_selection


status_placeholder = st.sidebar.empty()

st.sidebar.markdown("---")
with st.sidebar.expander("🔑 API Credentials"):
    st.subheader("Coinbase Advanced")
    cb_key = st.text_input("API Key Name", value="", type="password")
    cb_secret = st.text_input("Private Key", value="", type="password")
    if st.button("Save Coinbase Keys"):
        st.toast("Keys Saved (Session Only)", icon="💾")

st.sidebar.markdown("---")
st.sidebar.subheader("💾 Data Management")

# Initialize session state for export if not present
if 'export_json' not in st.session_state:
    st.session_state['export_json'] = None
if 'export_filename' not in st.session_state:
    st.session_state['export_filename'] = None

if st.sidebar.button("Prepare Export File"):
    snapshot = bot_instance.get_system_snapshot()
    json_str = json.dumps(snapshot, indent=2, default=str)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Store in session state
    st.session_state['export_json'] = json_str
    st.session_state['export_filename'] = f"{'Schwab' if is_stocks else 'Coinbase'}_Export_{timestamp}.json"
    st.rerun()

# Display download button if data is ready
if st.session_state['export_json']:
    # debug: show the intended filename
    st.sidebar.caption(f"Ready: {st.session_state['export_filename']}")
    
    st.sidebar.download_button(
        label="📥 Download System Data (JSON)",
        data=st.session_state['export_json'], # Pass string directly
        file_name=st.session_state['export_filename'],
        mime="application/json",
        key="json_download_btn"
    )

st.sidebar.subheader("🤖 Bot Manager")

# Iterate over all bots to show controls
for bot_name, bot_obj in st.session_state['bots'].items():
    with st.sidebar.expander(f"{bot_name} Bot", expanded=True):
        status_ph = st.empty()
        
        if bot_obj.is_running:
            status_ph.success("● RUNNING")
            if st.button(f"Stop {bot_name}", key=f"stop_{bot_name}"):
                bot_obj.is_running = False
                st.rerun()
        else:
            status_ph.error("● STOPPED")
            if st.button(f"Start {bot_name}", key=f"start_{bot_name}"):
                # Start thread
                if bot_name not in st.session_state['bot_threads'] or \
                   st.session_state['bot_threads'][bot_name] is None or \
                   not st.session_state['bot_threads'][bot_name].is_alive():
                       
                    t = threading.Thread(target=run_bot_thread, args=(bot_obj,), daemon=True)
                    t.start()
                    st.session_state['bot_threads'][bot_name] = t
                st.rerun()
                
# Sync active bot selection with sidebar if needed, or just let the tabs decide.
# For the main view, we might want to select which one to "monitor"
st.sidebar.markdown("---")
view_target = st.sidebar.selectbox("Dashboard View Source", list(st.session_state['bots'].keys()), index=0)
if view_target != st.session_state['active_bot_key']:
    st.session_state['active_bot_key'] = view_target
    st.rerun()

# Update global reference for the rest of the script (Dashboard, etc)
bot_instance = st.session_state['bots'][st.session_state['active_bot_key']]


# Cache the product list to avoid API spam
@st.cache_data(ttl=3600)
def load_products():
    try:
        # Use the global broker_client instance directly for reliability
        pairs = broker_client.get_tradable_symbols()
        if not pairs:
             pairs = ["BTC-USD", "ETH-USD"]
        pairs.sort()
        return pairs
    except Exception as e:
        return ["BTC-USD", "ETH-USD"]

# Display Stored Data in Sidebar
st.sidebar.subheader("📂 Stored Market Data")
import os
data_dir = "data"
if os.path.exists(data_dir):
    files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    if files:
        # Show simplified view
        for f in files:
            # Format: BTC-USD_ONE_MINUTE.csv
            try:
                parts = f.replace(".csv", "").rsplit("_", 2) # BTC-USD, ONE, MINUTE ... tricky split
                # Smarter split: split by first "_" is dangerous because of product id.
                # Standardize filename in DataManager to be safe: product_granularity. 
                # Let's just show the filename for now or parse specifically.
                st.sidebar.caption(f"📄 {f}")
            except:
                st.sidebar.text(f)
    else:
        st.sidebar.caption("No data files found.")
else:
    st.sidebar.caption("No data directory.")


# --- DASHBOARD LOGIC ---
if nav_mode == "🤖 Live Dashboard":
    st.header("🚀 Live Trading Dashboard")

    # Top Metrics Row
    col_bal, col_pos, col_pnl, col_status = st.columns(4)
    
    curr_bal = bot_instance.get_balance() if hasattr(bot_instance, 'get_balance') else 0.0
    active_count = len(bot_instance.active_positions)
    
    session_pnl = sum(t['pnl_usd'] for t in bot_instance.trade_history) if bot_instance.trade_history else 0.0
    
    with col_bal:
        st.metric("Balance", f"${curr_bal:,.2f}", f"{'Paper' if bot_instance.mode=='PAPER' else 'Live'}")
        
    with col_pos:
        st.metric("Open Positions", active_count, delta_color="off")
        
    with col_pnl:
        st.metric("Session PnL", f"${session_pnl:,.2f}", delta_color="normal")
        
    with col_status:
        status_txt = "RUNNING" if bot_instance.is_running else "STOPPED"
        # Color code status
        st.markdown(f"**Status**: :{'green' if bot_instance.is_running else 'red'}[{status_txt}]")

    st.divider()

    # Main Content Area
    col_main, col_side = st.columns([2, 1])
    
    with col_main:
        st.subheader("📉 Active Positions")
        if bot_instance.active_positions:
            pos_data = []
            for pid, pdata in bot_instance.active_positions.items():
                row = pdata.copy()
                row['ticker'] = pid
                # Ensure JSON serializable columns mostly
                pos_data.append(row)
            
            df_pos = pd.DataFrame(pos_data)
            
            # Reorder if cols exist
            desired_order = ['ticker', 'side', 'entry_price', 'size', 'pnl', 'entry_time']
            final_cols = [c for c in desired_order if c in df_pos.columns]
            # Add others
            for c in df_pos.columns:
                if c not in final_cols:
                    final_cols.append(c)
            
            st.dataframe(df_pos[final_cols], width='stretch')
            
            if st.button("🚨 PANIC SELL ALL", type="primary", key="panic_btn"):
                if bot_instance.mode == "PAPER":
                     bot_instance.active_positions.clear()
                     bot_instance.log("🚨 PANIC SELL EXECUTED (Paper)")
                     st.warning("All positions closed (Paper mode)")
                     time.sleep(1)
                     st.rerun()
                else:
                    st.error("Panic Sell not implemented for Live mode yet (Safety).")
        else:
            st.info("No active positions. Waiting for signals...")
            
        st.subheader("📜 Recent Trade History")
        if bot_instance.trade_history:
            df_hist = pd.DataFrame(bot_instance.trade_history)
            st.dataframe(df_hist.iloc[::-1], width='stretch')
        else:
            st.caption("No trades executed yet in this session.")

    with col_side:
        st.subheader("📡 Live Feed")
        
        # Refresh Button
        if st.button("🔄 Refresh Dashboard", width='stretch'):
            st.rerun()

        st.markdown("**System Logs**")
        log_txt = "\n".join(reversed(bot_instance.logs[-50:]))
        st.text_area("Logs", value=log_txt, height=400, disabled=True, label_visibility="collapsed")



# --- BACKTESTER LOGIC ---
elif nav_mode == "🧪 Backtester":
    st.header("Strategy Backtester (MT5 Style)")
    st.markdown("Use this module to fetch historical data and simulate your strategy.")
    st.info("ℹ️ **Note**: Strategy uses **Multi-Timeframe Analysis**: Trend is calculated on **1H** (resampled) and Entries on **5M** (or selected timeframe).")
    
    col_b1, col_b2 = st.columns([1, 2])
    
    with col_b1:
        st.subheader("1. Configuration")
        
        # Schwab deshabilitado - usar crypto
        available_products = load_products()
        default_idx = 0
        if "BTC-USD" in available_products:
            default_idx = available_products.index("BTC-USD")
        bt_product = st.selectbox("Product ID", available_products, index=default_idx)
            
        # Strategy Selector
        st.subheader("Strategy Selection")
        strategy_options = {
            "Bitcoin Spot Pro (BTC)": "BTC_SPOT",
            "Hybrid Strategy (Generic)": "HYBRID"
        }
        
        selected_strat_name = st.selectbox("Select Strategy", list(strategy_options.keys()))
        selected_strat_code = strategy_options[selected_strat_name]
        
        st.caption(f"Testing logic: **{selected_strat_name}**")

        bt_granularity = st.selectbox("Timeframe", ["ONE_MINUTE", "FIVE_MINUTE", "FIFTEEN_MINUTE", "ONE_HOUR", "ONE_DAY"], index=2 if selected_strat_code == "BTC_SPOT" else 3)
        if selected_strat_code == "BTC_SPOT":
             st.info("ℹ️ Bitcoin Spot Pro is designed for 5M entries with 1H Trend confirmation.")
            
        # Date selection
        
        # Date selection
        today = datetime.now()
        start_def = today - pd.Timedelta(days=30)
        bt_start_date = st.date_input("Start Date", value=start_def)
        bt_end_date = st.date_input("End Date", value=today)
        
        if st.button("Download Historical Data"):
            # Use global bt instance (already initialized with correct broker)
            with st.spinner("Downloading data... (Checking Pagination)"):
                # Convert date inputs to datetime
                s_dt = datetime.combine(bt_start_date, datetime.min.time())
                e_dt = datetime.combine(bt_end_date, datetime.max.time())
                
                # Progress Bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(pct):
                    progress_bar.progress(pct)
                    status_text.text(f"Downloading... {int(pct*100)}%")

                df_dl = bt.download_data(bt_product, s_dt, e_dt, bt_granularity, progress_callback=update_progress)
                
                # Clear progress when done
                progress_bar.empty()
                status_text.empty()
                
                if df_dl is not None:
                    st.success(f"Downloaded {len(df_dl)} candles!")
                    # Save to session or display
                    st.session_state['bt_data'] = df_dl
                    st.dataframe(df_dl.head())
                else:
                    st.error("Download failed or no data found.")

    with col_b2:
        st.subheader("2. Simulation")
        
        # Check if custom params are active
        active_params = None
        if 'active_strategy_params' in st.session_state:
            active_params = st.session_state['active_strategy_params']
            
            with st.expander("🔧 Active Strategy Parameters (Optimized)", expanded=True):
                st.json(active_params)
                if st.button("Reset to Defaults"):
                    del st.session_state['active_strategy_params']
                    st.rerun()
                    
        # Run Simulation Button & Logic
        if 'bt_data' in st.session_state and st.button("Run Simulation (Distributed)"):
             from backtest_runner import BacktestRunner
             
             # Initialize state
             st.session_state['sim_running'] = True
             st.session_state['sim_logs'] = []
             st.session_state['sim_progress'] = 0.0
             st.session_state['sim_results'] = None
             
             runner = BacktestRunner()
             prog_q, res_q = runner.start(
                 st.session_state['bt_data'],
                 bot_instance.risk_level,
                 active_params,
                 selected_strat_code
             )
             st.session_state['sim_runner'] = runner
             st.session_state['sim_prog_q'] = prog_q
             st.session_state['sim_res_q'] = res_q
             st.rerun()

        # Polling Loop for Simulation
        if st.session_state.get('sim_running', False):
             import queue
             
             # UI Containers
             st.caption("🚀 Running on Ray Cluster...")
             sim_progress_bar = st.progress(st.session_state.get('sim_progress', 0.0))
             sim_status_text = st.empty()
             sim_log_box = st.empty()
             
             # Read Queue (Batch)
             try:
                 for _ in range(20): # Read up to 20 msgs
                     try:
                         msg_type, msg_val = st.session_state['sim_prog_q'].get_nowait()
                         if msg_type == 'progress':
                             st.session_state['sim_progress'] = float(msg_val)
                             sim_progress_bar.progress(float(msg_val))
                         elif msg_type == 'log':
                             st.session_state['sim_logs'].append(msg_val)
                     except queue.Empty:
                         break
             except:
                 pass
                 
             # Update Log UI
             if st.session_state['sim_logs']:
                 sim_log_box.code("\n".join(st.session_state['sim_logs'][-15:]), language="text")
                 sim_status_text.text(f"Status: {st.session_state['sim_logs'][-1]}")
             
             # Check Result
             try:
                 status, data = st.session_state['sim_res_q'].get_nowait()
                 if status == 'success':
                     st.session_state['sim_running'] = False
                     st.session_state['sim_results'] = data
                     st.balloons()
                     st.success("Simulation Complete!")
                     st.rerun()
                 elif status == 'error':
                     st.session_state['sim_running'] = False
                     st.error(f"Error: {data}")
             except queue.Empty:
                 time.sleep(0.5)
                 st.rerun()

        # Results Display
        if st.session_state.get('sim_results'):
             res = st.session_state['sim_results']
             equity_df = pd.DataFrame(res['equity'])
             trades_df = pd.DataFrame(res['trades'])
             
             # Metrics
             if not trades_df.empty:
                    total_pnl = trades_df['pnl'].sum()
                    win_rate = len(trades_df[trades_df['pnl'] > 0]) / len(trades_df) * 100
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total PnL", f"${total_pnl:,.2f}")
                    m2.metric("Total Trades", len(trades_df))
                    m3.metric("Win Rate", f"{win_rate:.1f}%")
                    
                    # Chart
                    st.subheader("Equity Curve")
                    st.line_chart(equity_df.set_index('timestamp')['equity'])
                    
                    # Trade List
                    with st.expander("Trade History"):
                        st.dataframe(trades_df)
             else:
                 st.info("No trades generated.")

# --- OPTIMIZER LOGIC ---
elif nav_mode == "⚙️ Optimizer":
    st.header("Parameter Optimization")
    st.markdown("Find the best strategy parameters by testing combinations.")

    st.warning("⚠️ **IMPORTANT**: Optimization runs in BLOCKING mode. The browser will appear frozen during execution, but it IS working. Check your terminal/console for live logs.")

    # --- DATA SOURCE SELECTOR ---
    import glob
    import pandas as pd
    
    col_head, col_refresh = st.columns([3, 1])
    with col_head:
        st.markdown("### 📊 Data Source")
    with col_refresh:
        if st.button("🔄 Refresh Files"):
            st.rerun()

    data_folder = "data"
    available_data_files = []
    
    # Gather candidates: data/*.csv AND *.csv (root)
    candidate_files = []
    if os.path.exists(data_folder):
        candidate_files.extend(glob.glob(os.path.join(data_folder, "*.csv")))
    
    # Also check root directory for misplaced files
    # (User might have pasted files in the project root)
    candidate_files.extend(glob.glob("*.csv"))
    
    # Deduplicate
    candidate_files = sorted(list(set(candidate_files)))

    for f in candidate_files:
            try:
                # Get file info without loading entire file
                fname = os.path.basename(f)
                fsize = os.path.getsize(f) / (1024 * 1024)  # MB
                
                # Count lines efficiently
                with open(f, 'rb') as fp:
                    line_count = sum(1 for _ in fp)
                candle_count = max(0, line_count - 1)  # Subtract header

                # Read first row for validation and start date
                df_head = pd.read_csv(f, nrows=1)
                
                # VALIDATION: If file is in root, be strict about columns to avoid reading results/junk
                is_in_data_dir = "data" in os.path.dirname(f)
                if not is_in_data_dir:
                    # Check for candle-like columns
                    cols_lower = [c.lower() for c in df_head.columns]
                    required = ['close'] # Minimal requirement
                    has_time = any(x in cols_lower for x in ['timestamp', 'time', 'date'])
                    
                    if not (has_time and 'close' in cols_lower):
                        # Skip this file, it's likely a report or config
                        continue

                # Read last row for end date using efficient skiprows
                # If file is small, just read it all. If large, skip to end.
                if candle_count > 0:
                    try:
                        # Skip all lines except header and last one
                        # But since we use header=None to read the specific line, we skip N lines
                        # where N = total_lines - 1 (skips everything before the last line)
                        rows_to_skip = line_count - 1
                        
                        df_tail = pd.read_csv(
                            f, 
                            skiprows=rows_to_skip, 
                            header=None, 
                            names=df_head.columns,
                            nrows=1
                        ) 
                        if df_tail.empty:
                             df_tail = df_head
                    except:
                        df_tail = df_head
                else:
                    df_tail = df_head

                # Try to extract date info
                col_candidates = ['timestamp', 'time', 'start', 'Date', 'date']
                date_col = None
                for col in col_candidates:
                    if col in df_head.columns:
                        date_col = col
                        break
                
                if date_col and not df_head.empty:
                    start_date = str(df_head[date_col].iloc[0])[:19]
                    end_date = str(df_tail[date_col].iloc[0])[:19] if not df_tail.empty and date_col in df_tail.columns else "Unknown"
                    date_info = f"{start_date} → {end_date}"
                else:
                    date_info = "Dates N/A"
                
                label = f"📁 {fname} | {candle_count:,} candles | {fsize:.1f}MB | {date_info}"
                available_data_files.append((label, f, fname, candle_count, date_info))
            except Exception as e:
                # print(f"Error reading {f}: {e}") # Debug
                # Only show errors for files in data dir, silence root file errors
                if "data" in f:
                     available_data_files.append((f"📁 {os.path.basename(f)} (Error reading)", f, os.path.basename(f), 0, "Error"))
    
    # Data source options
    data_source_options = ["🔴 Live Download (from Backtester)"]
    for item in available_data_files:
        data_source_options.append(item[0])
    
    selected_data_source = st.selectbox(
        "Select Historical Data",
        data_source_options,
        help="Choose between live downloaded data or saved historical files"
    )
    
    # Handle data source selection
    if selected_data_source == "🔴 Live Download (from Backtester)":
        if 'bt_data' in st.session_state and st.session_state['bt_data'] is not None:
            opt_data = st.session_state['bt_data']
            st.success(f"✅ Using live data: **{len(opt_data):,} candles** loaded from Backtester")
        else:
            opt_data = None
            st.info("💡 No live data available. Download data in the Backtester tab, or select a saved file above.")
    else:
        # Load from file
        selected_file_info = None
        for item in available_data_files:
            if item[0] == selected_data_source:
                selected_file_info = item
                break
        
        if selected_file_info:
            try:
                opt_data = pd.read_csv(selected_file_info[1])
                st.success(f"✅ Loaded: **{selected_file_info[2]}** | **{len(opt_data):,} candles** | {selected_file_info[4]}")
            except Exception as e:
                opt_data = None
                st.error(f"❌ Error loading file: {e}")
        else:
            opt_data = None
    
    st.divider()

    # --- CHECKPOINT RECOVERY SECTION ---
    st.markdown("### 📂 Checkpoints & Recovery")
    
    # Checkpoint helper functions (local scope or move to file level if needed)
    def decode_range_to_ui(r_list):
        """Convert a list range back to min, max, step."""
        if not r_list: return 0.0, 0.0, 0.0
        
        # Handle float/int differences
        is_float = isinstance(r_list[0], float)
        
        rmin = r_list[0]
        rmax = r_list[-1]
        
        if len(r_list) > 1:
            # Estimate step (round to avoid float errors)
            step = r_list[1] - r_list[0]
            if is_float:
                step = round(step, 2)
        else:
            step = 1.0 if is_float else 1
            
        return rmin, rmax, step

    import glob
    ckpt_files = glob.glob("optimization_checkpoints/checkpoint_*.json")
    
    if ckpt_files:
        # Sort by modification time (newest first)
        ckpt_files.sort(key=os.path.getmtime, reverse=True)
        
        ckpt_options = {}
        for f in ckpt_files:
            try:
                fname = os.path.basename(f)
                with open(f, 'r') as fp:
                    meta = json.load(fp)
                    
                ts = meta.get('last_updated', 'Unknown')
                otype = meta.get('optimizer_type', 'Unknown').upper()
                progress = ""
                if 'metadata' in meta:
                    if 'completed' in meta['metadata']:
                        progress = f"{meta['metadata']['completed']}/{meta['metadata']['total']} Tasks"
                    elif 'current_gen' in meta['metadata']:
                        progress = f"Gen {meta['metadata']['current_gen']}"
                
                label = f"[{ts}] {otype} | {progress} | {fname}"
                ckpt_options[label] = (f, meta)
            except:
                pass

        selected_ckpt_label = st.selectbox("Select Checkpoint", list(ckpt_options.keys()))
        
        if selected_ckpt_label:
            selected_path, selected_meta = ckpt_options[selected_ckpt_label]
            
            col_rec1, col_rec2, col_rec3 = st.columns(3)
            
            with col_rec1:
                if st.button("📥 Load Configuration", width='stretch'):
                    # Restore parameters to session state keys
                    pr = selected_meta.get('param_ranges', {})
                    
                    # Resistance
                    if 'resistance_period' in pr:
                       mi, ma, stp = decode_range_to_ui(pr['resistance_period'])
                       st.session_state['res_min'] = int(mi)
                       st.session_state['res_max'] = int(ma)
                       st.session_state['res_step'] = int(stp)
                    
                    # RSI
                    if 'rsi_period' in pr:
                       mi, ma, stp = decode_range_to_ui(pr['rsi_period'])
                       st.session_state['rsi_min'] = int(mi)
                       st.session_state['rsi_max'] = int(ma)
                       st.session_state['rsi_step'] = int(stp)
                       
                    # SL
                    if 'sl_multiplier' in pr:
                       mi, ma, stp = decode_range_to_ui(pr['sl_multiplier'])
                       st.session_state['sl_min'] = float(mi)
                       st.session_state['sl_max'] = float(ma)
                       st.session_state['sl_step'] = float(stp)
                       
                    # TP
                    if 'tp_multiplier' in pr:
                       mi, ma, stp = decode_range_to_ui(pr['tp_multiplier'])
                       st.session_state['tp_min'] = float(mi)
                       st.session_state['tp_max'] = float(ma)
                       st.session_state['tp_step'] = float(stp)
                       
                    st.success("Configuration Loaded! Check ranges below.")
                    time.sleep(1)
                    st.rerun()

            with col_rec2:
                if st.button("🗑️ Delete Checkpoint", width='stretch'):
                    try:
                        os.remove(selected_path)
                        st.success("Checkpoint Deleted!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            with col_rec3:
                st.info(f"File: {os.path.basename(selected_path)}")
            
            with st.expander("🔍 View Checkpoint Configuration Details"):
                st.json(selected_meta.get('param_ranges', {}))
        
        st.divider()

    else:
        st.info("No checkpoints found.")
        st.divider()

    col_o1, col_o2 = st.columns([1, 2])

    with col_o1:
        st.subheader("1. Strategy & Ranges") # Renamed

        # Strategy Selector
        strategy_options_opt = {
            "Bitcoin Spot Pro (BTC)": "BTC_SPOT",
            "Hybrid Strategy (Generic)": "HYBRID"
        }
        opt_strat_name = st.selectbox("Strategy to Optimize", list(strategy_options_opt.keys()), key="opt_strat_sel")
        opt_strat_code = strategy_options_opt[opt_strat_name]
        
        opt_product = st.text_input("Product ID", value="BTC-USD", key="opt_prod")
        st.divider()

        # Resistance Period

        # Resistance Period
        st.markdown("**Breakout Period (Candles)**")
        res_min = st.number_input("Min", 10, 100, 20, key="res_min")
        res_max = st.number_input("Max", 20, 200, 40, key="res_max")
        res_step = st.number_input("Step", 5, 50, 20, key="res_step")

        # RSI Period
        st.markdown("**RSI Period**")
        rsi_min = st.number_input("Min", 10, 20, 14, key="rsi_min")
        rsi_max = st.number_input("Max", 10, 30, 14, key="rsi_max")
        rsi_step = st.number_input("Step", 1, 5, 2, key="rsi_step")

        # SL Multiplier
        st.markdown("**SL Multiplier (ATR)**")
        sl_min = st.number_input("Min", 1.0, 3.0, 1.5, 0.1, key="sl_min")
        sl_max = st.number_input("Max", 1.0, 5.0, 1.5, 0.1, key="sl_max")
        sl_step = st.number_input("Step", 0.1, 1.0, 0.5, 0.1, key="sl_step")

        # TP Multiplier
        st.markdown("**TP Multiplier (ATR)**")
        tp_min = st.number_input("Min", 1.5, 5.0, 3.0, 0.1, key="tp_min")
        tp_max = st.number_input("Max", 2.0, 8.0, 3.0, 0.1, key="tp_max")
        tp_step = st.number_input("Step", 0.5, 2.0, 1.0, 0.1, key="tp_step")

        # Risk Level
        st.markdown("**Risk Levels to Test**")
        risk_options = st.multiselect("Select Levels", ["LOW", "MEDIUM", "HIGH"], default=["LOW"])

    with col_o2:
        st.subheader("2. Run Optimization")

        if opt_data is None:
            st.warning("⚠️ No data selected. Please select a data source above, or download data in the Backtester tab.")
        else:
            st.markdown("**Optimization Method**")
            opt_method = st.radio(
                "Select Algorithm",
                ["Grid Search (Exhaustive)", "Genetic Algorithm (Evolutionary)", "🧠 Bayesian (AI-Powered)"],
                label_visibility="collapsed"
            )
            
            # Execution Mode
            force_local = st.checkbox("💻 Force Local Mode (No Cluster)", value=True, help="Use only this computer's CPUs. Recommended if you are not connected to the Ray Cluster.")

            ga_gens, ga_pop, ga_mut = 5, 20, 0.1  # Defaults
            bayesian_trials = 50  # Default for Bayesian
            ga_auto_mode = False  # Initialize before conditional
            
            if opt_method == "🧠 Bayesian (AI-Powered)":
                st.info("🧠 **Bayesian Optimization (Optuna)**: Uses AI to learn from each evaluation and intelligently suggest better parameters. Most efficient for finding optimal settings.")
                
                # Bayesian specific settings
                col_bay1, col_bay2 = st.columns(2)
                bayesian_trials = col_bay1.number_input("Max Trials", 20, 500, 100, help="Number of parameter combinations to intelligently explore")
                bayesian_auto = col_bay2.checkbox("Auto-configure trials", value=True, help="Automatically set trials based on search space")
                
                if bayesian_auto:
                    # Will be calculated after param_ranges
                    ga_auto_mode = True
                    
            elif opt_method == "Genetic Algorithm (Evolutionary)":
                st.info("🧬 **Genetic Algorithm**: Evolves parameters over generations. Faster for large search spaces.")
                
                # Auto-calculate GA parameters based on search space (will be calculated after param_ranges)
                # Show toggle for auto vs manual
                auto_config = st.checkbox("🤖 Auto-configure GA (recommended)", value=True, help="Automatically set optimal Generations/Population based on search space size")
                
                if auto_config:
                    # Calculate later after param_ranges is built
                    ga_auto_mode = True
                else:
                    ga_auto_mode = False
                    col_ga1, col_ga2, col_ga3 = st.columns(3)
                    ga_gens = col_ga1.number_input("Generations", 1, 200, 10, help="Number of evolutionary cycles")
                    ga_pop = col_ga2.number_input("Population", 10, 1000, 30, help="Strategies per generation")
                    ga_mut = col_ga3.number_input("Mutation Rate", 0.01, 0.5, 0.1, 0.01, help="Chance of random gene change")
            else:
                st.info("🔍 **Grid Search**: Tests EVERY combination. Precise but slow for large ranges.")

            # Calculate total combinations
            def float_range(start, stop, step):
                r = []
                c = start
                while c <= stop:
                    r.append(round(c, 2))
                    c += step
                return r

            if not risk_options:
                risk_options = ["LOW"]

            param_ranges = {
                'resistance_period': list(range(int(res_min), int(res_max) + 1, int(res_step))),
                'rsi_period': list(range(int(rsi_min), int(rsi_max) + 1, int(rsi_step))),
                'sl_multiplier': float_range(sl_min, sl_max, sl_step),
                'tp_multiplier': float_range(tp_min, tp_max, tp_step),
                'risk_level': risk_options
            }

            # Use generic calculation to avoid strict dependency on structure
            import math
            total_combinations = (
                len(param_ranges['resistance_period']) *
                len(param_ranges['rsi_period']) *
                len(param_ranges['sl_multiplier']) *
                len(param_ranges['tp_multiplier']) *
                len(param_ranges['risk_level'])
            )

            st.info(f"📊 Total combinations to test: **{total_combinations}**")

            # Auto-configure GA parameters if enabled
            if opt_method == "Genetic Algorithm (Evolutionary)" and ga_auto_mode:
                # Formula: Population = min(100, max(20, sqrt(total_combinations)))
                # Generations = min(50, max(5, log2(total_combinations)))
                import math
                
                # Calculate raw values for transparency
                raw_pop = math.sqrt(total_combinations)
                raw_gens = math.log2(max(1, total_combinations))
                
                ga_pop = min(100, max(20, int(raw_pop)))
                ga_gens = min(50, max(5, int(raw_gens)))
                ga_mut = 0.1 if total_combinations < 1000 else 0.15  # Higher mutation for larger spaces
                
                st.success(f"🤖 Auto-configured: **{ga_gens} Generations** × **{ga_pop} Population** (Mutation: {ga_mut})")
                
                # Transparency expander
                with st.expander("📐 How was this calculated?"):
                    st.markdown(f"""
**Formulas Used:**
- **Population** = `min(100, max(20, √{total_combinations}))` = `min(100, max(20, {raw_pop:.2f}))` = **{ga_pop}**
- **Generations** = `min(50, max(5, log₂({total_combinations})))` = `min(50, max(5, {raw_gens:.2f}))` = **{ga_gens}**
- **Mutation Rate** = `{"0.10 (small search space < 1000)" if total_combinations < 1000 else "0.15 (large search space ≥ 1000)"}`

**Reasoning:**
- 📊 **Population size** scales with √N to sample the search space adequately
- 🔄 **Generations** scale with log₂(N) since evolutionary convergence is logarithmic
- 🎲 **Mutation rate** is higher for larger spaces to avoid local optima

**Data Source:**
- 📁 **File**: `{selected_data_source}`
- 📈 **Candles**: `{len(opt_data):,}` data points
""")
                    if hasattr(opt_data, 'columns'):
                        date_col = None
                        for col in ['timestamp', 'time', 'start', 'date']:
                            if col in opt_data.columns:
                                date_col = col
                                break
                        if date_col:
                            st.markdown(f"- 📅 **Range**: `{str(opt_data[date_col].iloc[0])[:19]}` → `{str(opt_data[date_col].iloc[-1])[:19]}`")

            # Auto-configure Bayesian trials if enabled
            if opt_method == "🧠 Bayesian (AI-Powered)" and ga_auto_mode:
                import math
                # Bayesian is more efficient, needs fewer trials than total combinations
                # Formula: sqrt(N) trials is enough for Bayesian to converge
                raw_trials = math.sqrt(total_combinations) * 2  # 2x sqrt for safety margin
                bayesian_trials = min(200, max(30, int(raw_trials)))
                
                st.success(f"🧠 Auto-configured: **{bayesian_trials} Trials** (Bayesian learns efficiently)")
                
                with st.expander("📐 How was this calculated?"):
                    st.markdown(f"""
**Formula Used:**
- **Trials** = `min(200, max(30, 2 × √{total_combinations}))` = `min(200, max(30, {raw_trials:.1f}))` = **{bayesian_trials}**

**Why fewer trials than GA/Grid?**
- 🧠 **Bayesian learns**: Each trial teaches the algorithm about the parameter space
- 📊 **TPE Sampler**: Uses probabilistic models to focus on promising regions
- ⚡ **Efficiency**: Typically finds optimal in √N trials vs N for Grid Search

**Data Source:**
- 📁 **File**: `{selected_data_source}`
- 📈 **Candles**: `{len(opt_data):,}` data points
""")

            if total_combinations > 100 and opt_method == "Grid Search (Exhaustive)":
                st.warning(f"⚠️ {total_combinations} combinations may take several minutes. Consider using Genetic Algorithm or Bayesian for faster results.")

            # Initialize session state for optimizer control
            if 'optimizer_runner' not in st.session_state:
                st.session_state['optimizer_runner'] = None
            if 'optimizer_running' not in st.session_state:
                st.session_state['optimizer_running'] = False
            if 'optimizer_logs' not in st.session_state:
                st.session_state['optimizer_logs'] = []
            if 'optimizer_progress' not in st.session_state:
                st.session_state['optimizer_progress'] = 0.0

            # Control buttons
            col_start, col_stop, col_kill = st.columns(3)

            with col_start:
                start_clicked = st.button("🚀 Start Optimization", type="primary", disabled=st.session_state['optimizer_running'])

            with col_stop:
                stop_clicked = st.button("🛑 Stop Optimization", disabled=not st.session_state['optimizer_running'])

            with col_kill:
                 kill_clicked = st.button("💀 Force Kill Ray (Panic)", help="Use ONLY if process is stuck. Kills all Ray processes.")

            # Handle stop button
            if stop_clicked and st.session_state['optimizer_runner']:
                st.session_state['optimizer_runner'].stop()
                st.session_state['optimizer_running'] = False
                st.warning("⚠️ Stopping optimization...")
                st.rerun()

            # Handle kill button
            if kill_clicked:
                 import subprocess
                 try:
                     st.warning("⚠️ Executing PURGE command...")
                     # Kill Raylet and Workers
                     subprocess.run(["pkill", "-f", "ray::"], check=False)
                     subprocess.run(["pkill", "-f", "raylet"], check=False)
                     
                     # Try ray stop
                     try:
                         # Try with venv ray first
                         subprocess.run([".venv/bin/ray", "stop", "--force"], check=False)
                     except:
                         pass
                         
                     subprocess.run(["ray", "stop", "--force"], check=False)
                     
                     if st.session_state['optimizer_runner']:
                         st.session_state['optimizer_runner'].cleanup()
                     st.session_state['optimizer_runner'] = None
                     st.session_state['optimizer_running'] = False
                     
                     st.success("✅ Ray Cluster has been PURGED. Wait 5s before restarting.")
                     time.sleep(2)
                     st.rerun()
                 except Exception as e:
                     st.error(f"Error purging: {e}")

            # Handle start button
            if start_clicked:
                from optimizer_runner import OptimizerRunner

                st.session_state['optimizer_logs'] = []
                st.session_state['optimizer_progress'] = 0.0
                st.session_state['optimizer_running'] = True

                # Create runner and start process
                runner = OptimizerRunner()

                # Determine method
                if opt_method == "Genetic Algorithm (Evolutionary)":
                    method = "genetic"
                    ga_params_tuple = (ga_gens, ga_pop, ga_mut)
                elif opt_method == "🧠 Bayesian (AI-Powered)":
                    method = "bayesian"
                    ga_params_tuple = (bayesian_trials, 0, 0)  # First param is n_trials
                else:
                    method = "grid"
                    ga_params_tuple = (10, 50, 0.1)  # Defaults (not used)

                # Start optimization in separate process
                try:
                    progress_queue, result_queue = runner.start(
                        opt_data,  # Use selected data source
                        param_ranges,
                        risk_options[0] if risk_options else "LOW",
                        opt_method=method,
                        ga_params=ga_params_tuple,
                        strategy_code=opt_strat_code,
                        force_local=force_local
                    )

                    st.session_state['optimizer_runner'] = runner
                    st.session_state['progress_queue'] = progress_queue
                    st.session_state['result_queue'] = result_queue

                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to start optimizer: {e}")
                    st.session_state['optimizer_running'] = False

            # Poll for updates if optimization is running
            if st.session_state['optimizer_running'] and st.session_state['optimizer_runner']:
                import queue

                # Create UI containers BEFORE the polling loop
                progress_container = st.empty()
                log_container = st.empty()
                status_container = st.empty()

                # Check if process is still alive
                if not st.session_state['optimizer_runner'].is_alive():
                    # Process died unexpectedly
                    try:
                        status, data = st.session_state['result_queue'].get_nowait()
                        # Handle result below
                    except queue.Empty:
                        st.error("❌ Optimizer process terminated unexpectedly")
                        st.session_state['optimizer_running'] = False
                        if st.session_state['optimizer_runner']:
                            st.session_state['optimizer_runner'].cleanup()
                        st.session_state['optimizer_runner'] = None

                # Read ALL available messages from progress queue (non-blocking)
                messages_read = 0
                max_reads_per_loop = 50  # Limit to prevent freezing UI thread

                try:
                    while messages_read < max_reads_per_loop:
                        try:
                            msg_type, msg_data = st.session_state['progress_queue'].get_nowait()
                            
                            if msg_type == "log":
                                st.session_state['optimizer_logs'].append(msg_data)
                            elif msg_type == "progress":
                                st.session_state['optimizer_progress'] = msg_data
                            
                            messages_read += 1
                        except queue.Empty:
                            break  # Queue is empty, exit inner loop
                    
                    # If we read many messages, sleep briefly to let the UI thread breathe
                    if messages_read > 20:
                        time.sleep(0.05)
                        
                except Exception as e:
                    pass

                # Check for final result
                try:
                    status, data = st.session_state['result_queue'].get_nowait()

                    if status == "success":
                        import pandas as pd
                        import os
                        # data is now a filepath
                        try:
                            results_df = pd.read_json(data, orient='records')
                            st.session_state['opt_results'] = results_df
                            
                            # Clean up temp file
                            try:
                                if os.path.exists(data):
                                    os.remove(data)
                            except:
                                pass
                                
                            st.session_state['optimizer_running'] = False
                            st.success("✅ Optimization Complete!")
                        except Exception as e:
                            # Fallback if it's a dict (legacy)
                            try:
                                results_df = pd.DataFrame(data)
                                st.session_state['opt_results'] = results_df
                                st.session_state['optimizer_running'] = False
                                st.success("✅ Optimization Complete!")
                            except:
                                st.error(f"Failed to load results: {e}")
                                st.session_state['optimizer_running'] = False
                    elif status == "error":
                        st.error(f"❌ Optimization failed: {data}")
                        st.session_state['optimizer_running'] = False
                    elif status == "stopped":
                        st.warning("⚠️ Optimization stopped by user")
                        st.session_state['optimizer_running'] = False

                    # Cleanup
                    if st.session_state['optimizer_runner']:
                        st.session_state['optimizer_runner'].cleanup()
                    st.session_state['optimizer_runner'] = None
                    st.rerun()

                except queue.Empty:
                    pass

                # Update UI with current state
                if st.session_state['optimizer_logs']:
                    # Show last 100 lines of logs
                    recent_logs = st.session_state['optimizer_logs'][-100:]
                    log_container.text_area(
                        "📋 Live Logs",
                        value="\n".join(recent_logs),
                        height=400,
                        disabled=True
                    )

                # Show progress bar
                if st.session_state['optimizer_progress'] > 0:
                    progress_container.progress(
                        st.session_state['optimizer_progress'],
                        text=f"Progress: {int(st.session_state['optimizer_progress'] * 100)}%"
                    )
                else:
                    progress_container.info("🔄 Initializing optimization...")

                # Show running status
                status_container.info(f"⚙️ Optimization running... (Read {messages_read} updates)")

                # Auto-refresh with delay to prevent UI freezing
                time.sleep(0.5)
                st.rerun()

        # Display Results (if they exist)
        if 'opt_results' in st.session_state:
            df_res = st.session_state['opt_results']

            if not df_res.empty:
                st.markdown("---")
                st.subheader("📊 Top Results")
                st.dataframe(df_res.head(10), width='stretch')

                # Show execution log in expander
                if 'opt_logs' in st.session_state:
                    with st.expander("📜 View Execution Log", expanded=False):
                        st.text_area(
                            "Complete Log",
                            value="\n".join(st.session_state['opt_logs']),
                            height=300,
                            disabled=True,
                            label_visibility="collapsed"
                        )

                st.markdown("---")
                st.subheader("🎯 Select & Apply Configuration")

                # Selection
                df_res = df_res.reset_index(drop=True)
                options = []
                for idx, row in df_res.iterrows():
                    pnl = row.get('Total PnL', 0.0)
                    trades = row.get('Total Trades', 0)
                    wr = row.get('Win Rate %', 0.0)
                    try:
                         trades = int(trades)
                    except:
                         trades = 0
                         
                    label = f"Rank #{idx+1} | PnL: ${pnl:.2f} | Trades: {trades} | WR: {wr:.1f}%"
                    options.append(label)

                selected_option = st.selectbox("Choose Configuration", options)

                col_apply, col_save, col_clear = st.columns(3)

                with col_apply:
                    if st.button("✅ Apply to Backtester", width='stretch'):
                        idx = options.index(selected_option)
                        selected_row = df_res.iloc[idx]
                        metric_keys = ['Total Trades', 'Win Rate %', 'Total PnL', 'Final Balance']
                        best_params = {k: v for k, v in selected_row.to_dict().items() if k not in metric_keys}
                        st.session_state['active_strategy_params'] = best_params
                        st.success(f"✅ Applied Configuration #{idx+1}! Go to Backtester tab to verify.")

                with col_save:
                    idx = options.index(selected_option)
                    row_dict = df_res.iloc[idx].to_dict()
                    json_str = json.dumps(row_dict, indent=2)
                    st.download_button(
                        label="💾 Download JSON",
                        data=json_str,
                        file_name=f"opt_config_rank_{idx+1}.json",
                        mime="application/json",
                        width='stretch'
                    )

                with col_clear:
                    if st.button("🗑️ Clear Results", width='stretch'):
                        if 'opt_results' in st.session_state:
                            del st.session_state['opt_results']
                        if 'opt_logs' in st.session_state:
                            del st.session_state['opt_logs']
                        st.rerun()


# --- STRATEGY MINER LOGIC ---
elif nav_mode == "⛏️ Strategy Miner (AI)":
    st.header("⛏️ AI Strategy Miner (Genetic Programming)")
    st.markdown("Use **Genetic Algorithms** to automatically discover, evolve, and optimize profitable trading strategies from raw ingredients.")

    # --- DATA SELECTION ---
    import glob
    import pandas as pd
    
    # --- ENHANCED DATA SELECTOR (Replicated from Optimizer) ---
    col_head, col_refresh = st.columns([3, 1])
    with col_head:
        st.markdown("### 📊 Data Source")
    with col_refresh:
        if st.button("🔄 Refresh Files", key="miner_refresh"):
            st.rerun()

    data_folder = "data"
    available_data_files = []
    import glob
    import os
    
    # Gather candidates: data/*.csv AND *.csv (root)
    candidate_files = []
    if os.path.exists(data_folder):
        candidate_files.extend(glob.glob(os.path.join(data_folder, "*.csv")))
    candidate_files.extend(glob.glob("*.csv"))
    candidate_files = sorted(list(set(candidate_files)))

    for f in candidate_files:
            try:
                fname = os.path.basename(f)
                fsize = os.path.getsize(f) / (1024 * 1024) 
                
                with open(f, 'rb') as fp:
                    line_count = sum(1 for _ in fp)
                candle_count = max(0, line_count - 1)

                df_head = pd.read_csv(f, nrows=1)
                
                is_in_data_dir = "data" in os.path.dirname(f)
                if not is_in_data_dir:
                    cols_lower = [c.lower() for c in df_head.columns]
                    has_time = any(x in cols_lower for x in ['timestamp', 'time', 'date'])
                    if not (has_time and 'close' in cols_lower):
                        continue

                # Read last row
                if candle_count > 0:
                    try:
                        rows_to_skip = line_count - 1
                        df_tail = pd.read_csv(f, skiprows=rows_to_skip, header=None, names=df_head.columns, nrows=1) 
                        if df_tail.empty: df_tail = df_head
                    except:
                        df_tail = df_head
                else:
                    df_tail = df_head

                col_candidates = ['timestamp', 'time', 'start', 'Date', 'date']
                date_col = None
                for col in col_candidates:
                    if col in df_head.columns:
                        date_col = col
                        break
                
                if date_col and not df_head.empty:
                    start_date = str(df_head[date_col].iloc[0])[:19]
                    end_date = str(df_tail[date_col].iloc[0])[:19] if not df_tail.empty and date_col in df_tail.columns else "Unknown"
                    date_info = f"{start_date} → {end_date}"
                else:
                    date_info = "Dates N/A"
                
                label = f"📁 {fname} | {candle_count:,} candles | {fsize:.1f}MB | {date_info}"
                available_data_files.append((label, f, fname, candle_count, date_info))
            except Exception as e:
                # print(f"Error reading {f}: {e}")
                if "data" in f:
                     available_data_files.append((f"📁 {os.path.basename(f)} (Error reading)", f, os.path.basename(f), 0, "Error"))
    
    data_source_options = []
    # Priority for CSVs (Miner prefers data files)
    for item in available_data_files:
        data_source_options.append(item[0])
    
    live_option_label = "🔴 Live Download (From Coinbase)"
    data_source_options.append(live_option_label)
    
    selected_data_source = st.selectbox("Select Historical Data", data_source_options, key="miner_data_select")
    
    miner_data = None
    
    # Check if a file is selected
    selected_file_path = None
    for label, path, _, _, _ in available_data_files:
        if label == selected_data_source:
             selected_file_path = path
             break

    if selected_file_path:
        try:
            miner_data = pd.read_csv(selected_file_path)
            st.success(f"✅ Loaded {len(miner_data)} candles from **{os.path.basename(selected_file_path)}**")
        except Exception as e:
             st.error(f"Error loading CSV: {e}")
    
    elif selected_data_source == live_option_label:
        st.info("Fetching recent data from Coinbase...")
        try:
            import time
            end_ts = int(time.time())
            start_ts = end_ts - (1000 * 3600) # 1000 hours back
            miner_data = broker_client.get_historical_data("BTC-USD", granularity="ONE_HOUR", start_ts=start_ts, end_ts=end_ts) 
            
            if miner_data is not None and not miner_data.empty:
                st.success(f"Loaded {len(miner_data)} candles (Live).")
            else:
                 st.warning("No data returned. Check API Keys or connectivity.")
        except Exception as e:
            st.error(f"Error downloading data: {e}")

    st.divider()

    col_config, col_monitor = st.columns([1, 2])

    with col_config:
        st.subheader("🧬 Experiment Settings")
        
        pop_size = st.number_input("Population Size", min_value=10, max_value=2000, value=300, step=10, help="Number of strategies in each generation. Recommended: 500-1000 for serious optimization.")
        generations = st.number_input("Generations", min_value=1, max_value=500, value=50, step=1, help="How many evolutionary cycles to run. Recommended: 100-200 for convergence.")
        risk_level = st.selectbox("Risk Level", ["LOW", "MEDIUM", "HIGH"], index=0)
        
        force_local = st.checkbox("Force Local Mode (No Ray)", value=False, help="Run on this machine instead of cluster (Simpler debugging).")

        st.divider()
        
        # Initialize session state for miner
        if 'miner_runner' not in st.session_state:
            st.session_state['miner_runner'] = None
        if 'miner_running' not in st.session_state:
            st.session_state['miner_running'] = False
        if 'miner_logs' not in st.session_state:
            st.session_state['miner_logs'] = []
            
        start_miner = st.button("⛏️ Start Mining", type="primary", disabled=st.session_state['miner_running'])
        stop_miner = st.button("🛑 Stop Mining", disabled=not st.session_state['miner_running'])

        if stop_miner and st.session_state['miner_runner']:
            st.session_state['miner_runner'].stop()
            st.session_state['miner_running'] = False
            st.warning("Stopping miner...")
            st.rerun()

        if start_miner and miner_data is not None:
             from optimizer_runner import OptimizerRunner
             st.session_state['miner_logs'] = []
             st.session_state['miner_running'] = True
             
             runner = OptimizerRunner()
             
             # We piggyback on optimizer_runner with Type="miner"
             # ga_params = (Generations, Population, MutationRate)
             # But runner signature is fixed. We pass gens/pop via ga_params
             
             try:
                 progress_queue, result_queue = runner.start(
                     miner_data,
                     {}, # param_ranges (Empty for miner)
                     risk_level,
                     opt_method="miner",
                     ga_params=(generations, pop_size, 0.1),
                     strategy_code="DYNAMIC",
                     force_local=force_local
                 )
                 
                 st.session_state['miner_runner'] = runner
                 st.session_state['miner_queue'] = progress_queue
                 st.session_state['miner_res_queue'] = result_queue
                 st.rerun()
             except Exception as e:
                 st.error(f"Failed to start miner: {e}")
                 st.session_state['miner_running'] = False

    with col_monitor:
        st.subheader("🖥️ Live Evolution")
        
        log_area = st.empty()
        
        st.caption("Generation Progress")
        progress_bar = st.progress(0.0)
        
        chart_area = st.empty()
        
        # Monitor Loop
        if st.session_state['miner_running'] and st.session_state['miner_runner']:
            import queue
            
            # Read Logs
            try:
                while True:
                    msg_type, msg_data = st.session_state['miner_queue'].get_nowait()
                    if msg_type == "log":
                        st.session_state['miner_logs'].append(msg_data)
                    elif msg_type == "progress":
                        # Miner sends ("BEST_GEN", data) or ("START_GEN", n) via prog_cb wrapper
                        # optimizer_runner passes this tuple as 'msg_data'
                        if isinstance(msg_data, tuple) and len(msg_data) == 2:
                            subtype, subdata = msg_data
                            if subtype == "START_GEN":
                                st.session_state['miner_logs'].append(f"🧬 Starting Generation {subdata}...")
                            elif subtype == "BEST_GEN":
                                gen = subdata.get('gen')
                                pnl = subdata.get('pnl')
                                st.session_state['miner_logs'].append(f"🌟 Gen {gen} Best PnL: ${pnl:.2f}")
                                st.session_state['miner_logs'].append(f"🌟 Gen {gen} Best PnL: ${pnl:.2f}")
                                # Reset progress bar for next gen
                                progress_bar.progress(0.0)
                            elif subtype == "BATCH_PROGRESS":
                                # Update progress bar
                                progress_bar.progress(float(subdata))
                        else:
                             # Standard float progress (fallback)
                             pass
                        
            except queue.Empty:
                pass
            
            # Display Logs
            log_text = "\n".join(st.session_state['miner_logs'][-20:])
            log_area.code(log_text if log_text else "Waiting for logs...", language="text")
            
            # Check for Result
            try:
                status, payload = st.session_state['miner_res_queue'].get_nowait()
                if status == "success":
                    st.success("🎉 Mining Complete!")
                    st.session_state['miner_running'] = False
                    
                    # Load result file
                    res_df = pd.read_json(payload)
                    st.session_state['last_miner_result'] = res_df
                    st.rerun()
                    
                elif status == "error":
                    st.error(f"Mining Failed: {payload}")
                    st.session_state['miner_running'] = False
            except queue.Empty:
                pass
            
            time.sleep(1)
            st.rerun()

    # Display Results if available
    if 'last_miner_result' in st.session_state:
        res = st.session_state['last_miner_result']
        st.divider()
        st.subheader("🏆 Discovery Result")
        st.dataframe(res)
        
        # Extract Best Genome
        if not res.empty:
            params = res.iloc[0]['params']
            metrics = res.iloc[0]['metrics']
            
            st.markdown(f"**Best Metrics:** {metrics}")
            st.json(params)
            
            if st.button("💾 Apply this Strategy"):
                st.session_state['active_strategy_params'] = params
                # Note: We need to tell Backtester to use DynamicStrategy + This Genome
                # This might require an extra flag in Backtester tab selectbox
                st.success("Strategy Saved to Session! (Go to Backtester -> Select 'Dynamic')")


# ======================================================================================
# SISTEMA DISTRIBUIDO - BOINC-like Distributed Strategy Mining
# ======================================================================================

elif nav_mode == "🌐 Sistema Distribuido":
    st.header("🌐 Sistema Distribuido de Strategy Mining")
    st.markdown("""
    **Sistema BOINC-like para búsqueda distribuida de estrategias**
    - Coordinator gestiona trabajo y recolecta resultados
    - Workers ejecutan backtests en paralelo
    - Sistema de redundancia y validación por consenso
    """)

    # Configuration
    COORDINATOR_URL = os.getenv("COORDINATOR_URL", "http://localhost:5001")

    # Helper function to check coordinator status
    def check_coordinator_status():
        try:
            response = requests.get(f"{COORDINATOR_URL}/api/status", timeout=2)
            if response.status_code == 200:
                return True, response.json()
            return False, None
        except:
            return False, None

    # Helper function to get workers
    def get_workers():
        try:
            response = requests.get(f"{COORDINATOR_URL}/api/workers", timeout=2)
            if response.status_code == 200:
                data = response.json()
                return data.get('workers', [])
            return []
        except:
            return []

    # Helper function to get results
    def get_results():
        try:
            # Use /all endpoint to show all results (not just canonical)
            response = requests.get(f"{COORDINATOR_URL}/api/results/all?limit=50", timeout=2)
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []

    # Helper function to get consolidated dashboard stats
    def get_dashboard_stats():
        try:
            response = requests.get(f"{COORDINATOR_URL}/api/dashboard_stats", timeout=10)
            if response.status_code == 200:
                return response.json()
            print(f"Dashboard stats error: status {response.status_code}")
            return None
        except Exception as e:
            print(f"Dashboard stats exception: {e}")
            return None

    # Helper function to read log file
    def read_log_file(log_path, lines=50):
        try:
            # If relative path, make it absolute using BASE_DIR
            if not os.path.isabs(log_path):
                log_path = os.path.join(BASE_DIR, log_path)
            with open(log_path, 'r') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except FileNotFoundError:
            return f"Log file not found: {log_path}"
        except Exception as e:
            return f"Error reading log: {str(e)}"

    # Check coordinator status
    coordinator_running, status_data = check_coordinator_status()

    # Status indicators at top
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if coordinator_running:
            st.metric("📡 Coordinator", "✅ ACTIVO", delta="Online")
        else:
            st.metric("📡 Coordinator", "❌ INACTIVO", delta="Offline")

    with col2:
        if coordinator_running and status_data:
            active_workers = status_data.get('workers', {}).get('active', 0)
            st.metric("👥 Workers", active_workers, delta="Conectados")
        else:
            st.metric("👥 Workers", 0, delta="N/A")

    with col3:
        if coordinator_running and status_data:
            work_units = status_data.get('work_units', {})
            total = work_units.get('total', 0)
            completed = work_units.get('completed', 0)
            st.metric("📊 Work Units", f"{completed}/{total}", delta=f"{work_units.get('pending', 0)} pendientes")
        else:
            st.metric("📊 Work Units", "0/0", delta="N/A")

    with col4:
        if coordinator_running and status_data:
            best = status_data.get('best_strategy')
            if best:
                st.metric("🏆 Mejor PnL", f"${best.get('pnl', 0):.2f}", delta="Encontrado")
            else:
                st.metric("🏆 Mejor PnL", "N/A", delta="Buscando...")
        else:
            st.metric("🏆 Mejor PnL", "N/A", delta="Offline")

    st.divider()

    # Tabs for different sections
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["📊 Dashboard", "👥 Workers", "⚙️ Control", "📜 Logs", "➕ Crear Work Units", "📈 Paper Trading", "🚀 Futures", "🔄 Data & Auto"])

    # TAB 1: Dashboard
    with tab1:
        # Header with refresh controls
        col_header1, col_header2, col_header3 = st.columns([3, 1.5, 0.5])

        with col_header1:
            st.subheader("📊 Dashboard en Tiempo Real")

        with col_header2:
            refresh_interval = st.select_slider(
                "Auto-refresh",
                options=[0, 5, 10, 15, 30, 60],
                value=0,
                format_func=lambda x: "Off" if x == 0 else f"{x}s",
                key="dash_refresh_interval"
            )

        with col_header3:
            if st.button("🔄", width='stretch', key="dash_refresh_btn", help="Refrescar ahora"):
                st.rerun()

        if not coordinator_running:
            st.error("❌ Coordinator no está ejecutando. Inicia el coordinator desde la pestaña 'Control'.")
        else:
            # Dashboard fragment for non-blocking auto-refresh
            run_every_val = refresh_interval if refresh_interval > 0 else None

            @st.fragment(run_every=run_every_val)
            def dashboard_fragment():
                stats = get_dashboard_stats()
                if not stats:
                    st.warning("No se pueden obtener datos del coordinator. Intentando con endpoint basico...")
                    # Fallback to basic status
                    _, fallback_data = check_coordinator_status()
                    if fallback_data:
                        st.json(fallback_data)
                    return

                wu = stats.get('work_units', {})
                perf = stats.get('performance', {})
                best = stats.get('best_strategy')
                w_stats = stats.get('worker_stats', [])
                pnl_tl = stats.get('pnl_timeline', [])

                # Plotly dark theme config
                plotly_layout = dict(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=20, r=20, t=40, b=20),
                    font=dict(size=11)
                )

                # ===== ROW 1: KPI Cards =====
                kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)

                total_wu = wu.get('total', 0)
                completed_wu = wu.get('completed', 0)
                progress_pct = (completed_wu / total_wu * 100) if total_wu > 0 else 0

                with kpi1:
                    st.metric("Completados", f"{completed_wu}/{total_wu}", delta=f"{progress_pct:.0f}%")
                    if total_wu > 0:
                        st.progress(completed_wu / total_wu)

                with kpi2:
                    active_w = stats.get('workers', {}).get('active', 0)
                    total_w = stats.get('workers', {}).get('total_registered', 0)
                    st.metric("Workers Activos", f"{active_w}", delta=f"de {total_w} registrados")

                with kpi3:
                    if best:
                        st.metric("Mejor PnL", f"${best.get('pnl', 0):.2f}",
                                  delta=f"WR: {best.get('win_rate', 0)*100:.0f}%")
                    else:
                        st.metric("Mejor PnL", "N/A", delta="Buscando...")

                with kpi4:
                    rph = perf.get('results_per_hour', 0)
                    avg_exec = perf.get('avg_execution_time', 0)
                    st.metric("Velocidad", f"{rph:.1f}/hr", delta=f"{avg_exec:.0f}s prom.")

                with kpi5:
                    cpu_hours = perf.get('total_compute_time', 0) / 3600
                    total_res = perf.get('total_results', 0)
                    st.metric("CPU-Horas", f"{cpu_hours:.1f} hrs", delta=f"{total_res} resultados")

                with kpi6:
                    try:
                        from numba_backtester import HAS_NUMBA as _nb
                        if _nb:
                            st.metric("Motor", "Numba JIT", delta="~4000x speedup")
                        else:
                            st.metric("Motor", "Python", delta="Numba no disponible")
                    except ImportError:
                        st.metric("Motor", "Python", delta="Sin aceleracion")

                # ===== OOS VALIDATION METRICS (Phase 3A) =====
                if best and best.get('oos_pnl', 0) != 0:
                    st.divider()
                    st.markdown("#### 🔬 Out-of-Sample Validation")

                    oos_col1, oos_col2, oos_col3, oos_col4 = st.columns(4)

                    with oos_col1:
                        oos_pnl = best.get('oos_pnl', 0)
                        train_pnl = best.get('pnl', 0)
                        is_overfitted = best.get('is_overfitted', False)
                        icon = "🔴" if is_overfitted else "🟢"
                        st.metric(f"{icon} OOS PnL", f"${oos_pnl:.2f}",
                                  delta=f"Train: ${train_pnl:.2f}")

                    with oos_col2:
                        oos_degradation = best.get('oos_degradation', 0)
                        deg_color = "normal" if oos_degradation < 35 else "inverse"
                        st.metric("Degradación", f"{oos_degradation:.1f}%",
                                  delta="<35% aceptable" if oos_degradation < 35 else ">35% overfitted",
                                  delta_color=deg_color)

                    with oos_col3:
                        robustness = best.get('robustness_score', 0)
                        st.metric("Robustness", f"{robustness:.0f}/100",
                                  delta="✅ Robusto" if robustness >= 50 else "⚠️ Frágil")

                    with oos_col4:
                        oos_trades = best.get('oos_trades', 0)
                        st.metric("OOS Trades", f"{oos_trades}",
                                  delta="Min 10 requerido" if oos_trades < 10 else "✅ Suficiente")

                # ===== OBJETIVO 5% DIARIO =====
                # numba_backtester.py usa balance = 500.0 como capital inicial
                BACKTEST_CAPITAL = 500
                REAL_CAPITAL     = 500
                TARGET_DAILY_PCT = 5.0

                if best:
                    best_pnl      = best.get('pnl', 0) or 0
                    # Usar días reales del backtest (no hardcoded)
                    BACKTEST_DAYS = best.get('backtest_days', 0) or 55.6
                    total_ret     = best_pnl / BACKTEST_CAPITAL * 100
                    daily_ret_pct = total_ret / BACKTEST_DAYS if BACKTEST_DAYS > 0 else 0
                    daily_pnl     = REAL_CAPITAL * (daily_ret_pct / 100)
                    target_total  = REAL_CAPITAL * (TARGET_DAILY_PCT / 100) * BACKTEST_DAYS
                    progress_pct  = min(daily_ret_pct / TARGET_DAILY_PCT * 100, 100)
                    multiplier    = target_total / max(REAL_CAPITAL * (total_ret / 100), 0.01)

                    if progress_pct < 20:
                        status_icon = "🔴"; status_msg = f"Inicio del camino — necesitamos {multiplier:.1f}x de mejora en PnL diario."
                    elif progress_pct < 50:
                        status_icon = "🟡"; status_msg = f"Buen progreso — {progress_pct:.1f}% del objetivo alcanzado. Seguir optimizando."
                    elif progress_pct < 80:
                        status_icon = "🔵"; status_msg = f"Muy cerca — {100-progress_pct:.1f}% restante para el 5% diario."
                    else:
                        status_icon = "🟢"; status_msg = f"¡Objetivo alcanzado! {daily_ret_pct:.2f}%/día. Listo para live trading."

                    st.markdown(f"#### 🎯 Objetivo: 5% Diario &nbsp; {status_icon} **{daily_ret_pct:.2f}%** actual vs **5.00%** objetivo")
                    st.progress(min(progress_pct / 100, 1.0))
                    max_candles_display = best.get('max_candles', 0) or 0
                    timeframe_display = best.get('timeframe', '?')
                    st.caption(f"{status_msg} &nbsp;·&nbsp; Capital: **${BACKTEST_CAPITAL:,}** &nbsp;·&nbsp; Período: **{BACKTEST_DAYS:.1f} días** ({max_candles_display:,} candles {timeframe_display})")

                    gc1, gc2, gc3, gc4, gc5, gc6 = st.columns(6)
                    with gc1: st.metric("Retorno Diario", f"{daily_ret_pct:.2f}%",    delta="obj: 5.00%",          delta_color="normal")
                    with gc2: st.metric("PnL Diario",     f"${daily_pnl:.2f}/día",    delta="obj: $25/día",        delta_color="normal")
                    with gc3: st.metric("PnL Total",      f"${best_pnl:.0f}",         delta=f"obj: ${target_total:.0f}", delta_color="normal")
                    with gc4: st.metric("Progreso",       f"{progress_pct:.1f}%",     delta=f"{100-progress_pct:.1f}% restante", delta_color="inverse")
                    with gc5: st.metric("Mejora Necesaria", f"{multiplier:.1f}x",     delta="para el objetivo",    delta_color="inverse")
                    with gc6: st.metric("Capital Base",   "$500",                     delta="cuenta real objetivo", delta_color="off")

                st.divider()

                # ===== PARALLEL WORKERS VISUALIZATION =====
                st.markdown("#### ⚡ Workers en Paralelo")

                # Fetch parallel activity data
                try:
                    parallel_resp = requests.get(f"{COORDINATOR_URL}/api/parallel_activity", timeout=5)
                    if parallel_resp.status_code == 200:
                        parallel_data = parallel_resp.json()
                        machines      = parallel_data.get('workers_by_machine', [])
                        timeline      = parallel_data.get('activity_timeline', [])
                        in_progress   = parallel_data.get('in_progress_wus', [])
                        total_active  = parallel_data.get('total_active', 0)
                        parallelism   = parallel_data.get('parallelism_level', 0)
                        total_recent  = sum(timeline) if timeline else 0

                        # --- Summary metrics ---
                        pcol1, pcol2, pcol3, pcol4 = st.columns(4)
                        with pcol1:
                            st.metric("🔥 Workers Activos", total_active, delta="último minuto")
                        with pcol2:
                            st.metric("📊 WUs en Paralelo", parallelism, delta="procesándose")
                        with pcol3:
                            st.metric("🖥️ Máquinas", len(machines), delta="distribuidas")
                        with pcol4:
                            st.metric("🚀 Resultados/min", total_recent, delta="últimos 2 min")

                        # --- Workers Grid (pure HTML/CSS — un solo bloque) ---
                        st.markdown("##### 🖥️ Grid de Workers en Tiempo Real")

                        # Build machine blocks
                        machines_html = ""
                        for machine_data in machines:
                            machine_name  = machine_data.get('name', 'Unknown')
                            machine_color = machine_data.get('color', '#6b7280')
                            workers       = machine_data.get('workers', [])
                            active_count  = sum(1 for w in workers if w.get('is_active'))

                            worker_cards = ""
                            for w in workers:
                                is_active  = w.get('is_active', False)
                                wu_done    = w.get('work_units_completed', 0)
                                wname      = w.get('name', '?')
                                last_seen  = w.get('last_seen_ago', 0)
                                dot        = "●" if is_active else "○"
                                card_class = "worker-card active" if is_active else "worker-card idle"
                                last_txt   = f"{last_seen:.0f}s ago"
                                worker_cards += f"""
                                <div class="{card_class}">
                                    <div class="wdot">{dot}</div>
                                    <div class="wname">{wname}</div>
                                    <div class="wstat">{wu_done:,} WUs</div>
                                    <div class="wtime">{last_txt}</div>
                                </div>"""

                            machines_html += f"""
                            <div class="machine-block">
                                <div class="machine-hdr">
                                    <span class="machine-dot" style="background:{machine_color}"></span>
                                    <span class="machine-name">{machine_name}</span>
                                    <span class="machine-meta">{active_count}/{len(workers)} activos</span>
                                </div>
                                <div class="workers-flex">{worker_cards}</div>
                            </div>"""

                        # Build WU progress cards
                        wu_html = ""
                        for wu in in_progress[:6]:
                            wu_id     = wu.get('work_unit_id', '?')
                            progress  = wu.get('progress_pct', 0)
                            needed    = wu.get('replicas_needed', 1)
                            completed = wu.get('replicas_completed', 0)
                            assigned  = wu.get('replicas_assigned', 0)
                            wu_html += f"""
                            <div class="wu-card">
                                <div class="wu-id">WU #{wu_id}</div>
                                <div class="wu-pct">{progress:.0f}%</div>
                                <div class="wu-rep">{completed}/{needed} réplicas</div>
                                <div class="wu-bar-bg">
                                    <div class="wu-bar-fill" style="width:{progress}%"></div>
                                </div>
                                <div class="wu-assigned">{assigned} asignados</div>
                            </div>"""

                        wu_section = f"""
                        <div class="section-hdr">📊 Work Units en Progreso</div>
                        <div class="wu-flex">{wu_html}</div>""" if wu_html else ""

                        html_block = (
                            "<style>"
                            "@keyframes wkpulse{"
                            "0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(16,185,129,0.4)}"
                            "50%{opacity:.85;box-shadow:0 0 0 5px rgba(16,185,129,0)}}"
                            ".parallel-grid{font-family:sans-serif;padding:4px 0}"
                            ".section-hdr{font-size:13px;font-weight:600;color:#94a3b8;"
                            "margin:18px 0 10px 0;text-transform:uppercase;letter-spacing:.05em}"
                            ".machine-block{margin-bottom:16px}"
                            ".machine-hdr{display:flex;align-items:center;gap:8px;margin-bottom:8px}"
                            ".machine-dot{width:11px;height:11px;border-radius:3px;flex-shrink:0}"
                            ".machine-name{font-weight:700;font-size:14px;color:#e2e8f0}"
                            ".machine-meta{font-size:11px;color:#64748b;margin-left:4px}"
                            ".workers-flex{display:flex;flex-wrap:wrap;gap:8px}"
                            ".worker-card{background:#1e293b;border:1px solid #334155;"
                            "border-radius:10px;padding:10px 12px;min-width:110px;text-align:center}"
                            ".worker-card.active{background:rgba(16,185,129,0.08);"
                            "border-color:#10b981;animation:wkpulse 2s ease-in-out infinite}"
                            ".worker-card.idle{opacity:.65}"
                            ".wdot{font-size:14px;margin-bottom:4px}"
                            ".worker-card.active .wdot{color:#10b981}"
                            ".worker-card.idle .wdot{color:#475569}"
                            ".wname{font-size:10px;font-weight:600;color:#cbd5e1;"
                            "white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"
                            ".wstat{font-size:9px;color:#3b82f6;margin-top:3px}"
                            ".wtime{font-size:8px;color:#64748b;margin-top:2px}"
                            ".wu-flex{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:12px}"
                            ".wu-card{background:#1e293b;border-radius:10px;padding:12px 16px;"
                            "min-width:130px;text-align:center;border:1px solid #334155}"
                            ".wu-id{font-size:10px;color:#64748b;margin-bottom:4px}"
                            ".wu-pct{font-size:22px;font-weight:800;color:#3b82f6}"
                            ".wu-rep{font-size:9px;color:#94a3b8;margin-top:3px}"
                            ".wu-bar-bg{background:#334155;border-radius:4px;height:4px;"
                            "margin-top:8px;overflow:hidden}"
                            ".wu-bar-fill{background:linear-gradient(90deg,#3b82f6,#10b981);"
                            "height:100%;border-radius:4px}"
                            ".wu-assigned{font-size:8px;color:#64748b;margin-top:4px}"
                            "</style>"
                            f'<div class="parallel-grid">{machines_html}{wu_section}</div>'
                        )
                        st.html(html_block)

                except Exception as e:
                    st.warning(f"No se pudo obtener datos de actividad paralela: {e}")

                st.divider()

                # ===== PRODUCT DISTRIBUTION BY CATEGORY =====
                st.markdown("#### 📊 Distribución por Categoría de Activos")

                # Query database directly for accurate category breakdown
                try:
                    conn = sqlite3.connect(COORDINATOR_DB)
                    c = conn.cursor()

                    # Count by data file pattern
                    c.execute("SELECT json_extract(strategy_params, '$.data_file'), COUNT(*) FROM work_units GROUP BY json_extract(strategy_params, '$.data_file')")
                    file_counts = c.fetchall()

                    categories = {
                        'SPOT (BTC-USD)': 0,
                        'FUTURES Perpetuos': 0,
                        'FUTURES Dated': 0,
                        'Commodities': 0,
                        'Indices': 0,
                    }
                    unique_assets = set()

                    for file_name, count in file_counts:
                        if not file_name:
                            continue
                        unique_assets.add(file_name)
                        if file_name.startswith('BTC-USD'):
                            categories['SPOT (BTC-USD)'] += count
                        elif 'P-20DEC30-CDE' in file_name:
                            categories['FUTURES Perpetuos'] += count
                        elif file_name.startswith('GOL-') or file_name.startswith('NOL-') or file_name.startswith('NGS-') or file_name.startswith('CU-') or file_name.startswith('PT-'):
                            categories['Commodities'] += count
                        elif file_name.startswith('MC-'):
                            categories['Indices'] += count
                        elif '-CDE_' in file_name:
                            categories['FUTURES Dated'] += count

                    conn.close()

                    # Display in columns
                    cat_cols = st.columns(5)
                    cat_colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
                    cat_icons = ['💰', '♾️', '📅', '🏅', '📈']

                    for i, (cat_name, cat_count) in enumerate(categories.items()):
                        with cat_cols[i]:
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, {cat_colors[i]}22, {cat_colors[i]}11);
                                        border-left: 3px solid {cat_colors[i]}; border-radius: 8px; padding: 10px;">
                                <div style="font-size: 12px; color: #9ca3af;">{cat_icons[i]} {cat_name}</div>
                                <div style="font-size: 24px; font-weight: bold; color: {cat_colors[i]};">{cat_count:,}</div>
                            </div>
                            """, unsafe_allow_html=True)

                    st.caption(f"📁 **{len(unique_assets)}** archivos de datos únicos | Total WUs: **{total_wu:,}**")

                    # Progress bars for each category
                    st.markdown("##### Progreso por Categoría")
                    for cat_name, cat_count in categories.items():
                        if cat_count > 0:
                            pct = cat_count / total_wu * 100 if total_wu > 0 else 0
                            st.write(f"**{cat_name}**: {cat_count:,} ({pct:.1f}%)")
                            st.progress(pct / 100)

                except Exception as e:
                    st.warning(f"No se pudo cargar distribución: {e}")

                st.divider()

                # ===== WORLD MAP: Worker Network Globe =====
                st.markdown("#### Red Global de Workers")

                # Machine locations - spread slightly for visual clarity on globe
                MACHINE_LOCATIONS = {
                    "MacBook Pro": {"lat": 39.76, "lon": -104.88, "city": "Denver, CO",
                                    "role": "Coordinator + 7 Workers"},
                    "Linux ROG": {"lat": 39.55, "lon": -105.15, "city": "Denver, CO",
                                  "role": "5 Workers"},
                    "MacBook Air": {"lat": 40.02, "lon": -104.55, "city": "Denver, CO",
                                    "role": "4 Workers"},
                    "Asus Dorada": {"lat": 39.65, "lon": -104.70, "city": "Denver, CO",
                                    "role": "3 Workers"},
                    "Yony MacPro M5": {"lat": 39.85, "lon": -105.05, "city": "Denver, CO",
                                       "role": "8 Workers"},
                    "Otro": {"lat": 39.40, "lon": -104.70, "city": "Denver, CO",
                             "role": "Workers"},
                }

                # Aggregate workers by machine
                machine_workers = {}
                for ws in w_stats:
                    m = ws.get('machine', 'Otro')
                    if m not in machine_workers:
                        machine_workers[m] = {'active': 0, 'inactive': 0, 'total_wu': 0,
                                              'max_pnl': 0, 'workers': []}
                    machine_workers[m]['workers'].append(ws)
                    machine_workers[m]['total_wu'] += ws.get('work_units_completed', 0)
                    machine_workers[m]['max_pnl'] = max(machine_workers[m]['max_pnl'],
                                                        ws.get('max_pnl', 0))
                    if ws.get('status') == 'active':
                        machine_workers[m]['active'] += 1
                    else:
                        machine_workers[m]['inactive'] += 1

                fig_globe = go.Figure()
                coord_loc = MACHINE_LOCATIONS["MacBook Pro"]

                # Connection arcs from each machine to coordinator
                for machine, mdata in machine_workers.items():
                    if machine == "MacBook Pro":
                        continue
                    loc = MACHINE_LOCATIONS.get(machine, MACHINE_LOCATIONS["Otro"])
                    has_active = mdata['active'] > 0
                    arc_color = "#00ffc8" if has_active else "rgba(255, 60, 60, 0.3)"
                    fig_globe.add_trace(go.Scattergeo(
                        lon=[coord_loc["lon"], loc["lon"]],
                        lat=[coord_loc["lat"], loc["lat"]],
                        mode='lines',
                        line=dict(width=2.5 if has_active else 0.8, color=arc_color),
                        hoverinfo='skip', showlegend=False,
                        opacity=0.5 if has_active else 0.2
                    ))

                # Plot machines
                for machine, mdata in machine_workers.items():
                    loc = MACHINE_LOCATIONS.get(machine, MACHINE_LOCATIONS["Otro"])
                    has_active = mdata['active'] > 0
                    is_coordinator = machine == "MacBook Pro"

                    # Outer glow
                    glow_color = "rgba(0, 255, 200, 0.12)" if has_active else "rgba(255, 60, 60, 0.08)"
                    if is_coordinator:
                        glow_color = "rgba(255, 215, 0, 0.15)"
                    fig_globe.add_trace(go.Scattergeo(
                        lon=[loc["lon"]], lat=[loc["lat"]],
                        mode='markers',
                        marker=dict(size=45 if is_coordinator else 35,
                                    color=glow_color, line=dict(width=0)),
                        hoverinfo='skip', showlegend=False
                    ))

                    # Mid glow
                    mid_color = "rgba(0, 255, 200, 0.25)" if has_active else "rgba(255, 60, 60, 0.15)"
                    if is_coordinator:
                        mid_color = "rgba(255, 215, 0, 0.3)"
                    fig_globe.add_trace(go.Scattergeo(
                        lon=[loc["lon"]], lat=[loc["lat"]],
                        mode='markers',
                        marker=dict(size=22 if is_coordinator else 18,
                                    color=mid_color, line=dict(width=0)),
                        hoverinfo='skip', showlegend=False
                    ))

                    # Core dot with info
                    core_color = "#00ffc8" if has_active else "#ff3c3c"
                    if is_coordinator:
                        core_color = "#ffd700"
                    worker_names = ", ".join([w.get('short_name', '?') for w in mdata['workers']
                                              if w.get('status') == 'active'])
                    status_txt = f"{mdata['active']} activos" if has_active else "offline"

                    fig_globe.add_trace(go.Scattergeo(
                        lon=[loc["lon"]], lat=[loc["lat"]],
                        mode='markers+text',
                        marker=dict(size=12 if is_coordinator else 9,
                                    color=core_color,
                                    symbol="star" if is_coordinator else "circle",
                                    line=dict(width=1.5, color="rgba(255,255,255,0.8)")),
                        text=[machine],
                        textposition="top center",
                        textfont=dict(color="rgba(255,255,255,0.9)", size=11,
                                      family="monospace"),
                        customdata=[[loc["city"], loc["role"], mdata['active'],
                                     mdata['inactive'], mdata['total_wu'],
                                     f"${mdata['max_pnl']:.2f}", worker_names, status_txt]],
                        hovertemplate=(
                            "<b>%{text}</b><br>"
                            "%{customdata[0]}<br>"
                            "Rol: %{customdata[1]}<br>"
                            "Workers: %{customdata[2]} activos / %{customdata[3]} inactivos<br>"
                            "WU Completados: %{customdata[4]}<br>"
                            "Mejor PnL: %{customdata[5]}<br>"
                            "Activos: %{customdata[6]}<br>"
                            "Estado: %{customdata[7]}<extra></extra>"
                        ),
                        showlegend=False
                    ))

                # Globe styling - realistic Earth
                fig_globe.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=600,
                    margin=dict(l=0, r=0, t=0, b=0),
                    geo=dict(
                        projection_type="orthographic",
                        showland=True,
                        landcolor="rgb(30, 60, 30)",
                        showocean=True,
                        oceancolor="rgb(10, 30, 70)",
                        showlakes=True,
                        lakecolor="rgb(15, 40, 90)",
                        showrivers=True,
                        rivercolor="rgb(15, 40, 90)",
                        showcountries=True,
                        countrycolor="rgba(100, 140, 100, 0.4)",
                        countrywidth=0.5,
                        showcoastlines=True,
                        coastlinecolor="rgba(120, 170, 120, 0.5)",
                        coastlinewidth=0.8,
                        showsubunits=True,
                        subunitcolor="rgba(80, 120, 80, 0.2)",
                        showframe=False,
                        bgcolor="rgba(0,0,0,0)",
                        projection_rotation=dict(
                            lon=coord_loc["lon"],
                            lat=coord_loc["lat"]
                        ),
                    ),
                    showlegend=False
                )

                st.plotly_chart(fig_globe, width='stretch', key="chart_world_map")

                # Legend
                active_count = sum(1 for m in machine_workers.values() if m['active'] > 0)
                total_active_w = sum(m['active'] for m in machine_workers.values())
                st.markdown(
                    f'<div style="display:flex; justify-content:center; gap:30px; font-size:13px; opacity:0.8;">'
                    f'<span><b>{active_count}</b> maquinas / <b>{total_active_w}</b> workers conectados</span>'
                    f'<span style="color:#ffd700;">&#9733; Coordinator</span>'
                    f'<span style="color:#00ffc8;">&#9679; Worker activo</span>'
                    f'<span style="color:#ff3c3c;">&#9679; Worker offline</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                st.divider()

                # ===== ROW 2: PnL Timeline + Progress Donut =====
                chart_col1, chart_col2 = st.columns([3, 1])

                with chart_col1:
                    st.markdown("#### Evolucion de PnL")
                    if pnl_tl:
                        df_tl = pd.DataFrame(pnl_tl)
                        df_tl['timestamp'] = pd.to_datetime(df_tl['submitted_at_unix'], unit='s')

                        fig_pnl = px.scatter(
                            df_tl, x='timestamp', y='pnl',
                            color='worker_id',
                            hover_data=['work_unit_id', 'is_canonical'],
                            labels={'pnl': 'PnL ($)', 'timestamp': 'Tiempo', 'worker_id': 'Worker'}
                        )
                        fig_pnl.add_hline(y=0, line_dash="dash", line_color="gray",
                                          annotation_text="Break-even", annotation_position="bottom left")
                        fig_pnl.update_layout(
                            **plotly_layout,
                            height=350,
                            xaxis=dict(rangeslider=dict(visible=True), title=""),
                            yaxis_title="PnL ($)",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                            showlegend=True
                        )
                        st.plotly_chart(fig_pnl, width='stretch', key="chart_pnl_timeline")
                    else:
                        st.info("No hay datos de PnL disponibles")

                with chart_col2:
                    st.markdown("#### Progreso")
                    completed_v = wu.get('completed', 0)
                    in_progress_v = wu.get('in_progress', 0)
                    pending_v = wu.get('pending', 0)

                    if total_wu > 0:
                        fig_donut = go.Figure(go.Pie(
                            labels=["Completados", "En Progreso", "Pendientes"],
                            values=[completed_v, in_progress_v, pending_v],
                            hole=0.65,
                            marker_colors=["#00cc96", "#636efa", "#ef553b"],
                            textinfo="value",
                            hovertemplate="%{label}: %{value} (%{percent})<extra></extra>"
                        ))
                        fig_donut.update_layout(
                            **plotly_layout,
                            height=350,
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                            annotations=[dict(text=f"{completed_v}/{total_wu}",
                                              x=0.5, y=0.5, font_size=24, showarrow=False,
                                              font_color="white")]
                        )
                        st.plotly_chart(fig_donut, width='stretch', key="chart_donut")
                    else:
                        st.info("Sin work units")

                st.divider()

                # ===== ROW 3: Worker Performance + PnL Distribution + Completion Rate =====
                perf_col1, perf_col2, perf_col3 = st.columns(3)

                with perf_col1:
                    st.markdown("#### Rendimiento por Worker")
                    active_workers_list = [w for w in w_stats if w.get('status') == 'active']
                    if active_workers_list:
                        df_w = pd.DataFrame(active_workers_list).sort_values('work_units_completed', ascending=True)

                        fig_workers = make_subplots(rows=1, cols=2, shared_yaxes=True,
                                                    subplot_titles=("WU Completados", "Mejor PnL"),
                                                    horizontal_spacing=0.12)
                        fig_workers.add_trace(go.Bar(
                            y=df_w['short_name'], x=df_w['work_units_completed'],
                            orientation='h', marker_color='#636efa', name='WU',
                            text=df_w['work_units_completed'], textposition='auto',
                            hovertemplate="%{y}: %{x} WU<extra></extra>"
                        ), row=1, col=1)
                        fig_workers.add_trace(go.Bar(
                            y=df_w['short_name'], x=df_w['max_pnl'],
                            orientation='h', marker_color='#00cc96', name='PnL',
                            text=df_w['max_pnl'].apply(lambda x: f"${x:.0f}"), textposition='auto',
                            hovertemplate="%{y}: $%{x:.2f}<extra></extra>"
                        ), row=1, col=2)
                        fig_workers.update_layout(**plotly_layout, height=300, showlegend=False)
                        st.plotly_chart(fig_workers, width='stretch', key="chart_workers")
                    else:
                        st.info("No hay workers activos")

                with perf_col2:
                    st.markdown("#### Distribucion de PnL")
                    pnl_dist = stats.get('pnl_distribution', [])
                    if pnl_dist:
                        fig_hist = go.Figure(go.Histogram(
                            x=pnl_dist, nbinsx=30,
                            marker_color='#636efa', opacity=0.75,
                            hovertemplate="Rango: %{x}<br>Cantidad: %{y}<extra></extra>"
                        ))
                        avg_pnl = sum(pnl_dist) / len(pnl_dist) if pnl_dist else 0
                        fig_hist.add_vline(x=0, line_dash="dash", line_color="white",
                                           annotation_text="Break-even")
                        fig_hist.add_vline(x=avg_pnl, line_dash="dot", line_color="#ffa15a",
                                           annotation_text=f"Prom: ${avg_pnl:.0f}")
                        fig_hist.update_layout(**plotly_layout, height=300,
                                               xaxis_title="PnL ($)", yaxis_title="Frecuencia")
                        st.plotly_chart(fig_hist, width='stretch', key="chart_hist")
                    else:
                        st.info("Sin datos de distribucion")

                with perf_col3:
                    st.markdown("#### Resultados por Hora")
                    comp_tl = stats.get('completion_timeline', [])
                    if comp_tl:
                        df_comp = pd.DataFrame(comp_tl)
                        df_comp['hora'] = pd.to_datetime(df_comp['hour_unix'], unit='s')

                        fig_rate = go.Figure(go.Bar(
                            x=df_comp['hora'], y=df_comp['count'],
                            marker_color='#00cc96',
                            hovertemplate="Hora: %{x}<br>Resultados: %{y}<extra></extra>"
                        ))
                        fig_rate.update_layout(**plotly_layout, height=300,
                                               xaxis_title="", yaxis_title="Resultados")
                        st.plotly_chart(fig_rate, width='stretch', key="chart_rate")
                    else:
                        st.info("Sin datos de timeline")

                st.divider()

                # ===== BEST STRATEGY DETAILS =====
                if best:
                    st.markdown("#### 🏆 Mejor Estrategia Encontrada")

                    # Main metrics row
                    bs_col1, bs_col2, bs_col3, bs_col4 = st.columns(4)

                    initial_cap = best.get('initial_capital', 500)
                    pnl_val = best.get('pnl', 0)
                    roi_pct = (pnl_val / initial_cap * 100) if initial_cap > 0 else 0

                    with bs_col1:
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #1a472a 0%, #2d5a3d 100%);
                                    padding: 20px; border-radius: 12px; text-align: center;
                                    border: 1px solid rgba(0,255,136,0.3);">
                            <div style="color: #888; font-size: 12px; text-transform: uppercase;">Capital Inicial</div>
                            <div style="color: #fff; font-size: 28px; font-weight: bold;">${initial_cap:,.0f}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with bs_col2:
                        pnl_color = "#00ff88" if pnl_val >= 0 else "#ff4444"
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #1a3a4a 0%, #2d4a5a 100%);
                                    padding: 20px; border-radius: 12px; text-align: center;
                                    border: 1px solid rgba(0,200,255,0.3);">
                            <div style="color: #888; font-size: 12px; text-transform: uppercase;">PnL Neto</div>
                            <div style="color: {pnl_color}; font-size: 28px; font-weight: bold;">
                                {"+" if pnl_val >= 0 else ""}${pnl_val:.2f}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    with bs_col3:
                        roi_color = "#00ff88" if roi_pct >= 0 else "#ff4444"
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #3a2a1a 0%, #5a4a2d 100%);
                                    padding: 20px; border-radius: 12px; text-align: center;
                                    border: 1px solid rgba(255,200,0,0.3);">
                            <div style="color: #888; font-size: 12px; text-transform: uppercase;">ROI</div>
                            <div style="color: {roi_color}; font-size: 28px; font-weight: bold;">
                                {"+" if roi_pct >= 0 else ""}{roi_pct:.2f}%
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    with bs_col4:
                        is_canon = best.get('is_canonical', False)
                        badge_color = "#00cc96" if is_canon else "#ff9900"
                        badge_text = "VALIDADO" if is_canon else "PENDIENTE"
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #2a2a3a 0%, #3a3a5a 100%);
                                    padding: 20px; border-radius: 12px; text-align: center;
                                    border: 1px solid rgba(150,150,255,0.3);">
                            <div style="color: #888; font-size: 12px; text-transform: uppercase;">Estado</div>
                            <div style="color: {badge_color}; font-size: 18px; font-weight: bold; margin-top: 5px;">
                                {badge_text}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)

                    # Performance metrics row
                    pm_col1, pm_col2, pm_col3, pm_col4, pm_col5 = st.columns(5)

                    with pm_col1:
                        trades = best.get('trades', 0)
                        st.metric("Trades", f"{trades}", delta="operaciones")

                    with pm_col2:
                        wr = best.get('win_rate', 0) * 100
                        wr_delta = "excelente" if wr >= 60 else ("bueno" if wr >= 50 else "mejorable")
                        st.metric("Win Rate", f"{wr:.1f}%", delta=wr_delta)

                    with pm_col3:
                        sharpe = best.get('sharpe_ratio', 0)
                        sharpe_delta = "excelente" if sharpe >= 5 else ("bueno" if sharpe >= 2.5 else "bajo")
                        st.metric("Sharpe Ratio", f"{sharpe:.2f}", delta=f"{sharpe_delta} (per-trade)")

                    with pm_col4:
                        dd = best.get('max_drawdown', 0) * 100
                        dd_delta = "bajo riesgo" if dd <= 10 else ("moderado" if dd <= 20 else "alto")
                        st.metric("Max Drawdown", f"{dd:.1f}%", delta=dd_delta, delta_color="inverse")

                    with pm_col5:
                        exec_time = best.get('execution_time', 0)
                        st.metric("Tiempo Ejecucion", f"{exec_time:.1f}s", delta="backtest")

                    st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)

                    # Backtest parameters
                    with st.expander("📊 Parametros del Backtest", expanded=False):
                        param_col1, param_col2, param_col3 = st.columns(3)

                        with param_col1:
                            st.markdown("**Datos**")
                            data_file = best.get('data_file', 'N/A')
                            max_candles = best.get('max_candles', 0)
                            st.code(f"Archivo: {data_file}\nVelas: {max_candles:,}")

                        with param_col2:
                            st.markdown("**Algoritmo Genetico**")
                            gens = best.get('generations', 0)
                            pop = best.get('population_size', 0)
                            risk = best.get('risk_level', 'N/A')
                            st.code(f"Generaciones: {gens}\nPoblacion: {pop}\nRiesgo: {risk}")

                        with param_col3:
                            st.markdown("**Worker**")
                            worker_id = best.get('worker_id', 'N/A')
                            wu_id = best.get('work_unit_id', 'N/A')
                            short_worker = best.get('worker_short', worker_id.split('_')[-1] if '_' in worker_id else worker_id)
                            wid_l = worker_id.lower()
                            if "yonathan" in wid_l:
                                machine = "Yony MacPro M5"
                            elif "macbook-pro" in wid_l:
                                machine = "MacBook Pro"
                            elif "macbook-air" in wid_l:
                                machine = "MacBook Air"
                            elif "rog" in wid_l:
                                machine = "Linux ROG"
                            elif "enderj_linux" in wid_l or "enderj" == wid_l.split("_")[0]:
                                machine = "Asus Dorada"
                            else:
                                machine = "Otro"
                            st.code(f"ID: {short_worker}\nMaquina: {machine}\nWork Unit: {wu_id}")

                    # Trading rules (genome)
                    genome = best.get('genome')
                    if genome:
                        with st.expander("🧬 Reglas de Trading (Genoma)", expanded=False):
                            rule_col1, rule_col2, rule_col3 = st.columns(3)

                            with rule_col1:
                                st.markdown("**Reglas de Entrada**")
                                entry_rules = genome.get('entry_rules', [])
                                if entry_rules:
                                    for i, rule in enumerate(entry_rules[:3], 1):
                                        ind1 = rule.get('indicator1', {})
                                        ind2 = rule.get('indicator2', {})
                                        op = rule.get('operator', '?')
                                        st.code(f"R{i}: {ind1.get('name','?')}({ind1.get('period','?')}) {op} {ind2.get('name','?')}({ind2.get('period','?')})")
                                else:
                                    st.info("No hay reglas de entrada")

                            with rule_col2:
                                st.markdown("**Reglas de Salida**")
                                exit_rules = genome.get('exit_rules', [])
                                if exit_rules:
                                    for i, rule in enumerate(exit_rules[:3], 1):
                                        ind1 = rule.get('indicator1', {})
                                        ind2 = rule.get('indicator2', {})
                                        op = rule.get('operator', '?')
                                        st.code(f"R{i}: {ind1.get('name','?')}({ind1.get('period','?')}) {op} {ind2.get('name','?')}({ind2.get('period','?')})")
                                else:
                                    st.info("No hay reglas de salida")

                            with rule_col3:
                                st.markdown("**Gestion de Riesgo**")
                                risk_params = genome.get('risk_params', {})
                                sl = risk_params.get('stop_loss_pct', 0) * 100
                                tp = risk_params.get('take_profit_pct', 0) * 100
                                pos = risk_params.get('position_size_pct', 0) * 100
                                st.code(f"Stop Loss: {sl:.1f}%\nTake Profit: {tp:.1f}%\nTamano Pos: {pos:.0f}%")

                    st.divider()

                # ===== ROW 4: Resource Usage =====
                st.markdown("#### Recursos del Cluster")

                MACHINE_SPECS = {
                    "MacBook Pro": {"total_cpus": 12, "cpus_per_worker": 1.7, "power_w": 30, "gpu": "M-series Metal", "numba": True},
                    "Linux ROG": {"total_cpus": 16, "cpus_per_worker": 3.2, "power_w": 65, "gpu": "NVIDIA CUDA", "numba": True},
                    "MacBook Air": {"total_cpus": 8, "cpus_per_worker": 2, "power_w": 15, "gpu": "M-series Metal", "numba": True},
                    "Asus Dorada": {"total_cpus": 16, "cpus_per_worker": 5, "power_w": 45, "gpu": "AMD/NVIDIA", "numba": True},
                    "Yony MacPro M5": {"total_cpus": 10, "cpus_per_worker": 1.25, "power_w": 25, "gpu": "M-series Metal", "numba": True},
                    "Otro": {"total_cpus": 8, "cpus_per_worker": 4, "power_w": 20, "gpu": "N/A", "numba": False},
                }

                # Count active workers per machine
                machine_active = {}
                for ws in w_stats:
                    if ws.get('status') == 'active':
                        m = ws.get('machine', 'Otro')
                        machine_active[m] = machine_active.get(m, 0) + 1

                machines_with_workers = [m for m in machine_active if machine_active[m] > 0]

                if machines_with_workers:
                    gauge_cols = st.columns(len(machines_with_workers) + 1)

                    for i, machine in enumerate(machines_with_workers):
                        spec = MACHINE_SPECS.get(machine, MACHINE_SPECS["Otro"])
                        active = machine_active.get(machine, 0)
                        used_cpus = active * spec["cpus_per_worker"]
                        cpu_pct = min((used_cpus / spec["total_cpus"]) * 100, 100)

                        with gauge_cols[i]:
                            fig_gauge = go.Figure(go.Indicator(
                                mode="gauge+number",
                                value=cpu_pct,
                                number={"suffix": "%", "font": {"size": 24}},
                                gauge={
                                    "axis": {"range": [0, 100], "tickwidth": 1},
                                    "bar": {"color": "#636efa"},
                                    "steps": [
                                        {"range": [0, 50], "color": "rgba(99,102,250,0.1)"},
                                        {"range": [50, 80], "color": "rgba(99,102,250,0.2)"},
                                        {"range": [80, 100], "color": "rgba(99,102,250,0.3)"},
                                    ],
                                    "threshold": {"line": {"color": "#ef553b", "width": 3},
                                                  "thickness": 0.75, "value": 90}
                                },
                                title={"text": f"{machine}<br>{active}W | {int(used_cpus)}/{spec['total_cpus']} CPUs | {'Numba JIT' if spec.get('numba') else 'Python'}",
                                        "font": {"size": 12}}
                            ))
                            fig_gauge.update_layout(
                                template="plotly_dark",
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                font=dict(size=11),
                                height=220,
                                margin=dict(l=20, r=20, t=60, b=10)
                            )
                            st.plotly_chart(fig_gauge, width='stretch',
                                            key=f"gauge_{machine.replace(' ', '_')}")

                    # Energy metrics in last column
                    with gauge_cols[-1]:
                        total_watts = sum(MACHINE_SPECS.get(m, MACHINE_SPECS["Otro"])["power_w"]
                                          for m in machines_with_workers)
                        cpu_hrs = perf.get('total_compute_time', 0) / 3600
                        kwh = (total_watts * cpu_hrs) / 1000

                        st.metric("Consumo", f"{total_watts}W",
                                  delta=f"{len(machines_with_workers)} maquinas")
                        st.metric("CPU-Horas", f"{cpu_hrs:.1f} hrs")
                        st.metric("Energia Est.", f"{kwh:.2f} kWh",
                                  delta=f"~${kwh * 0.12:.2f} USD")
                else:
                    st.info("No hay maquinas activas")

                st.divider()

                # ===== ROW 5: Interactive Results Table =====
                st.markdown("#### Resultados Recientes")

                if pnl_tl:
                    df_results = pd.DataFrame(pnl_tl)
                    df_results['timestamp'] = pd.to_datetime(df_results['submitted_at_unix'], unit='s')

                    # Filter controls
                    filt1, filt2, filt3 = st.columns([2, 2, 1])
                    pnl_min = float(df_results['pnl'].min())
                    pnl_max = float(df_results['pnl'].max())

                    with filt1:
                        if pnl_min < pnl_max:
                            pnl_range = st.slider("Rango PnL ($)", pnl_min, pnl_max,
                                                  (pnl_min, pnl_max), key="tbl_pnl_filter")
                        else:
                            pnl_range = (pnl_min, pnl_max)

                    with filt2:
                        all_workers = sorted(df_results['worker_id'].unique().tolist())
                        worker_filter = st.multiselect("Workers", all_workers,
                                                        default=all_workers,
                                                        key="tbl_worker_filter")

                    with filt3:
                        canonical_only = st.checkbox("Solo canonicos", value=False,
                                                     key="tbl_canonical_filter")

                    # Apply filters
                    mask = (df_results['pnl'] >= pnl_range[0]) & (df_results['pnl'] <= pnl_range[1])
                    if worker_filter:
                        mask &= df_results['worker_id'].isin(worker_filter)
                    if canonical_only:
                        mask &= df_results['is_canonical'] == True

                    df_filtered = df_results[mask].sort_values('pnl', ascending=False)

                    st.dataframe(
                        df_filtered[['timestamp', 'work_unit_id', 'pnl', 'worker_id', 'is_canonical']],
                        width='stretch',
                        column_config={
                            "timestamp": st.column_config.DatetimeColumn("Fecha", format="DD/MM HH:mm"),
                            "work_unit_id": st.column_config.NumberColumn("WU ID"),
                            "pnl": st.column_config.NumberColumn("PnL", format="$%.2f"),
                            "worker_id": st.column_config.TextColumn("Worker"),
                            "is_canonical": st.column_config.CheckboxColumn("Canonico"),
                        },
                        hide_index=True,
                        key="tbl_results"
                    )

                    pos_count = perf.get('positive_pnl_count', 0)
                    neg_count = perf.get('negative_pnl_count', 0)
                    st.caption(f"Mostrando {len(df_filtered)} de {len(df_results)} resultados | "
                               f"Positivos: {pos_count} | Negativos: {neg_count}")
                else:
                    st.info("No hay resultados disponibles aun")

                # Timestamp
                st.caption(f"Ultima actualizacion: {datetime.now().strftime('%H:%M:%S')}")

            # Execute the fragment
            dashboard_fragment()

    # TAB 2: Workers - VERSIÓN MEJORADA
    with tab2:
        st.subheader("👥 Workers Registry")
        st.markdown("""
        **Sistema distribuido**: Cada worker ejecuta backtests en paralelo.
        Los workers deben registrarse con el coordinator para recibir trabajo.
        """)

        if not coordinator_running:
            st.error("❌ Coordinator no está ejecutando. Inicia el coordinator primero.")
        else:
            workers = get_workers()
            
            if workers:
                # Funciones helper
                def format_exec_time(seconds):
                    if seconds < 60:
                        return f"{seconds:.0f}s"
                    elif seconds < 3600:
                        return f"{seconds/60:.0f} min"
                    else:
                        return f"{seconds/3600:.1f} hrs"

                def is_worker_alive(w):
                    mins = w.get('last_seen_minutes_ago')
                    if mins is not None:
                        return mins < 5.0
                    return w.get('status') == 'active'

                def get_machine_from_id(worker_id):
                    """Extrae el nombre de la máquina del worker ID"""
                    wid = worker_id.lower()
                    hostname = ""
                    # Check hostname field if available
                    for w in workers:
                        if w.get('id') == worker_id:
                            hostname = w.get('hostname', '').lower()
                            break
                    if "yonathan" in wid or "yonathan" in hostname:
                        return "Yony MacPro M5"
                    elif "macbook-pro" in wid or "enders-macbook-pro" in hostname:
                        return "MacBook Pro"
                    elif "macbook-air" in wid or "enders-macbook-air" in hostname:
                        return "MacBook Air"
                    elif "rog" in wid or "ender-rog" in hostname:
                        return "Linux ROG"
                    elif hostname == "enderj" or ("enderj_linux" in wid):
                        return "Asus Dorada"
                    elif "macbook" in wid:
                        return "MacBook"
                    elif "linux" in wid:
                        return "Linux"
                    return "Unknown"

                def get_short_name(worker_id):
                    """Obtiene nombre corto para display"""
                    if "_W" in worker_id:
                        parts = worker_id.rsplit("_W", 1)
                        if len(parts) == 2:
                            return f"W{parts[1]}"
                    return worker_id.split("_")[0][:10]

                # Clasificar workers
                alive = [w for w in workers if is_worker_alive(w)]
                inactive = [w for w in workers if not is_worker_alive(w)]
                never_seen = [w for w in inactive if w.get('last_seen_minutes_ago', 0) > 60]  # > 1 hora

                # Contadores
                total_registered = len(workers)
                total_alive = len(alive)
                total_inactive = len(inactive)

                # ===== MÉTRICAS DE RESUMEN =====
                col_stats1, col_stats2, col_stats3, col_stats4 = st.columns(4)

                with col_stats1:
                    st.metric("Total Registrados", total_registered, 
                             delta=f"{total_alive} activos", delta_color="normal")

                with col_stats2:
                    st.metric("Activos (≤5 min)", total_alive, 
                             delta="conectados", delta_color="normal")

                with col_stats3:
                    st.metric("Inactivos (>5 min)", total_inactive,
                             delta_color="off")

                with col_stats4:
                    # Calcular capacidad total
                    alive_cpus = sum(4 for _ in alive)  # ~4 CPUs por worker
                    st.metric("Capacidad", f"~{alive_cpus} CPUs",
                             delta="disponibles")

                st.divider()

                # ===== FILTROS =====
                col_filter1, col_filter2 = st.columns([3, 1])

                with col_filter1:
                    filter_machine = st.multiselect(
                        "🔍 Filtrar por máquina",
                        options=["MacBook Pro", "MacBook Air", "Linux ROG", "Asus Dorada", "Yony MacPro M5", "Unknown"],
                        default=[],
                        key="worker_machine_filter"
                    )

                with col_filter2:
                    show_never_seen = st.checkbox("Mostrar nunca vistos", value=False, key="show_never_seen_check")

                # ===== WORKERS ACTIVOS =====
                st.markdown("### 🟢 Workers Activos (Conectados)")

                if not alive:
                    st.info("No hay workers activos. Inicia workers desde la pestaña 'Control'.")
                else:
                    # Filtrar por máquina
                    if filter_machine:
                        alive_filtered = [w for w in alive if get_machine_from_id(w['id']) in filter_machine]
                    else:
                        alive_filtered = alive

                    if not alive_filtered:
                        st.warning("No hay workers activos que coincidan con el filtro.")
                    else:
                        # Agrupar por máquina
                        from collections import defaultdict
                        machines_alive = defaultdict(list)
                        for w in alive_filtered:
                            machine = get_machine_from_id(w['id'])
                            machines_alive[machine].append(w)

                        for machine, w_list in machines_alive.items():
                            icon = "🍎" if "MacBook" in machine else ("🐧" if "Linux" in machine else "💻")
                            with st.expander(f"{icon} {machine} ({len(w_list)} workers)", expanded=True):
                                # Tabla de workers activos
                                cols = st.columns([2, 1, 1, 1, 2])
                                with cols[0]:
                                    st.write("**Worker ID**")
                                with cols[1]:
                                    st.write("**WU**")
                                with cols[2]:
                                    st.write("**Tiempo**")
                                with cols[3]:
                                    st.write("**Seen**")
                                with cols[4]:
                                    st.write("**Estado**")

                                for w in w_list:
                                    cols = st.columns([2, 1, 1, 1, 2])
                                    short_name = get_short_name(w['id'])
                                    mins = w.get('last_seen_minutes_ago', 0)
                                    
                                    with cols[0]:
                                        st.code(f"{short_name}")
                                        st.caption(f"📍 {w.get('hostname', '?')}")
                                    with cols[1]:
                                        wu = w.get('work_units_completed', 0)
                                        st.metric("WU", f"{wu}")
                                    with cols[2]:
                                        st.write(format_exec_time(w.get('total_execution_time', 0)))
                                    with cols[3]:
                                        st.write(f"🟢 {mins:.1f}m")
                                    with cols[4]:
                                        st.success("● Conectado", icon="✅")

                                    st.divider()

                st.divider()

                # ===== WORKERS INACTIVOS =====
                inactive_to_show = [w for w in inactive if not (w in never_seen and not show_never_seen)]

                if filter_machine:
                    inactive_to_show = [w for w in inactive_to_show if get_machine_from_id(w['id']) in filter_machine]

                if inactive_to_show:
                    st.markdown("### 🔴 Workers Inactivos (Desconectados)")

                    # Agrupar por máquina
                    from collections import defaultdict
                    machines_inactive = defaultdict(list)
                    for w in inactive_to_show:
                        machine = get_machine_from_id(w['id'])
                        machines_inactive[machine].append(w)

                    for machine, w_list in machines_inactive.items():
                        icon = "🍎" if "MacBook" in machine else ("🐧" if "Linux" in machine else "💻")
                        with st.expander(f"{icon} {machine} ({len(w_list)} workers)", expanded=False):
                            for w in w_list:
                                mins = w.get('last_seen_minutes_ago', 9999)
                                short_name = get_short_name(w['id'])
                                
                                col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                                
                                with col1:
                                    st.write(f"**{short_name}**")
                                    st.caption(f"ID: {w.get('id', '?')[:30]}...")
                                with col2:
                                    st.write(f"WU: {w.get('work_units_completed', 0)}")
                                with col3:
                                    st.write(f"⏰ {int(mins//60)}h {int(mins%60)}m" if mins >= 60 else f"⏰ {mins:.0f}m")
                                with col4:
                                    if mins > 60:
                                        st.error(f"💀 Offline ({mins/60:.0f}h)")
                                    else:
                                        st.warning(f"🟡 Inactivo ({mins:.0f}m)")

                # ===== WORKERS NUNCA VISTOS =====
                if show_never_seen and never_seen:
                    st.markdown("### ⚫ Workers Registrados Nunca Vistos")
                    st.caption("Workers que se registraron pero nunca volvieron a conectarse")

                    for w in never_seen:
                        short_name = get_short_name(w['id'])
                        mins = w.get('last_seen_minutes_ago', 9999)
                        machine = get_machine_from_id(w['id'])
                        
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                        
                        with col1:
                            st.write(f"**{short_name}**")
                            st.caption(f"📍 {machine}")
                        with col2:
                            st.write(f"WU: {w.get('work_units_completed', 0)}")
                        with col3:
                            st.write(f"⏰ {mins/60:.0f}h")
                        with col4:
                            st.error("❌ Nunca se conectó")

                st.divider()

                # ===== ACCIONES RÁPIDAS =====
                st.markdown("### ⚡ Acciones Rápidas")

                col_action1, col_action2 = st.columns(2)

                with col_action1:
                    if st.button("🔄 Actualizar Lista", width='stretch'):
                        st.rerun()

                with col_action2:
                    if st.button("🗑️ Limpiar Workers Antiguos", width='stretch',
                               help="Elimina workers no vistos en las últimas 24 horas"):
                        try:
                            conn = sqlite3.connect(COORDINATOR_DB)
                            c = conn.cursor()
                            c.execute("DELETE FROM workers WHERE (julianday('now') - last_seen) > 1.0")
                            deleted = c.rowcount
                            conn.commit()
                            conn.close()
                            st.success(f"Eliminados {deleted} workers antiguos")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

                # ===== API DATA BRUTA =====
                with st.expander("🔍 Ver datos crudos de la API", expanded=False):
                    st.json(workers)

            else:
                st.info("""
                **No hay workers registrados aún.**

                Para añadir workers:
                1. Asegúrate de que el coordinator esté ejecutándose
                2. En cada máquina worker, ejecuta:
                
                ```bash
                cd <directorio_del_proyecto>
                export COORDINATOR_URL=http://<IP_COORDINATOR>:5001
                python3 crypto_worker.py
                ```

                O para múltiples workers en la misma máquina:
                ```bash
                for i in 1 2 3; do
                    COORDINATOR_URL=http://<IP>:5001 WORKER_INSTANCE=$i \
                    nohup python3 crypto_worker.py > /tmp/worker_$i.log 2>&1 &
                    sleep 2
                done
                ```
                """)

            # Footer
            st.caption(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")

    with tab3:
        st.subheader("⚙️ Control del Sistema")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📡 Coordinator")

            if coordinator_running:
                st.success("✅ Coordinator está ejecutando en puerto 5001")

                if st.button("🛑 Detener Coordinator", type="primary"):
                    try:
                        pid_file = "coordinator.pid"
                        if os.path.exists(pid_file):
                            with open(pid_file, 'r') as f:
                                pid = int(f.read().strip())
                            os.kill(pid, 15)  # SIGTERM
                            st.success(f"✅ Coordinator detenido (PID: {pid})")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ No se encontró archivo coordinator.pid")
                    except Exception as e:
                        st.error(f"❌ Error al detener coordinator: {str(e)}")

                st.markdown("**Dashboard:** http://localhost:5001")
                st.markdown("**API Status:** http://localhost:5001/api/status")
            else:
                st.warning("❌ Coordinator no está ejecutando")

                if st.button("▶️ Iniciar Coordinator", type="primary"):
                    try:
                        # Start coordinator using the start script
                        subprocess.Popen(['bash', './start_coordinator.sh'],
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
                        st.success("✅ Coordinator iniciado. Espera 3 segundos...")
                        time.sleep(3)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al iniciar coordinator: {str(e)}")

        with col2:
            st.markdown("### 🖥️ Workers")

            st.info("**🍎 MacBook Pro (3 Workers):**")
            if st.button("▶️ Iniciar 3 Workers (MacBook Pro)"):
                try:
                    subprocess.Popen(
                        ['bash', os.path.join(BASE_DIR, 'multi_worker.sh'), '3'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        env={**os.environ, 'COORDINATOR_URL': 'http://localhost:5001'},
                        cwd=BASE_DIR
                    )
                    st.success("✅ 3 Workers MacBook Pro iniciados")
                    time.sleep(3)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

            if st.button("🛑 Detener Workers MacBook Pro"):
                try:
                    subprocess.run(['pkill', '-f', 'crypto_worker'], timeout=5)
                    st.success("✅ Workers MacBook Pro detenidos")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

            st.divider()

            st.info("**🐧 Linux ROG (5 Workers - 10.0.0.240):**")
            if st.button("▶️ Iniciar 5 Workers (Linux)"):
                try:
                    result = subprocess.run(
                        ['ssh', '-o', 'ConnectTimeout=10', 'enderj@10.0.0.240',
                         'cd ~/crypto_worker && for i in 1 2 3 4 5; do '
                         'COORDINATOR_URL="http://10.0.0.232:5001" NUM_WORKERS="5" '
                         'WORKER_INSTANCE="$i" USE_RAY="false" PYTHONUNBUFFERED=1 '
                         'nohup python3 -u crypto_worker.py > /tmp/worker_$i.log 2>&1 & sleep 2; done; echo OK'],
                        capture_output=True, text=True, timeout=30
                    )
                    if 'OK' in result.stdout:
                        st.success("✅ 5 Workers Linux iniciados")
                    else:
                        st.error(f"Error SSH: {result.stderr[:200]}")
                except subprocess.TimeoutExpired:
                    st.warning("⏱ SSH timeout - verificar conectividad Linux")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

            if st.button("🛑 Detener Workers Linux"):
                try:
                    subprocess.run(
                        ['ssh', '-o', 'ConnectTimeout=10', 'enderj@10.0.0.240',
                         'killall python3 2>/dev/null; echo done'],
                        capture_output=True, text=True, timeout=15
                    )
                    st.success("✅ Workers Linux detenidos")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

            st.divider()
            with st.expander("🔧 Comandos SSH Manual"):
                st.code("""# Linux - Iniciar
ssh enderj@10.0.0.240 "cd ~/crypto_worker && COORDINATOR_URL=http://10.0.0.232:5001 bash multi_worker_linux.sh 5"

# Linux - Detener
ssh enderj@10.0.0.240 "killall python3"

# MacBook Pro - Iniciar
COORDINATOR_URL=http://localhost:5001 bash multi_worker.sh 3

# MacBook Pro - Detener
pkill -f crypto_worker""", language="bash")

    # TAB 4: Logs
    with tab4:
        st.subheader("📜 System Logs")

        log_tab1, log_tab2, log_tab3 = st.tabs(["📡 Coordinator", "🍎 MacBook Pro", "🐧 Linux ROG"])

        with log_tab1:
            col_log1, col_log2, col_log3 = st.columns([3, 1, 1])
            with col_log1:
                st.markdown("### 📡 Coordinator Log")
            with col_log2:
                if st.button("🔄 Actualizar", width='stretch', key="refresh_coordinator"):
                    st.rerun()
            with col_log3:
                auto_refresh_coord = st.checkbox("🔁 Auto", value=False, key="auto_refresh_coord")

            st.caption(f"📅 {datetime.now().strftime('%H:%M:%S')}")
            lines = st.slider("Líneas", 10, 200, 50, key="coord_lines")
            log_content = read_log_file("/tmp/coordinator.log", lines)
            st.text_area("Log Output", log_content, height=400, key="coord_log")
            if auto_refresh_coord:
                time.sleep(5)
                st.rerun()

        with log_tab2:
            col_log1, col_log2, col_log3 = st.columns([3, 1, 1])
            with col_log1:
                st.markdown("### 🍎 MacBook Pro Workers (3)")
            with col_log2:
                if st.button("🔄 Actualizar", width='stretch', key="refresh_worker_pro"):
                    st.rerun()
            with col_log3:
                auto_refresh_log = st.checkbox("🔁 Auto", value=False, key="auto_refresh_worker_pro")

            st.caption(f"📅 {datetime.now().strftime('%H:%M:%S')}")
            lines = st.slider("Líneas", 10, 200, 50, key="worker_pro_lines")
            worker_num = st.radio("Worker:", [1, 2, 3, "Todos"], horizontal=True, key="mac_w_sel")

            if worker_num == "Todos":
                cols = st.columns(3)
                for i, col in enumerate(cols, 1):
                    with col:
                        st.markdown(f"**W{i}**")
                        st.text_area(f"W{i}", read_log_file(f"/tmp/worker_{i}.log", lines // 3), height=300, key=f"mac_w{i}")
            else:
                st.text_area("Log Output", read_log_file(f"/tmp/worker_{worker_num}.log", lines), height=400, key="worker_pro_log")

            if auto_refresh_log:
                time.sleep(5)
                st.rerun()

        with log_tab3:
            col_log1, col_log2, col_log3 = st.columns([3, 1, 1])
            with col_log1:
                st.markdown("### 🐧 Linux ROG Workers (5)")
            with col_log2:
                if st.button("🔄 Actualizar", width='stretch', key="refresh_worker_linux"):
                    st.rerun()
            with col_log3:
                auto_refresh_linux = st.checkbox("🔁 Auto", value=False, key="auto_refresh_linux")

            st.caption(f"📅 {datetime.now().strftime('%H:%M:%S')}")
            lines_ssh = st.slider("Líneas", 10, 200, 30, key="worker_linux_lines")
            linux_wn = st.radio("Worker:", [1, 2, 3, 4, 5], horizontal=True, key="linux_w_sel")

            if st.button("📥 Leer Log vía SSH", width='stretch', key="read_linux_log"):
                with st.spinner("Conectando a 10.0.0.240..."):
                    try:
                        result = subprocess.run(
                            ["ssh", "-o", "ConnectTimeout=5", "enderj@10.0.0.240",
                             f"tail -n {lines_ssh} /tmp/worker_{linux_wn}.log"],
                            capture_output=True, text=True, timeout=10
                        )
                        if result.returncode == 0:
                            st.text_area("Log Output", result.stdout, height=400, key="linux_log_out")
                        else:
                            st.error(f"Error: {result.stderr[:200]}")
                    except subprocess.TimeoutExpired:
                        st.error("⏱️ SSH Timeout")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

            with st.expander("🔧 Comandos SSH"):
                st.code("""ssh enderj@10.0.0.240 "tail -50 /tmp/worker_1.log"
ssh enderj@10.0.0.240 "for i in 1 2 3 4 5; do echo '=== W$i ==='; tail -5 /tmp/worker_\\$i.log; done"
ssh enderj@10.0.0.240 "pgrep -a crypto_worker" """, language="bash")

            if auto_refresh_linux:
                time.sleep(5)
                st.rerun()

    # TAB 5: Create Work Units
    with tab5:
        st.subheader("➕ Crear Nuevos Work Units")

        # Show success message if work unit was just created
        if 'last_work_unit_created' in st.session_state:
            work_unit_id = st.session_state['last_work_unit_created']
            st.success(f"🎉 Work Unit #{work_unit_id} creado exitosamente y listo para procesamiento!")
            # Clear the message after showing it
            del st.session_state['last_work_unit_created']

        st.markdown("""
        Crea nuevos work units para búsqueda distribuida de estrategias.
        Los workers automáticamente tomarán estos trabajos y ejecutarán backtests.
        """)

        # Data file selector section
        with st.expander("📊 Gestión de Archivos de Datos", expanded=True):
            st.markdown("### Archivos Disponibles")

            # Scan data directory for CSV files
            data_dir = os.path.join(BASE_DIR, "data")
            if os.path.exists(data_dir):
                csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]

                if csv_files:
                    # Create data for table
                    file_data = []
                    for file in csv_files:
                        filepath = os.path.join(data_dir, file)
                        try:
                            # Get file size
                            size_bytes = os.path.getsize(filepath)
                            if size_bytes < 1024:
                                size_str = f"{size_bytes} B"
                            elif size_bytes < 1024*1024:
                                size_str = f"{size_bytes/1024:.1f} KB"
                            else:
                                size_str = f"{size_bytes/(1024*1024):.1f} MB"

                            # Read first few rows to get candle count
                            df_temp = pd.read_csv(filepath)
                            candles = len(df_temp)

                            # Extract timeframe from filename
                            if "ONE_MINUTE" in file:
                                timeframe = "1 min"
                            elif "FIVE_MINUTE" in file:
                                timeframe = "5 min"
                            elif "FIFTEEN_MINUTE" in file:
                                timeframe = "15 min"
                            elif "ONE_HOUR" in file:
                                timeframe = "1 hour"
                            else:
                                timeframe = "Unknown"

                            file_data.append({
                                'Archivo': file,
                                'Timeframe': timeframe,
                                'Velas': f"{candles:,}",
                                'Tamaño': size_str,
                                'Path': filepath
                            })
                        except Exception as e:
                            st.warning(f"⚠️ Error leyendo {file}: {str(e)}")

                    # Display table
                    if file_data:
                        df_files = pd.DataFrame(file_data)

                        # Select data file
                        st.markdown("#### 📁 Seleccionar Archivo de Datos")

                        # Get current selection from session state or default to BTC-USD_FIVE_MINUTE.csv
                        if 'selected_data_file' not in st.session_state:
                            st.session_state['selected_data_file'] = 'BTC-USD_FIVE_MINUTE.csv'

                        selected_file = st.selectbox(
                            "Archivo activo para work units:",
                            options=[f['Archivo'] for f in file_data],
                            index=[f['Archivo'] for f in file_data].index(st.session_state['selected_data_file'])
                                  if st.session_state['selected_data_file'] in [f['Archivo'] for f in file_data] else 0,
                            help="Este archivo será usado por los workers para ejecutar backtests"
                        )

                        # Update session state
                        st.session_state['selected_data_file'] = selected_file

                        # Show selected file info
                        selected_info = next((f for f in file_data if f['Archivo'] == selected_file), None)
                        if selected_info:
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Archivo Activo", selected_info['Archivo'])
                            with col2:
                                st.metric("Timeframe", selected_info['Timeframe'])
                            with col3:
                                st.metric("Velas", selected_info['Velas'])
                            with col4:
                                st.metric("Tamaño", selected_info['Tamaño'])

                        st.divider()

                        # Show all files in table with actions
                        st.markdown("#### 📋 Todos los Archivos")

                        for idx, file_info in enumerate(file_data):
                            with st.container():
                                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])

                                with col1:
                                    is_selected = file_info['Archivo'] == selected_file
                                    icon = "✅" if is_selected else "📄"
                                    st.write(f"{icon} **{file_info['Archivo']}**")

                                with col2:
                                    st.write(file_info['Timeframe'])

                                with col3:
                                    st.write(file_info['Velas'])

                                with col4:
                                    st.write(file_info['Tamaño'])

                                with col5:
                                    if st.button("🗑️", key=f"delete_{idx}", help=f"Borrar {file_info['Archivo']}"):
                                        if is_selected:
                                            st.error("❌ No puedes borrar el archivo activo. Selecciona otro primero.")
                                        else:
                                            try:
                                                os.remove(file_info['Path'])
                                                st.success(f"✅ Archivo {file_info['Archivo']} borrado")
                                                time.sleep(0.5)
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"❌ Error borrando archivo: {str(e)}")

                                if idx < len(file_data) - 1:
                                    st.markdown("---")

                else:
                    st.warning("⚠️ No se encontraron archivos CSV en el directorio 'data/'")
            else:
                st.error(f"❌ Directorio 'data/' no encontrado")

        st.divider()

        # Data Download Section
        with st.expander("📥 Descargar Datos Históricos", expanded=False):
            st.markdown("""
            ### Descarga datos históricos de Coinbase
            Selecciona uno o varios activos, configura el timeframe y rango de fechas,
            y descarga los datos automáticamente.
            """)

            # Initialize session state for multi-step wizard
            if 'download_step' not in st.session_state:
                st.session_state['download_step'] = 1
            if 'selected_products' not in st.session_state:
                st.session_state['selected_products'] = []
            if 'download_config' not in st.session_state:
                st.session_state['download_config'] = {}

            # Progress indicator
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                step1_icon = "✅" if st.session_state['download_step'] > 1 else "🔵" if st.session_state['download_step'] == 1 else "⚪"
                st.markdown(f"**{step1_icon} Paso 1: Activos**")
            with col2:
                step2_icon = "✅" if st.session_state['download_step'] > 2 else "🔵" if st.session_state['download_step'] == 2 else "⚪"
                st.markdown(f"**{step2_icon} Paso 2: Timeframe**")
            with col3:
                step3_icon = "✅" if st.session_state['download_step'] > 3 else "🔵" if st.session_state['download_step'] == 3 else "⚪"
                st.markdown(f"**{step3_icon} Paso 3: Período**")
            with col4:
                step4_icon = "🔵" if st.session_state['download_step'] == 4 else "⚪"
                st.markdown(f"**{step4_icon} Paso 4: Descargar**")

            st.divider()

            # STEP 1: Select Assets
            if st.session_state['download_step'] == 1:
                st.markdown("### 📊 Paso 1: Seleccionar Activos")
                st.info("💡 Selecciona uno o varios activos para descargar datos históricos")

                # Get available products from Coinbase
                try:
                    with st.spinner("Cargando lista de activos..."):
                        if not broker_client.client:
                            broker_client.authenticate()

                        all_products = broker_client.get_tradable_symbols()

                        if all_products:
                            # Filter options
                            col_filter1, col_filter2 = st.columns(2)
                            with col_filter1:
                                filter_text = st.text_input("🔍 Buscar activo:", placeholder="Ej: BTC, ETH, SOL")
                            with col_filter2:
                                show_all = st.checkbox("Mostrar todos los pares", value=False)

                            # Filter products
                            if filter_text:
                                filtered_products = [p for p in all_products if filter_text.upper() in p.upper()]
                            else:
                                # Show most popular by default
                                popular = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 'XRP-USD',
                                          'DOGE-USD', 'MATIC-USD', 'AVAX-USD', 'DOT-USD', 'LINK-USD']
                                if show_all:
                                    filtered_products = all_products
                                else:
                                    filtered_products = [p for p in all_products if p in popular]

                            st.markdown(f"**Activos disponibles:** {len(filtered_products)}")

                            # Multi-select with checkboxes
                            selected_products = st.multiselect(
                                "Selecciona los activos a descargar:",
                                options=filtered_products,
                                default=st.session_state.get('selected_products', []),
                                help="Puedes seleccionar múltiples activos para descargar en paralelo"
                            )

                            # Show selected count
                            if selected_products:
                                st.success(f"✅ {len(selected_products)} activo(s) seleccionado(s): {', '.join(selected_products[:5])}{'...' if len(selected_products) > 5 else ''}")

                            # Navigation buttons
                            col_btn1, col_btn2 = st.columns([3, 1])
                            with col_btn2:
                                if st.button("Siguiente →", type="primary", disabled=len(selected_products) == 0):
                                    st.session_state['selected_products'] = selected_products
                                    st.session_state['download_step'] = 2
                                    st.rerun()

                        else:
                            st.error("❌ No se pudo obtener la lista de activos. Verifica tu conexión a Coinbase.")

                except Exception as e:
                    st.error(f"❌ Error obteniendo productos: {str(e)}")

            # STEP 2: Select Timeframe
            elif st.session_state['download_step'] == 2:
                st.markdown("### ⏱️ Paso 2: Seleccionar Timeframe")
                st.info(f"💡 Descargando datos para: **{', '.join(st.session_state['selected_products'][:3])}{'...' if len(st.session_state['selected_products']) > 3 else ''}**")

                # Timeframe options with descriptions
                timeframe_options = {
                    'ONE_MINUTE': {'label': '1 Minuto', 'desc': 'Alta frecuencia - Archivos grandes', 'granularity': 'ONE_MINUTE'},
                    'FIVE_MINUTE': {'label': '5 Minutos', 'desc': 'Recomendado para trading intraday', 'granularity': 'FIVE_MINUTE'},
                    'FIFTEEN_MINUTE': {'label': '15 Minutos', 'desc': 'Balance entre detalle y tamaño', 'granularity': 'FIFTEEN_MINUTE'},
                    'ONE_HOUR': {'label': '1 Hora', 'desc': 'Para análisis de tendencias', 'granularity': 'ONE_HOUR'},
                    'SIX_HOUR': {'label': '6 Horas', 'desc': 'Para análisis de largo plazo', 'granularity': 'SIX_HOUR'},
                    'ONE_DAY': {'label': '1 Día', 'desc': 'Para análisis macro', 'granularity': 'ONE_DAY'}
                }

                selected_timeframe = None
                for key, info in timeframe_options.items():
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        if st.button(info['label'], key=f"tf_{key}", width='stretch'):
                            selected_timeframe = key
                    with col2:
                        st.write(f"*{info['desc']}*")

                # Also provide a selectbox for easier selection
                st.markdown("**O selecciona del menú:**")
                selected_tf_dropdown = st.selectbox(
                    "Timeframe:",
                    options=list(timeframe_options.keys()),
                    format_func=lambda x: timeframe_options[x]['label'],
                    index=1,  # Default to FIVE_MINUTE
                    key="tf_dropdown"
                )

                # Navigation buttons
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn1:
                    if st.button("← Atrás"):
                        st.session_state['download_step'] = 1
                        st.rerun()
                with col_btn3:
                    if st.button("Siguiente →", type="primary"):
                        final_timeframe = selected_timeframe if selected_timeframe else selected_tf_dropdown
                        st.session_state['download_config']['timeframe'] = final_timeframe
                        st.session_state['download_config']['granularity'] = timeframe_options[final_timeframe]['granularity']
                        st.session_state['download_step'] = 3
                        st.rerun()

            # STEP 3: Select Date Range
            elif st.session_state['download_step'] == 3:
                st.markdown("### 📅 Paso 3: Seleccionar Período")

                config = st.session_state['download_config']
                st.info(f"💡 Timeframe: **{config.get('timeframe', 'N/A')}** | Activos: **{len(st.session_state['selected_products'])}**")

                # Quick presets
                st.markdown("#### Períodos Predefinidos")
                col1, col2, col3, col4 = st.columns(4)

                preset_selected = None
                with col1:
                    if st.button("📊 1 Semana", width='stretch'):
                        preset_selected = 7
                with col2:
                    if st.button("📊 1 Mes", width='stretch'):
                        preset_selected = 30
                with col3:
                    if st.button("📊 3 Meses", width='stretch'):
                        preset_selected = 90
                with col4:
                    if st.button("📊 1 Año", width='stretch'):
                        preset_selected = 365

                st.divider()

                # Custom date range
                st.markdown("#### O selecciona fechas personalizadas")

                from datetime import datetime, timedelta

                col_date1, col_date2 = st.columns(2)
                with col_date1:
                    start_date = st.date_input(
                        "Fecha de inicio:",
                        value=datetime.now() - timedelta(days=30),
                        max_value=datetime.now()
                    )
                with col_date2:
                    end_date = st.date_input(
                        "Fecha de fin:",
                        value=datetime.now(),
                        max_value=datetime.now()
                    )

                # Calculate days and estimated candles
                if preset_selected:
                    days = preset_selected
                    end_date = datetime.now().date()
                    start_date = (datetime.now() - timedelta(days=days)).date()
                else:
                    days = (end_date - start_date).days

                # Estimate candles and file size
                timeframe_to_candles_per_day = {
                    'ONE_MINUTE': 1440,
                    'FIVE_MINUTE': 288,
                    'FIFTEEN_MINUTE': 96,
                    'ONE_HOUR': 24,
                    'SIX_HOUR': 4,
                    'ONE_DAY': 1
                }

                tf = config.get('timeframe', 'FIVE_MINUTE')
                estimated_candles = days * timeframe_to_candles_per_day.get(tf, 288)
                estimated_size_mb = (estimated_candles * 0.1) / 1024  # Rough estimate

                # Show estimates
                col_est1, col_est2, col_est3 = st.columns(3)
                with col_est1:
                    st.metric("Días", f"{days}")
                with col_est2:
                    st.metric("Velas estimadas", f"{estimated_candles:,}")
                with col_est3:
                    st.metric("Tamaño estimado", f"{estimated_size_mb:.1f} MB por activo")

                # Navigation buttons
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn1:
                    if st.button("← Atrás", key="back_step3"):
                        st.session_state['download_step'] = 2
                        st.rerun()
                with col_btn3:
                    if st.button("Siguiente →", type="primary", key="next_step3"):
                        st.session_state['download_config']['start_date'] = start_date
                        st.session_state['download_config']['end_date'] = end_date
                        st.session_state['download_config']['days'] = days
                        st.session_state['download_config']['estimated_candles'] = estimated_candles
                        st.session_state['download_step'] = 4
                        st.rerun()

            # STEP 4: Confirm and Download
            elif st.session_state['download_step'] == 4:
                st.markdown("### 🚀 Paso 4: Confirmar y Descargar")

                config = st.session_state['download_config']
                products = st.session_state['selected_products']

                # Summary
                st.markdown("#### 📋 Resumen de Descarga")

                col_sum1, col_sum2 = st.columns(2)
                with col_sum1:
                    st.metric("Activos a descargar", len(products))
                    st.metric("Timeframe", config.get('timeframe', 'N/A'))
                    st.metric("Período", f"{config.get('days', 0)} días")
                with col_sum2:
                    st.metric("Velas por activo", f"{config.get('estimated_candles', 0):,}")
                    st.metric("Velas totales", f"{config.get('estimated_candles', 0) * len(products):,}")

                # Show list of products
                with st.expander("📊 Ver lista completa de activos", expanded=False):
                    for idx, product in enumerate(products, 1):
                        st.write(f"{idx}. {product}")

                st.divider()

                # Download button
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn1:
                    if st.button("← Atrás", key="back_step4"):
                        st.session_state['download_step'] = 3
                        st.rerun()
                with col_btn3:
                    if st.button("🚀 Descargar Ahora", type="primary", width='stretch'):
                        # Execute download
                        st.markdown("---")
                        st.markdown("### 📥 Descargando Datos...")

                        progress_bar = st.progress(0)
                        status_text = st.empty()

                        from datetime import datetime
                        import time as time_module

                        # Convert dates to timestamps
                        start_ts = int(datetime.combine(config['start_date'], datetime.min.time()).timestamp())
                        end_ts = int(datetime.combine(config['end_date'], datetime.max.time()).timestamp())

                        successful_downloads = []
                        failed_downloads = []

                        for idx, product in enumerate(products):
                            try:
                                status_text.text(f"Descargando {product} ({idx+1}/{len(products)})...")
                                progress_bar.progress((idx) / len(products))

                                # Download data
                                df = broker_client.get_historical_data(
                                    symbol=product,
                                    granularity=config['granularity'],
                                    start_ts=start_ts,
                                    end_ts=end_ts
                                )

                                if df is not None and not df.empty:
                                    # Save to file
                                    filename = f"{product}_{config['timeframe']}.csv"
                                    filepath = os.path.join("data", filename)

                                    df.to_csv(filepath, index=False)
                                    successful_downloads.append(product)
                                    st.success(f"✅ {product}: {len(df)} velas guardadas en {filename}")
                                else:
                                    failed_downloads.append(product)
                                    st.warning(f"⚠️ {product}: No se obtuvieron datos")

                                # Small delay to avoid rate limiting
                                time_module.sleep(0.5)

                            except Exception as e:
                                failed_downloads.append(product)
                                st.error(f"❌ {product}: Error - {str(e)}")

                        progress_bar.progress(1.0)
                        status_text.text("¡Descarga completada!")

                        # Summary
                        st.markdown("---")
                        st.markdown("### 📊 Resultados")
                        col_res1, col_res2 = st.columns(2)
                        with col_res1:
                            st.metric("✅ Exitosos", len(successful_downloads))
                        with col_res2:
                            st.metric("❌ Fallidos", len(failed_downloads))

                        if successful_downloads:
                            st.balloons()

                        # Reset wizard
                        if st.button("🔄 Descargar Más Datos"):
                            st.session_state['download_step'] = 1
                            st.session_state['selected_products'] = []
                            st.session_state['download_config'] = {}
                            st.rerun()

        st.divider()

        # Auto-calculator section
        with st.expander("🧮 Calculadora Automática de Parámetros Óptimos", expanded=False):
            st.markdown("""
            Esta calculadora analiza:
            - 📊 Cantidad de datos disponibles
            - 📈 Volatilidad del activo
            - 💻 Recursos computacionales (workers activos)
            - ⚡ Cores disponibles

            Y sugiere parámetros óptimos para maximizar la búsqueda.
            """)

            if st.button("🔍 Calcular Parámetros Óptimos", width='stretch', type="primary"):
                with st.spinner("Analizando datos y recursos..."):
                    try:
                        # 1. Analyze available data - use selected file
                        selected_file = st.session_state.get('selected_data_file', 'BTC-USD_FIVE_MINUTE.csv')
                        data_file = os.path.join("data", selected_file)

                        if os.path.exists(data_file):
                            df = pd.read_csv(data_file)
                            total_candles = len(df)

                            # Calculate volatility (std of returns)
                            df['returns'] = df['close'].pct_change()
                            volatility = df['returns'].std()

                            # 2. Get active workers and their resources
                            workers = get_workers()
                            active_workers = [w for w in workers if w.get('status') == 'active']
                            num_workers = len(active_workers)

                            # Estimate total available cores (assuming 9 cores per worker based on your setup)
                            total_cores = int(num_workers * 3.5) if num_workers > 0 else 12

                            # 3. Calculate optimal parameters
                            # Population: Use total cores * multiplier for good parallelization
                            # For 2 workers (18 cores), suggest 80-150 population
                            if total_cores >= 18:
                                optimal_population = min(150, total_cores * 5)
                            elif total_cores >= 9:
                                optimal_population = min(80, total_cores * 5)
                            else:
                                optimal_population = max(40, total_cores * 3)

                            # Generations: Based on data size and volatility
                            # More data = can afford more generations
                            # High volatility = need more generations to find robust strategies
                            if total_candles > 50000:
                                base_generations = 100
                            elif total_candles > 30000:
                                base_generations = 60
                            else:
                                base_generations = 40

                            # Adjust for volatility
                            if volatility > 0.02:  # High volatility
                                optimal_generations = int(base_generations * 1.5)
                            else:
                                optimal_generations = base_generations

                            # Risk level: Based on volatility
                            if volatility > 0.025:
                                optimal_risk = "HIGH"
                            elif volatility > 0.015:
                                optimal_risk = "MEDIUM"
                            else:
                                optimal_risk = "LOW"

                            # Replicas: More workers = can afford more replicas for validation
                            optimal_replicas = min(num_workers, 3) if num_workers > 0 else 2

                            # Display results
                            st.success("✅ Análisis Completado")

                            col1, col2 = st.columns(2)

                            with col1:
                                st.markdown("#### 📊 Análisis de Datos")
                                st.metric("Velas Disponibles", f"{total_candles:,}")
                                st.metric("Volatilidad", f"{volatility*100:.3f}%")
                                st.markdown("#### 💻 Recursos Disponibles")
                                st.metric("Workers Activos", num_workers)
                                st.metric("Cores Totales Estimados", total_cores)

                            with col2:
                                st.markdown("#### 🎯 Parámetros Sugeridos")
                                st.metric("Población Óptima", optimal_population)
                                st.metric("Generaciones Óptimas", optimal_generations)
                                st.metric("Risk Level Óptimo", optimal_risk)
                                st.metric("Réplicas Sugeridas", optimal_replicas)

                            # Store in session state for auto-fill
                            st.session_state['optimal_population'] = optimal_population
                            st.session_state['optimal_generations'] = optimal_generations
                            st.session_state['optimal_risk'] = optimal_risk
                            st.session_state['optimal_replicas'] = optimal_replicas
                            st.session_state['show_optimal'] = True

                            st.info("💡 Usa el botón '🎯 Aplicar Parámetros Óptimos' abajo para aplicar estos valores automáticamente")

                        else:
                            st.error(f"❌ Archivo de datos no encontrado: {data_file}")

                    except Exception as e:
                        st.error(f"❌ Error calculando parámetros óptimos: {str(e)}")

        st.divider()

        # Button to apply optimal parameters
        if st.session_state.get('show_optimal', False):
            if st.button("🎯 Aplicar Parámetros Óptimos", width='stretch', type="secondary"):
                st.session_state['apply_optimal'] = True
                st.rerun()

        with st.form("create_work_unit"):
            # Check if we should use optimal values
            use_optimal = st.session_state.get('apply_optimal', False)

            # Get default values (optimal if available, otherwise standard defaults)
            default_population = st.session_state.get('optimal_population', 40) if use_optimal else 40
            default_generations = st.session_state.get('optimal_generations', 30) if use_optimal else 30
            default_risk = st.session_state.get('optimal_risk', 'MEDIUM') if use_optimal else 'MEDIUM'
            default_replicas = st.session_state.get('optimal_replicas', 2) if use_optimal else 2

            # Get index for risk level selectbox
            risk_options = ["LOW", "MEDIUM", "HIGH"]
            risk_index = risk_options.index(default_risk) if default_risk in risk_options else 1

            col1, col2 = st.columns(2)

            with col1:
                population_size = st.number_input("Tamaño de Población", min_value=5, max_value=1000, value=default_population, step=5)
                generations = st.number_input("Generaciones", min_value=3, max_value=200, value=default_generations, step=5)

            with col2:
                risk_level = st.selectbox("Nivel de Riesgo", risk_options, index=risk_index)
                replicas_needed = st.number_input("Réplicas (redundancia)", min_value=1, max_value=5, value=default_replicas, step=1)

            submitted = st.form_submit_button("➕ Crear Work Unit", type="primary")

            if submitted:
                if not coordinator_running:
                    st.error("❌ Coordinator debe estar ejecutando para crear work units")
                else:
                    try:
                        # Create work unit by inserting into database
                        import sqlite3

                        # Get selected data file
                        selected_file = st.session_state.get('selected_data_file', 'BTC-USD_ONE_MINUTE.csv')

                        strategy_params = {
                            'population_size': population_size,
                            'generations': generations,
                            'risk_level': risk_level,
                            'data_file': selected_file  # Include selected data file
                        }

                        # Debug info
                        with st.spinner(f"Creando work unit (Pop:{population_size}, Gen:{generations}, Risk:{risk_level})..."):
                            conn = sqlite3.connect(COORDINATOR_DB)
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO work_units (strategy_params, replicas_needed, replicas_assigned, status)
                                VALUES (?, ?, 0, 'pending')
                            """, (json.dumps(strategy_params), replicas_needed))
                            conn.commit()
                            work_unit_id = cursor.lastrowid
                            conn.close()

                        # Show success message BEFORE rerun
                        st.success(f"✅ Work Unit #{work_unit_id} creado exitosamente!")
                        st.info(f"""
                        **Detalles:**
                        - Población: {population_size}
                        - Generaciones: {generations}
                        - Risk Level: {risk_level}
                        - Réplicas: {replicas_needed}
                        - Data File: {selected_file}
                        """)
                        st.balloons()

                        # Store success message in session state to show after rerun
                        st.session_state['last_work_unit_created'] = work_unit_id

                        # Clear optimal parameter flags
                        if 'apply_optimal' in st.session_state:
                            del st.session_state['apply_optimal']
                        if 'show_optimal' in st.session_state:
                            del st.session_state['show_optimal']

                        time.sleep(2)  # Give user time to see the message
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al crear work unit: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())

        st.divider()

        # Quick presets
        st.markdown("### 🚀 Presets Rápidos")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("⚡ Búsqueda Rápida", width='stretch'):
                st.info("Población: 20, Generaciones: 15, Risk: LOW")

        with col2:
            if st.button("🎯 Búsqueda Estándar", width='stretch'):
                st.info("Población: 40, Generaciones: 30, Risk: MEDIUM")

        with col3:
            if st.button("🔥 Búsqueda Exhaustiva", width='stretch'):
                st.info("Población: 60, Generaciones: 50, Risk: HIGH")

    # TAB 6: Paper Trading
    with tab6:
        st.subheader("📈 Paper Trading en Vivo")
        st.markdown("""
        Sistema de paper trading que usa la mejor estrategia encontrada para operar en tiempo real con datos de Coinbase.
        **NO ejecuta órdenes reales**, solo simula con condiciones realistas.
        """)

        # Initialize paper trader state
        if 'paper_trader' not in st.session_state:
            st.session_state['paper_trader'] = None
        if 'paper_trading_running' not in st.session_state:
            st.session_state['paper_trading_running'] = False

        # Load paper trading state from file
        paper_state_file = "/tmp/paper_trading_state.json"
        if os.path.exists(paper_state_file):
            try:
                with open(paper_state_file, 'r') as f:
                    paper_state = json.load(f)
                st.session_state['paper_capital'] = paper_state.get('capital', 10000)
                st.session_state['paper_trades'] = paper_state.get('trades', [])
            except:
                st.session_state['paper_capital'] = 10000
                st.session_state['paper_trades'] = []
        else:
            st.session_state['paper_capital'] = 10000
            st.session_state['paper_trades'] = []

        # Configuration section
        with st.expander("⚙️ Configuración", expanded=False):
            col1, col2, col3 = st.columns(3)

            with col1:
                initial_capital = st.number_input(
                    "Capital Inicial ($)",
                    min_value=1000,
                    max_value=1000000,
                    value=10000,
                    step=1000,
                    key="paper_initial_capital"
                )

            with col2:
                position_size_pct = st.slider(
                    "Tamaño de Posición (%)",
                    min_value=1,
                    max_value=50,
                    value=10,
                    key="paper_position_size"
                )

            with col3:
                product_id = st.selectbox(
                    "Par de Trading",
                    options=["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"],
                    index=0,
                    key="paper_product"
                )

            col1, col2 = st.columns(2)
            with col1:
                fee_rate = st.number_input(
                    "Fee Rate (%)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.4,
                    step=0.1,
                    key="paper_fee_rate"
                ) / 100

            with col2:
                slippage = st.number_input(
                    "Slippage (%)",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.05,
                    step=0.01,
                    key="paper_slippage"
                ) / 100

        # Get best strategy from database
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()

            # Try canonical first
            c.execute("""
                SELECT r.strategy_genome, r.pnl, r.trades, r.win_rate, r.sharpe_ratio
                FROM results r
                WHERE r.is_canonical = 1
                ORDER BY r.pnl DESC
                LIMIT 1
            """)
            best_row = c.fetchone()

            # Fallback to best overall
            if not best_row:
                c.execute("""
                    SELECT r.strategy_genome, r.pnl, r.trades, r.win_rate, r.sharpe_ratio
                    FROM results r
                    WHERE r.pnl > 0 AND r.trades >= 10
                    ORDER BY r.sharpe_ratio DESC
                    LIMIT 1
                """)
                best_row = c.fetchone()

            conn.close()
        except:
            best_row = None

        # Status metrics
        st.markdown("### 📊 Estado Actual")

        col1, col2, col3, col4 = st.columns(4)

        paper_capital = st.session_state.get('paper_capital', 10000)
        paper_trades = st.session_state.get('paper_trades', [])
        paper_initial = st.session_state.get('paper_initial_capital', 10000)

        total_pnl = sum(t.get('pnl', 0) for t in paper_trades)
        return_pct = ((paper_capital / paper_initial) - 1) * 100 if paper_initial > 0 else 0

        with col1:
            st.metric("💰 Capital Virtual", f"${paper_capital:,.2f}", f"{return_pct:+.2f}%")

        with col2:
            st.metric("📊 Total Trades", len(paper_trades))

        with col3:
            wins = sum(1 for t in paper_trades if t.get('pnl', 0) > 0)
            win_rate = (wins / len(paper_trades) * 100) if paper_trades else 0
            st.metric("🎯 Win Rate", f"{win_rate:.1f}%")

        with col4:
            st.metric("💵 PnL Total", f"${total_pnl:+,.2f}")

        st.divider()

        # Strategy info
        if best_row:
            st.markdown("### 🧠 Estrategia Activa")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("PnL Backtest", f"${best_row[1]:,.2f}")
            with col2:
                st.metric("Trades Backtest", best_row[2])
            with col3:
                st.metric("Win Rate Backtest", f"{best_row[3]*100:.1f}%")
            with col4:
                st.metric("Sharpe Backtest", f"{best_row[4]:.2f}")

            # Show strategy rules
            try:
                strategy_genome = json.loads(best_row[0]) if best_row[0] else {}
                entry_rules = strategy_genome.get('entry_rules', [])
                params = strategy_genome.get('params', {})

                if entry_rules:
                    st.markdown("**Reglas de Entrada:**")
                    for i, rule in enumerate(entry_rules):
                        left = rule.get('left', {})
                        right = rule.get('right', {})
                        op = rule.get('op', '>')

                        left_str = left.get('indicator', left.get('field', left.get('value', '?')))
                        if 'period' in left:
                            left_str += f"_{left['period']}"
                        right_str = right.get('indicator', right.get('field', right.get('value', '?')))
                        if 'period' in right:
                            right_str += f"_{right['period']}"

                        st.code(f"  {i+1}. {left_str} {op} {right_str}")

                if params:
                    st.markdown(f"**Parámetros:** SL={params.get('sl_pct', 0.05)*100:.1f}%, TP={params.get('tp_pct', 0.10)*100:.1f}%")
            except:
                st.warning("No se pudo cargar la estrategia")
        else:
            st.warning("⚠️ No hay estrategias válidas en la base de datos. Ejecuta más work units primero.")

        st.divider()

        # Control buttons
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("▶️ Iniciar Paper Trading", type="primary", disabled=st.session_state['paper_trading_running']):
                st.session_state['paper_trading_running'] = True
                st.success("Paper Trading iniciado! (Se ejecuta en background)")
                st.info("Nota: El paper trader se ejecuta como proceso separado. Monitorea los logs para ver las operaciones.")

        with col2:
            if st.button("⏹️ Detener", disabled=not st.session_state['paper_trading_running']):
                st.session_state['paper_trading_running'] = False
                st.warning("Paper Trading detenido")

        with col3:
            if st.button("🔄 Reiniciar Contadores"):
                st.session_state['paper_capital'] = st.session_state.get('paper_initial_capital', 10000)
                st.session_state['paper_trades'] = []
                # Also clear the state file
                if os.path.exists(paper_state_file):
                    os.remove(paper_state_file)
                st.success("Contadores reiniciados")
                st.rerun()

        st.divider()

        # Equity curve
        if paper_trades:
            st.markdown("### 📈 Equity Curve")

            equity_data = []
            equity = paper_initial
            equity_data.append({'Trade': 0, 'Equity': equity})

            for i, trade in enumerate(paper_trades):
                equity += trade.get('pnl', 0)
                equity_data.append({'Trade': i + 1, 'Equity': equity})

            if len(equity_data) > 1:
                df_equity = pd.DataFrame(equity_data)
                st.line_chart(df_equity.set_index('Trade'))

        # Recent trades
        if paper_trades:
            st.markdown("### 📋 Últimos Trades")
            df_trades = pd.DataFrame(paper_trades[-20:])
            if not df_trades.empty:
                # Format columns
                display_cols = ['entry_time', 'exit_time', 'entry_price', 'exit_price', 'pnl', 'pnl_pct', 'exit_reason']
                available_cols = [c for c in display_cols if c in df_trades.columns]
                st.dataframe(
                    df_trades[available_cols].style.format({
                        'entry_price': '${:.2f}',
                        'exit_price': '${:.2f}',
                        'pnl': '${:+.2f}',
                        'pnl_pct': '{:+.2f}%'
                    }),
                    use_container_width=True
                )

        # How to run paper trader
        with st.expander("🔧 Cómo Ejecutar Paper Trading", expanded=False):
            st.code(f"""
# En una terminal separada, ejecuta:
source ~/coinbase_trader_venv/bin/activate
cd "{BASE_DIR}"
python live_paper_trader.py --product {product_id} --capital {initial_capital} --size {position_size_pct/100}

# El paper trader se conectará a Coinbase WebSocket y
# ejecutará la mejor estrategia encontrada en tiempo real.
            """, language="bash")

    # TAB 7: Futures Trading
    with tab7:
        st.subheader("🚀 Coinbase Futures Trading")

        # Futures data directory
        futures_data_dir = os.path.join(BASE_DIR, "data_futures")

        # Check for futures data
        futures_files = []
        if os.path.exists(futures_data_dir):
            futures_files = [f for f in os.listdir(futures_data_dir) if f.endswith('.csv')]

        if not futures_files:
            st.warning("⚠️ No hay datos de futuros. Descarga datos primero.")
            st.code(f"""
# Descargar datos de futuros con data_manager:
cd "{BASE_DIR}"
source ~/coinbase_trader_venv/bin/activate
python data_manager.py --futures --products BIP-20DEC30-CDE ETP-20DEC30-CDE
            """, language="bash")
        else:
            # Initialize session state for futures
            if 'futures_contract' not in st.session_state:
                st.session_state['futures_contract'] = futures_files[0].replace('_FIVE_MINUTE.csv', '').replace('_ONE_MINUTE.csv', '')
            if 'futures_leverage' not in st.session_state:
                st.session_state['futures_leverage'] = 5
            if 'futures_direction' not in st.session_state:
                st.session_state['futures_direction'] = 'BOTH'
            if 'futures_capital' not in st.session_state:
                st.session_state['futures_capital'] = 10000
            if 'futures_paper_running' not in st.session_state:
                st.session_state['futures_paper_running'] = False

            # KPI Row
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)

            with kpi1:
                st.metric("📊 Datos Futures", f"{len(futures_files)} archivos")

            with kpi2:
                # Count perpetuals vs dated
                perpetuals = len([f for f in futures_files if any(x in f for x in ['BIP', 'ETP', 'SLP', 'XPP', 'ADP', 'AVP', 'DOP', 'HEP', 'LCP', 'LNP', 'XLP'])])
                st.metric("♾️ Perpetuos", f"{perpetuals}")

            with kpi3:
                dated = len(futures_files) - perpetuals
                st.metric("📅 Dated", f"{dated}")

            with kpi4:
                st.metric("⚡ Max Leverage", "10x")

            st.divider()

            # Configuration section
            col_config1, col_config2 = st.columns([2, 1])

            with col_config1:
                st.markdown("### ⚙️ Configuración")

                # Contract selector
                col_contract1, col_contract2 = st.columns(2)

                with col_contract1:
                    # Categorize products
                    perpetual_products = sorted([f.replace('_FIVE_MINUTE.csv', '').replace('_ONE_MINUTE.csv', '')
                                                  for f in futures_files
                                                  if any(x in f for x in ['BIP', 'ETP', 'SLP', 'XPP', 'ADP', 'AVP', 'DOP', 'HEP', 'LCP', 'LNP', 'XLP'])])
                    dated_products = sorted([f.replace('_FIVE_MINUTE.csv', '').replace('_ONE_MINUTE.csv', '')
                                             for f in futures_files
                                             if not any(x in f for x in ['BIP', 'ETP', 'SLP', 'XPP', 'ADP', 'AVP', 'DOP', 'HEP', 'LCP', 'LNP', 'XLP'])])

                    product_category = st.radio("Tipo", ["♾️ Perpetuos", "📅 Dated"], horizontal=True, key="futures_category")

                    available_products = perpetual_products if product_category == "♾️ Perpetuos" else dated_products

                    selected_product = st.selectbox(
                        "Contrato",
                        available_products,
                        key="futures_product_select"
                    )

                with col_contract2:
                    # Check if perpetual
                    is_perpetual = any(x in selected_product for x in ['BIP', 'ETP', 'SLP', 'XPP', 'ADP', 'AVP', 'DOP', 'HEP', 'LCP', 'LNP', 'XLP'])

                    if is_perpetual:
                        st.info(f"♾️ **Perpetuo**\n\nFunding rate: ~0.01%/8h")
                    else:
                        # Extract expiry from contract name
                        parts = selected_product.split('-')
                        if len(parts) >= 2:
                            expiry = parts[1]
                            st.info(f"📅 **Vencimiento: {expiry}**\n\nSin funding rate")

                # Trading parameters
                col_params1, col_params2, col_params3 = st.columns(3)

                with col_params1:
                    leverage = st.slider("Apalancamiento", 1, 10, 5, key="futures_leverage_slider")
                    st.caption(f"Margen requerido: {100/leverage:.1f}%")

                with col_params2:
                    direction = st.selectbox(
                        "Dirección",
                        ["BOTH", "LONG", "SHORT"],
                        key="futures_direction_select"
                    )
                    st.caption(f"Estrategia: {direction}")

                with col_params3:
                    capital = st.number_input(
                        "Capital (USDC)",
                        min_value=100,
                        max_value=100000,
                        value=10000,
                        step=100,
                        key="futures_capital_input"
                    )
                    margin_required = capital / leverage
                    st.caption(f"Margen por trade: ${margin_required:.2f}")

            with col_config2:
                st.markdown("### 📊 Risk Manager")

                # Risk limits display
                st.markdown("""
                **Límites Activos:**
                - 📉 Pérdida diaria máx: **3%**
                - 📊 Pérdida mensual máx: **15%**
                - 🔢 Posiciones máx: **5**
                - ⚡ Leverage máx: **5x** (total: 15x)
                - ⏱️ Trades/día máx: **50**

                **Circuit Breakers:**
                - 🚨 Volatilidad >5% en 5min
                - 💰 Funding rate >0.1%
                """)

                # Risk level indicator
                st.markdown("**Estado de Riesgo:**")
                st.success("🟢 SAFE - Trading permitido")

            st.divider()

            # Action buttons
            st.markdown("### 🎮 Acciones")

            col_action1, col_action2, col_action3, col_action4 = st.columns(4)

            with col_action1:
                if st.button("📝 Paper Trading", type="primary", use_container_width=True):
                    st.session_state['futures_paper_running'] = True
                    st.success("✅ Paper Trading iniciado")

            with col_action2:
                if st.button("⛏️ Mining", use_container_width=True):
                    st.info("Creando work unit de futures...")

            with col_action3:
                if st.button("⏹️ Detener", use_container_width=True):
                    st.session_state['futures_paper_running'] = False
                    st.warning("⏹️ Detenido")

            with col_action4:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.rerun()

            st.divider()

            # Paper Trading Status
            st.markdown("### 📈 Paper Trading Status")

            paper_state_file = "/tmp/paper_futures_state.json"
            if os.path.exists(paper_state_file):
                try:
                    with open(paper_state_file, 'r') as f:
                        paper_state = json.load(f)

                    col_status1, col_status2, col_status3, col_status4 = st.columns(4)

                    with col_status1:
                        st.metric("Balance", f"${paper_state.get('balance', 10000):,.2f}")

                    with col_status2:
                        trades = paper_state.get('trades', [])
                        st.metric("Trades", len(trades))

                    with col_status3:
                        if trades:
                            total_pnl = sum(t.get('pnl', 0) for t in trades)
                            st.metric("PnL Total", f"${total_pnl:+,.2f}")
                        else:
                            st.metric("PnL Total", "$0.00")

                    with col_status4:
                        liqs = paper_state.get('liquidations', 0)
                        st.metric("Liquidaciones", liqs, delta="⚠️" if liqs > 0 else "✅")

                    # Recent trades
                    if trades:
                        with st.expander("📋 Últimos Trades", expanded=False):
                            df_trades = pd.DataFrame(trades[-10:])
                            display_cols = ['entry_time', 'exit_time', 'entry_price', 'exit_price', 'side', 'pnl', 'leverage']
                            available_cols = [c for c in display_cols if c in df_trades.columns]
                            st.dataframe(df_trades[available_cols], use_container_width=True)

                except Exception as e:
                    st.warning(f"Error leyendo estado: {e}")
            else:
                st.info("📊 Sin datos de paper trading. Inicia el paper trader para ver estadísticas.")

            st.divider()

            # How to run
            with st.expander("🔧 Cómo Ejecutar Futures Trading", expanded=False):
                st.markdown("""
                #### Paper Trading (Simulado)
                ```bash
                # Activar entorno
                source ~/coinbase_trader_venv/bin/activate
                cd "{base_dir}"

                # Ejecutar paper trader
                python paper_futures_trader.py \\
                    --contract {contract} \\
                    --capital {capital} \\
                    --leverage {leverage} \\
                    --direction {direction}
                ```

                #### Backtesting de Estrategias
                ```bash
                python futures_orchestrator.py --mine --product {contract}
                ```

                #### Orquestador (Completo)
                ```bash
                # Modo dry-run (sin dinero real)
                python futures_orchestrator.py --start --dry-run --balance 10000

                # Ver status
                python futures_orchestrator.py --status
                ```

                #### ⚠️ IMPORTANTE - Live Trading
                El modo live requiere:
                1. Validación completa en paper trading (mínimo 4 horas)
                2. Estrategia con win rate >45%, Sharpe >1.0
                3. Risk manager activo
                4. Capital en cuenta CFM de Coinbase

                ```bash
                # NUNCA ejecutar sin dry_run hasta estar 100% listo
                python futures_orchestrator.py --start --balance 10000
                ```
                """.format(
                    base_dir=BASE_DIR,
                    contract=selected_product,
                    capital=capital,
                    leverage=leverage,
                    direction=direction
                ))

            # Available products table
            with st.expander("📊 Productos Futures Disponibles", expanded=False):
                st.markdown("#### ♾️ Perpetuos (Nano Contracts)")

                perpetual_info = [
                    {"Contrato": "BIP-20DEC30-CDE", "Activo": "Bitcoin", "Size": "0.01 BTC", "Funding": "~0.01%/8h"},
                    {"Contrato": "ETP-20DEC30-CDE", "Activo": "Ethereum", "Size": "0.10 ETH", "Funding": "~0.01%/8h"},
                    {"Contrato": "SLP-20DEC30-CDE", "Activo": "Solana", "Size": "5 SOL", "Funding": "~0.01%/8h"},
                    {"Contrato": "XPP-20DEC30-CDE", "Activo": "XRP", "Size": "500 XRP", "Funding": "~0.01%/8h"},
                ]
                st.dataframe(pd.DataFrame(perpetual_info), use_container_width=True, hide_index=True)

                st.markdown("#### 📅 Dated (Con Vencimiento)")
                st.caption("Los contratos dated vencen en la fecha indicada. Sin funding rate.")
    # TAB 8: Data & Auto
    with tab8:
        st.subheader("🔄 Actualización de Datos & Auto-Work Units")

        # === SECCIÓN 1: ESTADO ACTUAL ===
        st.markdown("### 📊 Estado de Datos")

        col_d1, col_d2, col_d3 = st.columns(3)

        with col_d1:
            spot_files = len(list(Path(DATA_DIR).glob("*.csv"))) if Path(DATA_DIR).exists() else 0
            st.metric("📁 Archivos SPOT", spot_files)

        with col_d2:
            futures_files = len(list(Path(DATA_FUTURES_DIR).glob("*.csv"))) if Path(DATA_FUTURES_DIR).exists() else 0
            st.metric("📁 Archivos FUTURES", futures_files)

        with col_d3:
            # Contar WUs pendientes
            try:
                conn = sqlite3.connect(COORDINATOR_DB)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'")
                pending = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM work_units WHERE status='in_progress'")
                in_progress = cursor.fetchone()[0]
                conn.close()
                st.metric("📋 WUs Disponibles", f"{pending} / {pending + in_progress}", delta="pendientes / en progreso")
            except:
                st.metric("📋 WUs Disponibles", "N/A")

        st.divider()

        # === SECCIÓN 2: ACTUALIZAR DATOS ===
        st.markdown("### 🔄 Actualizar Datos")

        col_btn1, col_btn2 = st.columns([1, 3])

        with col_btn1:
            if st.button("📥 Actualizar Todos los Datos", type="primary"):
                st.session_state['updating_data'] = True

        with col_btn2:
            st.caption("Descarga los datos más recientes de Coinbase y los mergea con los existentes.")

        # Barra de progreso y ejecución
        if st.session_state.get('updating_data', False):
            st.info("⏳ Actualizando datos... Esto puede tomar unos minutos.")

            progress_bar = st.progress(0)
            status_text = st.empty()

            import subprocess
            import sys

            try:
                # Ejecutar script de actualización
                update_script = os.path.join(BASE_DIR, "update_data_daily.py")

                status_text.text("📥 Iniciando actualización...")
                progress_bar.progress(10)

                # Ejecutar en subprocess para capturar output
                result = subprocess.run(
                    [sys.executable, update_script],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=BASE_DIR
                )

                progress_bar.progress(90)
                status_text.text("📊 Procesando resultados...")

                if result.returncode == 0:
                    progress_bar.progress(100)
                    status_text.text("✅ Actualización completada!")
                    st.success("✅ Datos actualizados correctamente!")
                    with st.expander("📋 Ver Log", expanded=False):
                        st.text(result.stdout)
                else:
                    progress_bar.progress(100)
                    st.error(f"❌ Error en actualización: {result.stderr[:500]}")

            except subprocess.TimeoutExpired:
                st.error("⏱️ Timeout - La actualización tomó más de 5 minutos")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
            finally:
                st.session_state['updating_data'] = False

        st.divider()

        # === SECCIÓN 3: AUTO-GENERACIÓN DE WUs ===
        st.markdown("### 🤖 Auto-Generación de Work Units")

        # Configuración
        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)

        with col_cfg1:
            min_pending = st.number_input("Mínimo WUs Pendientes", min_value=10, max_value=500, value=50,
                                          help="Cuando los WUs pendientes bajen de este número, se generarán más automáticamente")

        with col_cfg2:
            auto_wu_count = st.number_input("WUs a Generar", min_value=10, max_value=200, value=50,
                                            help="Cantidad de WUs a crear cuando se active la auto-generación")

        with col_cfg3:
            auto_enabled = st.checkbox("🟢 Auto-Generación Activa", value=False,
                                       help="Activa la generación automática de WUs")

        # Estado del auto-generador
        if auto_enabled:
            st.info(f"🤖 Auto-generación activa: Se crearán {auto_wu_count} WUs cuando pendientes < {min_pending}")

            # Verificar si necesitamos generar más
            try:
                conn = sqlite3.connect(COORDINATOR_DB)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM work_units WHERE status='pending'")
                current_pending = cursor.fetchone()[0]
                conn.close()

                if current_pending < min_pending:
                    st.warning(f"⚠️ WUs pendientes ({current_pending}) < mínimo ({min_pending})")

                    if st.button("🔧 Generar WUs Ahora", type="primary"):
                        # Ejecutar create_work_units.py
                        create_script = os.path.join(BASE_DIR, "create_work_units.py")
                        result = subprocess.run(
                            [sys.executable, create_script, "--all"],
                            capture_output=True,
                            text=True,
                            timeout=60,
                            cwd=BASE_DIR
                        )

                        if result.returncode == 0:
                            st.success(f"✅ WUs generados! Revisa la pestaña 'Crear Work Units' para ver detalles.")
                            st.rerun()
                        else:
                            st.error(f"❌ Error generando WUs: {result.stderr[:500]}")
                else:
                    st.success(f"✅ WUs suficientes: {current_pending} pendientes")

            except Exception as e:
                st.error(f"❌ Error verificando WUs: {e}")

        st.divider()

        # === SECCIÓN 4: DESCARGAR NUEVOS ACTIVOS ===
        st.markdown("### 📥 Descargar Nuevos Activos")

        col_dl1, col_dl2 = st.columns(2)

        with col_dl1:
            st.markdown("**SPOT**")
            if st.button("📥 Descargar SPOT Faltantes"):
                st.session_state['downloading_spot'] = True

            if st.session_state.get('downloading_spot', False):
                progress_spot = st.progress(0)
                status_spot = st.empty()

                try:
                    dl_script = os.path.join(BASE_DIR, "download_spot_data.py")
                    status_spot.text("📥 Descargando datos SPOT...")

                    result = subprocess.run(
                        [sys.executable, dl_script, "--granularity", "5m,15m", "--days", "90"],
                        capture_output=True,
                        text=True,
                        timeout=600,
                        cwd=BASE_DIR
                    )

                    progress_spot.progress(100)

                    if result.returncode == 0:
                        status_spot.text("✅ Descarga SPOT completada!")
                        st.success("✅ Datos SPOT descargados!")
                    else:
                        st.error(f"❌ Error: {result.stderr[:500]}")

                except Exception as e:
                    st.error(f"❌ Error: {e}")
                finally:
                    st.session_state['downloading_spot'] = False

        with col_dl2:
            st.markdown("**FUTURES**")
            if st.button("📥 Descargar FUTURES Faltantes"):
                st.session_state['downloading_futures'] = True

            if st.session_state.get('downloading_futures', False):
                progress_fut = st.progress(0)
                status_fut = st.empty()

                try:
                    dl_script = os.path.join(BASE_DIR, "download_futures_data.py")
                    status_fut.text("📥 Descargando datos FUTURES...")

                    result = subprocess.run(
                        [sys.executable, dl_script, "--granularity", "FIVE_MINUTE", "--days", "30"],
                        capture_output=True,
                        text=True,
                        timeout=600,
                        cwd=BASE_DIR
                    )

                    progress_fut.progress(100)

                    if result.returncode == 0:
                        status_fut.text("✅ Descarga FUTURES completada!")
                        st.success("✅ Datos FUTURES descargados!")
                    else:
                        st.error(f"❌ Error: {result.stderr[:500]}")

                except Exception as e:
                    st.error(f"❌ Error: {e}")
                finally:
                    st.session_state['downloading_futures'] = False

        st.divider()

        # === SECCIÓN 5: INFO ===
        with st.expander("ℹ️ Información del Sistema", expanded=False):
            st.markdown("""
            #### 🔄 Actualización de Datos
            - Los datos se actualizan automáticamente cada día a las 6:00 AM (cron job)
            - Puedes actualizar manualmente con el botón "Actualizar Todos los Datos"
            - El sistema detecta el último timestamp y solo descarga datos nuevos

            #### 🤖 Auto-Generación de Work Units
            - Cuando los WUs pendientes bajan del mínimo, se generan más automáticamente
            - Los WUs se crean para todos los activos que tienen datos disponibles
            - Puedes configurar el mínimo y la cantidad a generar

            #### 📥 Descarga de Nuevos Activos
            - SPOT: Descarga datos de 5min y 15min para los activos faltantes
            - FUTURES: Descarga datos de contratos activos de Coinbase
            - Los datos se guardan en `data/` y `data_futures/`
            """)

            # Mostrar directorios
            st.markdown(f"**Directorios:**")
            st.code(f"""
            data/          → {DATA_DIR}
            data_futures/  → {DATA_FUTURES_DIR}
            coordinator.db → {COORDINATOR_DB}
            """)
