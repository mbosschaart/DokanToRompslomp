// Listen for messages from popup.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'getSelectedOrders') {
        // Get all checkboxes that are selected
        const checkboxes = document.querySelectorAll('.cb-select-items:checked');
        let selectedOrders = [];

        checkboxes.forEach(checkbox => {
            selectedOrders.push(checkbox.value);
        });

        // Send the selected orders back to popup.js
        sendResponse({ orders: selectedOrders });
    }
});

// Create and add the "Process Orders" button overlay
function addOverlayButton() {
    // Check if the button already exists to avoid duplicates
    if (document.getElementById('process-orders-overlay-button')) {
        return;
    }

    // Create the button
    const button = document.createElement('button');
    button.id = 'process-orders-overlay-button';
    button.textContent = 'Invoice Selected orders';
    button.style.position = 'fixed';
    button.style.bottom = '20px';
    button.style.right = '20px';
    button.style.padding = '15px';
    button.style.fontSize = '16px';
    button.style.backgroundColor = '#007bff';
    button.style.color = '#fff';
    button.style.border = 'none';
    button.style.borderRadius = '5px';
    button.style.cursor = 'pointer';
    button.style.zIndex = '1000';

    // Add an event listener to handle the button click
    button.addEventListener('click', () => {
        console.log('Overlay button clicked.');

        // Disable the button and provide feedback
        button.disabled = true;
        button.textContent = "Sending... Please wait";
        button.style.backgroundColor = "#ccc";
        button.style.cursor = "not-allowed";

        const checkboxes = document.querySelectorAll('.cb-select-items:checked');
        let selectedOrders = [];

        checkboxes.forEach(checkbox => {
            selectedOrders.push(checkbox.value);
        });

        if (selectedOrders.length === 0) {
            alert('Please select at least one order.');
            resetButton(button, "Invoice Selected orders");
            return;
        }

        // Send the selected orders to background.js to process them
        chrome.runtime.sendMessage({ action: 'sendOrders', orders: selectedOrders }, (response) => {
            if (response && response.status === 'success') {
                alert('Orders sent successfully to Rompslomp!');
                // Uncheck all selected checkboxes after confirmation
                checkboxes.forEach(checkbox => {
                    checkbox.checked = false;
                });
            } else {
                alert('Failed to send orders. Please try again.');
            }
            // Re-enable the button and restore the text
            resetButton(button, "Invoice Selected orders");
        });
    });

    // Append the button to the body of the page
    document.body.appendChild(button);
}

// Helper function to reset button states
function resetButton(button, text) {
    button.disabled = false;
    button.textContent = text;
    button.style.backgroundColor = "#007bff"; // Restore original background color
    button.style.cursor = "pointer";
}

// Add the overlay button when the content script loads
addOverlayButton();
