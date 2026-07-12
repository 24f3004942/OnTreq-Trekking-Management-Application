const { createApp } = Vue;

createApp({
    data() {
        return {
            myTreks: [],
            participants: [], // NEW: Holds the fetched trekkers
            selectedTrekName: '', // NEW: For the modal title
            message: '',
            isError: false,
            isLoading: false
        }
    },
    mounted() {
        // STRICT SECURITY GUARD: Only Staff allowed
        const token = localStorage.getItem('token');
        const role = localStorage.getItem('role');
        
        if (!token || role !== 'staff') {
            window.location.href = 'index.html';
            return;
        }
        
        this.fetchMyTreks();
    },
    methods: {
        async fetchMyTreks() {
            try {
                const response = await fetch('http://127.0.0.1:5000/api/staff-ops/my-treks', {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                
                if (response.status === 401) return this.handleSessionExpired();
                
                if (response.ok) {
                    this.myTreks = await response.json();
                }
            } catch (error) {
                console.error("Error fetching assigned treks:", error);
            }
        },
        
        async saveTrekUpdates(trek) {
            this.isLoading = true;
            this.message = '';
            
            try {
                const response = await fetch(`http://127.0.0.1:5000/api/staff-ops/my-treks/${trek.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify({
                        status: trek.status,
                        available_slots: trek.available_slots
                    })
                });

                if (response.status === 401) return this.handleSessionExpired();
                
                const data = await response.json();
                
                if (response.ok) {
                    this.message = `Successfully updated ${trek.name}.`;
                    this.isError = false;
                    // Flash success message then hide it after 3 seconds
                    setTimeout(() => { this.message = ''; }, 3000);
                } else {
                    this.message = data.msg || 'Failed to update trek.';
                    this.isError = true;
                }
            } catch (error) {
                this.message = 'Network error occurred.';
                this.isError = true;
            } finally {
                this.isLoading = false;
            }
        },

        // NEW METHOD: Fetch participants and open modal
        async viewParticipants(trek) {
            this.selectedTrekName = trek.name;
            try {
                const response = await fetch(`http://127.0.0.1:5000/api/staff-ops/my-treks/${trek.id}/participants`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.status === 401) return this.handleSessionExpired();
                if (response.ok) {
                    this.participants = await response.json();
                    // Trigger Bootstrap Modal
                    const modal = new bootstrap.Modal(document.getElementById('participantsModal'));
                    modal.show();
                }
            } catch (error) {
                console.error("Error fetching participants:", error);
            }
        },
        
        handleSessionExpired() {
            alert("Session expired. Please log in again.");
            this.logout();
        },
        
        logout() {
            localStorage.clear();
            window.location.href = 'index.html';
        }
    }
}).mount('#staff-app');