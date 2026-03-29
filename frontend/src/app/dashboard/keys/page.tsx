'use client';
import { useState, useEffect, useMemo } from 'react';
import { KeyRound, Plus, Save, Trash2, ShieldCheck, Eye, EyeOff, ExternalLink, AlertTriangle, RefreshCw } from 'lucide-react';
import Button from '@/components/ui/Button';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import { SelectInput } from '@/components/ui/Input';
import ConfirmationModal from '@/components/modals/ConfirmationModal';
import DeleteConfirmationModal from '@/components/modals/DeleteConfirmationModal';
import { useToast } from '@/components/ui/Toast';
import { getKeys, saveKey, deleteKey } from '@/lib/api/keys';
import { EXCHANGES } from '@/lib/constants';
import type { ExchangeKeyPreview } from '@/types/keys';

export default function ApiKeysPage() {
    const [keys, setKeys] = useState<ExchangeKeyPreview[]>([]);
    const [loading, setLoading] = useState(true);

    const [exchangeName, setExchangeName] = useState('upbit');
    const [apiKey, setApiKey] = useState('');
    const [apiSecret, setApiSecret] = useState('');
    const [showSecret, setShowSecret] = useState(false);
    const [saving, setSaving] = useState(false);
    const [deleting, setDeleting] = useState<number | null>(null);
    const [showUpdateConfirm, setShowUpdateConfirm] = useState(false);
    const [deletingKeyInfo, setDeletingKeyInfo] = useState<{ id: number; name: string } | null>(null);
    const toast = useToast();

    const fetchKeys = async () => {
        try {
            const data = await getKeys();
            setKeys(data);
        } catch {
            toast.error('API 키를 불러오지 못했습니다.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchKeys();
    }, []);

    const existingKeyForExchange = useMemo(() => {
        return keys.find(k => k.exchange_name === exchangeName);
    }, [keys, exchangeName]);

    const isUpdate = !!existingKeyForExchange;

    const handleSaveKey = async (e: React.FormEvent) => {
        e.preventDefault();

        if (isUpdate) {
            setShowUpdateConfirm(true);
            return;
        }

        await executeSaveKey();
    };

    const executeSaveKey = async () => {
        setShowUpdateConfirm(false);
        setSaving(true);
        try {
            await saveKey({
                exchange_name: exchangeName,
                api_key: apiKey,
                api_secret: apiSecret,
            });
            toast.success(isUpdate ? 'API 키가 업데이트되었습니다.' : 'API 키가 안전하게 저장되었습니다.');
            setApiKey('');
            setApiSecret('');
            fetchKeys();
        } catch {
            toast.error('저장 실패. 로그인 상태인지 확인해 주세요.');
        } finally {
            setSaving(false);
        }
    };

    const handleDeleteKey = async (keyId: number, keyExchangeName: string) => {
        setDeletingKeyInfo({ id: keyId, name: keyExchangeName });
    };

    const executeDeleteKey = async () => {
        if (!deletingKeyInfo) return;
        const keyId = deletingKeyInfo.id;
        setDeletingKeyInfo(null);
        setDeleting(keyId);
        try {
            await deleteKey(keyId);
            setKeys(prev => prev.filter(k => k.id !== keyId));
        } catch {
            toast.error('삭제 실패. 다시 시도해 주세요.');
        } finally {
            setDeleting(null);
        }
    };

    return (
        <div className="p-6 lg:p-8 max-w-5xl mx-auto animate-fade-in-up" role="main">
            <header className="mb-8">
                <h1 className="text-2xl font-bold mb-1 flex items-center gap-2.5">
                    <KeyRound className="w-6 h-6 text-secondary" />
                    거래소 연동 설정
                </h1>
                <p className="text-sm text-th-text-muted">자동매매에 필요한 거래소 API 키를 관리합니다.</p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

                {/* Add Key Form */}
                <div className="glass-panel p-6 rounded-2xl">
                    <h3 className="text-base font-bold mb-5 flex items-center gap-2">
                        <Plus className="w-4 h-4 text-primary" />
                        API 키 {isUpdate ? '업데이트' : '등록'}
                    </h3>

                    <form onSubmit={handleSaveKey} className="space-y-4">
                        <SelectInput
                            type="select"
                            label="거래소 선택"
                            value={exchangeName}
                            onChange={(e) => setExchangeName(e.target.value)}
                        >
                            {EXCHANGES.map((ex) => (
                                <option key={ex.value} value={ex.value}>{ex.label}</option>
                            ))}
                        </SelectInput>

                        {isUpdate && (
                            <div className="flex items-start gap-2 p-3 bg-amber-500/[0.06] border border-amber-500/20 rounded-xl">
                                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                                <div>
                                    <p className="text-xs text-amber-400 font-medium">
                                        이미 {exchangeName.toUpperCase()} API 키가 등록되어 있습니다.
                                    </p>
                                    <p className="text-[10px] sm:text-xs text-amber-500/70 mt-0.5">
                                        새 키를 입력하면 기존 키가 업데이트됩니다. 삭제 후 재등록하려면 오른쪽 목록에서 삭제해주세요.
                                    </p>
                                </div>
                            </div>
                        )}

                        <div>
                            <label className="text-xs text-th-text-muted font-medium mb-1.5 block">API Key (Access Key)</label>
                            <input
                                type="text"
                                value={apiKey}
                                onChange={(e) => setApiKey(e.target.value)}
                                required
                                placeholder="API 키를 입력하세요"
                                className="w-full bg-th-card border border-th-border rounded-xl p-3 text-sm focus:border-primary/30 transition-colors"
                            />
                        </div>

                        <div>
                            <label className="text-xs text-th-text-muted font-medium mb-1.5 block">Secret Key</label>
                            <div className="relative">
                                <input
                                    type={showSecret ? "text" : "password"}
                                    value={apiSecret}
                                    onChange={(e) => setApiSecret(e.target.value)}
                                    required
                                    placeholder="시크릿 키를 입력하세요"
                                    className="w-full bg-th-card border border-th-border rounded-xl p-3 pr-10 text-sm focus:border-primary/30 transition-colors"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowSecret(!showSecret)}
                                    aria-label={showSecret ? '비밀번호 숨기기' : '비밀번호 보기'}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-th-text-muted hover:text-th-text transition-colors"
                                >
                                    {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            </div>
                            <p className="text-[10px] sm:text-xs text-amber-500/70 mt-2 flex items-center gap-1">
                                <ShieldCheck className="w-3 h-3" />
                                Secret Key는 서버에 안전하게 저장됩니다.
                            </p>
                        </div>

                        <Button
                            type="submit"
                            variant="primary"
                            size="lg"
                            fullWidth
                            loading={saving}
                        >
                            {isUpdate ? (
                                <>
                                    <RefreshCw className="w-4 h-4" />
                                    {saving ? "업데이트 중..." : "키 업데이트"}
                                </>
                            ) : (
                                <>
                                    <Save className="w-4 h-4" />
                                    {saving ? "저장 중..." : "저장하기"}
                                </>
                            )}
                        </Button>
                    </form>
                </div>

                {/* Saved Keys */}
                <div className="glass-panel p-6 rounded-2xl h-fit">
                    <h3 className="text-base font-bold mb-5 flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-secondary" />
                        등록된 API 키
                    </h3>

                    {loading ? (
                        <div className="py-8 text-center">
                            <LoadingSpinner size="sm" message="불러오는 중..." />
                        </div>
                    ) : keys.length === 0 ? (
                        <div className="text-center py-10 bg-th-card rounded-xl border border-dashed border-th-border">
                            <EmptyState
                                icon={<KeyRound className="w-10 h-10" />}
                                title="등록된 API 키가 없습니다."
                            />
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {keys.map((key) => (
                                <div key={key.id} className="bg-th-card border border-th-border p-4 rounded-xl flex justify-between items-center group hover:border-primary/20 transition-colors">
                                    <div>
                                        <span className="uppercase text-[10px] sm:text-xs font-semibold bg-primary/10 text-primary px-2 py-0.5 rounded-md">
                                            {key.exchange_name}
                                        </span>
                                        <p className="font-mono text-sm tracking-wider text-th-text-secondary mt-1.5">
                                            {key.api_key_preview}
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => handleDeleteKey(key.id, key.exchange_name)}
                                        disabled={deleting === key.id}
                                        aria-label="API 키 삭제"
                                        className="text-th-text-muted hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all p-2 hover:bg-red-500/[0.08] rounded-lg disabled:opacity-50"
                                    >
                                        {deleting === key.id ? (
                                            <div className="w-4 h-4 border border-gray-500/20 border-t-gray-400 rounded-full animate-spin" />
                                        ) : (
                                            <Trash2 className="w-4 h-4" />
                                        )}
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Help Section */}
                <div className="lg:col-span-2 glass-panel p-6 rounded-2xl">
                    <div className="flex items-start gap-4">
                        <div className="p-2.5 bg-secondary/10 rounded-xl border border-secondary/10 shrink-0">
                            <KeyRound className="w-5 h-5 text-secondary" />
                        </div>
                        <div className="flex-1">
                            <h3 className="text-base font-bold mb-2">API 키 발급 가이드</h3>
                            <p className="text-sm text-th-text-secondary mb-4 leading-relaxed">
                                자동 매매를 위해 거래소에서 API 키를 발급받아야 합니다.
                            </p>
                            <div className="flex flex-wrap gap-3 mb-4">
                                <a
                                    href="https://upbit.com/service_center/guide"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="bg-th-card hover:bg-th-hover text-th-text px-4 py-2 rounded-lg border border-th-border flex items-center gap-2 transition-colors text-xs font-medium"
                                >
                                    <ExternalLink className="w-3.5 h-3.5 text-primary" />
                                    업비트 고객센터
                                </a>
                                <a
                                    href="https://upbit.com/mypage/open_api_management"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="bg-secondary/[0.08] hover:bg-secondary/[0.15] text-secondary px-4 py-2 rounded-lg border border-secondary/20 flex items-center gap-2 transition-colors text-xs font-medium"
                                >
                                    업비트 API 관리
                                </a>
                                <a
                                    href="https://www.bithumb.com/api_support/management_api"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="bg-th-card hover:bg-th-hover text-th-text px-4 py-2 rounded-lg border border-th-border flex items-center gap-2 transition-colors text-xs font-medium"
                                >
                                    <ExternalLink className="w-3.5 h-3.5 text-primary" />
                                    빗썸 API 관리
                                </a>
                            </div>
                            <div className="space-y-3">
                                {/* 업비트 발급 가이드 */}
                                <div className="p-4 bg-th-card rounded-xl border border-th-border-light">
                                    <h4 className="text-xs font-semibold text-th-text mb-2.5">업비트 (Upbit) API 발급 방법</h4>
                                    <ol className="text-xs text-th-text-secondary space-y-1.5 list-decimal pl-4">
                                        <li><a href="https://upbit.com/mypage/open_api_management" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">업비트 Open API 관리</a> 페이지 접속</li>
                                        <li><strong className="text-th-text">Open API Key 발급</strong> 클릭</li>
                                        <li>권한 설정: <strong className="text-th-text">자산조회</strong>, <strong className="text-th-text">주문조회</strong>, <strong className="text-th-text">주문하기</strong> 체크 <span className="text-red-400">(출금 체크 금지)</span></li>
                                        <li><strong className="text-th-text">허용 IP 주소</strong>에 서버 IP 입력: <code className="text-primary bg-th-card px-1 rounded text-[10px] sm:text-xs">13.124.235.43</code></li>
                                        <li>2단계 인증 후 <strong className="text-th-text">Access Key</strong>와 <strong className="text-th-text">Secret Key</strong> 복사</li>
                                    </ol>
                                </div>

                                {/* 빗썸 발급 가이드 */}
                                <div className="p-4 bg-th-card rounded-xl border border-th-border-light">
                                    <h4 className="text-xs font-semibold text-th-text mb-2.5">빗썸 (Bithumb) API 발급 방법</h4>
                                    <ol className="text-xs text-th-text-secondary space-y-1.5 list-decimal pl-4">
                                        <li><a href="https://www.bithumb.com/api_support/management_api" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">빗썸 API 관리</a> 페이지 접속</li>
                                        <li><strong className="text-th-text">API Key 발급</strong> 클릭</li>
                                        <li>권한 설정: <strong className="text-th-text">거래 기능 사용</strong>, <strong className="text-th-text">조회</strong> 체크 <span className="text-red-400">(출금 체크 금지)</span></li>
                                        <li><strong className="text-th-text">허용 IP</strong>에 서버 IP 입력: <code className="text-primary bg-th-card px-1 rounded text-[10px] sm:text-xs">13.124.235.43</code></li>
                                        <li>본인인증 후 <strong className="text-th-text">API Key(Connect Key)</strong>와 <strong className="text-th-text">Secret Key</strong> 복사</li>
                                    </ol>
                                </div>

                                {/* 보안 체크리스트 */}
                                <div className="p-4 bg-th-card rounded-xl border border-th-border-light">
                                    <h4 className="text-xs font-semibold text-th-text mb-2 flex items-center gap-1.5">
                                        <ShieldCheck className="w-3.5 h-3.5 text-primary" />
                                        보안 체크리스트
                                    </h4>
                                    <ul className="text-xs text-th-text-secondary space-y-1.5 list-disc pl-4">
                                        <li><strong className="text-th-text">IP 주소 제한</strong> 설정 필수 (서버 IP: <code className="text-primary bg-th-card px-1 rounded text-[10px] sm:text-xs">13.124.235.43</code>)</li>
                                        <li><strong className="text-th-text">주문, 조회</strong> 권한만 허용. <strong className="text-red-400">출금 권한은 절대 체크하지 마세요.</strong></li>
                                        <li>Secret Key는 발급 시 한 번만 표시되므로 반드시 별도 보관하세요.</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

            </div>

            <ConfirmationModal
                isOpen={showUpdateConfirm}
                title="API 키 업데이트"
                message="기존 키가 새로운 키로 업데이트됩니다. 계속하시겠습니까?"
                confirmLabel="업데이트"
                onConfirm={executeSaveKey}
                onCancel={() => setShowUpdateConfirm(false)}
            />

            <DeleteConfirmationModal
                isOpen={!!deletingKeyInfo}
                title="API 키 삭제"
                message={`${deletingKeyInfo?.name.toUpperCase() ?? ''} API 키를 삭제하시겠습니까?`}
                onConfirm={executeDeleteKey}
                onCancel={() => setDeletingKeyInfo(null)}
            />
        </div>
    );
}
