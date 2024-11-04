document.addEventListener('DOMContentLoaded', () => {
    // Find the "Send Orders" button in the DOM
    const sendOrdersButton = document.getElementById('send-orders-button');

    if (!sendOrdersButton) {
        console.error('Send Orders button not found in the DOM.');
        return;
    }

    // Add click event listener to the button
    sendOrdersButton.addEventListener('click', () => {
        // Send a message to the content script to get selected orders
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            chrome.tabs.sendMessage(tabs[0].id, { action: 'getSelectedOrders' }, (response) => {
                if (chrome.runtime.lastError) {
                    console.error('Error communicating with content script:', chrome.runtime.lastError.message);
                    alert('Failed to communicate with the page. Please refresh the page and try again.');
                    return;
                }

                let selectedOrders = response.orders;

                // Check if no orders are selected
                if (selectedOrders.length === 0) {
                    alert('Please select at least one order.');
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
                });
            });
        });
    });
});
