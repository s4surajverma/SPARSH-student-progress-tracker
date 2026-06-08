/**
 * School Result Analysis System
 * Authentication Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // If we're on the login page but already have a token, redirect to dashboard
    if (apiClient.getToken() && window.location.pathname.endsWith('index.html')) {
        window.location.href = '/dashboard.html';
        return;
    }

    const loginForm = document.getElementById('loginForm');
    const errorAlert = document.getElementById('loginError');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const submitBtn = document.getElementById('submitBtn');

            // Reset UI
            errorAlert.classList.add('hidden');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Logging in...';

            try {
                // 1. Authenticate and get token
                const tokenData = await apiClient.fetch('/auth/login', {
                    method: 'POST',
                    body: JSON.stringify({
                        username: username,
                        password: password
                    })
                });

                apiClient.setToken(tokenData.access_token);

                // 2. Fetch user profile to get role and name
                const profile = await apiClient.fetch('/auth/me');
                
                // Store UI visibility data
                localStorage.setItem('user_role', profile.role);
                localStorage.setItem('user_name', profile.full_name);

                // Redirect to dashboard
                window.location.href = '/dashboard.html';

            } catch (error) {
                // Show error
                errorAlert.textContent = error.message || 'Login failed. Please check your credentials.';
                errorAlert.classList.remove('hidden');
                
                // Reset button
                submitBtn.disabled = false;
                submitBtn.textContent = 'Login';
            }
        });
    }
});
