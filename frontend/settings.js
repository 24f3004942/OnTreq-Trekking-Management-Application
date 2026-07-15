const { createApp } = Vue;

createApp({
    data() {
        return {
            form: { first_name: '', last_name: '', email: '', phone: '', password: '' },
            message: '',
            isError: false,
            isLoading: false
        }
    },
    computed: {
        // Settings is shared across all 3 roles - send "Back to Dashboard" to
        // the right place instead of hardcoding an admin-only link.
        dashboardLink() {
            const role = localStorage.getItem('role');
            if (role === 'admin') return 'admin_dashboard.html';
            if (role === 'staff') return 'staff_dashboard.html';
            return 'user_dashboard.html';
        }
    },
    mounted() {
        // SECURITY GUARD: any logged-in role can reach Settings (Admin/Staff/Trekker)
        const token = localStorage.getItem('token');
        if (!token) {
            window.location.href = 'index.html';
            return;
        }
        this.fetchCurrentProfile();
    },
    methods: {
        async fetchCurrentProfile() {
            try {
                const response = await fetch('http://127.0.0.1:5000/api/auth/me', {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.status === 401) return this.handleSessionExpired();
                const data = await response.json();
                if (response.ok) {
                    this.form.first_name = data.first_name || '';
                    this.form.last_name = data.last_name || '';
                    this.form.email = data.email || '';
                }
            } catch (error) {
                console.error('Failed to load profile:', error);
            }
        },
        async updateSettings() {
            this.isLoading = true;
            this.message = '';
            try {
                const payload = { ...this.form };
                if (!payload.password) delete payload.password; // don't overwrite with blank

                const response = await fetch('http://127.0.0.1:5000/api/auth/profile', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify(payload)
                });
                if (response.status === 401) return this.handleSessionExpired();
                const data = await response.json();

                this.message = data.msg;
                this.isError = !response.ok;
                if (response.ok) {
                    this.form.password = ''; // clear the password field after a successful save
                    localStorage.setItem('email', this.form.email);
                }
            } catch (error) {
                this.message = 'Network error occurred. Please try again.';
                this.isError = true;
            } finally {
                this.isLoading = false;
            }
        },
        handleSessionExpired() {
            localStorage.clear();
            window.location.href = 'index.html';
        },
        logout() {
            localStorage.clear();
            window.location.href = 'index.html';
        }
    }
}).mount('#settings-app');
