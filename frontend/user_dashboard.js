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
            profileForm: { email: '', password: '' }
        }
    },
    computed: {
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
        async bookRoute(trekId, trekName) {
            if (!confirm(`Are you ready to book the ${trekName} adventure?`)) return;
            this.isLoading = true;
            try {
                const response = await fetch(`http://127.0.0.1:5000/api/user-ops/book/${trekId}`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.status === 401) return this.handleSessionExpired();
                const data = await response.json();
                if (response.ok) {
                    alert(data.msg); 
                    this.fetchTreks(); 
                    this.fetchMyBookings(); 
                    this.currentTab = 'history'; 
                } else {
                    alert("Booking Failed: " + data.msg);
                }
            } catch (error) {
                alert("Network error occurred.");
            } finally {
                this.isLoading = false;
            }
        },
        async updateProfile() {
            this.isLoading = true;
            try {
                const response = await fetch('http://127.0.0.1:5000/api/user-ops/profile', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    },
                    body: JSON.stringify(this.profileForm)
                });
                const data = await response.json();
                if (response.ok) {
                    alert(data.msg);
                    this.profileForm = { email: '', password: '' };
                } else {
                    alert("Error: " + data.msg);
                }
            } catch (error) {
                alert("Network error.");
            } finally {
                this.isLoading = false;
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
}).mount('#user-app');