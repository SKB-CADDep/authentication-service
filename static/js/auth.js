// Глобальный перехватчик для всех fetch запросов
const originalFetch = window.fetch;
window.fetch = function(...args) {
    let [resource, config] = args;
    
    // Добавляем токен к каждому запросу к API
    if (resource.includes('/api/') || resource.includes('/auth/')) {
        const token = localStorage.getItem('access_token');
        
        if (token) {
            config = config || {};
            config.headers = config.headers || {};
            config.headers['Authorization'] = `Bearer ${token}`;
        }
    }
    
    return originalFetch(resource, config)
        .then(response => {
            // Если 401 - токен истек, перенаправляем на логин
            if (response.status === 401) {
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                localStorage.removeItem('user_info');
                window.location.href = '/login';
            }
            return response;
        });
};

// Функция для выхода
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_info');
    window.location.href = '/login';
}

// Функция для получения информации о текущем пользователе
function getCurrentUser() {
    const userInfo = localStorage.getItem('user_info');
    return userInfo ? JSON.parse(userInfo) : null;
}

// Функция для обновления токена
async function refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
        logout();
        return null;
    }
    
    try {
        const response = await fetch('/auth/refresh', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('refresh_token', data.refresh_token);
            return data.access_token;
        } else {
            logout();
            return null;
        }
    } catch (error) {
        console.error('Token refresh error:', error);
        logout();
        return null;
    }
}

// Проверка авторизации при загрузке страницы
window.addEventListener('DOMContentLoaded', () => {
    const publicPages = ['/login', '/health'];
    const currentPage = window.location.pathname;
    
    // Если это не публичная страница
    if (!publicPages.includes(currentPage)) {
        const token = localStorage.getItem('access_token');
        
        if (!token) {
            // Перенаправляем на логин
            window.location.href = '/login';
        }
    }
});

