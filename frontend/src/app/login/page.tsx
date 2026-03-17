'use client';
import { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import Logo from '@/components/Logo';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import KakaoLoginButton from '@/components/KakaoLoginButton';
import { useAuth } from '@/contexts/AuthContext';
import api from '@/lib/api';

export default function LoginPage() {
    const [termsAgreed, setTermsAgreed] = useState(false);
    const router = useRouter();
    const { isAuthenticated, isLoading } = useAuth();

    // Redirect to dashboard if already authenticated
    if (!isLoading && isAuthenticated) {
        router.replace('/dashboard');
    }

    // Show blank screen while checking auth or if already authenticated (prevents flash)
    if (isLoading || isAuthenticated) {
        return <div className="min-h-screen bg-[#020617]" />;
    }

    return (
        <div className="min-h-screen flex relative overflow-hidden bg-[#020617] animate-fade-in">
            {/* Left - Branding */}
            <div className="hidden lg:flex lg:w-1/2 relative items-center justify-center p-12">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/[0.06] to-accent/[0.04]" />
                <div className="absolute top-[20%] left-[10%] w-[60%] h-[60%] bg-primary/[0.06] rounded-full blur-[120px] pointer-events-none" />

                <div className="relative z-10 max-w-md">
                    <div className="mb-8">
                        <Logo size="lg" />
                    </div>

                    <h1 className="text-3xl font-bold tracking-tight mb-4 leading-snug text-th-text">
                        백테스트로 검증하고,<br />
                        <span className="text-gradient-primary">수익으로 증명합니다</span>
                    </h1>

                    <p className="text-th-text-secondary leading-relaxed text-sm">
                        전략을 직접 검증하고 신뢰할 수 있는 자동매매를 경험하세요.
                        수익이 날 때만 수수료를 내는 공정한 플랫폼입니다.
                    </p>

                    <div className="mt-10 grid grid-cols-2 gap-4">
                        {[
                            { label: '지원 거래소', value: 'Upbit' },
                            { label: '분석 주기', value: '실시간' },
                            { label: '리스크 관리', value: '자동 손절' },
                            { label: '백테스팅', value: '포트폴리오' },
                        ].map((item) => (
                            <div key={item.label} className="p-3 rounded-xl bg-th-card border border-th-border-light">
                                <p className="text-[10px] font-semibold text-th-text-muted uppercase tracking-wider mb-1">{item.label}</p>
                                <p className="text-sm font-bold text-th-text">{item.value}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Right - Login Form */}
            <div className="flex-1 flex items-center justify-center p-6 lg:p-12">
                <div className="w-full max-w-sm">
                    {/* Mobile logo */}
                    <div className="mb-10 lg:hidden">
                        <Logo size="md" />
                    </div>

                    <div className="mb-8">
                        <h2 className="text-2xl font-bold mb-2 text-th-text">로그인</h2>
                        <p className="text-sm text-th-text-secondary">카카오 계정으로 간편하게 시작하세요.</p>
                    </div>

                    {/* 투자 위험 고지 */}
                    <div className="mb-5 p-4 bg-amber-500/[0.04] border border-amber-500/15 rounded-xl flex items-start gap-3">
                        <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                        <p className="text-xs text-amber-500/80 leading-relaxed">
                            가상자산 투자는 원금 손실 위험이 있습니다. 본 서비스는 투자 권유가 아니며, 모든 투자 결과에 대한 책임은 이용자 본인에게 있습니다.
                        </p>
                    </div>

                    {/* 약관 동의 */}
                    <label className="flex items-start gap-3 cursor-pointer mb-4 group">
                        <input
                            type="checkbox"
                            checked={termsAgreed}
                            onChange={(e) => setTermsAgreed(e.target.checked)}
                            className="mt-0.5 w-4 h-4 accent-primary cursor-pointer shrink-0"
                        />
                        <span className="text-xs text-th-text-muted leading-relaxed group-hover:text-th-text-secondary transition-colors">
                            <Link href="/terms" target="_blank" className="text-primary hover:underline">서비스 이용약관</Link>을 읽었으며, 투자 위험 고지에 동의합니다.
                        </span>
                    </label>

                    <div className={!termsAgreed ? 'opacity-40 pointer-events-none' : ''}>
                        <KakaoLoginButton />
                    </div>

                    {!termsAgreed && (
                        <p className="text-xs text-amber-500/70 mt-2 text-center">약관에 동의해야 로그인할 수 있습니다.</p>
                    )}

                    <p className="text-xs text-th-text-muted mt-6 leading-relaxed text-center">
                        첫 로그인 시 자동으로 가입됩니다.
                    </p>

                    {/* 개발 전용 테스트 로그인 */}
                    {process.env.NODE_ENV === 'development' && (
                        <div className="mt-6 p-4 rounded-xl border border-dashed border-th-border bg-th-card">
                            <p className="text-[10px] text-th-text-muted font-mono uppercase mb-3">Dev Only</p>
                            <div className="flex gap-2">
                                <button
                                    type="button"
                                    onClick={async () => {
                                        const res = await api.post('/auth/dev-login?role=admin');
                                        localStorage.setItem('access_token', res.data.access_token);
                                        window.location.href = '/dashboard';
                                    }}
                                    className="flex-1 px-3 py-2 rounded-lg bg-primary/10 text-primary text-xs font-semibold border border-primary/20 hover:bg-primary/20 transition-colors"
                                >
                                    관리자 로그인
                                </button>
                                <button
                                    type="button"
                                    onClick={async () => {
                                        const res = await api.post('/auth/dev-login?role=user');
                                        localStorage.setItem('access_token', res.data.access_token);
                                        window.location.href = '/dashboard';
                                    }}
                                    className="flex-1 px-3 py-2 rounded-lg bg-accent/10 text-accent text-xs font-semibold border border-accent/20 hover:bg-accent/20 transition-colors"
                                >
                                    일반 유저 로그인
                                </button>
                            </div>
                        </div>
                    )}

                    <div className="mt-10 pt-6 border-t border-th-border-light">
                        <Link href="/" className="text-xs text-th-text-muted hover:text-th-text-secondary transition-colors">
                            ← 메인으로 돌아가기
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
