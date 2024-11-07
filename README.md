# README.md

## Overview

This script is designed to synchronize invoices between a Dokan-powered e-commerce store and Rompslomp, a financial management system. The script processes orders from Dokan, retrieves or creates customer details and product information in Rompslomp, and then generates sales invoices based on the orders. This solution is particularly useful for automating the accounting process and maintaining accurate records, which helps reduce manual work and human error.

The script integrates multiple components, including API requests, caching, retry mechanisms, error handling, and logging, to create a reliable and scalable invoicing automation solution.

## Purpose

The primary purpose of the script is to streamline and automate the process of creating invoices for orders placed in a Dokan e-commerce store. By integrating with Rompslomp, this script:
- Retrieves new orders from Dokan ("processing" orders).
- Finds or creates customer records in Rompslomp.
- Looks up or creates product entries based on the items in an order.
- Generates invoices that accurately reflect the order details, including applicable VAT rates.
- Provides comprehensive logging and error handling to manage the entire invoicing process efficiently.

The script reduces manual intervention, ensures the consistency of invoices, and enables automatic compliance with tax regulations through proper VAT handling.

## Key Features

- **Order Retrieval**: The script fetches "processing" orders from Dokan.
- **Contact Management**: Uses Rompslomp to check if customers already exist, and creates them if they do not.
- **Product Lookup**: Matches product SKUs between Dokan and Rompslomp to correctly add line items to invoices.
- **Invoice Creation**: Generates Rompslomp invoices based on Dokan orders, including product, shipping line items, and tax information.
- **VAT Handling**: Dynamically applies VAT rates depending on the shipping country.
- **Error Handling and Resilience**: Implements retry logic with exponential backoff and caches contact/product details to prevent redundant API calls.
- **Persistent Caching**: Uses `diskcache` for efficient retrieval of previously fetched data.

## External Dependencies

- **`pandas`**: Used for managing and manipulating data loaded from CSV files.
- **`requests`**: Handles HTTP requests to interact with Dokan and Rompslomp APIs.
- **`aiohttp`**: Not implemented here, but might be used for future asynchronous requests to further optimize performance.
- **`dotenv`**: Loads configuration variables from a `.env` file.
- **`diskcache`**: Implements persistent caching to reduce redundant API calls for contact and product lookups.
- **`tenacity`**: Provides retry logic with exponential backoff, allowing the script to handle transient network errors and API rate limits.
- **`logging`**: Logs messages to both the console and a file to provide detailed tracking of the invoicing process.

## Installation

Before running the script, ensure that you have Python installed, as well as the required dependencies. You can install the dependencies using the following command:

```bash
pip install pandas requests python-dotenv tenacity diskcache
```

## Environment Configuration

The script uses environment variables for configuration, which can be set in a `.env` file. Below is an example of the required environment variables:

```plaintext
DOKAN_BASE_URL=https://example.com/wp-json/dokan/v1/orders
DOKAN_USERNAME=<your_username>
DOKAN_PASSWORD=<your_application_password>
ROMPSLOMP_COMPANY_ID=<your Rompslomp company ID>
ROMPSLOMP_API_KEY=<your_api_key>
ROMPSLOMP_BASE_URL=https://api.rompslomp.nl/api/v1/companies
ROMPSLOMP_CONTACTS_ENDPOINT=/contacts
ROMPSLOMP_PRODUCTS_ENDPOINT=/products
ROMPSLOMP_INVOICES_ENDPOINT=/sales_invoices
```
To obtain your Rompslomp company id, please check this link: https://app.rompslomp.nl/developer/veelgestelde-vragen/company-id-opvragen

Make sure that the `.env` file is in the root directory of your project so the script can load the environment variables correctly.

## Script Components

### Utility Functions

- **`log_debug(message)`**: Logs debug messages if debugging mode (`DEBUG`) is enabled.
- **`round_up_to_nearest_5_or_10_cents(amount)`**: Rounds up amounts to the nearest 5 or 10 cents to ensure pricing consistency.
- **`handle_request_error(e, response=None)`**: Centralized error handling for HTTP requests, logging status codes and error messages.
- **`validate_order_data(order)`**: Validates required fields in the order data to ensure that all the necessary information is available.

### Configuration Manager (`ConfigManager`)

Handles configuration variables, loading them from environment variables using `dotenv`. It stores API URLs and credentials used to interact with Dokan and Rompslomp.

### Data Loader (`DataLoader`)

Loads VAT and shipping mapping information from CSV files:
- **`vat_mapping.csv`**: Maps country codes to VAT rates and types.
- **`shipping_mapping.csv`**: Maps Dokan shipping methods to products in Rompslomp for accurate invoice generation.

### VAT Handling (`VATHandler`)

Responsible for calculating the correct VAT rates:
- Retrieves VAT information based on the shipping country.
- Applies the appropriate VAT rates to invoice line items based on EU/non-EU distinctions.

### Dokan API Handler (`DokanAPI`)

Interacts with the Dokan API to fetch order data:
- **`get_last_processing_order()`**: Retrieves the most recent processing orders.
- **`get_order_by_id(order_id)`**: Retrieves a specific order by its ID.

### Rompslomp API Handler (`RompslompAPI`)

Interacts with the Rompslomp API for creating contacts, fetching products, and generating invoices:
- **`get_contact_id(email)`**: Searches for a contact using the provided email.
- **`get_product_id_by_sku(sku)`**: Searches for a product by SKU.
- **`create_contact(contact_data)`**: Creates a new contact in Rompslomp if no match is found.
- **`create_invoice(invoice_data)`**: Generates an invoice in Rompslomp.
- **`patch_invoice(invoice_id, patch_data)`**: Updates an invoice with correct price details.

