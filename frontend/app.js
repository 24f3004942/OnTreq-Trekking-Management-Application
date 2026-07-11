const { createApp } = Vue;

createApp({
    data() {
        return {
            isLoginMode: true, // Toggles between Login and Register views
            email: '',
            password: '',
            errorMessage: '',
            successMessage: '',
            isLoading: false
        }
    },
    methods: {
        toggleMode() {
            this.isLoginMode = !this.isLoginMode;
            this.errorMessage = '';
            this.successMessage = '';
            this.email = '';
            this.password = '';
        },
        async submitForm() {
            this.isLoading = true;
            this.errorMessage = '';
            this.successMessage = '';

            const endpoint = this.isLoginMode ? 'http://127.0.0.1:5000/api/auth/login' : 'http://127.0.0.1:5000/api/auth/register';
            
            try {
                // We use standard fetch API to avoid extra dependencies
                const response = await fetch(endpoint, {
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

                if (this.isLoginMode) {
                    // Store token and role in localStorage for future API calls
                    localStorage.setItem('token', data.token);
                    localStorage.setItem('role', data.role);
                    
                    this.successMessage = 'Login successful! Redirecting...';
                    
                    // In the future, we will redirect to the specific dashboard here
                    console.log("Logged in as:", data.role);
                } else {
                    this.successMessage = 'Registration successful! You can now log in.';
                    setTimeout(() => this.toggleMode(), 2000); // Switch to login after 2 seconds
                }

            } catch (error) {
                this.errorMessage = error.message;
            } finally {
                this.isLoading = false;
            }
        }
    }
}).mount('#app');