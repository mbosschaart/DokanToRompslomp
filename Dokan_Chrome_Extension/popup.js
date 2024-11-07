document.addEventListener('DOMContentLoaded', () => {
    // Find the "Send Orders" button in the DOM
    const sendOrdersButton = document.getElementById('send-orders-button');

    if (!sendOrdersButton) {
        console.error('Send Orders button not found in the DOM.');
        return;
    }

    // Add click event listener to the button
    sendOrdersButton.addEventListener('click', () => {
        console.log('Send Orders button clicked.');

        // Disable the button and provide feedback
        sendOrdersButton.disabled = true;
        sendOrdersButton.innerHTML = `<span class="spinner"></span> Sending... Please wait`;
        sendOrdersButton.style.backgroundColor = "#ccc"; // Change background color to indicate it's disabled
        sendOrdersButton.style.cursor = "not-allowed";

        // Send a message to the content script to get selected orders
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            chrome.tabs.sendMessage(tabs[0].id, { action: 'getSelectedOrders' }, (response) => {
                if (chrome.runtime.lastError) {
                    console.error('Error communicating with content script:', chrome.runtime.lastError.message);
                    alert('Failed to communicate with the page. Please refresh the page and try again.');
                    resetButton(sendOrdersButton, "Invoice Selected Orders");
                    return;
                }

                let selectedOrders = response.orders;

                // Check if no orders are selected
                if (selectedOrders.length === 0) {
                    alert('Please select at least one order.');
                    resetButton(sendOrdersButton, "Invoice Selected Orders");
                    return;
                }

                console.log('Selected orders:', selectedOrders);

                // Send the selected orders to background script
                chrome.runtime.sendMessage({ action: 'sendOrders', orders: selectedOrders }, (backgroundResponse) => {
                    console.log('Response received from background script:', backgroundResponse);
                    if (backgroundResponse && backgroundResponse.status === 'success') {
                        alert('Orders sent successfully to Rompslomp!');
                    } else {
                        alert('Failed to send orders. Please try again.');
                    }

                    // Re-enable the button and restore the text
                    resetButton(sendOrdersButton, "Invoice Selected Orders");
                });
            });
        });
    });

    // Helper function to reset button states
    function resetButton(button, text) {
        button.disabled = false;
        button.innerHTML = text;
        button.style.backgroundColor = ""; // Restore original background color
        button.style.cursor = "pointer";
    }
});

// Add CSS for spinner in popup.js
const styleElement = document.createElement('style');
styleElement.innerHTML = `
.spinner {
    border: 2px solid #f3f3f3; 
    border-top: 2px solid #3498db; 
    border-radius: 50%;
    width: 12px;
    height: 12px;
    animation: spin 1s linear infinite;
    display: inline-block;
    margin-right: 5px;
}
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}`;
document.head.appendChild(styleElement);
