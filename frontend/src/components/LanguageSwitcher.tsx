'use client';

import { useLocale } from 'next-intl';
import { usePathname, useRouter } from '@/i18n/routing';
import { ChangeEvent, useTransition } from 'react';
import { Globe } from 'lucide-react';

export default function LanguageSwitcher() {
    const locale = useLocale();
    const router = useRouter();
    const pathname = usePathname();
    const [isPending, startTransition] = useTransition();

    const onSelectChange = (e: ChangeEvent<HTMLSelectElement>) => {
        const nextLocale = e.target.value;
        startTransition(() => {
            router.replace(pathname, { locale: nextLocale });
        });
    };

    return (
        <div className="relative flex items-center">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-white/50 border border-stone-200 rounded-lg hover:bg-white/80 transition-colors">
                <Globe className="w-4 h-4 text-stone-600" />
                <select
                    defaultValue={locale}
                    className="bg-transparent border-none text-sm font-medium text-stone-700 focus:ring-0 cursor-pointer outline-none"
                    onChange={onSelectChange}
                    disabled={isPending}
                >
                    <option value="en">English</option>
                    <option value="hi">हिंदी</option>
                </select>
            </div>
        </div>
    );
}
