import axios from 'axios';

// Create a configured axios instance
const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
});

// 401 리다이렉트 중복 방지 플래그
let isRedirecting = false;

// Request Interceptor: Attach Token automatically
api.interceptors.request.use(
    (config) => {
        if (typeof window !== 'undefined') {
            const token = localStorage.getItem('access_token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Response Interceptor: Handle Global Errors (Like 401 Unauthorized)
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            if (typeof window !== 'undefined' && !isRedirecting) {
                localStorage.removeItem('access_token');
                // 로그인 페이지나 공개 커뮤니티 페이지가 아닌 경우에만 리다이렉트
                const pathname = window.location.pathname;
                const isPublicPage = pathname === '/login' || pathname.startsWith('/community');
                if (!isPublicPage) {
                    isRedirecting = true;
                    window.location.href = '/login';
                }
            }
        }
        return Promise.reject(error);
    }
);

export default api;
