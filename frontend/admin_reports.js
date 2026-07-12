const { createApp } = Vue;

createApp({
    mounted() {
        const token = localStorage.getItem('token');
        if (!token || localStorage.getItem('role') !== 'admin') {
            window.location.href = 'index.html';
            return;
        }
        this.fetchAnalytics();
    },
    methods: {
        async fetchAnalytics() {
            try {
                const response = await fetch('http://127.0.0.1:5000/api/admin/analytics', {
                    headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                });
                if (response.ok) {
                    const data = await response.json();
                    this.renderCharts(data);
                }
            } catch (error) {
                console.error("Failed to load analytics");
            }
        },
        renderCharts(data) {
            // Chart 1: Difficulty Breakdown
            new Chart(document.getElementById('difficultyChart'), {
                type: 'doughnut',
                data: {
                    labels: ['Easy', 'Moderate', 'Hard', 'Extreme'],
                    datasets: [{
                        data: data.difficulty_chart,
                        backgroundColor: ['#2ed573', '#1e90ff', '#ffa502', '#ff4757'],
                        borderWidth: 0
                    }]
                },
                options: { plugins: { legend: { labels: { color: '#fff' } } } }
            });

            // Chart 2: Booking Status
            new Chart(document.getElementById('statusChart'), {
                type: 'bar',
                data: {
                    labels: ['Active Bookings', 'Cancelled', 'Completed'],
                    datasets: [{
                        label: 'Total Count',
                        data: data.booking_status_chart,
                        backgroundColor: ['#1e90ff', '#a4b0be', '#2ed573']
                    }]
                },
                options: {
                    scales: {
                        y: { ticks: { color: '#fff' }, grid: { color: '#333' } },
                        x: { ticks: { color: '#fff' }, grid: { display: false } }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        },
        logout() {
            localStorage.clear();
            window.location.href = 'index.html';
        }
    }
}).mount('#reports-app');