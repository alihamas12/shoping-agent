from langchain.tools import tool
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
import json
from pydantic import BaseModel, Field
from typing import Optional, Type
import openai
import os
from session_manager import session_manager, search_products, get_product_details


openai.api_key = os.getenv("OPENAI_API_KEY")

class NavigateInput(BaseModel):
    url: str = Field(description="URL to navigate to")
    session_id: str = Field(description="Session ID for persistent browser state")

@tool("navigate", args_schema=NavigateInput)
def navigate(url: str, session_id: str) -> str:
    """Navigate to a URL in browser with persistent session"""
    return session_manager.execute_action(session_id, "navigate", url)

class FillFormInput(BaseModel):
    session_id: str = Field(description="Session ID for persistent browser state")
    field_id: str = Field(description="ID of the input field")
    value: str = Field(description="Value to fill in")

@tool("fill_form", args_schema=FillFormInput)
def fill_form(session_id: str, field_id: str, value: str) -> str:
    """Fill a form field on a webpage"""
    return session_manager.execute_action(session_id, "fill_form", field_id, value)

class ClickElementInput(BaseModel):
    session_id: str = Field(description="Session ID for persistent browser state")
    element_id: str = Field(description="ID of the element to click")

@tool("click_element", args_schema=ClickElementInput)
def click_element(session_id: str, element_id: str) -> str:
    """Click an element on a webpage"""
    return session_manager.execute_action(session_id, "click_element", element_id)

class StorePersonalInfoInput(BaseModel):
    session_id: str = Field(description="Session ID for persistent browser state")
    info_type: str = Field(description="Type of personal info (email, phone, name, etc.)")
    value: str = Field(description="Personal information value")

@tool("store_personal_info", args_schema=StorePersonalInfoInput)
def store_personal_info(session_id: str, info_type: str, value: str) -> str:
    """Securely store personal information"""
    session_manager.store_personal_info(session_id, info_type, value)
    return f"Stored {info_type} securely for session {session_id}"

class GetPersonalInfoInput(BaseModel):
    session_id: str = Field(description="Session ID for persistent browser state")
    info_type: str = Field(description="Type of personal info to retrieve")

@tool("get_personal_info", args_schema=GetPersonalInfoInput)
def get_personal_info(session_id: str, info_type: str) -> str:
    """Retrieve personal information"""
    value = session_manager.get_personal_info(session_id, info_type)
    if value:
        return f"Retrieved {info_type}: {value}"
    return f"No {info_type} found for session {session_id}"

class SearchProductInput(BaseModel):
    product_name: str = Field(description="Name of the product to search for")
    website: Optional[str] = Field(description="Website to search on (Amazon, BestBuy, etc.)", default="Amazon")

@tool("search_product", args_schema=SearchProductInput)
def search_product(product_name: str, website: str = "Amazon") -> str:
    """Search for products using Tavily API (works with any e-commerce site) - FIXED"""
    return search_products(product_name, website)

class GetProductDetailsInput(BaseModel):
    url: str = Field(description="URL of the product page")

@tool("get_product_details", args_schema=GetProductDetailsInput)
def get_product_details(url: str) -> str:
    """Get product details from any e-commerce URL - FIXED"""
    return get_product_details(url)

class PurchaseProductInput(BaseModel):
    session_id: str = Field(description="Session ID for persistent browser state")
    product_name: str = Field(description="Name of the product to purchase")
    website: Optional[str] = Field(description="Website to purchase from (Amazon, BestBuy, etc.)", default="Amazon")

@tool("purchase_product", args_schema=PurchaseProductInput)
def purchase_product(session_id: str, product_name: str, website: str = "Amazon") -> str:
    """Automate the purchase of a product on any e-commerce site - FIXED"""
    try:

        email = session_manager.get_personal_info(session_id, "email")
        phone = session_manager.get_personal_info(session_id, "phone")
        name = session_manager.get_personal_info(session_id, "name")
        address = session_manager.get_personal_info(session_id, "address")
        credit_card = session_manager.get_personal_info(session_id, "credit_card")
        password = session_manager.get_personal_info(session_id, "password")
        
        if not all([email, phone, name, address, credit_card, password]):
            missing_info = []
            if not email: missing_info.append("email")
            if not phone: missing_info.append("phone")
            if not name: missing_info.append("name")
            if not address: missing_info.append("address")
            if not credit_card: missing_info.append("credit card")
            if not password: missing_info.append("password")
            
            return f"Cannot purchase. Missing information: {', '.join(missing_info)}. Please provide this information first."
        
        website_urls = {
            "amazon": "https://www.amazon.com",
            "bestbuy": "https://www.bestbuy.com",
            "walmart": "https://www.walmart.com",
            "ebay": "https://www.ebay.com",
            "target": "https://www.target.com",
            "costco": "https://www.costco.com",
            "newegg": "https://www.newegg.com",
            "daraz": "https://www.daraz.pk"  
        }
        
        website_lower = website.lower()
        if website_lower in website_urls:
            session_manager.execute_action(session_id, "navigate", website_urls[website_lower])
        else:

            session_manager.execute_action(session_id, "navigate", website_urls["amazon"])

        session_manager.execute_action(session_id, "search_product", product_name)
        

        return f"Would purchase {product_name} from {website} for {name}. The actual purchase would involve: logging in with {email}, proceeding to checkout, using stored shipping address ({address}) and payment method (ending in {credit_card[-4:]}). This is a simulation - no actual purchase was made."
    except Exception as e:
        return f"Error during purchase process: {str(e)}"

class ScrapeInput(BaseModel):
    url: str = Field(description="URL to scrape content from")

@tool("scrape", args_schema=ScrapeInput)
def scrape(url: str) -> str:
    """Scrape content from a webpage - FIXED"""
    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        response = session.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text()
        return text[:2000] 
    except Exception as e:
        return f"Error scraping {url}: {str(e)}"

@tool("web_search")
def web_search(query: str) -> str:
    """Search the web using Serper API - FIXED"""
    try:
        url = "https://google.serper.dev/search"
        payload = json.dumps({
            "q": query
        })
        headers = {
            'X-API-KEY': os.getenv("SERPER_API_KEY"),
            'Content-Type': 'application/json'
        }

        session = requests.Session()
        response = session.post(url, headers=headers, data=payload)
        results = response.json()
        return str(results.get("organic", [])[:3])
    except Exception as e:
        return f"Serper search error: {str(e)}"

@tool("tavily_search")
def tavily_search(query: str) -> str:
    """Search using Tavily API - FIXED"""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        response = client.search(query, max_results=3)
        return str(response)
    except Exception as e:
        return f"Tavily search error: {str(e)}"

@tool("openai_completion")
def openai_completion(prompt: str) -> str:
    """Generate text using OpenAI API"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"OpenAI error: {str(e)}"

tools = [navigate, fill_form, click_element, store_personal_info, get_personal_info, search_product, get_product_details, purchase_product, scrape, web_search, tavily_search, openai_completion]