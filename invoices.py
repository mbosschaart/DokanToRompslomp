import pandas as pd
import requests
import logging
import json
import time
import sys
from datetime import datetime, timedelta
import os
import math
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
import diskcache as dc
import random

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DEBUG = True

# List of EU countries
EU_COUNTRIES = [
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "PL", "PT", "RO", "SE", "SI", "SK", "NL"
]

# Initialize persistent cache
cache = dc.Cache('./cache')

def log_debug(message):
    """
    Logs debug messages if DEBUG is set to True.

    Args:
        message (str): The message to log.

    Example:
        log_debug("This is a test debug message.")
    """
    if DEBUG:
        logging.debug(message)

# Utility function to round up to the nearest 5 or 10 cents
def round_up_to_nearest_5_or_10_cents(amount):
    """
    Rounds up the given amount to the nearest 5 or 10 cents.

    Args:
        amount (float): The amount to be rounded.

    Returns:
        float: The rounded amount.

    Example:
        round_up_to_nearest_5_or_10_cents(4.33)  # Returns 4.35
    """
    return math.ceil(amount * 20) / 20.0

# Centralized error handling function
def handle_request_error(e, response=None):
    """
    Handles request errors by logging relevant information.

    Args:
        e (Exception): The exception that was raised.
        response (requests.Response, optional): The response object, if available.

    This function is typically used for handling network-related errors, such as connection errors or server errors.
    """
    logging.error(f"Request failed: {e}")
    if response is not None:
        logging.error(f"Response status code: {response.status_code}")
        logging.error(f"Response content: {response.text}")

# Data validation utility function
def validate_order_data(order):
    """
    Validates the order data to ensure all required fields are present.

    Args:
        order (dict): The order data.

    Returns:
        bool: True if the order data is valid, False otherwise.

    Important Fields:
        - 'billing': Ensures billing information is available.
        - 'line_items': Required to create invoice line items.
        - 'id': The order identifier.
        - 'date_created': Used for setting invoice and due dates.
        - 'shipping': Required to determine the destination and applicable VAT rates.
    """
    required_fields = ['billing', 'line_items', 'id', 'date_created', 'shipping']
    for field in required_fields:
        if field not in order:
            logging.error(f"Missing required field in order: {field}")
            return False
    if not order['billing'].get('email'):
        logging.error("Missing email in billing information")
        return False
    return True

# Get template ID based on the shipping country code
def get_template_id(country_code):
    """
    Determines the appropriate template ID for the invoice based on the shipping country.

    Args:
        country_code (str): The shipping country code.

    Returns:
        int: The template ID for the invoice.

    The template IDs are used to differentiate invoice formats based on the destination country:
        - NL: Template for orders shipped within the Netherlands.
        - EU: Template for other EU countries.
        - OTHER: Template for non-EU countries.
    """
    TEMPLATE_IDS = {
        "NL": 217484825,
        "EU": 816357573,
        "OTHER": 911144380
    }
    if country_code == "NL":
        return TEMPLATE_IDS["NL"]
    elif country_code in EU_COUNTRIES:
        return TEMPLATE_IDS["EU"]
    else:
        return TEMPLATE_IDS["OTHER"]

