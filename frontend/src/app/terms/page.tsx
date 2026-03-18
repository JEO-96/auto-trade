'use client';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import Logo from '@/components/Logo';

export default function TermsPage() {
    return (
        <div className="min-h-screen bg-background px-6 py-12">
            <div className="max-w-2xl mx-auto">
                <div className="mb-10">
                    <Logo size="md" />
                </div>

                <Link href="/login" className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors mb-8">
                    <ArrowLeft className="w-3.5 h-3.5" />
                    돌아가기
                </Link>

                <h1 className="text-2xl font-bold text-white mb-2">서비스 이용약관</h1>
                <p className="text-xs text-gray-500 mb-10">최종 업데이트: 2026년 3월</p>

                <div className="space-y-8 text-sm text-gray-400 leading-relaxed">

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제1조 (목적)</h2>
                        <p>본 약관은 Backtested(이하 &quot;서비스&quot;)가 제공하는 모의투자 시뮬레이션 및 백테스팅 서비스의 이용 조건 및 절차, 이용자와 서비스 제공자의 권리·의무 및 책임 사항을 규정함을 목적으로 합니다.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제2조 (투자 위험 고지)</h2>
                        <div className="p-4 bg-amber-500/[0.05] border border-amber-500/20 rounded-xl space-y-2">
                            <p className="text-amber-400 font-medium">⚠ 중요: 반드시 읽어주세요</p>
                            <ul className="space-y-2 list-disc list-inside">
                                <li>가상자산 투자는 원금 손실이 발생할 수 있으며, 투자 원금 전액을 잃을 수도 있습니다.</li>
                                <li>과거의 수익률 또는 백테스팅 결과는 미래의 수익을 보장하지 않습니다.</li>
                                <li>본 서비스는 「자본시장과 금융투자업에 관한 법률」상 투자자문업 또는 투자일임업에 해당하지 않으며, 투자 권유를 제공하지 않습니다.</li>
                                <li>모든 투자 결정과 그 결과에 대한 책임은 이용자 본인에게 있습니다.</li>
                            </ul>
                        </div>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제3조 (서비스 제공자의 면책)</h2>
                        <p className="mb-3">서비스 제공자는 다음 각 호의 사유로 발생한 손해에 대해 책임을 지지 않습니다.</p>
                        <ul className="space-y-2 list-disc list-inside">
                            <li>본 서비스는 모의투자 시뮬레이션을 제공하며, 실제 자산 거래를 수행하지 않습니다.</li>
                            <li>모의투자 결과를 기반으로 이용자가 직접 수행한 실제 투자로 인한 손실</li>
                            <li>알고리즘의 오작동, 버그, 또는 예상치 못한 시장 상황에 의한 시뮬레이션 오류</li>
                            <li>네트워크 오류, 서버 점검으로 인한 서비스 중단</li>
                            <li>천재지변, 해킹 등 불가항력적 사유로 인한 손실</li>
                            <li>이용자의 귀책사유로 발생한 손해</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제4조 (서비스 이용 자격)</h2>
                        <ul className="space-y-2 list-disc list-inside">
                            <li>본 서비스는 카카오 계정으로 가입한 이용자에게 제공됩니다.</li>
                            <li>이용자는 본 서비스가 모의투자 시뮬레이션임을 이해하고 있어야 합니다.</li>
                            <li>모의투자 결과를 실제 투자에 활용할 경우, 모든 책임은 이용자 본인에게 있습니다.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제5조 (서비스 범위)</h2>
                        <ul className="space-y-2 list-disc list-inside">
                            <li>본 서비스는 모의투자(가상매매) 시뮬레이션, 백테스팅, 커뮤니티 기능을 제공합니다.</li>
                            <li>본 서비스는 이용자의 거래소 API 키를 수집하지 않으며, 이용자의 실제 자산에 접근하지 않습니다.</li>
                            <li>모의투자 결과는 실제 시장 데이터를 기반으로 하나, 실제 거래 결과와 다를 수 있습니다.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제6조 (개인정보 처리)</h2>
                        <p>서비스는 카카오 OAuth를 통해 수집한 이용자의 개인정보(이메일, 닉네임)를 서비스 제공 목적으로만 사용하며, 「개인정보 보호법」을 준수합니다. 이용자는 언제든지 계정 삭제를 요청할 수 있습니다.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제7조 (서비스 변경 및 중단)</h2>
                        <p>서비스 제공자는 사전 고지 없이 서비스를 변경하거나 중단할 수 있으며, 이로 인한 손해에 대해 책임을 지지 않습니다.</p>
                    </section>

                    <section>
                        <h2 className="text-base font-semibold text-white mb-3">제8조 (준거법 및 관할)</h2>
                        <p>본 약관은 대한민국 법률에 따라 해석되며, 서비스 이용과 관련한 분쟁은 대한민국 법원을 관할 법원으로 합니다.</p>
                    </section>

                </div>

                <div className="mt-12 pt-8 border-t border-white/[0.04] text-xs text-gray-500 text-center space-y-2">
                    <p>본 약관에 동의하지 않을 경우 서비스를 이용하실 수 없습니다.</p>
                </div>
            </div>
        </div>
    );
}
