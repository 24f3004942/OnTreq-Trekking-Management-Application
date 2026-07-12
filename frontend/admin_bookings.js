const { createApp } = Vue;

createApp({
    data() {
        return {
            bookings: [],
            searchQuery: '',
            message: ''
        }
    },
    computed: {
        filteredBookings() {
            if (!this.searchQuery) return this.bookings;
            // Search by booking ID
            return this.bookings.filter(b => 
                b.id.toString().includes(this.searchQuery) ||
                b.user_email.toLowerCase().includes(this.searchQuery.toLowerCase())
            );
        }
    },
    mounted() {
        const token = localStorage.getItem('token');
        if (!token || localStorage.getItem('role') !== 'admin') {
            window.location.href = 'index.html';
            return;
        }
        this.fetchBookings();
    },
    methods: {
        async fetchBookings() {
            try {
                const response = await fetch('http://127.0.0.1:5000/api/admin/bookings', {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.ok) {
                    this.bookings = await response.json();
                } else if (response.status === 401) {
                    this.logout();
                }
            } catch (error) {
                console.error("Error fetching bookings:", error);
            }
        },
        logout() {
            localStorage.clear();
            window.location.href = 'index.html';
        }
    }
}).mount('#admin-bookings-app');