# Configuration Manager
class ConfigManager:
    """
    Manages configuration variables for the script, such as API URLs and credentials.

    Environment Variables:
        - DOKAN_BASE_URL: Base URL for the Dokan API.
        - DOKAN_USERNAME and DOKAN_PASSWORD: Authentication credentials for Dokan.
        - ROMPSLOMP_COMPANY_ID: The company ID for Rompslomp.
        - ROMPSLOMP_API_KEY: API key for accessing Rompslomp.
        - ROMPSLOMP_BASE_URL: Base URL for Rompslomp's API.
        - ROMPSLOMP_CONTACTS_ENDPOINT, ROMPSLOMP_PRODUCTS_ENDPOINT, ROMPSLOMP_INVOICES_ENDPOINT: Specific endpoints for different operations.

    Example .env File:
        DOKAN_BASE_URL=https://example.com/wp-json/dokan/v1
        DOKAN_USERNAME=your_username
        DOKAN_PASSWORD=your_password
        ROMPSLOMP_COMPANY_ID=1234567890
        ROMPSLOMP_API_KEY=your_api_key
    """
    def __init__(self):
        self.dokan_base_url = os.getenv("DOKAN_BASE_URL")
        self.dokan_auth = (os.getenv("DOKAN_USERNAME"), os.getenv("DOKAN_PASSWORD"))
        self.rompslomp_company_id = os.getenv("ROMSLOMP_COMPANY_ID")
        self.rompslomp_base_url = f"{os.getenv('ROMSLOMP_BASE_URL')}/{self.rompslomp_company_id}"
        self.rompslomp_api_key = os.getenv("ROMSLOMP_API_KEY")
        self.rompslomp_headers = {
            "Authorization": f"Bearer {self.rompslomp_api_key}",
            "Content-Type": "application/json"
        }
        self.rompslomp_contacts_url = f"{self.rompslomp_base_url}{os.getenv('ROMSLOMP_CONTACTS_ENDPOINT')}"
        self.rompslomp_products_url = f"{self.rompslomp_base_url}{os.getenv('ROMSLOMP_PRODUCTS_ENDPOINT')}"
        self.rompslomp_invoices_url = f"{self.rompslomp_base_url}{os.getenv('ROMSLOMP_INVOICES_ENDPOINT')}"

# Data Loader for CSV Loading and Caching
class DataLoader:
    """
    Loads and caches data from CSV files, such as VAT mapping and shipping mapping.

    - 'vat_mapping.csv': Contains VAT information for different countries.
    - 'shipping_mapping.csv': Maps shipping methods from Dokan to products in Rompslomp.

    These CSV files must be present in the same directory as the script for proper functioning.
    """
    def __init__(self):
        self.vat_mapping_dict = None
        self.shipping_mapping_dict = None

    def load_vat_mapping(self):
        """
        Loads the VAT mapping from a CSV file.

        Returns:
            dict: A dictionary containing VAT mapping data.
        """
        if self.vat_mapping_dict is None:
            self.vat_mapping_dict = pd.read_csv('vat_mapping.csv').set_index('country_code').to_dict(orient='index')
        return self.vat_mapping_dict

    def load_shipping_mapping(self):
        """
        Loads the shipping mapping from a CSV file.

        Returns:
            dict: A dictionary containing shipping mapping data.
        """
        if self.shipping_mapping_dict is None:
            self.shipping_mapping_dict = pd.read_csv('shipping_mapping.csv').set_index(['Dokan_method', 'price']).to_dict(orient='index')
        return self.shipping_mapping_dict

# VAT Handling Utility Class
class VATHandler:
    """
    Handles VAT calculations and related logic.

    The VATHandler class is responsible for ensuring that the correct VAT rates are applied based on the country of the customer.
    This is crucial for maintaining tax compliance across different regions, especially when dealing with EU and non-EU customers.
    """
    def __init__(self, data_loader):
        self.data_loader = data_loader

    def get_vat_info_for_country(self, country_code):
        """
        Fetches VAT information for a given country code.

        Args:
            country_code (str): The country code.

        Returns:
            tuple: A tuple containing the VAT type ID and VAT rate.
        """
        vat_mapping_dict = self.data_loader.load_vat_mapping()
        vat_info = vat_mapping_dict.get(country_code)
        if vat_info:
            vat_type_id = int(vat_info['vat_type_id'])  # Convert to standard int
            vat_rate = float(vat_info['vat_rate'])  # Convert to standard float
            return vat_type_id, vat_rate
        return None, None

    def determine_vat_for_line_item(self, shipping_country, is_eu_country, total, vat_type_id, price_per_unit):
        """
        Determines the appropriate VAT values for a line item.

        Args:
            shipping_country (str): The shipping country code.
            is_eu_country (bool): Whether the country is in the EU.
            total (float): The total price from Dokan.
            vat_type_id (int): The existing VAT type ID from Rompslomp.
            price_per_unit (float): The price per unit.

        Returns:
            tuple: A tuple containing the updated VAT type ID, VAT rate, and price per unit.
        """
        if is_eu_country:
            vat_type_id, vat_rate = self.get_vat_info_for_country(shipping_country)
        else:
            vat_rate = 0.0  # Non-EU countries have 0% VAT
            vat_type_id = 681363806  # Set to 0% VAT for non-EU countries unless it's a margin product
            price_per_unit = total  # Use the price from Dokan for non-EU orders

        return vat_type_id, vat_rate, price_per_unit

