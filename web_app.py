import streamlit as st
from langchain.tools import StructuredTool
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import requests
import json
from pydantic import BaseModel, Field
from typing import Optional
import os
import threading
from cryptography.fernet import Fernet
import base64
from fake_useragent import UserAgent
import undetected_chromedriver as uc
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from dotenv import load_dotenv
load_dotenv()

class SecureStorage:
    def __init__(self):
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            key = Fernet.generate_key()
            print(f"Set ENCRYPTION_KEY in .env: {key.decode()}")
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, data):
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data):
        return self.cipher.decrypt(encrypted_data.encode()).decode()

secure_storage = SecureStorage()

class BrowserSessionManager:
    def __init__(self):
        self.sessions = {}
        self.personal_info = {}
        self.lock = threading.Lock()

    def get_session(self, session_id):
        with self.lock:
            if session_id not in self.sessions:
                options = uc.ChromeOptions()
                options.add_argument("--disable-web-security")
                options.add_argument("--allow-running-insecure-content")
                options.add_argument("--disable-extensions")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--remote-debugging-port=9222")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                ua = UserAgent()
                user_agent = ua.random
                options.add_argument(f"--user-agent={user_agent}")
                driver = uc.Chrome(options=options, use_subprocess=False)
                driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                self.sessions[session_id] = driver
            return self.sessions[session_id]

    def store_personal_info(self, session_id, info_type, value):
        encrypted_value = secure_storage.encrypt(value)
        if session_id not in self.personal_info:
            self.personal_info[session_id] = {}
        self.personal_info[session_id][info_type] = encrypted_value

    def get_personal_info(self, session_id, info_type):
        if session_id in self.personal_info and info_type in self.personal_info[session_id]:
            encrypted_value = self.personal_info[session_id][info_type]
            return secure_storage.decrypt(encrypted_value)
        return None

    def close_session(self, session_id):
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].quit()
                del self.sessions[session_id]
            if session_id in self.personal_info:
                del self.personal_info[session_id]

session_manager = BrowserSessionManager()

def search_products_func(product_name, website="Amazon"):
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        query = f"buy {product_name} on {website}"
        response = client.search(query, max_results=3)
        if 'results' in response and len(response['results']) > 0:
            products = []
            for result in response['results'][:3]:
                if 'content' in result and result['content']:
                    products.append(result['content'][:200])
            if products:
                return f"Products found: {', '.join(products)}"
        return f"No products found for '{product_name}' on {website}."
    except Exception as e:
        return f"Error searching for products: {str(e)}"

