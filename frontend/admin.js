const { createApp } = Vue;

createApp({
    data() {
        return {
            stats: {
                treks: 0,
                users: 0,
                staff: 0,
                bookings: 0
            }
        }
    },
    mounted() {
        // SECURITY GUARD: Check if user is logged in AND is an admin
        const token = localStorage.getItem('token');
        const role = localStorage.getItem('role');

        if (!token || role !== 'admin') {
            alert("Unauthorized access. Redirecting to login.");
            window.location.href = 'index.html';
            return;
        }

        // Fetch stats when page loads
        this.fetchStats();
    },
    methods: {
        async fetchStats() {
            try {
                const response = await fetch('http://127.0.0.1:5000/api/admin/stats', {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    this.stats = data;
                }
            } catch (error) {
                console.error("Failed to load dashboard stats:", error);
            }
        },
        logout() {
            localStorage.removeItem('token');
            localStorage.removeItem('role');
            window.location.href = 'index.html';
        }
    }
}).mount('#admin-app');