# Dokan API Handler
class DokanAPI:
    """
    Handles interactions with the Dokan API to fetch order data.

    API Endpoints Used:
        - 'get_last_processing_order()': Fetches all processing orders.
        - 'get_order_by_id(order_id)': Fetches a specific order by ID.

    These endpoints are used to retrieve the relevant order information necessary for creating invoices in Rompslomp.
    """
    def __init__(self, config):
        self.base_url = config.dokan_base_url
        self.auth = config.dokan_auth

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10) + wait_exponential(multiplier=random.uniform(0.5, 1.5)), retry=retry_if_exception(lambda e: isinstance(e, requests.RequestException) and e.response is not None and e.response.status_code in [429, 500, 502, 503]))
    def get_last_processing_order(self):
        """
        Fetches the last processing orders from Dokan.

        Returns:
            list: A list of processing orders.
        """
        try:
            if 'last_processing_orders' in cache:
                logging.info("Fetching orders from cache.")
                return cache['last_processing_orders']

            params = {'status': 'processing', 'orderby': 'date', 'order': 'desc', 'per_page': 100}
            response = requests.get(self.base_url, auth=self.auth, params=params)
            self.handle_response(response)
            orders = response.json()
            cache.set('last_processing_orders', orders, expire=3600)  # Cache for 1 hour
            return orders
        except requests.RequestException as e:
            handle_request_error(e)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10) + wait_exponential(multiplier=random.uniform(0.5, 1.5)), retry=retry_if_exception(lambda e: isinstance(e, requests.RequestException) and e.response is not None and e.response.status_code in [429, 500, 502, 503]))
    def get_order_by_id(self, order_id):
        """
        Fetches a specific order by ID from Dokan.

        Args:
            order_id (str): The ID of the order to fetch.

        Returns:
            dict: The order data, or None if the order could not be fetched.
        """
        try:
            cache_key = f'order_{order_id}'
            if cache_key in cache:
                logging.info(f"Fetching order {order_id} from cache.")
                return cache[cache_key]

            url = f"{self.base_url}/{order_id}"
            response = requests.get(url, auth=self.auth)
            self.handle_response(response)
            order = response.json()
            cache.set(cache_key, order, expire=3600)  # Cache for 1 hour
            return order
        except requests.RequestException as e:
            handle_request_error(e)
            return None

    def handle_response(self, response):
        """
        Handles the response from an API request, including error handling for rate limits and server errors.

        Args:
            response (requests.Response): The response object.
        """
        if response.status_code == 429:  # Too many requests
            logging.warning("Rate limit hit. Retrying after delay...")
            time.sleep(10)
            raise requests.exceptions.RequestException("Rate limit hit", response=response)
        elif 500 <= response.status_code < 600:  # Server errors
            logging.error(f"Server error: {response.status_code}")
            raise requests.exceptions.RequestException("Server error", response=response)
        elif response.status_code == 404:
            logging.error("Resource not found")
            return None
        else:
            response.raise_for_status()