def get_product_details_func(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find('title')
        if title:
            return f"Product: {title.get_text(strip=True)}"
        else:
            return "Could not get product details."
    except Exception as e:
        return f"Error getting product details: {str(e)}"

def navigate_func(url: str, session_id: str) -> str:
    try:
        driver = session_manager.get_session(session_id)
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        return f"Navigated to {url}, title: {driver.title}"
    except Exception as e:
        return f"Error navigating to {url}: {str(e)}"

def fill_form_func(session_id: str, field_id: str, value: str) -> str:
    try:
        driver = session_manager.get_session(session_id)
        field = driver.find_element(By.ID, field_id)
        field.clear()
        field.send_keys(value)
        return f"Filled field '{field_id}' with '{value}'."
    except Exception as e:
        return f"Error filling form: {str(e)}"

def click_element_func(session_id: str, element_id: str) -> str:
    try:
        driver = session_manager.get_session(session_id)
        element = driver.find_element(By.ID, element_id)
        element.click()
        return f"Clicked element '{element_id}'."
    except Exception as e:
        return f"Error clicking element: {str(e)}"

def store_personal_info_func(session_id: str, info_type: str, value: str) -> str:
    session_manager.store_personal_info(session_id, info_type, value)
    return f"Stored {info_type} securely for session {session_id}."

def get_personal_info_func(session_id: str, info_type: str) -> str:
    value = session_manager.get_personal_info(session_id, info_type)
    if value:
        return f"Retrieved {info_type}: {value}"
    return f"No {info_type} found for session {session_id}."

def purchase_product_func(session_id: str, product_name: str, website: str = "Amazon") -> str:

    email = session_manager.get_personal_info(session_id, "email")
    phone = session_manager.get_personal_info(session_id, "phone")
    name = session_manager.get_personal_info(session_id, "name")
    address = session_manager.get_personal_info(session_id, "address")
    credit_card = session_manager.get_personal_info(session_id, "credit_card")
    password = session_manager.get_personal_info(session_id, "password")

    if not all([email, phone, name, address, credit_card, password]):
        missing = [k for k, v in {
            "email": email, "phone": phone, "name": name,
            "address": address, "credit_card": credit_card, "password": password
        }.items() if not v]
        return f"Cannot purchase. Missing information: {', '.join(missing)}. Please store this information first."
    return f"Simulated purchase: Would buy {product_name} from {website} for {name} ({email}) using stored address and payment method. This is a simulation."

def scrape_func(url: str) -> str:
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        response = session.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text()
        return text[:1500]
    except Exception as e:
        return f"Error scraping {url}: {str(e)}"

def web_search_func(query: str) -> str:
    try:
        url = "https://google.serper.dev/search"
        payload = json.dumps({"q": query})
        headers = {'X-API-KEY': os.getenv("SERPER_API_KEY"), 'Content-Type': 'application/json'}
        session = requests.Session()
        response = session.post(url, headers=headers, data=payload)
        results = response.json()
        return str(results.get("organic", [])[:2])
    except Exception as e:
        return f"Serper search error: {str(e)}"

def tavily_search_func(query: str) -> str:
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        response = client.search(query, max_results=2)
        return str(response)
    except Exception as e:
        return f"Tavily search error: {str(e)}"
class NavigateInput(BaseModel):
    url: str = Field(description="URL to navigate to")
    session_id: str = Field(description="Session ID for persistent browser state")

class FillFormInput(BaseModel):
    session_id: str = Field(description="Session ID for persistent browser state")
    field_id: str = Field(description="ID of the input field")
    value: str = Field(description="Value to fill in")

class ClickElementInput(BaseModel):
    session_id: str = Field(description="Session ID for persistent browser state")
    element_id: str = Field(description="ID of the element to click")

class StorePersonalInfoInput(BaseModel):
    session_id: str = Field(description="Session ID for persistent browser state")
    info_type: str = Field(description="Type of personal info (email, phone, name, etc.)")
    value: str = Field(description="Personal information value")

class GetPersonalInfoInput(BaseModel):
    session_id: str = Field(description="Session ID for persistent browser state")
    info_type: str = Field(description="Type of personal info to retrieve")

class SearchProductInput(BaseModel):
    product_name: str = Field(description="Name of the product to search for")
    website: Optional[str] = Field(description="Website to search on (Amazon, BestBuy, etc.)", default="Amazon")

class GetProductDetailsInput(BaseModel):
    url: str = Field(description="URL of the product page")

class PurchaseProductInput(BaseModel):
    session_id: str = Field(description="Session ID for persistent browser state")
    product_name: str = Field(description="Name of the product to purchase")
    website: Optional[str] = Field(description="Website to purchase from (Amazon, BestBuy, etc.)", default="Amazon")

class ScrapeInput(BaseModel):
    url: str = Field(description="URL to scrape content from")

navigate = StructuredTool.from_function(
    func=navigate_func,
    name="navigate",
    description="Navigate to a URL in browser with persistent session",
    args_schema=NavigateInput,
)

fill_form = StructuredTool.from_function(
    func=fill_form_func,
    name="fill_form",
    description="Fill a form field on a webpage",
    args_schema=FillFormInput,
)

click_element = StructuredTool.from_function(
    func=click_element_func,
    name="click_element",
    description="Click an element on a webpage",
    args_schema=ClickElementInput,
)

store_personal_info = StructuredTool.from_function(
    func=store_personal_info_func,
    name="store_personal_info",
    description="Securely store personal information",
    args_schema=StorePersonalInfoInput,
)

get_personal_info = StructuredTool.from_function(
    func=get_personal_info_func,
    name="get_personal_info",
    description="Retrieve personal information",
    args_schema=GetPersonalInfoInput,
)

search_product = StructuredTool.from_function(
    func=search_products_func,
    name="search_product",
    description="Search for products using Tavily API (works with any e-commerce site)",
    args_schema=SearchProductInput,
)

get_product_details = StructuredTool.from_function(
    func=get_product_details_func,
    name="get_product_details",
    description="Get product details from any e-commerce URL",
    args_schema=GetProductDetailsInput,
)

purchase_product = StructuredTool.from_function(
    func=purchase_product_func,
    name="purchase_product",
    description="Automate the purchase of a product on any e-commerce site (simulated)",
    args_schema=PurchaseProductInput,
)

scrape = StructuredTool.from_function(
    func=scrape_func,
    name="scrape",
    description="Scrape content from a webpage",
    args_schema=ScrapeInput,
)

web_search = StructuredTool.from_function(
    func=web_search_func,
    name="web_search",
    description="Search the web using Serper API",
)

tavily_search = StructuredTool.from_function(
    func=tavily_search_func,
    name="tavily_search",
    description="Search using Tavily API",
)

tools = [
    navigate, fill_form, click_element, store_personal_info, get_personal_info,
    search_product, get_product_details, purchase_product, scrape,
    web_search, tavily_search
]

google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set")

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=google_api_key)

agent_executor = create_react_agent(model, tools)

