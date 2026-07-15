const { createApp } = Vue;

createApp({
    data() {
        return {
            form: {
                first_name: '', last_name: '', email: '', phone: '',
                password: '', confirmPassword: '', 
                emergency_contact: '', experience_level: 'Beginner', medical_conditions: ''
            },
            message: '', isError: false, isLoading: false
        }
    },
    methods: {
        async registerUser() {
            if (this.form.password !== this.form.confirmPassword) {
                this.message = "Passwords do not match.";
                this.isError = true; 
                return;
            }
            this.isLoading = true; 
            this.message = '';

            try {
                const response = await fetch('http://127.0.0.1:5000/api/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(this.form)
                });
                const data = await response.json();
                
                if (response.ok) {
                    this.message = data.msg + " Redirecting to secure login...";
                    this.isError = false;
                    setTimeout(() => { window.location.href = 'index.html'; }, 2000);
                } else {
                    this.message = data.msg || 'Registration failed.';
                    this.isError = true;
                }
            } catch (error) {
                this.message = 'Network error. Server offline.';
                this.isError = true;
            } finally { 
                this.isLoading = false; 
            }
        }
    }
}).mount('#register-app');