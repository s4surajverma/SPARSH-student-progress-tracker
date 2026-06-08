/**
 * School Result Analysis System
 * Historical Reports Upload Workflow Logic
 */

document.addEventListener('DOMContentLoaded', async () => {
    const viewReports = document.getElementById('view-reports');
    if (!viewReports) return;

    const singleYearSelect = document.getElementById('singleYear');
    
    // --- Initialize Data ---
    async function initReportsData() {
        try {
            const years = await apiClient.fetch('/academic/years');
            years.forEach(y => {
                const opt = document.createElement('option');
                opt.value = y.id;
                opt.textContent = y.year_label;
                if (y.is_current) opt.selected = true;
                singleYearSelect.appendChild(opt);
            });
        } catch (err) {
            console.error("Failed to load academic years for reports.", err);
        }
    }
    initReportsData();

    // --- Utils ---
    function showAlert(elementId, message, type='danger') {
        const el = document.getElementById(elementId);
        if (!message) {
            el.innerHTML = '';
            return;
        }
        el.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    }

    // ==========================================
    // SINGLE UPLOAD WORKFLOW
    // ==========================================
    const singleForm = document.getElementById('singleReportForm');
    if (singleForm) {
        singleForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const btn = document.getElementById('btnSingleUpload');
            const fileInput = document.getElementById('singleFile');
            const adm = document.getElementById('singleAdm').value.trim();
            const yearId = document.getElementById('singleYear').value;

            if (!fileInput.files[0]) return;

            btn.disabled = true;
            btn.textContent = 'Uploading...';
            showAlert('singleAlertArea', '');

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('admission_number', adm);
            formData.append('academic_year_id', yearId);

            try {
                const response = await fetch('/api/v1/reports/upload', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${apiClient.getToken()}` },
                    body: formData
                });

                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || 'Upload failed');

                showAlert('singleAlertArea', `Success: Report uploaded for admission number ${adm}.`, 'success');
                singleForm.reset();

            } catch (err) {
                showAlert('singleAlertArea', err.message, 'danger');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Upload Report';
            }
        });
    }

    // ==========================================
    // BULK ZIP UPLOAD WORKFLOW (Two-Step)
    // ==========================================
    let bulkZipPayload = null; // Store the FormData for final commit

    const step1 = document.getElementById('bulkStep1');
    const step2 = document.getElementById('bulkStep2');
    const step3 = document.getElementById('bulkStep3');

    // --- Step 1: Preview ---
    document.getElementById('bulkReportForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const fileInput = document.getElementById('bulkZipFile');
        if (!fileInput.files[0]) return;

        const btn = document.getElementById('btnPreviewZip');
        btn.disabled = true;
        btn.textContent = 'Analyzing ZIP...';
        showAlert('bulkAlertArea', '');

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        bulkZipPayload = formData;

        try {
            const response = await fetch('/api/v1/reports/upload-zip/preview', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${apiClient.getToken()}` },
                body: formData
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Preview failed');

            // Render Preview
            document.getElementById('zipTotal').textContent = data.total_files;
            document.getElementById('zipMatched').textContent = data.matched;
            document.getElementById('zipErrors').textContent = data.errors;

            const tbody = document.getElementById('zipTableBody');
            tbody.innerHTML = '';
            data.entries.forEach(entry => {
                let statusClass = '';
                if (entry.status === 'matched') statusClass = 'text-success fw-bold';
                else if (entry.status === 'duplicate') statusClass = 'text-warning';
                else statusClass = 'text-danger';

                tbody.innerHTML += `
                    <tr>
                        <td>${entry.filename}</td>
                        <td class="${statusClass}">${entry.status.toUpperCase().replace('_', ' ')}</td>
                        <td>${entry.message}</td>
                    </tr>
                `;
            });

            // Transition UI
            step1.classList.add('hidden');
            step2.classList.remove('hidden');

            // Disable confirm if 0 matched
            document.getElementById('btnConfirmZip').disabled = (data.matched === 0);

        } catch (err) {
            showAlert('bulkAlertArea', err.message, 'danger');
            bulkZipPayload = null;
        } finally {
            btn.disabled = false;
            btn.textContent = 'Preview Content';
        }
    });

    // --- Step 2: Cancel ---
    document.getElementById('btnCancelZip').addEventListener('click', () => {
        step2.classList.add('hidden');
        step1.classList.remove('hidden');
        bulkZipPayload = null;
    });

    // --- Step 2: Confirm ---
    document.getElementById('btnConfirmZip').addEventListener('click', async (e) => {
        const btn = e.currentTarget;
        btn.disabled = true;
        btn.textContent = 'Extracting and Uploading...';

        try {
            const response = await fetch('/api/v1/reports/upload-zip', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${apiClient.getToken()}` },
                body: bulkZipPayload
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Upload failed');

            // Render Outcome
            const area = document.getElementById('zipOutcomeArea');
            area.innerHTML = `
                <div class="row text-center mb-3">
                    <div class="col-sm-4"><div class="card p-3 border-success"><h3 class="text-success">${data.uploaded}</h3><small>Uploaded</small></div></div>
                    <div class="col-sm-4"><div class="card p-3 border-warning"><h3 class="text-warning">${data.skipped}</h3><small>Skipped (Dupes)</small></div></div>
                    <div class="col-sm-4"><div class="card p-3 border-danger"><h3 class="text-danger">${data.errors}</h3><small>Errors</small></div></div>
                </div>
            `;

            step2.classList.add('hidden');
            step3.classList.remove('hidden');

        } catch (err) {
            alert('Upload Error: ' + err.message);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Confirm Upload';
        }
    });

    // --- Step 3: New Upload ---
    document.getElementById('btnNewZip').addEventListener('click', () => {
        document.getElementById('bulkReportForm').reset();
        bulkZipPayload = null;
        step3.classList.add('hidden');
        step1.classList.remove('hidden');
    });
});
