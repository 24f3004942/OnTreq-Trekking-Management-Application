const { createApp } = Vue;

createApp({
    data() {
        return {
            staffList: [],
            searchQuery: '',
            form: { name: '', email: '', contact: '', password: '', confirmPassword: '', years_experience: '', certifications: '' },
            message: '',
            isError: false,
            isLoading: false
        }
    },
    computed: {
        // Milestone 3 Requirement: "Search users, staff, or treks"
        filteredStaff() {
            if (!this.searchQuery) return this.staffList;
            const q = this.searchQuery.toLowerCase();
            return this.staffList.filter(s =>
                s.name.toLowerCase().includes(q) || s.email.toLowerCase().includes(q) || String(s.id).includes(q)
            );
        }
    },
    mounted() {
        const token = localStorage.getItem('token');
        const role = localStorage.getItem('role');
        if (!token || role !== 'admin') {
            window.location.href = 'index.html';
            return;
        }
        this.fetchStaff();
    },
    methods: {
        async fetchStaff() {
            try {
                const response = await fetch('http://127.0.0.1:5000/api/staff/', {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.status === 401) return this.handleSessionExpired();
                if (response.ok) this.staffList = await response.json();
            } catch (error) {
                console.error("Error fetching staff:", error);
            }
        },
        async submitForm() {
            this.isLoading = true;
            this.message = '';
            try {
                const response = await fetch('http://127.0.0.1:5000/api/staff/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify(this.form)
                });
                if (response.status === 401) return this.handleSessionExpired();
                const data = await response.json();
                if (response.ok) {
                    this.message = data.msg;
                    this.isError = false;
                    this.fetchStaff();
                    this.form = { name: '', email: '', contact: '', password: '' };
                } else {
                    this.message = data.msg || 'Operation failed.';
                    this.isError = true;
                }
            } catch (error) {
                this.message = 'Network error occurred.';
                this.isError = true;
            } finally {
                this.isLoading = false;
            }
        },
        async toggleStatus(staff) {
            const action = staff.is_active ? 'blacklist' : 'reactivate';
            if (!confirm(`Are you sure you want to ${action} ${staff.name}?`)) return;
            try {
                const response = await fetch(`http://127.0.0.1:5000/api/staff/${staff.id}/toggle-status`, {
                    method: 'PUT',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.status === 401) return this.handleSessionExpired();
                const data = await response.json();
                if (response.ok) {
                    this.message = data.msg;
                    this.isError = false;
                    this.fetchStaff();
                } else {
                    this.message = data.msg || 'Operation failed.';
                    this.isError = true;
                }
            } catch (error) {
                this.message = 'Network error occurred.';
                this.isError = true;
            }
        },
        async removeStaff(id) {
            if (!confirm("Are you sure you want to revoke this staff member's access? This will permanently delete their account.")) return;
            try {
                const response = await fetch(`http://127.0.0.1:5000/api/staff/${id}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.status === 401) return this.handleSessionExpired();
                if (response.ok) {
                    this.message = 'Staff access revoked successfully.';
                    this.isError = false;
                    this.fetchStaff();
                }
            } catch (error) {
                this.message = 'Network error during deletion.';
                this.isError = true;
            }
        },
        handleSessionExpired() {
            alert("Your security session has expired. Please log in again.");
            this.logout();
        },
        logout() {
            localStorage.removeItem('token');
            localStorage.removeItem('role');
            window.location.href = 'index.html';
        }
    }
}).mount('#manage-staff-app');