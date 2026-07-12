const { createApp } = Vue;

createApp({
    data() {
        return {
            users: [],
            searchQuery: '',
            message: '',
            isError: false
        }
    },
    computed: {
        // Milestone 3 Requirement: "Search users, staff, or treks"
        filteredUsers() {
            if (!this.searchQuery) return this.users;
            return this.users.filter(user => 
                user.email.toLowerCase().includes(this.searchQuery.toLowerCase())
            );
        }
    },
    mounted() {
        const token = localStorage.getItem('token');
        if (!token || localStorage.getItem('role') !== 'admin') {
            window.location.href = 'index.html';
            return;
        }
        this.fetchUsers();
    },
    methods: {
        async fetchUsers() {
            try {
                const response = await fetch('http://127.0.0.1:5000/api/admin/users', {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.status === 401) return this.handleSessionExpired();
                if (response.ok) this.users = await response.json();
            } catch (error) {
                console.error("Error fetching users:", error);
            }
        },
        async toggleStatus(user) {
            const action = user.is_active ? 'blacklist' : 'activate';
            if (!confirm(`Are you sure you want to ${action} this user?`)) return;

            try {
                const response = await fetch(`http://127.0.0.1:5000/api/admin/users/${user.id}/toggle-status`, {
                    method: 'PUT',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.status === 401) return this.handleSessionExpired();
                
                const data = await response.json();
                if (response.ok) {
                    this.message = data.msg;
                    this.isError = false;
                    this.fetchUsers(); // Refresh the list
                }
            } catch (error) {
                this.message = 'Network error occurred.';
                this.isError = true;
            }
        },
        handleSessionExpired() {
            alert("Session expired. Please log in again.");
            localStorage.clear();
            window.location.href = 'index.html';
        },
        logout() {
            localStorage.clear();
            window.location.href = 'index.html';
        }
    }
}).mount('#manage-users-app');