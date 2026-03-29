'use client';
import { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import ModalWrapper, { ModalHeader } from '@/components/ui/ModalWrapper';

interface RiskDisclaimerModalProps {
    onConfirm: () => void;
    onCancel: () => void;
}

export default function RiskDisclaimerModal({ onConfirm, onCancel }: RiskDisclaimerModalProps) {
    const [checked1, setChecked1] = useState(false);
    const [checked2, setChecked2] = useState(false);
    const [checked3, setChecked3] = useState(false);

    const allChecked = checked1 && checked2 && checked3;

    return (
        <ModalWrapper isOpen={true} ariaLabelledBy="risk-modal-title">
                <ModalHeader
                    icon={<div className="w-9 h-9 bg-amber-500/10 rounded-xl flex items-center justify-center border border-amber-500/20"><AlertTriangle className="w-5 h-5 text-amber-500" /></div>}
                    title="투자 위험 고지"
                    titleId="risk-modal-title"
                    onClose={onCancel}
                />

                {/* Body */}
                <div className="p-6 space-y-4">
                    <p className="text-xs text-th-text-secondary leading-relaxed">
                        모의투자 봇을 가동하기 전, 아래 내용을 반드시 확인하고 동의해 주세요.
                    </p>

                    <div className="space-y-3">
                        <label className="flex items-start gap-3 cursor-pointer group">
                            <input
                                type="checkbox"
                                checked={checked1}
                                onChange={(e) => setChecked1(e.target.checked)}
                                className="mt-0.5 w-4 h-4 rounded border-th-text-muted bg-transparent accent-amber-500 cursor-pointer shrink-0"
                            />
                            <span className="text-xs text-th-text-secondary leading-relaxed group-hover:text-th-text-secondary transition-colors">
                                <strong className="text-th-text">원금 손실 위험</strong>을 이해합니다.
                                가상자산 투자는 원금 손실이 발생할 수 있으며, 과거의 수익률이 미래의 수익을 보장하지 않습니다.
                            </span>
                        </label>

                        <label className="flex items-start gap-3 cursor-pointer group">
                            <input
                                type="checkbox"
                                checked={checked2}
                                onChange={(e) => setChecked2(e.target.checked)}
                                className="mt-0.5 w-4 h-4 rounded border-th-text-muted bg-transparent accent-amber-500 cursor-pointer shrink-0"
                            />
                            <span className="text-xs text-th-text-secondary leading-relaxed group-hover:text-th-text-secondary transition-colors">
                                본 서비스는 <strong className="text-th-text">투자 자문 또는 투자 권유 서비스가 아닙니다.</strong>
                                모든 투자 결정과 그 결과에 대한 책임은 이용자 본인에게 있습니다.
                            </span>
                        </label>

                        <label className="flex items-start gap-3 cursor-pointer group">
                            <input
                                type="checkbox"
                                checked={checked3}
                                onChange={(e) => setChecked3(e.target.checked)}
                                className="mt-0.5 w-4 h-4 rounded border-th-text-muted bg-transparent accent-amber-500 cursor-pointer shrink-0"
                            />
                            <span className="text-xs text-th-text-secondary leading-relaxed group-hover:text-th-text-secondary transition-colors">
                                알고리즘 오류, 네트워크 장애, 거래소 점검 등 <strong className="text-th-text">시스템 사유로 인한 손실</strong>에 대해
                                서비스 제공자가 책임지지 않음을 동의합니다.
                            </span>
                        </label>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex gap-3 p-6 pt-2">
                    <button
                        onClick={onCancel}
                        className="flex-1 py-2.5 rounded-xl border border-white/[0.06] text-sm font-medium text-th-text-secondary hover:bg-white/[0.03] transition-colors"
                    >
                        취소
                    </button>
                    <button
                        onClick={onConfirm}
                        disabled={!allChecked}
                        className="flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all disabled:opacity-30 disabled:cursor-not-allowed bg-primary hover:bg-primary-dark text-white"
                    >
                        동의하고 가동
                    </button>
                </div>
        </ModalWrapper>
    );
}
