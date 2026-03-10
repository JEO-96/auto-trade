'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function DashboardPostRedirect() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const id = searchParams.get('id');

    useEffect(() => {
        router.replace(`/community/post?id=${id}`);
    }, [router, id]);

    return null;
}