### Invoice Processor (`InvoiceProcessor`)

Handles the main invoicing logic:
- **`create_concept_invoice(order)`**: The core function that takes an order from Dokan, finds or creates the relevant contacts, looks up product information, calculates VAT, and generates an invoice in Rompslomp.
- Tracks the number of successful and failed invoices and logs summary information at the end of the run.

## Workflow

1. **Fetch Orders**: The script starts by retrieving either a specific order by ID or all orders with a "processing" status from Dokan.
2. **Validate Orders**: Each order is validated to ensure it has the necessary information (billing details, line items, etc.).
3. **Contact Handling**: The script checks if the customer is already in Rompslomp. If not, it creates a new contact.
4. **Product Handling**: Looks up each product from the order in Rompslomp, using SKU as the identifier.
5. **Invoice Creation**: Generates an invoice based on the order details, including VAT calculations.
6. **Logging and Retry**: Any errors encountered during API requests are logged, and requests are retried if necessary.
7. **Summary**: At the end, a summary of the processed invoices is logged, indicating successes and failures.

## Running the Script

To run the script, use the following command:

```bash
python invoices.py
```

To process a specific order by its ID, pass the order ID as an argument:

```bash
python invoices.py 12345
```

## Logging

The script uses Python's logging module to provide informative messages about its operations:
- **INFO** level logs for standard process tracking.
- **ERROR** level logs for any issues or exceptions.
- Logs include information about each API request, response, and errors for easier debugging.



## Chrome Extension Addendum

### Overview

In addition to the Python script for automating invoicing, a Chrome extension is provided to allow seamless selection and processing of orders directly from the Dokan orders page. This extension helps streamline the process by allowing users to select orders visually and submit them to be processed by the backend server. 

### Chrome Extension Components

The Chrome extension consists of the following components:

1. **Popup HTML (`popup.html`)**: Provides a user interface with a button labeled **"Send Selected Orders to Rompslomp"**.
2. **Popup JavaScript (`popup.js`)**: Handles button clicks in the popup, collects selected order IDs from the webpage, and sends the data to the background script.
3. **Content Script (`content.js`)**: Injected into the Dokan orders page to interact directly with the DOM elements on the page, such as checkboxes for selecting orders. It also creates an overlay button for processing orders.
4. **Background Script (`background.js`)**: Handles communication between the popup and the backend Flask server. It listens for messages from `popup.js` and sends the selected orders to the backend for processing.

### Backend Server (`backend_server.py`)

The backend server (`backend_server.py`) is implemented using Flask and serves as the communication point between the Chrome extension and the invoice generation script. It receives order IDs from the extension and triggers the invoice creation process.

Place the original invoices.py scripts and the supporting files in the same directory as the Chrome Extension.

#### Key Features of `backend_server.py`

- **Flask API Endpoint**: The Flask server provides a `/process_orders` endpoint that listens for POST requests containing order IDs.
- **CORS Support**: Uses `flask_cors` to enable cross-origin requests from the Chrome extension.
- **Running the Invoice Script**: For each order ID received, the backend runs the `invoices.py` script using Python's `subprocess` module.
- **Error Handling**: If the script fails for any reason (e.g., invalid order ID or a subprocess error), it returns a failure response with the error details.

#### How It Works

1. **Start the Flask Server**: To start the backend server, run the following command:

   ```bash
   python backend_server.py
   ```

   By default, the server runs on `http://localhost:1234` and listens for incoming requests from the Chrome extension.

2. **Process Orders Endpoint (`/process_orders`)**: The extension sends a list of selected order IDs to this endpoint.
   - The server receives the list and loops through each order ID.
   - It runs the `invoices.py` script with the order ID as an argument.
   - If the script completes successfully, it sends a success response back to the extension.

3. **CORS Configuration**: The server is configured to allow requests from any origin (`origins: "*"`) to enable communication with the extension running in Chrome.

### Running the Extension

1. **Install and Load the Extension**:
   - Load the unpacked extension into Chrome from the **Extensions** page (`chrome://extensions/`).
2. **Start the Backend Server**:
   - Ensure the `backend_server.py` is running and listening on `http://localhost:1234`.
3. **Interact with the Dokan Orders Page**:
   - Go to the Dokan orders page (`https://example.com/dashboard/orders/`) and select the orders you want to process.
   - Click the **"Send Selected Orders to Rompslomp"** button in the popup or the overlay button on the page.
   - The extension will send the selected orders to the backend server, which will process the invoices and create them in Rompslomp.

### Troubleshooting

- **No Response from Server**: Ensure the Flask server is running and accessible (`http://localhost:1234`).
- **CORS Errors**: Verify that CORS is properly configured in `backend_server.py` to allow requests from the extension.
- **Extension Not Working**: Reload the extension in Chrome and ensure the content script is injected correctly.

With the addition of the backend server and Chrome extension, the entire workflow—from selecting orders on the Dokan page to generating


## Conclusion

This script automates the invoicing process for Dokan orders by integrating with Rompslomp, saving time and reducing errors. With retry mechanisms, caching, and comprehensive logging, the solution is robust and efficient, designed to handle various scenarios encountered during invoice generation. Future enhancements could make the script even more responsive and user-friendly.

Please feel free to contribute to this repository by suggesting improvements or submitting pull requests!
