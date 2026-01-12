import { useEffect, useRef } from 'react';
import { BookOpen, Scale, FileText } from 'lucide-react';

interface Citation {
    uuid: string;
    text: string;
    source_doc: string;
    page_number: number;
    law_type: string;
    score: number;
    entity_name?: string;
    summary: string;
}

interface ResearchVaultProps {
    citations: Citation[];
    activeCitationId: string | null;
}

export function ResearchVault({ citations, activeCitationId }: ResearchVaultProps) {
    const scrollRefs = useRef<{ [key: string]: HTMLDivElement | null }>({});

    // Auto-scroll to active citation
    useEffect(() => {
        if (activeCitationId && scrollRefs.current[activeCitationId]) {
            scrollRefs.current[activeCitationId]?.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
            });
        }
    }, [activeCitationId]);

    if (!citations || citations.length === 0) {
        return (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 p-8 text-center">
                <BookOpen className="w-12 h-12 mb-4 opacity-50" />
                <p className="text-sm font-medium">Research Vault is empty.</p>
                <p className="text-xs mt-1">Generate a draft to see relevant legal sources here.</p>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col bg-slate-50 border-l border-slate-200">
            <div className="p-4 border-b border-slate-200 bg-white flex items-center gap-2 sticky top-0 z-10">
                <BookOpen className="w-4 h-4 text-slate-600" />
                <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide">Research Vault</h2>
                <span className="text-xs px-2 py-0.5 bg-slate-100 rounded-full text-slate-500 font-medium ml-auto">
                    {citations.length} Sources
                </span>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {citations.map((citation) => (
                    <div
                        key={citation.uuid}
                        ref={(el) => {
                            if (el) scrollRefs.current[citation.uuid] = el;
                        }}
                        className={`group relative bg-white rounded-lg border transition-all duration-300 ${activeCitationId === citation.uuid
                                ? 'border-blue-500 shadow-md ring-1 ring-blue-500/20'
                                : 'border-slate-200 hover:border-blue-300 hover:shadow-sm'
                            }`}
                    >
                        {/* Header */}
                        <div className="px-4 py-3 border-b border-slate-100 flex items-start justify-between bg-slate-50/50 rounded-t-lg">
                            <div className="flex items-center gap-2">
                                <div className={`p-1.5 rounded-md ${citation.law_type === 'Statute' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                                    {citation.law_type === 'Statute' ? <Scale className="w-3.5 h-3.5" /> : <FileText className="w-3.5 h-3.5" />}
                                </div>
                                <div>
                                    <h3 className="text-xs font-bold text-slate-800 leading-tight">
                                        {citation.entity_name || "Legal Source"}
                                    </h3>
                                    <p className="text-[10px] text-slate-500 font-medium truncate w-48">
                                        {citation.source_doc} • Page {citation.page_number}
                                    </p>
                                </div>
                            </div>
                            <div className="text-[10px] font-mono text-slate-400">
                                {(citation.score * 100).toFixed(0)}% Match
                            </div>
                        </div>

                        {/* Content */}
                        <div className="p-4">
                            <p className="text-xs leading-relaxed text-slate-700 font-serif whitespace-pre-wrap">
                                {citation.text}
                            </p>
                        </div>

                        {/* Active Indicator */}
                        {activeCitationId === citation.uuid && (
                            <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500 rounded-l-lg animate-pulse" />
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
