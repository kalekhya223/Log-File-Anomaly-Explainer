// Chart rendering logic for LogSentry AI Results page

document.addEventListener('DOMContentLoaded', () => {
    // Check if CHARTS_DATA is available in global namespace
    if (typeof CHARTS_DATA === 'undefined') {
        console.warn('CHARTS_DATA is not defined. Skipping chart initialization.');
        return;
    }

    let levelChart = null;
    let trendChart = null;
    let anomalyChart = null;

    // Helper to get colors based on theme
    function getThemeColors() {
        const theme = document.documentElement.getAttribute('data-theme') || 'dark';
        if (theme === 'dark') {
            return {
                text: '#94a3b8',
                grid: 'rgba(255, 255, 255, 0.08)',
                cardBg: '#161e31'
            };
        } else {
            return {
                text: '#475569',
                grid: 'rgba(0, 0, 0, 0.08)',
                cardBg: '#ffffff'
            };
        }
    }

    function initCharts() {
        const colors = getThemeColors();

        // -------------------------------------------------------------
        // Chart 1: Log Level Distribution (Doughnut Chart)
        // -------------------------------------------------------------
        const levelCanvas = document.getElementById('levelDistributionChart');
        if (levelCanvas) {
            const levelData = CHARTS_DATA.levels_distribution;
            const labels = Object.keys(levelData);
            const data = Object.values(levelData);

            // Palette matching our levels
            const colorsMap = {
                'DEBUG': '#64748b',    // Slate
                'INFO': '#3b82f6',     // Blue
                'WARNING': '#f59e0b',  // Amber
                'ERROR': '#ef4444',    // Rose
                'CRITICAL': '#b91c1c'  // Deep Red
            };
            const backgroundColors = labels.map(lbl => colorsMap[lbl] || '#cbd5e1');

            if (levelChart) levelChart.destroy();

            levelChart = new Chart(levelCanvas, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: backgroundColors,
                        borderWidth: 2,
                        borderColor: colors.cardBg,
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: colors.text,
                                font: { family: 'Outfit', size: 11 }
                            }
                        }
                    },
                    cutout: '65%'
                }
            });
        }

        // -------------------------------------------------------------
        // Chart 2: Severe Issues Trend (Line Chart)
        // -------------------------------------------------------------
        const trendCanvas = document.getElementById('errorTrendChart');
        if (trendCanvas) {
            const trendData = CHARTS_DATA.error_trend;

            if (trendChart) trendChart.destroy();

            trendChart = new Chart(trendCanvas, {
                type: 'line',
                data: {
                    labels: trendData.labels,
                    datasets: [{
                        label: 'Severe Events (Errors/Warnings)',
                        data: trendData.data,
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointBackgroundColor: '#818cf8',
                        pointBorderColor: colors.cardBg,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                color: colors.grid
                            },
                            ticks: {
                                color: colors.text,
                                font: { family: 'Outfit', size: 10 },
                                maxRotation: 45,
                                minRotation: 45
                            }
                        },
                        y: {
                            grid: {
                                color: colors.grid
                            },
                            ticks: {
                                color: colors.text,
                                font: { family: 'Outfit', size: 10 },
                                stepSize: 1,
                                precision: 0
                            },
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        // -------------------------------------------------------------
        // Chart 3: Anomaly Distribution (Horizontal Bar Chart)
        // -------------------------------------------------------------
        const anomalyCanvas = document.getElementById('anomalyDistributionChart');
        if (anomalyCanvas) {
            const anomalyData = CHARTS_DATA.anomalies_distribution;
            const labels = Object.keys(anomalyData);
            const data = Object.values(anomalyData);

            if (anomalyChart) anomalyChart.destroy();

            if (labels.length > 0) {
                anomalyChart = new Chart(anomalyCanvas, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: data,
                            backgroundColor: [
                                'rgba(139, 92, 246, 0.75)', // Violet
                                'rgba(59, 130, 246, 0.75)',  // Blue
                                'rgba(239, 68, 68, 0.75)',   // Red
                                'rgba(245, 158, 11, 0.75)',  // Orange
                                'rgba(16, 185, 129, 0.75)'   // Emerald
                            ],
                            borderColor: colors.cardBg,
                            borderWidth: 1,
                            borderRadius: 6
                        }]
                    },
                    options: {
                        indexAxis: 'y', // Makes it horizontal
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: false
                            }
                        },
                        scales: {
                            x: {
                                grid: {
                                    color: colors.grid
                                },
                                ticks: {
                                    color: colors.text,
                                    font: { family: 'Outfit', size: 10 },
                                    stepSize: 1,
                                    precision: 0
                                },
                                beginAtZero: true
                            },
                            y: {
                                grid: {
                                    display: false
                                },
                                ticks: {
                                    color: colors.text,
                                    font: { family: 'Outfit', size: 10 }
                                }
                            }
                        }
                    }
                });
            }
        }
    }

    // Initialize charts
    initCharts();

    // Re-initialize charts on theme toggle to match theme colors
    const themeToggleBtn = document.getElementById('themeToggle');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            // Wait slightly for DOM attribute changes
            setTimeout(initCharts, 50);
        });
    }
});
