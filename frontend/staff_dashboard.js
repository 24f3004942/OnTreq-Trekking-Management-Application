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
    computed: {
        openTreksCount() {
            return this.myTreks.filter(t => t.status === 'Open').length;
        },
        totalParticipants() {
            // FIX: backend's /api/staff-ops/my-treks returns the count under the
            // key `participants` (matches what the per-row badge already used
            // in staff_dashboard.html) - this was reading `participant_count`,
            // which never existed, so the dashboard total was always stuck at 0.
            return this.myTreks.reduce((total, trek) => total + (trek.participants || 0), 0);
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

        // Wireframe screen 9: explicit "Mark as Completed" action.
        // Sets the status and persists immediately (backend cascades all
        // 'Booked' bookings on this trek to 'Completed').
        async markCompleted(trek) {
            if (!confirm(`Mark "${trek.name}" as Completed? All active bookings will be closed out.`)) return;
            trek.status = 'Completed';
            await this.saveTrekUpdates(trek);
            this.fetchMyTreks();
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
                    bootstrap.Modal.getOrCreateInstance(document.getElementById('participantsModal')).show();
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