// options.js
document.addEventListener('DOMContentLoaded', restoreOptions);
document.getElementById('saveBtn').addEventListener('click', saveOptions);

// Restore the saved machineId from Chrome storage
function restoreOptions() {
    chrome.storage.local.get({ machineId: '' }, function(items) {
        document.getElementById('machineId').value = items.machineId;
    });
}

// Save the entered machineId to Chrome storage
function saveOptions() {
    const machineId = document.getElementById('machineId').value.trim();
    const status = document.getElementById('status');

    if (!machineId) {
        status.style.color = 'red';
        status.textContent = 'Lütfen bir isim girin.';
        setTimeout(() => status.textContent = '', 3000);
        return;
    }

    chrome.storage.local.set({ machineId: machineId }, function() {
        // Update status to let user know options were saved.
        status.style.color = '#4bb543'; // Success green
        status.textContent = 'Ayarlar başarıyla kaydedildi!';
        setTimeout(function() {
            status.textContent = '';
        }, 3000);
    });
}
