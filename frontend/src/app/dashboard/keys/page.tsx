'use client';
import { useState, useEffect } from 'react';
import { KeyRound, Plus, Save, Trash2, ShieldCheck, Eye, EyeOff, ExternalLink } from 'lucide-react';
import api from '@/lib/api';

type ExchangeKeyPreview = {
    id: number;
    exchange_name: string;
    api_key_preview: string;
}

export default function ApiKeysPage() {
    const [keys, setKeys] = useState<ExchangeKeyPreview[]>([]);
    const [loading, setLoading] = useState(true);

    // Form state
    const [exchangeName, setExchangeName] = useState('upbit');
    const [apiKey, setApiKey] = useState('');
    const [apiSecret, setApiSecret] = useState('');
    const [showSecret, setShowSecret] = useState(false);
    const [saving, setSaving] = useState(false);

    const fetchKeys = async () => {
        try {
            const res = await api.get('/keys/');
            setKeys(res.data);
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
            await api.post('/keys/', {
                exchange_name: exchangeName,
                api_key: apiKey,
                api_secret: apiSecret
            });

            alert('API 키가 안전하게 저장되었습니다.');
            setApiKey('');
            setApiSecret('');
            fetchKeys(); // Refresh list
        } catch (err) {
            alert('저장 실패. 로그인 상태인지 확인해 주세요.');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="p-8 max-w-5xl mx-auto animate-fade-in-up">
            <header className="mb-8 flex justify-between items-end border-b border-gray-800 pb-6">
                <div>
                    <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
                        <KeyRound className="w-8 h-8 text-secondary" /> 거래소 연동 설정
                    </h1>
                    <p className="text-gray-400">CCXT 연동을 위한 글로벌 암호화폐 거래소 API 키를 관리합니다.</p>
                </div>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">

                {/* ADD NEW KEY FORM */}
                <div className="glass-panel p-6 rounded-2xl">
                    <h3 className="text-xl font-bold mb-6 flex items-center gap-2"><Plus className="w-5 h-5 text-primary" /> API 키 등록/수정</h3>

                    <form onSubmit={handleSaveKey} className="space-y-4">
                        <div>
                            <label className="text-sm text-gray-400 mb-1 block">거래소 선택</label>
                            <select
                                value={exchangeName}
                                onChange={(e) => setExchangeName(e.target.value)}
                                className="w-full bg-surface border border-gray-700 rounded-lg p-3 text-white focus:ring-primary focus:border-primary"
                            >
                                <option value="binance">Binance (바이낸스)</option>
                                <option value="upbit">Upbit (업비트)</option>
                                <option value="bybit">Bybit (바이비트)</option>
                            </select>
                        </div>

                        <div>
                            <label className="text-sm text-gray-400 mb-1 block">API Key (Access Key)</label>
                            <input
                                type="text"
                                value={apiKey}
                                onChange={(e) => setApiKey(e.target.value)}
                                required
                                placeholder="ex: XXXXXXXXXXXXXXXXXX"
                                className="w-full bg-surface border border-gray-700 rounded-lg p-3 focus:ring-primary focus:border-primary"
                            />
                        </div>

                        <div>
                            <label className="text-sm text-gray-400 mb-1 block">Secret Key</label>
                            <div className="relative">
                                <input
                                    type={showSecret ? "text" : "password"}
                                    value={apiSecret}
                                    onChange={(e) => setApiSecret(e.target.value)}
                                    required
                                    placeholder="ex: YYYYYYYYYYYYYYYYYY"
                                    className="w-full bg-surface border border-gray-700 rounded-lg p-3 pr-10 focus:ring-primary focus:border-primary"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowSecret(!showSecret)}
                                    className="absolute right-3 top-3 text-gray-500 hover:text-white"
                                >
                                    {showSecret ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                </button>
                            </div>
                            <p className="text-xs text-yellow-500/80 mt-2 flex items-center gap-1">
                                <ShieldCheck className="w-3 h-3" />
                                Secret Key는 서버에 즉시 암호화되어 저장됩니다.
                            </p>
                        </div>

                        <button
                            type="submit"
                            disabled={saving}
                            className="w-full bg-primary hover:bg-blue-600 disabled:bg-primary/50 text-white font-semibold py-3 rounded-lg flex justify-center items-center gap-2 mt-4 transition-colors"
                        >
                            <Save className="w-5 h-5" /> {saving ? "저장 중..." : "저장하기"}
                        </button>
                    </form>
                </div>

                {/* LIST OF SAVED KEYS */}
                <div className="glass-panel p-6 rounded-2xl h-fit">
                    <h3 className="text-xl font-bold mb-6 flex items-center gap-2"><ShieldCheck className="w-5 h-5 text-secondary" /> 등록된 API 키</h3>

                    {loading ? (
                        <p className="text-gray-400">키 정보를 불러오는 중...</p>
                    ) : keys.length === 0 ? (
                        <div className="text-center py-10 bg-surface/30 rounded-lg border border-dashed border-gray-700">
                            <KeyRound className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                            <p className="text-gray-400">등록된 거래소 API 키가 없습니다.</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {keys.map((key) => (
                                <div key={key.id} className="bg-surface border border-gray-700 p-4 rounded-lg flex justify-between items-center group hover:border-primary/50 transition-colors">
                                    <div>
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="uppercase text-xs font-bold bg-primary/20 text-primary px-2 py-0.5 rounded">
                                                {key.exchange_name}
                                            </span>
                                        </div>
                                        <p className="font-mono text-sm tracking-widest text-gray-300">
                                            {key.api_key_preview}
                                        </p>
                                    </div>
                                    <button className="text-gray-500 hover:text-danger opacity-0 group-hover:opacity-100 transition-opacity p-2 bg-danger/10 rounded-md">
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* HELP SECTION */}
                <div className="md:col-span-2 glass-panel p-6 rounded-2xl bg-secondary/5 border-secondary/20 border">
                    <div className="flex items-start gap-4">
                        <div className="p-3 bg-secondary/20 rounded-xl">
                            <KeyRound className="w-6 h-6 text-secondary" />
                        </div>
                        <div className="flex-1">
                            <h3 className="text-xl font-bold mb-2">API 키 발급 방법이 궁금하신가요?</h3>
                            <p className="text-gray-300 mb-4 leading-relaxed">
                                업비트나 바이낸스 같은 거래소에서 자동 매매를 하려면 API 키라는 통행증이 필요합니다.
                                아래 링크를 통해 각 거래소의 공식 가이드를 확인해 보세요.
                            </p>
                            <div className="flex flex-wrap gap-4">
                                <a
                                    href="https://upbit.com/service_center/guide"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="bg-surface hover:bg-surface/80 text-white px-4 py-2.5 rounded-lg border border-gray-700 flex items-center gap-2 transition-all font-medium text-sm"
                                >
                                    <ExternalLink className="w-4 h-4 text-primary" />
                                    업비트 고객센터 가이드
                                </a>
                                <a
                                    href="https://upbit.com/mypage/open_api_management"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="bg-secondary/10 hover:bg-secondary/20 text-secondary px-4 py-2.5 rounded-lg border border-secondary/30 flex items-center gap-2 transition-all font-medium text-sm"
                                >
                                    업비트 API 관리 바로가기
                                </a>
                            </div>
                            <div className="mt-4 p-4 bg-black/30 rounded-lg border border-gray-800">
                                <h4 className="text-sm font-bold text-white mb-2 flex items-center gap-2">
                                    <ShieldCheck className="w-4 h-4 text-primary" /> 필수 확인 사항
                                </h4>
                                <ul className="text-xs text-gray-400 space-y-1.5 list-disc pl-4">
                                    <li>API 발급 시 <strong className="text-white">IP 주소 제한</strong>을 설정하는 것이 보안상 매우 중요합니다. (현재 서버 IP: <code className="bg-gray-800 text-primary px-1 rounded">13.124.235.43</code>)</li>
                                    <li>권한 설정 단계에서 <strong className="text-white">주문하기, 조회하기</strong> 권한만 체크해 주세요. <strong className="text-danger">출금 권한</strong>은 절대 체크하지 마세요.</li>
                                    <li>Secret Key는 발급 시 단 한 번만 보여주므로 반드시 따로 메모해 두셔야 합니다.</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}
