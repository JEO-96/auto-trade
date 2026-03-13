'use client';

import React from 'react';

const KAKAO_CLIENT_ID = process.env.NEXT_PUBLIC_KAKAO_CLIENT_ID || 'YOUR_KAKAO_CLIENT_ID';

export default function KakaoLoginButton() {
    const handleKakaoLogin = () => {
        const redirectUri = `${window.location.origin}/auth/kakao`;
        const kakaoAuthUrl = `https://kauth.kakao.com/oauth/authorize?client_id=${KAKAO_CLIENT_ID}&redirect_uri=${redirectUri}&response_type=code`;
        window.location.href = kakaoAuthUrl;
    };

    return (
        <button
            onClick={handleKakaoLogin}
            className="w-full bg-[#FEE500] hover:bg-[#FDD835] active:bg-[#F9C800] text-[#191919] font-semibold py-3 px-4 rounded-xl flex items-center justify-center gap-3 transition-all text-sm"
        >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path fillRule="evenodd" clipRule="evenodd" d="M12 4C7.58172 4 4 6.83502 4 10.3318C4 12.5511 5.46746 14.5029 7.67104 15.656L6.77258 18.9482C6.72684 19.1157 6.8173 19.2921 6.98227 19.3621C7.03608 19.3849 7.09457 19.3892 7.1511 19.3744L11.0286 18.3562C11.3475 18.4019 11.6708 18.4251 11.9998 18.4251C16.4181 18.4251 19.9998 15.5901 19.9998 12.0933C19.9998 8.59654 16.4181 5.76152 12 5.76152" fill="#191919" />
                <path d="M12 4C7.58172 4 4 6.83502 4 10.3318C4 12.5511 5.46746 14.5029 7.67104 15.656L6.77258 18.9482C6.72684 19.1157 6.8173 19.2921 6.98227 19.3621C7.03608 19.3849 7.09457 19.3892 7.1511 19.3744L11.0286 18.3562C11.3475 18.4019 11.6708 18.4251 11.9998 18.4251C16.4181 18.4251 19.9998 15.5901 19.9998 12.0933C19.9998 8.59654 16.4181 4 12 4Z" fill="#191919" />
            </svg>
            카카오로 시작하기
        </button>
    );
}