# Rompslomp API Handler
class RompslompAPI:
    """
    Handles interactions with the Rompslomp API, including creating contacts, fetching products, and creating invoices.

    Retry Mechanism:
        - Each API call is wrapped in a retry mechanism to handle transient errors like rate limits or server unavailability.
        - Retries are configured with exponential backoff, ensuring requests are spaced out in case of repeated failures.
    """
    def __init__(self, config):
        self.base_url = config.rompslomp_base_url
        self.headers = config.rompslomp_headers
        self.contacts_url = config.rompslomp_contacts_url
        self.products_url = config.rompslomp_products_url
        self.invoices_url = config.rompslomp_invoices_url

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10) + wait_exponential(multiplier=random.uniform(0.5, 1.5)), retry=retry_if_exception(lambda e: isinstance(e, requests.RequestException) and e.response is not None and e.response.status_code in [429, 500, 502, 503]))
    def get_contact_id(self, email):
        """
        Fetches the contact ID from Rompslomp by email address, using caching for efficiency.

        Args:
            email (str): The email address of the contact.

        Returns:
            int: The contact ID if found, otherwise None.
        """
        cache_key = f'contact_{email}'
        if cache_key in cache:
            logging.info(f"Fetching contact ID for {email} from cache.")
            return cache[cache_key]

        try:
            params = {'search[contact_person_email_address]': email}
            response = requests.get(self.contacts_url, headers=self.headers, params=params)
            self.handle_response(response)
            contacts = response.json()
            log_debug(f"Searching for contact with email: {email}")
            log_debug(f"Rompslomp contact search response: {contacts}")
            if 'contacts' in contacts and isinstance(contacts['contacts'], list) and contacts['contacts']:
                for contact in contacts['contacts']:
                    if contact.get('contact_person_email_address') == email:
                        contact_id = contact['id']
                        logging.info(f"Contact found: {contact['name']} with contact ID: {contact_id}")
                        cache.set(cache_key, contact_id, expire=3600)  # Cache for 1 hour
                        return contact_id
            return None
        except requests.RequestException as e:
            handle_request_error(e)
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10) + wait_exponential(multiplier=random.uniform(0.5, 1.5)), retry=retry_if_exception(lambda e: isinstance(e, requests.RequestException) and e.response is not None and e.response.status_code in [429, 500, 502, 503]))
    def get_product_id_by_sku(self, sku):
        """
        Fetches the product ID from Rompslomp by SKU, using caching for efficiency.

        Args:
            sku (str): The SKU of the product.

        Returns:
            tuple: A tuple containing product details such as ID, description, price, VAT rate, etc., or None if the product is not found.
        """
        cache_key = f'product_{sku}'
        if cache_key in cache:
            logging.info(f"Fetching product ID for SKU {sku} from cache.")
            return cache[cache_key]

        try:
            params = {'search[product_codes][]': sku}
            response = requests.get(self.products_url, headers=self.headers, params=params)
            self.handle_response(response)
            products = response.json()
            log_debug(f"Searching for product with product_code: {sku}")
            log_debug(f"Rompslomp product search response: {products}")
            if 'products' in products and isinstance(products['products'], list) and products['products']:
                for product in products['products']:
                    if product.get('invoice_line', {}).get('product_code') == sku:
                        logging.info(f"Product found with product_code (SKU): {sku} and product ID: {product['id']}")
                        price_per_unit = product['invoice_line'].get('price_per_unit', 0)
                        price_with_vat = product['invoice_line'].get('price_with_vat', 0)
                        vat_rate = product['invoice_line'].get('vat_rate', '0.21')
                        vat_type_id = product['invoice_line'].get('vat_type_id', None)
                        account_id = product['invoice_line'].get('account_id', None)
                        account_path = product['invoice_line'].get('account_path', None)

                        product_data = (
                            product['id'],
                            product['invoice_line'].get('description'),
                            price_per_unit,
                            price_with_vat,
                            vat_rate,
                            vat_type_id,
                            account_id,
                            account_path
                        )
                        cache.set(cache_key, product_data, expire=3600)  # Cache for 1 hour
                        return product_data
            # If no product found, try removing the last '-' and retry
            if '-' in sku:
                new_sku = sku.rsplit('-', 1)[0]
                logging.info(f"Retrying with modified SKU: {new_sku}")
                return self.get_product_id_by_sku(new_sku)
            return None, None, None, None, None, None, None, None
        except requests.RequestException as e:
            handle_request_error(e)
            return None, None, None, None, None, None, None, None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10) + wait_exponential(multiplier=random.uniform(0.5, 1.5)), retry=retry_if_exception(lambda e: isinstance(e, requests.RequestException) and e.response is not None and e.response.status_code in [429, 500, 502, 503]))
    def create_contact(self, contact_data):
        """
        Creates a new contact in Rompslomp.

        Args:
            contact_data (dict): The contact data to be created.

        Returns:
            dict: The response data containing the created contact information, or None if the contact could not be created.
        """
        try:
            response = requests.post(self.contacts_url, headers=self.headers, data=json.dumps(contact_data))
            self.handle_response(response)
            return response.json()
        except requests.RequestException as e:
            handle_request_error(e)
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10) + wait_exponential(multiplier=random.uniform(0.5, 1.5)), retry=retry_if_exception(lambda e: isinstance(e, requests.RequestException) and e.response is not None and e.response.status_code in [429, 500, 502, 503]))
    def create_invoice(self, invoice_data):
        """
        Creates a new sales invoice in Rompslomp.

        Args:
            invoice_data (dict): The invoice data to be created.

        Returns:
            dict: The response data containing the created invoice information, or None if the invoice could not be created.
        """
        try:
            response = requests.post(self.invoices_url, headers=self.headers, json={"sales_invoice": invoice_data})
            self.handle_response(response)
            return response.json()
        except requests.RequestException as e:
            handle_request_error(e)
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10) + wait_exponential(multiplier=random.uniform(0.5, 1.5)), retry=retry_if_exception(lambda e: isinstance(e, requests.RequestException) and e.response is not None and e.response.status_code in [429, 500, 502, 503]))
    def patch_invoice(self, invoice_id, patch_data):
        """
        Patches an existing sales invoice in Rompslomp.

        Args:
            invoice_id (int): The ID of the invoice to be patched.
            patch_data (dict): The data to patch in the invoice.
        """
        try:
            patch_url = f"{self.invoices_url}/{invoice_id}"
            response = requests.patch(patch_url, headers=self.headers, json=patch_data)
            self.handle_response(response)
            logging.info(f"Invoice {invoice_id} successfully patched with correct price_per_unit values.")
        except requests.RequestException as e:
            handle_request_error(e)

    def handle_response(self, response):
        """
        Handles the response from an API request, including error handling for rate limits and server errors.

        Args:
            response (requests.Response): The response object.
        """
        if response.status_code == 429:  # Too many requests
            logging.warning("Rate limit hit. Retrying after delay...")
            time.sleep(10)
            raise requests.exceptions.RequestException("Rate limit hit", response=response)
        elif 500 <= response.status_code < 600:  # Server errors
            logging.error(f"Server error: {response.status_code}")
            raise requests.exceptions.RequestException("Server error", response=response)
        elif response.status_code == 404:
            logging.error("Resource not found")
            return None
        else:
            response.raise_for_status()

