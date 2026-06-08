/**
 * School Result Analysis System
 * API Client & Authentication Wrapper
 */

const API_BASE_URL = '/api/v1';

const apiClient = {
    /**
     * Get the stored JWT token
     */
    getToken: () => localStorage.getItem('token'),

    /**
     * Set the stored JWT token
     */
    setToken: (token) => localStorage.setItem('token', token),

    /**
     * Clear all stored auth data
     */
    clearAuth: () => {
        localStorage.removeItem('token');
        localStorage.removeItem('user_role');
        localStorage.removeItem('user_name');
    },

    /**
     * Generic fetch wrapper that adds Authorization header and handles 401s
     */
    async fetch(endpoint, options = {}) {
        const token = this.getToken();
        const headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

            // Handle Unauthorized (token expired or invalid)
            if (response.status === 401) {
                this.clearAuth();
                window.location.href = '/index.html';
                throw new Error('Unauthorized');
            }

            const data = await response.json().catch(() => null);

            if (!response.ok) {
                const errorMsg = data?.detail || response.statusText;
                throw new Error(errorMsg);
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    /**
     * Specialized wrapper for form url-encoded data (used for login)
     */
    async fetchForm(endpoint, formData) {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            body: new URLSearchParams(formData),
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });

        const data = await response.json().catch(() => null);

        if (!response.ok) {
            const errorMsg = data?.detail || response.statusText;
            throw new Error(errorMsg);
        }

        return data;
    }
};
