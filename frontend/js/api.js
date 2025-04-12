/**
 * API client for the SRT Correction System
 * Handles all communication with the backend API
 */

class ApiClient {
    constructor(baseUrl = 'http://localhost:5002/api') {
        this.baseUrl = baseUrl;
    }

    /**
     * Make a GET request to the API
     * @param {string} endpoint - API endpoint
     * @returns {Promise<any>} - Response data
     */
    async get(endpoint) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`);
            if (!response.ok) {
                throw new Error(`API error: ${response.status} ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API GET error:', error);
            throw error;
        }
    }

    /**
     * Make a POST request to the API
     * @param {string} endpoint - API endpoint
     * @param {any} data - Data to send
     * @returns {Promise<any>} - Response data
     */
    async post(endpoint, data) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            if (!response.ok) {
                throw new Error(`API error: ${response.status} ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API POST error:', error);
            throw error;
        }
    }

    /**
     * Upload a file to the API
     * @param {string} endpoint - API endpoint
     * @param {FormData} formData - Form data with file
     * @returns {Promise<any>} - Response data
     */
    async uploadFile(endpoint, formData) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                body: formData
            });
            if (!response.ok) {
                throw new Error(`API error: ${response.status} ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API upload error:', error);
            throw error;
        }
    }

    /**
     * Get the health status of the API
     * @returns {Promise<any>} - Health status
     */
    async getHealth() {
        return this.get('/health');
    }

    /**
     * Get the correction dictionary
     * @returns {Promise<object>} - Correction dictionary
     */
    async getCorrectionDictionary() {
        return this.get('/dictionaries/correction');
    }

    /**
     * Update the correction dictionary
     * @param {object} dictionary - New correction dictionary
     * @returns {Promise<any>} - Response data
     */
    async updateCorrectionDictionary(dictionary) {
        return this.post('/dictionaries/correction', dictionary);
    }

    /**
     * Get the protection dictionary
     * @returns {Promise<object>} - Protection dictionary
     */
    async getProtectionDictionary() {
        return this.get('/dictionaries/protection');
    }

    /**
     * Update the protection dictionary
     * @param {object} dictionary - New protection dictionary
     * @returns {Promise<any>} - Response data
     */
    async updateProtectionDictionary(dictionary) {
        return this.post('/dictionaries/protection', dictionary);
    }

    /**
     * Process an SRT file
     * @param {File} file - SRT file to process
     * @returns {Promise<any>} - Task information
     */
    async processFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.uploadFile('/process', formData);
    }

    /**
     * Get the status of a processing task
     * @param {string} taskId - Task ID
     * @returns {Promise<any>} - Task status
     */
    async getTaskStatus(taskId) {
        return this.get(`/tasks/${taskId}`);
    }

    /**
     * Get the download URL for a processed file
     * @param {string} filename - Filename
     * @returns {string} - Download URL
     */
    getDownloadUrl(filename) {
        return `${this.baseUrl}/download/${filename}`;
    }
}

// Create a global API client instance
const api = new ApiClient();
