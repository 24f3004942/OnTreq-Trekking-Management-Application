const { createApp } = Vue;

createApp({
    data() {
        return {
            stats: {
                treks: 0,
                users: 0,
                staff: 0,
                bookings: 0
            },
            recentBookings: [] // Added this for the dashboard feed
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

        // Fetch stats and recent bookings when page loads
        this.fetchStats();
        this.fetchRecentBookings();
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
        async fetchRecentBookings() {
            try {
                const response = await fetch('http://127.0.0.1:5000/api/admin/bookings', {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    // Reverse to get newest first, then slice the top 5
                    this.recentBookings = data.reverse().slice(0, 5); 
                }
            } catch (error) {
                console.error("Failed to fetch recent bookings:", error);
            }
        },
        logout() {
            localStorage.removeItem('token');
            localStorage.removeItem('role');
            window.location.href = 'index.html';
        }
    }
}).mount('#admin-app');