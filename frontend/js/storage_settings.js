/**
 * SPARSH - Storage Settings Management Logic
 *
 * Handles the OAuth-based Google Drive Setup:
 * Connect Google Account → Folder URL → Verify → Test → Save
 *
 * Google Drive is the only storage provider.
 */

document.addEventListener('DOMContentLoaded', () => {
    const viewStorage = document.getElementById('view-storage-settings');
    if (!viewStorage) return;

    // --- State ---
    let driveConnected = false;
    let verifiedFolderId = null;
    let testUploadPassed = false;

    // --- Elements ---
    const btnSave = document.getElementById('btnSaveStorage');
    const alertArea = document.getElementById('storageAlertArea');

    // Status Panel
    const statusProvider = document.getElementById('statusProvider');
    const driveDetailedStatus = document.getElementById('driveDetailedStatus');
    
    // Checklists
    const chkGoogleConnected = document.getElementById('chkGoogleConnected');
    const chkFolderUrl = document.getElementById('chkFolderUrl');
    const chkFolderVerified = document.getElementById('chkFolderVerified');
    const chkUploadTest = document.getElementById('chkUploadTest');
    
    // History
    const histLastVerified = document.getElementById('histLastVerified');
    const histLastUpload = document.getElementById('histLastUpload');

    // Step 1: Google OAuth
    const googleNotConnected = document.getElementById('googleNotConnected');
    const googleConnected = document.getElementById('googleConnected');
    const btnConnectGoogle = document.getElementById('btnConnectGoogle');
    const btnDisconnectGoogle = document.getElementById('btnDisconnectGoogle');
    const connectedGoogleEmail = document.getElementById('connectedGoogleEmail');
    const oauthUnavailable = document.getElementById('oauthUnavailable');

    // Step 2: Verification
    const folderUrlInput = document.getElementById('driveFolderUrl');
    const btnVerify = document.getElementById('btnVerifyFolder');
    const btnTestUpload = document.getElementById('btnTestUpload');
    const verifyArea = document.getElementById('verifyResultArea');

    // --- Helpers ---
    function showAlert(msg, type = 'danger') {
        if (!msg) { alertArea.innerHTML = ''; return; }
        alertArea.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show">
            ${msg}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>`;
    }

    function setCheckmark(el, status) {
        if (!el) return;
        if (status === 'yes') {
            el.innerHTML = '<span class="text-success fw-bold">✓</span>';
        } else if (status === 'no') {
            el.innerHTML = '<span class="text-danger fw-bold">✗</span>';
        } else {
            el.innerHTML = '<span class="text-muted">—</span>';
        }
    }

    function resetVerification() {
        verifiedFolderId = null;
        testUploadPassed = false;
        btnTestUpload.classList.add('hidden');
        btnSave.disabled = true;
        verifyArea.classList.add('hidden');
        verifyArea.innerHTML = '';
        
        setCheckmark(chkFolderVerified, 'pending');
        setCheckmark(chkUploadTest, 'pending');
    }

    function updateSaveButtonState() {
        // Save is enabled only when connected + folder verified + test passed
        btnSave.disabled = !(driveConnected && verifiedFolderId && testUploadPassed);
    }

    // --- Core Logic ---

    // 1. Load Settings
    async function loadSettings() {
        try {
            const data = await apiClient.fetch('/settings/storage');

            driveConnected = data.google_drive_connected;
            statusProvider.textContent = 'Google Drive';

            // Update connection state
            if (driveConnected) {
                setCheckmark(chkGoogleConnected, 'yes');
                googleNotConnected.classList.add('hidden');
                googleConnected.classList.remove('hidden');
                connectedGoogleEmail.textContent = data.google_user_email || 'Unknown';
                folderUrlInput.disabled = false;
            } else {
                setCheckmark(chkGoogleConnected, 'no');
                googleNotConnected.classList.remove('hidden');
                googleConnected.classList.add('hidden');
                folderUrlInput.disabled = true;
            }

            if (data.folder_url_saved) {
                setCheckmark(chkFolderUrl, 'yes');
                folderUrlInput.value = `https://drive.google.com/drive/folders/${data.drive_folder_id}`;
                setCheckmark(chkFolderVerified, 'yes');
                verifiedFolderId = data.drive_folder_id;
                if (data.last_successful_upload_at) {
                    setCheckmark(chkUploadTest, 'yes');
                    testUploadPassed = true;
                } else {
                    setCheckmark(chkUploadTest, 'no');
                }
            } else {
                setCheckmark(chkFolderUrl, 'no');
                setCheckmark(chkFolderVerified, 'pending');
                setCheckmark(chkUploadTest, 'pending');
            }

            // Populate History
            histLastVerified.textContent = data.last_verified_at ? new Date(data.last_verified_at).toLocaleString() : 'Never';
            histLastUpload.textContent = data.last_successful_upload_at ? new Date(data.last_successful_upload_at).toLocaleString() : 'Never';

            // Check OAuth availability
            checkOAuthAvailability();

            // Update save button
            updateSaveButtonState();

        } catch (err) {
            showAlert("Failed to load settings: " + err.message);
        }
    }

    // 2. Check OAuth Availability
    async function checkOAuthAvailability() {
        try {
            const data = await apiClient.fetch('/settings/storage/drive-availability');
            if (!data.google_drive_available) {
                oauthUnavailable.classList.remove('hidden');
                btnConnectGoogle.disabled = true;
            } else {
                oauthUnavailable.classList.add('hidden');
                btnConnectGoogle.disabled = false;
            }
        } catch (err) {
            // Silently fail
        }
    }

    // 3. Connect Google Drive (OAuth)
    btnConnectGoogle.addEventListener('click', async () => {
        btnConnectGoogle.disabled = true;
        btnConnectGoogle.textContent = 'Connecting...';

        try {
            const data = await apiClient.fetch('/settings/storage/oauth/start');
            // Open OAuth URL in the same window (Google will redirect back)
            window.location.href = data.auth_url;
        } catch (err) {
            showAlert('Failed to start Google connection: ' + err.message);
            btnConnectGoogle.disabled = false;
            btnConnectGoogle.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"/></svg>
                Connect Google Drive`;
        }
    });

    // 4. Disconnect Google Drive
    btnDisconnectGoogle.addEventListener('click', async () => {
        if (!confirm('Are you sure you want to disconnect Google Drive?')) return;
        
        btnDisconnectGoogle.disabled = true;
        btnDisconnectGoogle.textContent = 'Disconnecting...';

        try {
            await apiClient.fetch('/settings/storage/oauth/disconnect', { method: 'POST' });
            showAlert('Google Drive disconnected.', 'success');
            resetVerification();
            await loadSettings();
        } catch (err) {
            showAlert('Failed to disconnect: ' + err.message);
        } finally {
            btnDisconnectGoogle.disabled = false;
            btnDisconnectGoogle.textContent = 'Disconnect';
        }
    });

    // 5. Folder URL Input
    folderUrlInput.addEventListener('input', () => {
        if (folderUrlInput.value.trim().length > 0) {
            setCheckmark(chkFolderUrl, 'yes');
        } else {
            setCheckmark(chkFolderUrl, 'no');
        }
        resetVerification();
    });

    // 6. Verify Folder
    btnVerify.addEventListener('click', async () => {
        const url = folderUrlInput.value.trim();
        if (!url) {
            showAlert('Please enter a Google Drive folder URL.');
            return;
        }

        btnVerify.disabled = true;
        btnVerify.textContent = 'Verifying...';
        resetVerification();

        try {
            const data = await apiClient.fetch('/settings/storage/verify', {
                method: 'POST',
                body: JSON.stringify({ folder_url: url }),
            });

            verifyArea.classList.remove('hidden');

            if (data.verified) {
                verifiedFolderId = data.folder_id;
                setCheckmark(chkFolderVerified, 'yes');
                histLastVerified.textContent = new Date().toLocaleString();
                
                verifyArea.innerHTML = `
                    <div class="alert alert-success">
                        <strong>✓ Folder Verified</strong><br>
                        <span class="text-muted">Folder Name:</span> <strong>${data.folder_name}</strong>
                    </div>`;
                btnTestUpload.classList.remove('hidden');
            } else {
                setCheckmark(chkFolderVerified, 'no');
                verifyArea.innerHTML = `
                    <div class="alert alert-danger">
                        <strong>✗ Verification Failed</strong><br>
                        <p class="mb-0">${data.message}</p>
                    </div>`;
            }
        } catch (err) {
            verifyArea.classList.remove('hidden');
            verifyArea.innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
        } finally {
            btnVerify.disabled = false;
            btnVerify.textContent = 'Verify Folder';
        }
    });

    // 7. Test Upload
    btnTestUpload.addEventListener('click', async () => {
        const url = folderUrlInput.value.trim();
        btnTestUpload.disabled = true;
        btnTestUpload.textContent = 'Testing...';

        try {
            const data = await apiClient.fetch('/settings/storage/test-upload', {
                method: 'POST',
                body: JSON.stringify({ folder_url: url }),
            });

            if (data.success) {
                testUploadPassed = true;
                setCheckmark(chkUploadTest, 'yes');
                histLastUpload.textContent = new Date().toLocaleString();
                updateSaveButtonState();
                
                verifyArea.innerHTML += `
                    <div class="alert alert-success mt-2">
                        <strong>✓ Test Upload Passed</strong><br>
                        ${data.message}
                    </div>`;
                btnTestUpload.classList.add('hidden');
            } else {
                setCheckmark(chkUploadTest, 'no');
                verifyArea.innerHTML += `
                    <div class="alert alert-warning mt-2">
                        <strong>✗ Test Upload Failed</strong><br>
                        <p class="mb-0">${data.message}</p>
                    </div>`;
            }
        } catch (err) {
            verifyArea.innerHTML += `<div class="alert alert-danger mt-2">${err.message}</div>`;
        } finally {
            btnTestUpload.disabled = false;
            btnTestUpload.textContent = 'Test Upload';
        }
    });

    // 8. Save Settings
    btnSave.addEventListener('click', async () => {
        btnSave.disabled = true;
        btnSave.textContent = 'Saving...';

        const payload = {
            storage_provider: 'google_drive',
            drive_folder_id: verifiedFolderId,
        };

        try {
            await apiClient.fetch('/settings/storage', {
                method: 'PUT',
                body: JSON.stringify(payload),
            });

            showAlert('Storage settings saved successfully.', 'success');
            await loadSettings(); 
        } catch (err) {
            showAlert('Failed to save: ' + err.message);
            btnSave.disabled = false;
        } finally {
            btnSave.textContent = 'Save Settings';
        }
    });

    // --- Handle OAuth Redirect Results ---
    function handleOAuthRedirect() {
        const params = new URLSearchParams(window.location.search);
        
        // Check if we landed on storage-settings from an OAuth redirect
        if (params.has('oauth_success')) {
            const email = params.get('email') || '';
            showAlert(`Successfully connected Google Drive as <strong>${decodeURIComponent(email)}</strong>.`, 'success');
            // Clean URL
            history.replaceState(null, '', '/storage-settings');
        } else if (params.has('oauth_error')) {
            const error = params.get('oauth_error');
            let msg = 'Google Drive connection failed.';
            if (error === 'access_denied') msg = 'Google Drive connection was cancelled.';
            else if (error === 'no_refresh_token') msg = 'Failed to obtain a refresh token. Please try again.';
            else if (error === 'token_exchange_failed') msg = 'Failed to exchange authorization code. Please try again.';
            showAlert(msg);
            history.replaceState(null, '', '/storage-settings');
        }
    }

    // --- Init ---
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.attributeName === 'class' && !viewStorage.classList.contains('hidden')) {
                loadSettings();
            }
        });
    });
    observer.observe(viewStorage, { attributes: true });

    if (!viewStorage.classList.contains('hidden')) {
        loadSettings();
    }

    // Handle OAuth redirect on page load
    handleOAuthRedirect();
});
