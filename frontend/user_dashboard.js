const { createApp } = Vue;

createApp({
    data() {
        return {
            treks: [],
            myBookings: [],
            searchQuery: '',
            filterDifficulty: '',
            filterDuration: '',
            message: '',
            isError: false,
            isLoading: false,
            currentTab: 'browse',
            profileForm: { email: '', password: '' },
            exportStatus: '',
            selectedTrekId: null,
            selectedTrekName: '',
            isProcessingPayment: false,
            loadError: false, // true when the trek catalog could not be fetched
            userEmail: '', // NEW: For the Welcome Message
            selectedTrekDetails: null // NEW: For the Details Modal
        }
    },
    computed: {
        // Wireframe screen 12: Trekking History = completed & cancelled only.
        pastBookings() {
            return this.myBookings.filter(b => b.status === 'Completed' || b.status === 'Cancelled');
        },
        filteredTreks() {
            return this.treks.filter(trek => {
                if (trek.status !== 'Open' || trek.available_slots <= 0) return false;
                
                const matchesSearch = trek.name.toLowerCase().includes(this.searchQuery.toLowerCase()) || 
                                      trek.location.toLowerCase().includes(this.searchQuery.toLowerCase());
                const matchesDiff = this.filterDifficulty === '' || trek.difficulty === this.filterDifficulty;
                
                let matchesDur = true;
                if (this.filterDuration === 'short') matchesDur = trek.duration <= 3;
                if (this.filterDuration === 'medium') matchesDur = trek.duration > 3 && trek.duration <= 7;
                if (this.filterDuration === 'long') matchesDur = trek.duration > 7;

                return matchesSearch && matchesDiff && matchesDur;
            });
        }
    },
    mounted() {
       const token = localStorage.getItem('token');
        const role = localStorage.getItem('role');
        if (!token || role !== 'trekker') {
            window.location.href = 'index.html';
            return;
        }
        
        // Welcome the user by FIRST NAME (per wireframe: "Welcome, Amit!").
        // The JWT now carries first_name as an additional claim; if it's
        // missing (older token), fall back to /api/auth/me, then to the
        // email's local part as a last resort.
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            this.userEmail = payload.first_name || '';
            if (!this.userEmail) {
                fetch('http://127.0.0.1:5000/api/auth/me', {
                    headers: { 'Authorization': `Bearer ${token}` }
                }).then(r => r.ok ? r.json() : null).then(me => {
                    if (me && me.first_name) this.userEmail = me.first_name;
                    else if (me && me.email) this.userEmail = me.email.split('@')[0];
                });
                const p = JSON.parse(atob(token.split('.')[1]));
                this.userEmail = (p.email || 'Adventurer').split('@')[0];
            }
        } catch(e) {
            this.userEmail = 'Adventurer';
        }

        this.fetchTreks();
        this.fetchMyBookings();
    },
    updated() {
        // Scroll Animation Logic
        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    obs.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15, rootMargin: "0px 0px -50px 0px" });
        
        document.querySelectorAll('.reveal-up:not(.is-visible)').forEach((el) => {
            observer.observe(el);
        });
    },
    methods: {
        async startExport() {
            this.exportStatus = 'Initializing secure export...';
            try {
                const response = await fetch('http://127.0.0.1:5000/api/user-ops/export', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                const data = await response.json();
                
                if (response.ok) {
                    this.pollExportStatus(data.task_id); // Start tracking it!
                } else {
                    this.exportStatus = 'Failed to start export.';
                }
            } catch (error) {
                this.exportStatus = 'Network error.';
            }
        },
        
        async pollExportStatus(taskId) {
            // Check the status every 1.5 seconds
            const interval = setInterval(async () => {
                const res = await fetch(`http://127.0.0.1:5000/api/user-ops/export/status/${taskId}`, {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                const data = await res.json();
                this.exportStatus = data.msg; // Update UI with current status
                
                if (data.state === 'SUCCESS') {
                    clearInterval(interval);
                    this.exportStatus = 'Download starting...';
                    
                    // Force the browser to download the file
                    window.location.href = `http://127.0.0.1:5000/api/user-ops/export/download/${data.filename}`;
                    
                    // Clear the message after a few seconds
                    setTimeout(() => { this.exportStatus = ''; }, 3000);
                } else if (data.state === 'FAILURE') {
                    clearInterval(interval);
                }
            }, 1500);
        },

        getTrekImage(id) {
            const premiumImages = [
                'https://images.unsplash.com/photo-1522163182402-834f871fd851?auto=format&fit=crop&w=800&q=80',
                'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=800&q=80',
                'https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=800&q=80',
                'https://images.unsplash.com/photo-1454496522488-7a8e488e8606?auto=format&fit=crop&w=800&q=80',
                'https://images.unsplash.com/photo-1486870591958-9b9d0d1dda99?auto=format&fit=crop&w=800&q=80',
                'https://images.unsplash.com/photo-1605649487212-4d4ce7714201?auto=format&fit=crop&w=800&q=80'
            ];
            return premiumImages[id % premiumImages.length];
        },
        async fetchTreks() {
            try {
                const response = await fetch('http://127.0.0.1:5000/api/treks/'); 
                if (response.ok) this.treks = await response.json();
            } catch (error) { console.error("Error fetching treks:", error); }
        },
        async fetchMyBookings() {
            try {
                const response = await fetch('http://127.0.0.1:5000/api/user-ops/my-bookings', {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.ok) this.myBookings = await response.json();
            } catch (error) { console.error("Error fetching bookings:", error); }
        },
        // UPDATED: Book Route (Replaced alerts with Toasts)
        async bookRoute(trekId) {
            this.isLoading = true;
            try {
                const response = await fetch(`http://127.0.0.1:5000/api/user-ops/book/${trekId}`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.status === 401) return this.handleSessionExpired();
                const data = await response.json();
                
                if (response.ok) {
                    this.showToast(data.msg, true);
                    this.fetchTreks(); 
                    this.fetchMyBookings(); 
                    this.currentTab = 'history'; 
                } else {
                    this.showToast("Booking Failed: " + data.msg, false);
                }
            } catch (error) {
                this.showToast("Network error occurred.", false);
            } finally {
                this.isLoading = false;
            }
        },

        // NEW: Cancel an active booking (releases the trek slot back to the pool)
        async cancelBooking(bookingId) {
            if (!confirm("Cancel this booking? Your slot will be released back for other trekkers.")) return;
            this.isLoading = true;
            try {
                const response = await fetch(`http://127.0.0.1:5000/api/user-ops/my-bookings/${bookingId}/cancel`, {
                    method: 'PUT',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.status === 401) return this.handleSessionExpired();
                const data = await response.json();
                if (response.ok) {
                    this.showToast(data.msg, true);
                    this.fetchMyBookings();
                    this.fetchTreks();
                } else {
                    this.showToast(data.msg || 'Could not cancel booking.', false);
                }
            } catch (error) {
                this.showToast('Network error occurred.', false);
            } finally {
                this.isLoading = false;
            }
        },

        // NEW: Toast Notification Handler
        showToast(message, isSuccess = true) {
            const toastEl = document.getElementById('liveToast');
            const msgEl = document.getElementById('toastMessage');
            msgEl.textContent = message;
            msgEl.className = `toast-body fw-bold ${isSuccess ? 'text-success' : 'text-danger'}`;
            const toast = new bootstrap.Toast(toastEl);
            toast.show();
        },

        // Remove any orphaned Bootstrap backdrops / body scroll locks.
        // Prevents the "page frozen behind a grey overlay" state when
        // switching between the details modal and the payment modal.
        cleanupModalArtifacts() {
            if (!document.querySelector('.modal.show')) {
                document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';
            }
        },

        // NEW: Intercept booking click to show Payment Modal
        initiateBooking(trekId, trekName) {
            this.selectedTrekId = trekId;
            this.selectedTrekName = trekName;

            const detailsEl = document.getElementById('detailsModal');
            const detailsInst = detailsEl ? bootstrap.Modal.getInstance(detailsEl) : null;
            const openPayment = () => {
                this.cleanupModalArtifacts();
                bootstrap.Modal.getOrCreateInstance(document.getElementById('paymentModal')).show();
            };

            if (detailsInst && detailsEl.classList.contains('show')) {
                // Wait for the details modal to fully hide before opening the
                // payment modal, so their backdrops never overlap.
                detailsEl.addEventListener('hidden.bs.modal', openPayment, { once: true });
                detailsInst.hide();
            } else {
                openPayment();
            }
        },

        // Wireframe screen 10: "View Details" action on a booking row -
        // looks the trek up from the loaded catalog and reuses the details modal.
        viewBookingTrek(trekId) {
            const trek = this.treks.find(t => t.id === trekId);
            if (trek) this.viewDetails(trek);
            else this.showToast('Trek details are no longer available.', false);
        },

        viewDetails(trek) {
            this.selectedTrekDetails = trek;
            bootstrap.Modal.getOrCreateInstance(document.getElementById('detailsModal')).show();
        },

        // NEW: Simulate Payment Gateway Delay
        async processPayment() {
            this.isProcessingPayment = true;
            setTimeout(() => {
                this.isProcessingPayment = false;
                const el = document.getElementById('paymentModal');
                const modal = bootstrap.Modal.getInstance(el);
                if (modal) modal.hide();
                // Once fully hidden, clear any leftover backdrop before booking.
                el.addEventListener('hidden.bs.modal', () => this.cleanupModalArtifacts(), { once: true });
                setTimeout(() => this.cleanupModalArtifacts(), 500); // safety net
                // Proceed to actual backend booking API
                this.bookRoute(this.selectedTrekId);
            }, 1500); // 1.5 second fake processing delay
        },

        // UPDATED: Profile Update (Replaced alerts with Toasts)
        async updateProfile() {
            this.isLoading = true;
            try {
                const response = await fetch('http://127.0.0.1:5000/api/user-ops/profile', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token')}` },
                    body: JSON.stringify(this.profileForm)
                });
                const data = await response.json();
                if (response.ok) {
                    this.showToast(data.msg, true);
                    this.profileForm = { email: '', password: '' };
                } else {
                    this.showToast("Error: " + data.msg, false);
                }
            } catch (error) { this.showToast("Network error.", false); } 
            finally { this.isLoading = false; }
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
}).mount('#user-app');