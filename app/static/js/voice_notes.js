/* 音声ノート分析 - Chart.js 可視化 */

/**
 * アイゼンハワーマトリクス散布図
 */
function initMatrixChart(apiUrl) {
    fetch(apiUrl)
        .then(r => r.json())
        .then(data => {
            if (!data.length) return;

            const colorMap = {
                do_first: 'rgba(220, 53, 69, 0.8)',
                schedule: 'rgba(255, 193, 7, 0.8)',
                delegate: 'rgba(255, 140, 0, 0.8)',
                eliminate: 'rgba(173, 181, 189, 0.6)',
            };

            const datasets = {};
            const labels = {
                do_first: '今すぐやる',
                schedule: '計画する',
                delegate: '任せる',
                eliminate: '排除する',
            };

            data.forEach(task => {
                const q = task.quadrant;
                if (!datasets[q]) {
                    datasets[q] = {
                        label: labels[q] || q,
                        data: [],
                        backgroundColor: colorMap[q] || 'rgba(100,100,100,0.5)',
                        borderColor: colorMap[q] || 'rgba(100,100,100,0.8)',
                        borderWidth: 2,
                        pointRadius: task.is_overdue ? 10 : 7,
                        pointHoverRadius: 12,
                    };
                }
                datasets[q].data.push({
                    x: task.urgency,
                    y: task.importance,
                    title: task.title,
                    deadline: task.deadline,
                    isOverdue: task.is_overdue,
                });
            });

            const ctx = document.getElementById('matrixChart');
            if (!ctx) return;

            new Chart(ctx, {
                type: 'scatter',
                data: { datasets: Object.values(datasets) },
                options: {
                    responsive: true,
                    scales: {
                        x: {
                            title: { display: true, text: '緊急度', font: { size: 14 } },
                            min: 0, max: 6,
                            grid: { color: 'rgba(0,0,0,0.05)' },
                        },
                        y: {
                            title: { display: true, text: '重要度', font: { size: 14 } },
                            min: 0, max: 6,
                            grid: { color: 'rgba(0,0,0,0.05)' },
                        },
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const d = context.raw;
                                    let label = d.title;
                                    if (d.deadline) label += ` (期限: ${d.deadline})`;
                                    if (d.isOverdue) label += ' [超過!]';
                                    return label;
                                }
                            }
                        },
                        annotation: {
                            annotations: {
                                line1: {
                                    type: 'line',
                                    xMin: 3.5, xMax: 3.5,
                                    borderColor: 'rgba(0,0,0,0.15)',
                                    borderDash: [5, 5],
                                },
                                line2: {
                                    type: 'line',
                                    yMin: 3.5, yMax: 3.5,
                                    borderColor: 'rgba(0,0,0,0.15)',
                                    borderDash: [5, 5],
                                },
                            }
                        }
                    }
                }
            });
        });
}

/**
 * 思考パターンタイプ分布（ドーナツチャート）
 */
function initPatternChart(apiUrl) {
    fetch(apiUrl)
        .then(r => r.json())
        .then(data => {
            const counts = data.type_counts || {};
            if (!Object.keys(counts).length) return;

            const typeLabels = {
                cognitive_bias: '認知バイアス',
                habit: '習慣',
                strength: '強み',
                weakness: '課題',
            };
            const typeColors = {
                cognitive_bias: '#dc3545',
                habit: '#0dcaf0',
                strength: '#198754',
                weakness: '#ffc107',
            };

            const ctx = document.getElementById('patternTypeChart');
            if (!ctx) return;

            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(counts).map(k => typeLabels[k] || k),
                    datasets: [{
                        data: Object.values(counts),
                        backgroundColor: Object.keys(counts).map(k => typeColors[k] || '#6c757d'),
                        borderWidth: 2,
                        borderColor: '#fff',
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' },
                    }
                }
            });
        });
}

/**
 * 改善進捗レーダーチャート
 */
function initImprovementRadar(apiUrl) {
    fetch(apiUrl)
        .then(r => r.json())
        .then(data => {
            const cats = data.categories || {};
            if (!Object.keys(cats).length) return;

            const ctx = document.getElementById('improvementRadar');
            if (!ctx) return;

            new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: Object.values(cats).map(c => c.label),
                    datasets: [{
                        label: '改善進捗 (%)',
                        data: Object.values(cats).map(c => c.avg_progress),
                        backgroundColor: 'rgba(26, 107, 60, 0.2)',
                        borderColor: '#1a6b3c',
                        pointBackgroundColor: '#1a6b3c',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: '#1a6b3c',
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 100,
                            ticks: { stepSize: 25 },
                        }
                    },
                    plugins: {
                        legend: { display: false },
                    }
                }
            });
        });
}
