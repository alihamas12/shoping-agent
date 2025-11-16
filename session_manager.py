import threading
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from secure_storage import secure_storage
import requests
from bs4 import BeautifulSoup
import time
from fake_useragent import UserAgent

class BrowserSessionManager:
    def __init__(self):
        self.sessions = {}
        self.personal_info = {}
        self.lock = threading.Lock()
    
    def get_session(self, session_id):
        with self.lock:
            if session_id not in self.sessions:
                options = uc.ChromeOptions()
                options.add_argument("--headless")

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
        """Securely store personal information"""
        encrypted_value = secure_storage.encrypt(value)
        if session_id not in self.personal_info:
            self.personal_info[session_id] = {}
        self.personal_info[session_id][info_type] = encrypted_value
    
    def get_personal_info(self, session_id, info_type):
        """Retrieve personal information"""
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
    
    def execute_action(self, session_id, action, *args, **kwargs):
        driver = self.get_session(session_id)
        try:
            if action == "navigate":
                driver.get(args[0])
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                return f"Navigated to {args[0]}, title: {driver.title}"
            elif action == "fill_form":
                field = driver.find_element(By.ID, args[0])
                field.clear()
                field.send_keys(args[1])
                return f"Filled field '{args[0]}' with '{args[1]}'"
            elif action == "click_element":
                element = driver.find_element(By.ID, args[0])
                element.click()
                return f"Clicked element '{args[0]}'"
            elif action == "search_product":
                search_box = driver.find_element(By.CSS_SELECTOR, "input[type='search'], input[name='q'], input[name='query'], input[name='search'], #search, .search-input, .search-box")
                search_box.clear()
                search_box.send_keys(args[0])
                search_box.send_keys(Keys.RETURN)
                return f"Searched for '{args[0]}' on current site"
            elif action == "add_to_cart":

                add_to_cart_button = driver.find_element(By.CSS_SELECTOR, "#add-to-cart-button, .add-to-cart, .buy-now, .btn-add-to-cart, .cart-button, .add-to-cart-button")
                add_to_cart_button.click()
                return "Added product to cart"
            elif action == "proceed_to_checkout":

                checkout_button = driver.find_element(By.CSS_SELECTOR, "[name*='checkout'], .checkout-button, .proceed-to-checkout, .btn-checkout, #checkout")
                checkout_button.click()
                return "Proceeded to checkout"
            elif action == "fill_address":
                address_field = driver.find_element(By.CSS_SELECTOR, "[name*='address'], #address, .address-field, #address-line1")
                address_field.send_keys(args[0])
                return f"Filled address with {args[0]}"
            elif action == "fill_email":
                email_field = driver.find_element(By.CSS_SELECTOR, "[name*='email'], #email, .email-field")
                email_field.send_keys(args[0])
                return f"Filled email with {args[0]}"
            elif action == "fill_password":
                password_field = driver.find_element(By.CSS_SELECTOR, "[name*='password'], #password, .password-field")
                password_field.send_keys(args[0])
                return f"Filled password"
            elif action == "click_signin":
                signin_button = driver.find_element(By.CSS_SELECTOR, "[name*='login'], #signInSubmit, .signin-button, .login-button")
                signin_button.click()
                return "Clicked sign in"
            elif action == "fill_payment_info":
                card_number_field = driver.find_element(By.CSS_SELECTOR, "[name*='card'], #card-number, .card-number, .payment-field")
                card_number_field.send_keys(args[0])
                return f"Filled card number"
            elif action == "get_title":
                return driver.title
            elif action == "get_url":
                return driver.current_url
            else:
                return f"Unknown action: {action}"
        except Exception as e:
            return f"Error in {action}: {str(e)}"

def search_products(product_name, website="Amazon"):
    """Search for products using Tavily API (works with any e-commerce site) - FIXED"""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        
        query = f"buy {product_name} on {website}"
        response = client.search(query, max_results=5)
        

        if 'results' in response and len(response['results']) > 0:
            products = []
            for result in response['results'][:3]:
                if 'content' in result and result['content']:
                    products.append(result['content'][:200])
            if products:
                return f"Products found: {', '.join(products)}"
        
        return f"No products found for '{product_name}' on {website}"
    except Exception as e:
        return f"Error searching for products: {str(e)}"

def get_product_details(url):
    """Get product details from any e-commerce URL - FIXED"""
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
            return "Could not get product details"
    except Exception as e:
        return f"Error getting product details: {str(e)}"


session_manager = BrowserSessionManager()