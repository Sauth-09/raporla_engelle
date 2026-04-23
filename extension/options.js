// options.js
document.addEventListener('DOMContentLoaded', restoreOptions);
document.getElementById('saveBtn').addEventListener('click', saveOptions);

// Restore the saved machineId from Chrome storage
function restoreOptions() {
    chrome.storage.local.get({ machineId: '', serverUrl: 'http://localhost:5050' }, function(items) {
        document.getElementById('machineId').value = items.machineId;
        document.getElementById('serverUrl').value = items.serverUrl;
    });
}

// Save the entered machineId to Chrome storage
function saveOptions() {
    const machineId = document.getElementById('machineId').value.trim();
    const serverUrl = document.getElementById('serverUrl').value.trim();
    const status = document.getElementById('status');

    if (!machineId) {
        status.style.color = 'red';
        status.textContent = 'Lütfen bir isim girin.';
        setTimeout(() => status.textContent = '', 3000);
        return;
    }

    let formattedUrl = serverUrl;
    if (formattedUrl && !formattedUrl.startsWith('http://') && !formattedUrl.startsWith('https://')) {
        formattedUrl = 'http://' + formattedUrl;
        document.getElementById('serverUrl').value = formattedUrl;
    }

    chrome.storage.local.set({ machineId: machineId, serverUrl: formattedUrl || 'http://localhost:5050' }, function() {
        // Update status to let user know options were saved.
        status.style.color = '#4bb543'; // Success green
        status.textContent = 'Ayarlar başarıyla kaydedildi!';
        setTimeout(function() {
            status.textContent = '';
        }, 3000);
    });
}
