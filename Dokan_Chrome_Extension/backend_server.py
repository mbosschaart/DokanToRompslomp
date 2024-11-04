from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app, resources={r"/process_orders": {"origins": "*"}})

# Define the path to the invoices script
INVOICES_SCRIPT_PATH = os.path.join(os.getcwd(), 'invoices.py')

@app.route('/process_orders', methods=['POST'])
def process_orders():
    try:
        data = request.get_json()
        order_ids = data.get("orders", [])

        # Validate that we received a list of order IDs
        if not isinstance(order_ids, list) or not order_ids:
            logging.error("Invalid or empty orders list received.")
            return jsonify({"status": "error", "message": "Invalid or empty orders list"}), 400

        # Loop through each order ID and process it
        results = []
        for order_id in order_ids:
            try:
                logging.info(f"Processing order ID: {order_id}")

                # Run the invoices.py script with the order ID
                result = subprocess.run(
                    ["python3", INVOICES_SCRIPT_PATH, str(order_id)],
                    capture_output=True,
                    text=True,
                    check=True
                )

                logging.info(f"Invoice created successfully for order ID {order_id}: {result.stdout}")
                results.append({"order_id": order_id, "status": "success", "output": result.stdout})
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to create invoice for order ID {order_id}: {e.stderr}")
                results.append({"order_id": order_id, "status": "failed", "error": e.stderr})
            except Exception as e:
                logging.error(f"Unexpected error for order ID {order_id}: {str(e)}")
                results.append({"order_id": order_id, "status": "failed", "error": str(e)})

        return jsonify({"status": "completed", "results": results}), 200

    except Exception as e:
        logging.error(f"Unexpected error in /process_orders endpoint: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=1234, debug=True)