# Invoice Processor
class InvoiceProcessor:
    """
    Processes invoices by interacting with Dokan and Rompslomp APIs.

    To improve maintainability, consider breaking down 'create_concept_invoice()' into smaller methods such as:
        - 'create_or_get_contact()': Handle contact creation or retrieval.
        - 'prepare_invoice_lines()': Prepare the line items for the invoice.
        - 'submit_invoice()': Create the invoice in Rompslomp.

    This will improve readability and make the code easier to test and debug.
    """
    def __init__(self, dokan_api, rompslomp_api, vat_handler, data_loader):
        self.dokan_api = dokan_api
        self.rompslomp_api = rompslomp_api
        self.vat_handler = vat_handler
        self.data_loader = data_loader  # Store the data_loader as an instance variable
        self.success_count = 0
        self.failure_count = 0
        self.failed_orders = []
        self.invoices_with_issues = []

    def create_concept_invoice(self, order):
        """
        Creates a concept invoice for a given order.

        Args:
            order (dict): The order data.
        """
        if not validate_order_data(order):
            self.failure_count += 1
            self.failed_orders.append(order['id'])
            return

        try:
            # Extract customer information from Dokan order
            customer = order['billing']
            name = f"{customer['first_name']} {customer['last_name']}"
            email = customer['email']

            # Check if contact exists in Rompslomp
            contact_id = self.rompslomp_api.get_contact_id(email)
            if not contact_id:
                logging.info(f"No contact found with email: {email}. Creating new contact.")
                contact_data = {
                    "contact": {
                        "is_individual": True if 'company' not in customer or not customer['company'] else False,
                        "is_supplier": True if 'company' in customer and customer['company'] else False,
                        "company_name": customer['company'] if 'company' in customer and customer['company'] else None,
                        "contact_person_name": f"{customer['first_name']} {customer['last_name']}",
                        "contact_person_email_address": email,
                        "address": f"{customer.get('address_1', '')}, {customer.get('address_2', '')}" if customer.get('address_2', '') else customer.get('address_1', ''),
                        "zipcode": customer.get('postcode', ''),
                        "city": customer.get('city', ''),
                        "country_code": customer.get('country', 'NL'),  # Default to NL if country is missing
                        "phone": customer.get('phone', None)
                    }
                }
                contact = self.rompslomp_api.create_contact(contact_data)
                if contact and 'contact' in contact and 'id' in contact['contact']:
                    contact_id = contact['contact']['id']
                    logging.info(f"Contact created successfully with ID: {contact_id}")
                else:
                    logging.error(f"Unexpected response format: {contact}")
                    self.failure_count += 1
                    self.failed_orders.append(order['id'])
                    return

            # Prepare invoice lines
            lines = []

            # Add product lines
            for item in order['line_items']:
                sku = item.get('sku')
                product_id, product_description, price_per_unit, price_with_vat, vat_rate, vat_type_id, account_id, account_path = self.rompslomp_api.get_product_id_by_sku(sku)
                if not product_id:
                    logging.error(f"Product could not be matched, skipping invoice creation for SKU: {sku}")
                    self.failure_count += 1
                    self.failed_orders.append(order['id'])
                    return

                shipping_country = order['shipping'].get('country', 'NL')
                is_eu_country = shipping_country in EU_COUNTRIES
                vat_type_id, vat_rate, price_per_unit = self.vat_handler.determine_vat_for_line_item(
                    shipping_country, is_eu_country, item.get('price', 0), vat_type_id, price_per_unit
                )

                lines.append({
                    "description": product_description if product_description else item['name'],
                    "quantity": item['quantity'],
                    "price_per_unit": price_per_unit,
                    "vat_rate": vat_rate,
                    "vat_type_id": vat_type_id,
                    "product_id": product_id,
                    "account_id": account_id,
                    "account_path": account_path
                })

            # Add shipping line
            shipping_mapping_dict = self.data_loader.load_shipping_mapping()
            for shipping_line in order.get('shipping_lines', []):
                method_title = shipping_line.get('method_title', '')
                total = float(shipping_line.get('total', 0))
                matching_row = shipping_mapping_dict.get((method_title, total))

                if matching_row:
                    sku = matching_row['SKU']
                    product_id, product_description, price_per_unit, price_with_vat, vat_rate, vat_type_id, account_id, account_path = self.rompslomp_api.get_product_id_by_sku(sku)
                    if product_id:
                        shipping_country = order['shipping'].get('country', 'NL')
                        is_eu_country = shipping_country in EU_COUNTRIES
                        vat_type_id, vat_rate, price_per_unit = self.vat_handler.determine_vat_for_line_item(
                            shipping_country, is_eu_country, total, vat_type_id, price_per_unit
                        )

                        lines.append({
                            "description": product_description if product_description else method_title,
                            "quantity": 1,
                            "price_per_unit": price_per_unit,
                            "vat_rate": vat_rate,
                            "vat_type_id": vat_type_id,
                            "product_id": product_id,
                            "account_id": account_id,
                            "account_path": account_path
                        })
                    else:
                        logging.error(f"Shipping method could not be matched, skipping shipping line for method: {method_title}")

            # Prepare invoice data
            invoice_date = order['date_created'].split('T')[0]  # Get the date from the Dokan order
            due_date = (datetime.strptime(invoice_date, '%Y-%m-%d') + timedelta(days=30)).strftime('%Y-%m-%d')
            invoice_data = {
                "contact_id": contact_id,
                "template_id": get_template_id(order['shipping'].get('country', 'NL')),
                "payment_reference": order['id'],
                "description": order['id'],
                "invoice_lines": lines,
                "date": invoice_date,
                "due_date": due_date
            }

            # Create the invoice in Rompslomp
            invoice = self.rompslomp_api.create_invoice(invoice_data)
            if not invoice:
                self.failure_count += 1
                self.failed_orders.append(order['id'])
                return

            self.success_count += 1
            logging.info(f"Invoice created successfully for order {order['id']}")

        except Exception as e:
            logging.error(f"Failed to create invoice for order {order['id']}: {e}")
            self.failure_count += 1
            self.failed_orders.append(order['id'])

