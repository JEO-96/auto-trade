'use client';
import Link from 'next/link';
import { Activity, ArrowLeft } from 'lucide-react';

export default function PrivacyPage() {
    return (
        <div className="min-h-screen bg-background px-6 py-12">
            <div className="max-w-2xl mx-auto">
                <div className="flex items-center gap-2.5 mb-10">
                    <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center border border-primary/20">
                        <Activity className="w-4 h-4 text-primary" />
                    </div>
                    <span className="text-base font-extrabold tracking-tight text-white">BACKTESTED</span>
                </div>

                <Link href="/" className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors mb-8">
                    <ArrowLeft className="w-3.5 h-3.5" />
                    돌아가기
                </Link>

                <h1 className="text-2xl font-bold text-white mb-2">개인정보처리방침</h1>
                <p className="text-xs text-gray-500 mb-10">최종 업데이트: 2025년 8월</p>

                <div className="space-y-8 text-sm text-gray-400 leading-relaxed">

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제1조 (개인정보의 처리 목적)</h2>
                        <p className="mb-3">플레이위드(이하 &quot;회사&quot;)는 Backtested 서비스(이하 &quot;서비스&quot;) 제공을 위해 다음의 목적으로 개인정보를 처리합니다.</p>
                        <ul className="space-y-2 list-disc list-inside">
                            <li><strong className="text-gray-300">회원가입 및 관리:</strong> 본인 식별, 서비스 이용 자격 확인, 부정 이용 방지</li>
                            <li><strong className="text-gray-300">서비스 제공:</strong> 자동매매 봇 운영, 백테스트 실행, 커뮤니티 기능 제공</li>
                            <li><strong className="text-gray-300">결제 처리:</strong> 크레딧 충전 및 결제 내역 관리</li>
                            <li><strong className="text-gray-300">고객 지원:</strong> 문의 응대, 공지사항 전달</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제2조 (수집하는 개인정보 항목)</h2>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="border-b border-white/[0.08]">
                                        <th className="py-2 pr-4 text-gray-300 font-medium">수집 시점</th>
                                        <th className="py-2 pr-4 text-gray-300 font-medium">수집 항목</th>
                                        <th className="py-2 text-gray-300 font-medium">수집 방법</th>
                                    </tr>
                                </thead>
                                <tbody className="text-gray-400">
                                    <tr className="border-b border-white/[0.04]">
                                        <td className="py-2 pr-4">회원가입</td>
                                        <td className="py-2 pr-4">이메일, 닉네임, 카카오 계정 식별자</td>
                                        <td className="py-2">카카오 OAuth</td>
                                    </tr>
                                    <tr className="border-b border-white/[0.04]">
                                        <td className="py-2 pr-4">서비스 이용</td>
                                        <td className="py-2 pr-4">거래소 API 키 (암호화 저장)</td>
                                        <td className="py-2">이용자 직접 입력</td>
                                    </tr>
                                    <tr className="border-b border-white/[0.04]">
                                        <td className="py-2 pr-4">결제</td>
                                        <td className="py-2 pr-4">결제 수단 정보, 결제 내역</td>
                                        <td className="py-2">토스페이먼츠 PG</td>
                                    </tr>
                                    <tr>
                                        <td className="py-2 pr-4">자동 수집</td>
                                        <td className="py-2 pr-4">접속 IP, 접속 시간, 브라우저 정보</td>
                                        <td className="py-2">서버 로그</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제3조 (개인정보의 보유 및 이용 기간)</h2>
                        <ul className="space-y-2 list-disc list-inside">
                            <li><strong className="text-gray-300">회원 정보:</strong> 회원 탈퇴 시까지 (탈퇴 후 즉시 파기)</li>
                            <li><strong className="text-gray-300">거래 기록:</strong> 전자상거래법에 따라 5년 보관</li>
                            <li><strong className="text-gray-300">결제 기록:</strong> 전자상거래법에 따라 5년 보관</li>
                            <li><strong className="text-gray-300">접속 로그:</strong> 통신비밀보호법에 따라 3개월 보관</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제4조 (개인정보의 제3자 제공)</h2>
                        <p className="mb-3">회사는 원칙적으로 이용자의 개인정보를 외부에 제공하지 않습니다. 다만, 다음의 경우는 예외로 합니다.</p>
                        <ul className="space-y-2 list-disc list-inside">
                            <li>이용자가 사전에 동의한 경우</li>
                            <li>법령에 의해 요구되는 경우</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제5조 (개인정보 처리 위탁)</h2>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead>
                                    <tr className="border-b border-white/[0.08]">
                                        <th className="py-2 pr-4 text-gray-300 font-medium">수탁업체</th>
                                        <th className="py-2 text-gray-300 font-medium">위탁 업무</th>
                                    </tr>
                                </thead>
                                <tbody className="text-gray-400">
                                    <tr className="border-b border-white/[0.04]">
                                        <td className="py-2 pr-4">토스페이먼츠</td>
                                        <td className="py-2">결제 처리</td>
                                    </tr>
                                    <tr className="border-b border-white/[0.04]">
                                        <td className="py-2 pr-4">Amazon Web Services (AWS)</td>
                                        <td className="py-2">데이터 저장 및 서버 호스팅</td>
                                    </tr>
                                    <tr>
                                        <td className="py-2 pr-4">카카오</td>
                                        <td className="py-2">소셜 로그인 인증</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제6조 (개인정보의 안전성 확보 조치)</h2>
                        <ul className="space-y-2 list-disc list-inside">
                            <li>거래소 API 키는 Fernet 대칭키 암호화를 적용하여 저장합니다.</li>
                            <li>비밀번호는 bcrypt 해시 처리하여 저장합니다.</li>
                            <li>모든 통신은 SSL/TLS(HTTPS)로 암호화됩니다.</li>
                            <li>JWT 기반 인증으로 무단 접근을 방지합니다.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제7조 (이용자의 권리)</h2>
                        <p className="mb-3">이용자는 언제든지 다음의 권리를 행사할 수 있습니다.</p>
                        <ul className="space-y-2 list-disc list-inside">
                            <li>개인정보 열람, 정정, 삭제 요청</li>
                            <li>개인정보 처리 정지 요청</li>
                            <li>회원 탈퇴 및 계정 삭제 요청</li>
                        </ul>
                        <p className="mt-3">위 요청은 이메일(seal5945@gmail.com)로 접수할 수 있으며, 지체 없이 처리합니다.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제8조 (개인정보 보호책임자)</h2>
                        <div className="p-4 bg-white/[0.03] border border-white/[0.06] rounded-xl space-y-1">
                            <p><span className="text-gray-300">성명:</span> 주은오</p>
                            <p><span className="text-gray-300">직위:</span> 대표</p>
                            <p><span className="text-gray-300">이메일:</span> seal5945@gmail.com</p>
                        </div>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제9조 (방침의 변경)</h2>
                        <p>본 방침은 관련 법령 및 서비스 정책의 변경에 따라 수정될 수 있으며, 변경 시 서비스 내 공지사항을 통해 안내합니다.</p>
                    </section>

                </div>

                <div className="mt-12 pt-8 border-t border-white/[0.04] text-xs text-gray-600 text-center space-y-2">
                    <p>플레이위드 | 대표 주은오 | 사업자등록번호 880-58-00862</p>
                    <p>서울특별시 영등포구 경인로 882, 1103호(영등포동1가, 여의도씨티아이)</p>
                </div>
            </div>
        </div>
    );
}