def main():
    st.set_page_config(page_title="AI Automation Agent", layout="wide")

    st.markdown("""
    <style>
    :root {
        --text-color: #262730;
        --bg-color: #ffffff;
        --user-bg: #e3f2fd;
        --agent-bg: #f0f2f6;
        --info-bg: #e8f5e8;
        --border-color: #cccccc;
    }
    body {
        color: var(--text-color) !important;
        background-color: var(--bg-color) !important;
    }
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4 !important;
        text-align: center;
        margin-bottom: 1rem;
    }
    .chat-container {
        height: 500px;
        overflow-y: auto;
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: var(--bg-color);
        color: var(--text-color);
    }
    .message {
        padding: 0.5rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        word-wrap: break-word;
    }
    .user-message {
        background-color: var(--user-bg);
        text-align: right;
        color: var(--text-color) !important;
    }
    .agent-message {
        background-color: var(--agent-bg);
        text-align: left;
        color: var(--text-color) !important;
    }
    .info-box {
        background-color: var(--info-bg);
        border-left: 5px solid #4caf50;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-radius: 4px;
        color: var(--text-color) !important;
        font-size: 0.9rem;
    }
    .stMarkdown, .stText, .stHeader, .stSubheader, .stCaption {
        color: var(--text-color) !important;
    }
    .stTextInput > div > div > input {
        color: var(--text-color) !important;
        background-color: var(--bg-color) !important;
    }
    .stSelectbox > div > div {
        color: var(--text-color) !important;
    }
    .stButton > button {
        color: var(--text-color) !important;
        background-color: #f0f2f6 !important;
    }
    [data-testid="stSidebar"] {
        background-color: #f0f2f6 !important;
    }
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stText,
    [data-testid="stSidebar"] .stHeader,
    [data-testid="stSidebar"] .stSubheader {
        color: var(--text-color) !important;
    }
    .tool-call-display {
        font-style: italic;
        color: #888888;
        font-size: 0.85em;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="main-header">AI Automation Agent</h1>', unsafe_allow_html=True)


    if 'messages' not in st.session_state:
        st.session_state.messages = [AIMessage(content="Hello! I am your AI automation assistant. How can I help you today?")]
    if 'session_id' not in st.session_state:
        st.session_state.session_id = "default_session"

    st.markdown("""
    <div class="info-box">
    <strong>Instructions:</strong><br>
    - Store personal info (email, phone, address, etc.) using the sidebar.<br>
    - Ask me to search for or purchase items from e-commerce sites (Amazon, BestBuy, etc.).<br>
    - Example: "Buy a laptop on Amazon" (requires stored info).
    </div>
    """, unsafe_allow_html=True)

    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            if isinstance(msg, HumanMessage):
                st.markdown(f'<div class="message user-message">You: {msg.content}</div>', unsafe_allow_html=True)
            elif isinstance(msg, AIMessage):
                st.markdown(f'<div class="message agent-message">Agent: {msg.content}</div>', unsafe_allow_html=True)

    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_input("Your message:", key="input_text")
        submit_button = st.form_submit_button("Send")

    if submit_button and user_input:

        st.session_state.messages.append(HumanMessage(content=user_input))

        config = {"configurable": {"thread_id": st.session_state.session_id}}

        try:
            response_messages = []
            tool_calls_log = []
            for chunk in agent_executor.stream(
                {"messages": st.session_state.messages, "session_id": st.session_state.session_id}, 
                config
            ):
                if "agent" in chunk:
                    agent_chunk = chunk["agent"]
                    if "messages" in agent_chunk:
                        response_messages.extend(agent_chunk["messages"])
                elif "tools" in chunk:

                    pass

            final_response = ""
            for msg in response_messages:
                if hasattr(msg, 'content') and msg.content:
                    final_response += msg.content + "\n"

            if final_response.strip():
                st.session_state.messages.append(AIMessage(content=final_response.strip()))

        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            st.session_state.messages.append(AIMessage(content=error_msg))

        st.rerun()

    with st.sidebar:
        st.header(" Personal Information")
        st.markdown("Store your details here:")

        with st.form(key="info_form", clear_on_submit=True):
            info_type = st.selectbox("Info Type", ["name", "email", "phone", "address", "credit_card", "password"])
            info_value = st.text_input("Value", type="default" if info_type not in ["credit_card", "password"] else "password")
            store_btn = st.form_submit_button("Store")

        if store_btn and info_value:
            store_msg = f"Store my {info_type} as {info_value}"
            st.session_state.messages.append(HumanMessage(content=store_msg))
            config = {"configurable": {"thread_id": st.session_state.session_id}}

            result = store_personal_info_func(st.session_state.session_id, info_type, info_value)
            st.session_state.messages.append(AIMessage(content=result))
            st.success(f"Stored {info_type} successfully!")
            st.rerun()

        st.subheader("Stored Info")
        info_types = ["name", "email", "phone", "address", "credit_card", "password"]
        for it in info_types:
            val = session_manager.get_personal_info(st.session_state.session_id, it)
            if val:
                display_val = '*' * len(val) if it in ['credit_card', 'password'] else val
                st.write(f"**{it.title()}:** {display_val}")
            else:
                st.write(f"**{it.title()}:** Not stored")

if __name__ == "__main__":
    main()