# Main process
if __name__ == "__main__":
    # Main process:
    # - Initializes configuration, API handlers, and data loaders.
    # - If an order ID is provided as an argument, processes only that order.
    # - Otherwise, processes all processing orders from Dokan.
    # - Logs a summary of successful and failed invoices at the end.

    # Initialize configuration and APIs
    config = ConfigManager()
    dokan_api = DokanAPI(config)
    rompslomp_api = RompslompAPI(config)
    data_loader = DataLoader()
    vat_handler = VATHandler(data_loader)

    invoice_processor = InvoiceProcessor(dokan_api, rompslomp_api, vat_handler, data_loader)

    if len(sys.argv) > 1:
        # If an order ID is provided, process only that order
        order_id = sys.argv[1]
        logging.info(f"Fetching order with ID {order_id} from Dokan...")
        order = dokan_api.get_order_by_id(order_id)
        if order:
            logging.info(f"Creating invoice for order {order['id']}...")
            try:
                invoice_processor.create_concept_invoice(order)
            except Exception as e:
                logging.error(f"Failed to create invoice for order {order['id']}: {e}")
        else:
            logging.info(f"Order with ID {order_id} not found.")
    else:
        # Otherwise, process all processing orders
        logging.info("Fetching all processing orders from Dokan...")
        orders = dokan_api.get_last_processing_order()
        if orders:
            for order in orders:
                logging.info(f"Creating invoice for order {order['id']}...")
                try:
                    invoice_processor.create_concept_invoice(order)
                except Exception as e:
                    logging.error(f"Failed to create invoice for order {order['id']}: {e}")
                    continue
        else:
            logging.info("No processing orders found.")

    # Summary of results
    logging.info(f"Summary: {invoice_processor.success_count} invoices processed successfully, {invoice_processor.failure_count} invoices failed.")
    if invoice_processor.failed_orders:
        logging.info(f"Failed orders: {', '.join(map(str, invoice_processor.failed_orders))}")
    if invoice_processor.invoices_with_issues:
        logging.info(f"Invoices with line item issues: {', '.join(map(str, invoice_processor.invoices_with_issues))}")
