const { createApp } = Vue;

createApp({
    data() {
        return {
            email: '',
            password: '',
            errorMessage: '',
            successMessage: '',
            isLoading: false
        }
    },
    methods: {
        async submitForm() {
            this.isLoading = true;
            this.errorMessage = '';
            this.successMessage = '';

            try {
                const response = await fetch('http://127.0.0.1:5000/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        email: this.email,
                        password: this.password
                    })
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.msg || 'Authentication failed');
                }

                // Store token and role in localStorage for future API calls
                localStorage.setItem('token', data.token);
                localStorage.setItem('role', data.role);

                this.successMessage = 'Login successful! Redirecting...';

                setTimeout(() => {
                    if (data.role === 'admin') {
                        window.location.href = 'admin_dashboard.html';
                    } else if (data.role === 'staff') {
                        window.location.href = 'staff_dashboard.html';
                    } else {
                        window.location.href = 'user_dashboard.html';
                    }
                }, 1000);

            } catch (error) {
                this.errorMessage = error.message;
            } finally {
                this.isLoading = false;
            }
        }
    }
}).mount('#app');
