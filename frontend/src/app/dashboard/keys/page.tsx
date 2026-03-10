'use client';
import { useState, useEffect } from 'react';
import { KeyRound, Plus, Save, Trash2, ShieldCheck, Eye, EyeOff, ExternalLink } from 'lucide-react';
import Button from '@/components/ui/Button';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import { SelectInput } from '@/components/ui/Input';
import { getKeys, saveKey } from '@/lib/api/keys';
import type { ExchangeKeyPreview } from '@/types/keys';

export default function ApiKeysPage() {
    const [keys, setKeys] = useState<ExchangeKeyPreview[]>([]);
    const [loading, setLoading] = useState(true);

    const [exchangeName, setExchangeName] = useState('upbit');
    const [apiKey, setApiKey] = useState('');
    const [apiSecret, setApiSecret] = useState('');
    const [showSecret, setShowSecret] = useState(false);
    const [saving, setSaving] = useState(false);

    const fetchKeys = async () => {
        try {
            const data = await getKeys();
            setKeys(data);
        } catch (err) {
            console.error("Failed to fetch API keys", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchKeys();
    }, []);

    const handleSaveKey = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        try {
            await saveKey({
                exchange_name: exchangeName,
                api_key: apiKey,
                api_secret: apiSecret,
            });
            alert('API 키가 안전하게 저장되었습니다.');
            setApiKey('');
            setApiSecret('');
            fetchKeys();
        } catch (err) {
            alert('저장 실패. 로그인 상태인지 확인해 주세요.');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="p-6 lg:p-8 max-w-5xl mx-auto animate-fade-in-up" role="main">
            <header className="mb-8">
                <h1 className="text-2xl font-bold mb-1 flex items-center gap-2.5">
                    <KeyRound className="w-6 h-6 text-secondary" />
                    거래소 연동 설정
                </h1>
                <p className="text-sm text-gray-500">CCXT 연동을 위한 거래소 API 키를 관리합니다.</p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

                {/* Add Key Form */}
                <div className="glass-panel p-6 rounded-2xl">
                    <h3 className="text-base font-bold mb-5 flex items-center gap-2">
                        <Plus className="w-4 h-4 text-primary" />
                        API 키 등록
                    </h3>

                    <form onSubmit={handleSaveKey} className="space-y-4">
                        <SelectInput
                            type="select"
                            label="거래소 선택"
                            value={exchangeName}
                            onChange={(e) => setExchangeName(e.target.value)}
                        >
                            <option value="upbit">Upbit (업비트)</option>
                            <option value="binance">Binance (바이낸스)</option>
                            <option value="bybit">Bybit (바이비트)</option>
                        </SelectInput>

                        <div>
                            <label className="text-xs text-gray-500 font-medium mb-1.5 block">API Key (Access Key)</label>
                            <input
                                type="text"
                                value={apiKey}
                                onChange={(e) => setApiKey(e.target.value)}
                                required
                                placeholder="API 키를 입력하세요"
                                className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 text-sm focus:border-primary/30 transition-colors"
                            />
                        </div>

                        <div>
                            <label className="text-xs text-gray-500 font-medium mb-1.5 block">Secret Key</label>
                            <div className="relative">
                                <input
                                    type={showSecret ? "text" : "password"}
                                    value={apiSecret}
                                    onChange={(e) => setApiSecret(e.target.value)}
                                    required
                                    placeholder="시크릿 키를 입력하세요"
                                    className="w-full bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 pr-10 text-sm focus:border-primary/30 transition-colors"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowSecret(!showSecret)}
                                    aria-label={showSecret ? '비밀번호 숨기기' : '비밀번호 보기'}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition-colors"
                                >
                                    {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            </div>
                            <p className="text-[10px] text-amber-500/70 mt-2 flex items-center gap-1">
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
                            <Save className="w-4 h-4" />
                            {saving ? "저장 중..." : "저장하기"}
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
                        <div className="text-center py-10 bg-white/[0.02] rounded-xl border border-dashed border-white/[0.06]">
                            <EmptyState
                                icon={<KeyRound className="w-10 h-10" />}
                                title="등록된 API 키가 없습니다."
                            />
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {keys.map((key) => (
                                <div key={key.id} className="bg-white/[0.03] border border-white/[0.06] p-4 rounded-xl flex justify-between items-center group hover:border-primary/20 transition-colors">
                                    <div>
                                        <span className="uppercase text-[10px] font-semibold bg-primary/10 text-primary px-2 py-0.5 rounded-md">
                                            {key.exchange_name}
                                        </span>
                                        <p className="font-mono text-sm tracking-wider text-gray-400 mt-1.5">
                                            {key.api_key_preview}
                                        </p>
                                    </div>
                                    <button aria-label="API 키 삭제" className="text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all p-2 hover:bg-red-500/[0.08] rounded-lg">
                                        <Trash2 className="w-4 h-4" />
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
                            <p className="text-sm text-gray-400 mb-4 leading-relaxed">
                                자동 매매를 위해 거래소에서 API 키를 발급받아야 합니다.
                            </p>
                            <div className="flex flex-wrap gap-3 mb-4">
                                <a
                                    href="https://upbit.com/service_center/guide"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="bg-white/[0.04] hover:bg-white/[0.08] text-white px-4 py-2 rounded-lg border border-white/[0.06] flex items-center gap-2 transition-colors text-xs font-medium"
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
                            </div>
                            <div className="p-4 bg-white/[0.02] rounded-xl border border-white/[0.04]">
                                <h4 className="text-xs font-semibold text-white mb-2 flex items-center gap-1.5">
                                    <ShieldCheck className="w-3.5 h-3.5 text-primary" />
                                    보안 체크리스트
                                </h4>
                                <ul className="text-xs text-gray-400 space-y-1.5 list-disc pl-4">
                                    <li><strong className="text-white">IP 주소 제한</strong> 설정 필수 (서버 IP: <code className="text-primary bg-white/[0.04] px-1 rounded text-[10px]">13.124.235.43</code>)</li>
                                    <li><strong className="text-white">주문, 조회</strong> 권한만 허용. <strong className="text-red-400">출금 권한은 절대 체크하지 마세요.</strong></li>
                                    <li>Secret Key는 발급 시 한 번만 표시되므로 반드시 별도 보관하세요.</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}
