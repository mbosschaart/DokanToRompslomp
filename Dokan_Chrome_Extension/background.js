chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'sendOrders') {
        console.log('Background script received orders:', request.orders);

        fetch('http://127.0.0.1:1234/process_orders', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ orders: request.orders })
        })
        .then(response => {
            console.log('Response received from Flask server:', response);
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('Server responded with status ' + response.status);
            }
        })
        .then(data => {
            console.log('Data received from Flask server:', data);
            if (data.status === 'completed') {
                sendResponse({ status: 'success', results: data.results });
            } else {
                sendResponse({ status: 'error', message: data.message });
            }
        })
        .catch(error => {
            console.error('Error communicating with server:', error);
            sendResponse({ status: 'error', message: 'Failed to communicate with the server.' });
        });

        // Inform Chrome that we will send a response asynchronously
        return true;
    }
});
