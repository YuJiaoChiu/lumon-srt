/**
 * Main application script for the SRT Correction System
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const progressSection = document.getElementById('progress-section');
    const progressBar = document.getElementById('progress-bar');
    const progressStatus = document.getElementById('progress-status');
    const processingFileName = document.getElementById('processing-file-name');
    const resultsSection = document.getElementById('results-section');
    const resultSummary = document.getElementById('result-summary');
    const downloadLink = document.getElementById('download-link');
    const replacementsTable = document.getElementById('replacements-table');
    
    // Dictionary elements
    const correctionTable = document.getElementById('correction-table');
    const protectionTable = document.getElementById('protection-table');
    const addCorrectionBtn = document.getElementById('add-correction-btn');
    const addProtectionBtn = document.getElementById('add-protection-btn');
    const saveCorrectionBtn = document.getElementById('save-correction-btn');
    const saveProtectionBtn = document.getElementById('save-protection-btn');
    
    // Modal elements
    const correctionModal = new bootstrap.Modal(document.getElementById('correction-modal'));
    const protectionModal = new bootstrap.Modal(document.getElementById('protection-modal'));
    const errorModal = new bootstrap.Modal(document.getElementById('error-modal'));
    const errorMessage = document.getElementById('error-message');
    const saveCorrectionEntryBtn = document.getElementById('save-correction-entry-btn');
    const saveProtectionEntryBtn = document.getElementById('save-protection-entry-btn');
    const wrongTermInput = document.getElementById('wrong-term');
    const correctTermInput = document.getElementById('correct-term');
    const protectionTermInput = document.getElementById('protection-term');
    
    // State variables
    let currentTaskId = null;
    let pollingInterval = null;
    let correctionDict = {};
    let protectionDict = {};
    let editingTerm = null;
    
    // Initialize the application
    init();
    
    /**
     * Initialize the application
     */
    async function init() {
        try {
            // Load dictionaries
            await loadDictionaries();
            
            // Set up event listeners
            setupEventListeners();
            
            // Check API health
            const health = await api.getHealth();
            console.log('API health:', health);
        } catch (error) {
            showError('初始化失败: ' + error.message);
        }
    }
    
    /**
     * Load dictionaries from the API
     */
    async function loadDictionaries() {
        try {
            // Load correction dictionary
            correctionDict = await api.getCorrectionDictionary();
            renderCorrectionDictionary();
            
            // Load protection dictionary
            protectionDict = await api.getProtectionDictionary();
            renderProtectionDictionary();
        } catch (error) {
            showError('加载词典失败: ' + error.message);
        }
    }
    
    /**
     * Set up event listeners
     */
    function setupEventListeners() {
        // File upload form
        uploadForm.addEventListener('submit', handleFileUpload);
        
        // Dictionary buttons
        addCorrectionBtn.addEventListener('click', showAddCorrectionModal);
        addProtectionBtn.addEventListener('click', showAddProtectionModal);
        saveCorrectionBtn.addEventListener('click', saveCorrectionDictionary);
        saveProtectionBtn.addEventListener('click', saveProtectionDictionary);
        
        // Modal buttons
        saveCorrectionEntryBtn.addEventListener('click', saveCorrectionEntry);
        saveProtectionEntryBtn.addEventListener('click', saveProtectionEntry);
        
        // File input change
        fileInput.addEventListener('change', function() {
            if (fileInput.files.length > 0) {
                uploadBtn.textContent = `处理 "${fileInput.files[0].name}"`;
            } else {
                uploadBtn.textContent = '上传并处理';
            }
        });
    }
    
    /**
     * Handle file upload form submission
     * @param {Event} event - Form submit event
     */
    async function handleFileUpload(event) {
        event.preventDefault();
        
        if (!fileInput.files || fileInput.files.length === 0) {
            showError('请选择一个文件');
            return;
        }
        
        const file = fileInput.files[0];
        if (!file.name.toLowerCase().endsWith('.srt')) {
            showError('只支持SRT格式的字幕文件');
            return;
        }
        
        try {
            // Show progress section
            progressSection.style.display = 'block';
            resultsSection.style.display = 'none';
            uploadBtn.disabled = true;
            fileInput.disabled = true;
            
            // Update progress UI
            processingFileName.textContent = `正在处理: ${file.name}`;
            progressBar.style.width = '0%';
            progressBar.setAttribute('aria-valuenow', 0);
            progressStatus.textContent = '正在上传文件...';
            
            // Upload file
            const response = await api.processFile(file);
            currentTaskId = response.task_id;
            
            // Start polling for task status
            progressStatus.textContent = '文件已上传，正在处理...';
            startPolling();
        } catch (error) {
            resetUploadForm();
            showError('上传失败: ' + error.message);
        }
    }
    
    /**
     * Start polling for task status
     */
    function startPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
        
        pollingInterval = setInterval(async () => {
            try {
                if (!currentTaskId) {
                    clearInterval(pollingInterval);
                    return;
                }
                
                const status = await api.getTaskStatus(currentTaskId);
                updateProgressUI(status);
                
                if (status.status === 'completed' || status.status === 'error') {
                    clearInterval(pollingInterval);
                    
                    if (status.status === 'completed') {
                        showResults(status);
                    } else {
                        resetUploadForm();
                        showError('处理失败: ' + (status.error || '未知错误'));
                    }
                }
            } catch (error) {
                clearInterval(pollingInterval);
                resetUploadForm();
                showError('获取任务状态失败: ' + error.message);
            }
        }, 1000); // Poll every second
    }
    
    /**
     * Update the progress UI based on task status
     * @param {object} status - Task status
     */
    function updateProgressUI(status) {
        const progress = Math.round(status.progress || 0);
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
        
        switch (status.status) {
            case 'queued':
                progressStatus.textContent = '排队中...';
                break;
            case 'processing':
                progressStatus.textContent = `处理中... ${progress}%`;
                break;
            case 'completed':
                progressStatus.textContent = '处理完成!';
                progressBar.classList.remove('progress-bar-animated');
                progressBar.classList.add('bg-success');
                break;
            case 'error':
                progressStatus.textContent = '处理失败!';
                progressBar.classList.remove('progress-bar-animated');
                progressBar.classList.add('bg-danger');
                break;
        }
    }
    
    /**
     * Show the results of a completed task
     * @param {object} status - Task status
     */
    function showResults(status) {
        resultsSection.style.display = 'block';
        
        // Set download link
        if (status.download_url) {
            downloadLink.href = api.baseUrl + status.download_url;
            downloadLink.download = status.result.corrected_file.split('/').pop();
        }
        
        // Set result summary
        const totalReplacements = status.result.total_replacements || 0;
        resultSummary.textContent = `成功处理文件，共进行了 ${totalReplacements} 次替换。`;
        
        // Clear previous replacements
        replacementsTable.innerHTML = '';
        
        // Add replacements to table
        const replacements = status.result.replacements || {};
        for (const [key, count] of Object.entries(replacements)) {
            const [wrong, correct] = key.split(' -> ');
            
            const row = document.createElement('tr');
            const wrongCell = document.createElement('td');
            const correctCell = document.createElement('td');
            const countCell = document.createElement('td');
            
            wrongCell.textContent = wrong;
            correctCell.textContent = correct || '(删除)';
            countCell.textContent = count;
            
            row.appendChild(wrongCell);
            row.appendChild(correctCell);
            row.appendChild(countCell);
            replacementsTable.appendChild(row);
        }
        
        // Reset form for next upload
        resetUploadForm();
    }
    
    /**
     * Reset the upload form
     */
    function resetUploadForm() {
        uploadBtn.disabled = false;
        fileInput.disabled = false;
        fileInput.value = '';
        uploadBtn.textContent = '上传并处理';
    }
    
    /**
     * Show an error message
     * @param {string} message - Error message
     */
    function showError(message) {
        errorMessage.textContent = message;
        errorModal.show();
    }
    
    /**
     * Render the correction dictionary table
     */
    function renderCorrectionDictionary() {
        correctionTable.innerHTML = '';
        
        for (const [wrong, correct] of Object.entries(correctionDict)) {
            addCorrectionRow(wrong, correct);
        }
    }
    
    /**
     * Add a row to the correction dictionary table
     * @param {string} wrong - Wrong term
     * @param {string} correct - Correct term
     */
    function addCorrectionRow(wrong, correct) {
        const row = document.createElement('tr');
        
        const wrongCell = document.createElement('td');
        wrongCell.textContent = wrong;
        
        const correctCell = document.createElement('td');
        correctCell.textContent = correct || '(删除)';
        
        const actionsCell = document.createElement('td');
        
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-primary me-1';
        editBtn.innerHTML = '<i class="bi bi-pencil"></i>';
        editBtn.addEventListener('click', () => editCorrectionEntry(wrong, correct));
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-danger';
        deleteBtn.innerHTML = '<i class="bi bi-trash"></i>';
        deleteBtn.addEventListener('click', () => deleteCorrectionEntry(wrong));
        
        actionsCell.appendChild(editBtn);
        actionsCell.appendChild(deleteBtn);
        
        row.appendChild(wrongCell);
        row.appendChild(correctCell);
        row.appendChild(actionsCell);
        
        correctionTable.appendChild(row);
    }
    
    /**
     * Render the protection dictionary table
     */
    function renderProtectionDictionary() {
        protectionTable.innerHTML = '';
        
        for (const term of Object.keys(protectionDict)) {
            addProtectionRow(term);
        }
    }
    
    /**
     * Add a row to the protection dictionary table
     * @param {string} term - Protected term
     */
    function addProtectionRow(term) {
        const row = document.createElement('tr');
        
        const termCell = document.createElement('td');
        termCell.textContent = term;
        
        const actionsCell = document.createElement('td');
        
        const editBtn = document.createElement('button');
        editBtn.className = 'btn btn-sm btn-primary me-1';
        editBtn.innerHTML = '<i class="bi bi-pencil"></i>';
        editBtn.addEventListener('click', () => editProtectionEntry(term));
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-sm btn-danger';
        deleteBtn.innerHTML = '<i class="bi bi-trash"></i>';
        deleteBtn.addEventListener('click', () => deleteProtectionEntry(term));
        
        actionsCell.appendChild(editBtn);
        actionsCell.appendChild(deleteBtn);
        
        row.appendChild(termCell);
        row.appendChild(actionsCell);
        
        protectionTable.appendChild(row);
    }
    
    /**
     * Show the add correction entry modal
     */
    function showAddCorrectionModal() {
        editingTerm = null;
        wrongTermInput.value = '';
        correctTermInput.value = '';
        document.getElementById('correction-modal-label').textContent = '添加矫正条目';
        correctionModal.show();
    }
    
    /**
     * Show the add protection entry modal
     */
    function showAddProtectionModal() {
        editingTerm = null;
        protectionTermInput.value = '';
        document.getElementById('protection-modal-label').textContent = '添加保护条目';
        protectionModal.show();
    }
    
    /**
     * Edit a correction entry
     * @param {string} wrong - Wrong term
     * @param {string} correct - Correct term
     */
    function editCorrectionEntry(wrong, correct) {
        editingTerm = wrong;
        wrongTermInput.value = wrong;
        correctTermInput.value = correct || '';
        document.getElementById('correction-modal-label').textContent = '编辑矫正条目';
        correctionModal.show();
    }
    
    /**
     * Edit a protection entry
     * @param {string} term - Protected term
     */
    function editProtectionEntry(term) {
        editingTerm = term;
        protectionTermInput.value = term;
        document.getElementById('protection-modal-label').textContent = '编辑保护条目';
        protectionModal.show();
    }
    
    /**
     * Delete a correction entry
     * @param {string} wrong - Wrong term
     */
    function deleteCorrectionEntry(wrong) {
        if (confirm(`确定要删除矫正条目 "${wrong}" 吗?`)) {
            delete correctionDict[wrong];
            renderCorrectionDictionary();
        }
    }
    
    /**
     * Delete a protection entry
     * @param {string} term - Protected term
     */
    function deleteProtectionEntry(term) {
        if (confirm(`确定要删除保护条目 "${term}" 吗?`)) {
            delete protectionDict[term];
            renderProtectionDictionary();
        }
    }
    
    /**
     * Save a correction entry from the modal
     */
    function saveCorrectionEntry() {
        const wrong = wrongTermInput.value.trim();
        const correct = correctTermInput.value.trim();
        
        if (!wrong) {
            showError('错误词不能为空');
            return;
        }
        
        if (editingTerm && editingTerm !== wrong) {
            // If editing and the wrong term changed, delete the old entry
            delete correctionDict[editingTerm];
        }
        
        correctionDict[wrong] = correct;
        renderCorrectionDictionary();
        correctionModal.hide();
    }
    
    /**
     * Save a protection entry from the modal
     */
    function saveProtectionEntry() {
        const term = protectionTermInput.value.trim();
        
        if (!term) {
            showError('保护词不能为空');
            return;
        }
        
        if (editingTerm && editingTerm !== term) {
            // If editing and the term changed, delete the old entry
            delete protectionDict[editingTerm];
        }
        
        protectionDict[term] = '';
        renderProtectionDictionary();
        protectionModal.hide();
    }
    
    /**
     * Save the correction dictionary to the API
     */
    async function saveCorrectionDictionary() {
        try {
            saveCorrectionBtn.disabled = true;
            saveCorrectionBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>保存中...';
            
            const response = await api.updateCorrectionDictionary(correctionDict);
            
            if (response.status === 'success') {
                alert(`矫正词典已保存，共 ${response.count} 个条目`);
            } else {
                showError('保存失败: ' + (response.error || '未知错误'));
            }
        } catch (error) {
            showError('保存失败: ' + error.message);
        } finally {
            saveCorrectionBtn.disabled = false;
            saveCorrectionBtn.innerHTML = '<i class="bi bi-save me-1"></i>保存词典';
        }
    }
    
    /**
     * Save the protection dictionary to the API
     */
    async function saveProtectionDictionary() {
        try {
            saveProtectionBtn.disabled = true;
            saveProtectionBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>保存中...';
            
            const response = await api.updateProtectionDictionary(protectionDict);
            
            if (response.status === 'success') {
                alert(`保护词典已保存，共 ${response.count} 个条目`);
            } else {
                showError('保存失败: ' + (response.error || '未知错误'));
            }
        } catch (error) {
            showError('保存失败: ' + error.message);
        } finally {
            saveProtectionBtn.disabled = false;
            saveProtectionBtn.innerHTML = '<i class="bi bi-save me-1"></i>保存词典';
        }
    }
});
