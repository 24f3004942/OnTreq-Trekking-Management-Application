const { createApp } = Vue;

createApp({
    data() {
        return {
            bookings: [], // This will hold the data once users start booking
            searchQuery: '',
            message: ''
        }
    },
    mounted() {
        // SECURITY GUARD
        const token = localStorage.getItem('token');
        const role = localStorage.getItem('role');
        
        if (!token || role !== 'admin') {
            window.location.href = 'index.html';
            return;
        }
        
        // Note: We will add the fetchBookings() API call here in Milestone 5 
        // once the User Booking Engine is actually built!
    },
    methods: {
        logout() {
            localStorage.clear();
            window.location.href = 'index.html';
        }
    }
}).mount('#admin-bookings-app');