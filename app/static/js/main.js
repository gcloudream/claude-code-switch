// Main JavaScript for Claude API Relay Station

class ClaudeRelay {
    constructor() {
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupAlerts();
        this.setupCharts();
        this.setupTheme();
        this.addThemeToggle();
    }
    
    setupEventListeners() {
        // Copy API key functionality
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('copy-btn')) {
                this.copyToClipboard(e.target);
            }
        });
        
        // Modal functionality
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-trigger')) {
                this.openModal(e.target.dataset.modal);
            }
            
            if (e.target.classList.contains('modal-close')) {
                this.closeModal();
            }
        });
        
        // Form submissions
        document.addEventListener('submit', (e) => {
            if (e.target.classList.contains('async-form')) {
                e.preventDefault();
                this.handleAsyncForm(e.target);
            }
        });
        
        // Auto-hide alerts
        setTimeout(() => {
            document.querySelectorAll('.alert').forEach(alert => {
                alert.style.transition = 'opacity 0.3s ease';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 300);
            });
        }, 5000);
    }
    
    setupAlerts() {
        // Auto-dismiss alerts after 5 seconds
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            setTimeout(() => {
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 300);
            }, 5000);
        });
    }
    
    setupCharts() {
        // Setup Chart.js defaults for dark theme
        if (typeof Chart !== 'undefined') {
            Chart.defaults.color = '#b0b0b0';
            Chart.defaults.backgroundColor = 'rgba(99, 102, 241, 0.1)';
            Chart.defaults.borderColor = '#6366f1';
            Chart.defaults.scale.grid.color = '#3a3a3a';
            Chart.defaults.plugins.legend.labels.usePointStyle = true;
        }
    }
    
    // Utility functions
    copyToClipboard(button) {
        const text = button.dataset.copy || button.textContent;
        navigator.clipboard.writeText(text).then(() => {
            const original = button.textContent;
            button.textContent = '已复制!';
            button.classList.add('btn-success');
            
            setTimeout(() => {
                button.textContent = original;
                button.classList.remove('btn-success');
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy: ', err);
            this.showAlert('复制失败', 'error');
        });
    }
    
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
    }
    
    closeModal() {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.style.display = 'none';
        });
        document.body.style.overflow = 'auto';
    }
    
    showAlert(message, type = 'info') {
        const alertContainer = document.querySelector('.alert-container') || document.querySelector('.main .container');
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        
        alertContainer.insertBefore(alert, alertContainer.firstChild);
        
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    }
    
    async handleAsyncForm(form) {
        const formData = new FormData(form);
        const button = form.querySelector('button[type="submit"]');
        const originalText = button.textContent;
        
        button.disabled = true;
        button.innerHTML = '<span class="loading"></span> 处理中...';
        
        try {
            const response = await fetch(form.action, {
                method: form.method,
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const result = await response.json();
            
            if (response.ok) {
                this.showAlert(result.message || '操作成功', 'success');
                if (result.redirect) {
                    window.location.href = result.redirect;
                }
                if (result.refresh) {
                    window.location.reload();
                }
            } else {
                this.showAlert(result.error || '操作失败', 'error');
            }
        } catch (error) {
            console.error('Form submission error:', error);
            this.showAlert('网络错误，请重试', 'error');
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
    
    // Chart creation helpers
    createUsageChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Token使用量',
                    data: data.values,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#3a3a3a'
                        }
                    },
                    x: {
                        grid: {
                            color: '#3a3a3a'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
    
    createModelUsageChart(canvasId, data) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;
        
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.labels,
                datasets: [{
                    data: data.values,
                    backgroundColor: [
                        '#6366f1',
                        '#8b5cf6',
                        '#10b981',
                        '#f59e0b',
                        '#ef4444'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    // API helpers
    async apiRequest(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };
        
        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return response.json();
    }
    
    // Utility functions
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }
    
    formatDateTime(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN');
    }
    
    formatDuration(ms) {
        if (ms < 1000) {
            return ms.toFixed(0) + 'ms';
        } else {
            return (ms / 1000).toFixed(1) + 's';
        }
    }
    
    // Theme management
    setupTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
    }
    
    addThemeToggle() {
        // Only add theme toggle if not already present
        if (document.querySelector('.theme-toggle')) return;
        
        const toggle = document.createElement('button');
        toggle.className = 'theme-toggle';
        toggle.innerHTML = '<span class="theme-toggle-icon">🌙</span>';
        toggle.setAttribute('aria-label', 'Toggle theme');
        toggle.setAttribute('title', 'Toggle light/dark theme');
        
        toggle.addEventListener('click', () => this.toggleTheme());
        document.body.appendChild(toggle);
        
        this.updateThemeIcon();
    }
    
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        this.updateThemeIcon();
        this.showAlert(`已切换到${newTheme === 'dark' ? '暗色' : '亮色'}主题`, 'success');
    }
    
    updateThemeIcon() {
        const toggle = document.querySelector('.theme-toggle-icon');
        if (toggle) {
            const theme = document.documentElement.getAttribute('data-theme');
            toggle.textContent = theme === 'dark' ? '☀️' : '🌙';
        }
    }
    
    // Enhanced notification system
    showNotification(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>${this.getNotificationIcon(type)}</span>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" style="margin-left: auto; background: none; border: none; color: inherit; cursor: pointer; font-size: 1.2em;">&times;</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        requestAnimationFrame(() => {
            notification.classList.add('show');
        });
        
        // Auto remove
        setTimeout(() => {
            notification.style.transform = 'translateX(400px)';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, duration);
    }
    
    getNotificationIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || icons.info;
    }
    
    // Enhanced loading state management
    showLoading(element, text = '加载中...') {
        if (!element) return;
        
        element.dataset.originalContent = element.innerHTML;
        element.disabled = true;
        element.innerHTML = `<span class="loading"></span> ${text}`;
    }
    
    hideLoading(element) {
        if (!element) return;
        
        element.disabled = false;
        element.innerHTML = element.dataset.originalContent || element.innerHTML;
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.claudeRelay = new ClaudeRelay();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ClaudeRelay;
}