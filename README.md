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
DOKAN_BASE_URL=https://example.com/wp-json/dokan/v1
DOKAN_USERNAME=your_username
DOKAN_PASSWORD=your_password
ROMSLOMP_COMPANY_ID=1234567890
ROMSLOMP_API_KEY=your_api_key
ROMSLOMP_BASE_URL=https://api.rompslomp.nl/api/v1/companies
ROMSLOMP_CONTACTS_ENDPOINT=/contacts
ROMSLOMP_PRODUCTS_ENDPOINT=/products
ROMSLOMP_INVOICES_ENDPOINT=/sales_invoices
```

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

- **`vat_mapping.csv`**: Maps country codes to VAT rates and types. The CSV file should have the following columns:

  - `country_code`: The two-letter country code (e.g., NL, DE).
  - `vat_type_id`: The ID representing the type of VAT (you can get these from the Rompslomp . /api/v1/companies/{company\_id}/vat\_types endpoint.
  - `vat_rate`: The VAT rate applicable to that country (i.e. 0.21)

- **`shipping_mapping.csv`**: Maps Dokan shipping methods to products in Rompslomp for accurate invoice generation. The CSV file should have the following columns:

  - `Dokan_method`: The shipping method name used in Dokan.
  - `price`: The price associated with that shipping method.
  - `SKU`: The SKU corresponding to the shipping product in Rompslomp.

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

## Future Improvements

- **Asynchronous API Requests**: Consider implementing `aiohttp` to make API calls asynchronously, which would further improve the performance for large batches of orders.
- **Error Handling Enhancements**: Introduce more granular error handling for specific types of issues, such as network errors or rate-limiting responses.
- **User Notifications**: Add email notifications or Slack integration to alert users about the script's status, especially in case of errors.

## Conclusion

This script automates the invoicing process for Dokan orders by integrating with Rompslomp, saving time and reducing errors. With retry mechanisms, caching, and comprehensive logging, the solution is robust and efficient, designed to handle various scenarios encountered during invoice generation. Future enhancements could make the script even more responsive and user-friendly.

Please feel free to contribute to this repository by suggesting improvements or submitting pull requests!

