const { createApp } = Vue;

createApp({
    data() {
        return {
            treks: [],
            staffList: [],
            searchQuery: '',
            form: { name: '', location: '', difficulty: 'Moderate', duration: '', available_slots: '', start_date: '', end_date: '', base_price: '', max_altitude: '', staff_id: '', status: 'Pending' },
            message: '',
            isError: false,
            isLoading: false,
            isEditing: false,
            editId: null
        }
    },
    computed: {
        todayStr() {
        return new Date().toISOString().split('T')[0];
        },
        // Wireframe screen 4 + Milestone 3: search treks by name, location, or ID
        filteredTreks() {
            if (!this.searchQuery) return this.treks;
            const q = this.searchQuery.toLowerCase();
            return this.treks.filter(t =>
                t.name.toLowerCase().includes(q) ||
                t.location.toLowerCase().includes(q) ||
                String(t.id).includes(q)
            );
        }
    },
    // NEW: Watchers keep an eye on these specific fields
    watch: {
        'form.duration'(newValue) {
            this.calculateEndDate();
        },
        'form.start_date'(newValue) {
            this.calculateEndDate();
        }
    },
    mounted() {
        const token = localStorage.getItem('token');
        const role = localStorage.getItem('role');
        if (!token || role !== 'admin') {
            window.location.href = 'index.html';
            return;
        }
        this.fetchTreks();
        this.fetchStaff();
    },
    methods: {
        // NEW: The auto-calculation logic
        calculateEndDate() {
            if (this.form.start_date && this.form.duration && this.form.duration > 0) {
                // Create a JavaScript Date object from the selected start date
                const start = new Date(this.form.start_date);
                
                // Add the duration. (We subtract 1 because a 1-day trek starting on the 12th ends on the 12th)
                const durationInDays = parseInt(this.form.duration, 10);
                start.setDate(start.getDate() + (durationInDays - 1));
                
                // HTML Date inputs strictly require the YYYY-MM-DD format
                const year = start.getFullYear();
                const month = String(start.getMonth() + 1).padStart(2, '0');
                const day = String(start.getDate()).padStart(2, '0');
                
                this.form.end_date = `${year}-${month}-${day}`;
            }
        },

        /* ... KEEP ALL YOUR OTHER EXISTING METHODS BELOW THIS EXACTLY THE SAME ... */
        
            
        async fetchTreks() {
            try {
                const response = await fetch('http://127.0.0.1:5000/api/treks/', {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.status === 401 || response.status === 422) return this.handleSessionExpired();
                if (response.ok) this.treks = await response.json();
            } catch (error) {
                console.error("Error fetching treks:", error);
            }
        },

        async fetchStaff() {
            try {
                const response = await fetch('http://127.0.0.1:5000/api/staff/', {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.ok) {
                    this.staffList = await response.json();
                }
            } catch (error) {
                console.error("Error fetching staff:", error);
            }
        },
        
        // NEW: Load data into form when "Edit" is clicked
        startEdit(trek) {
            this.isEditing = true;
            this.editId = trek.id;
            // Copy data to form
            this.form = { ...trek, max_altitude: trek.max_altitude || '' };
            this.message = '';
            // Scroll to top so admin can see the form
            window.scrollTo({ top: 0, behavior: 'smooth' });
        },

        // NEW: Cancel editing and clear form
        cancelEdit() {
            this.isEditing = false;
            this.editId = null;
            this.resetForm();
            this.message = '';
        },

        // UPDATED: Handles both Create and Update
        async submitForm() {
            this.isLoading = true;
            this.message = '';
            
            const url = this.isEditing ? `http://127.0.0.1:5000/api/treks/${this.editId}` : 'http://127.0.0.1:5000/api/treks/';
            const method = this.isEditing ? 'PUT' : 'POST';

            try {
                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify(this.form)
                });

                if (response.status === 401 || response.status === 422) return this.handleSessionExpired();
                const data = await response.json();

                if (response.ok) {
                    this.message = data.msg;
                    this.isError = false;
                    this.fetchTreks();
                    this.cancelEdit(); // Reset back to create mode
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

        async deleteTrek(trekId) {
            if (!confirm("Are you sure you want to permanently delete this route? This cannot be undone.")) return;
            try {
                const response = await fetch(`http://127.0.0.1:5000/api/treks/${trekId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.status === 401 || response.status === 422) return this.handleSessionExpired();
                if (response.ok) {
                    this.message = 'Route deleted successfully.';
                    this.isError = false;
                    if (this.editId === trekId) this.cancelEdit(); // If they delete what they are editing
                    this.fetchTreks();
                }
            } catch (error) {
                this.message = 'Network error while trying to delete.';
                this.isError = true;
            }
        },
        resetForm() {
            this.form = {
                id: null, name: '', location: '', difficulty: 'Moderate',
                duration: '', base_price: '', max_altitude: '',
                staff_id: '', available_slots: '', start_date: '', end_date: '',
                status: 'Pending' // <--- JUST ADD THIS LINE
            };
            this.isEditing = false;
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
}).mount('#manage-treks-app');