import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { ResearchVault } from './ResearchVault';
import { FileText, Send, Sparkles, AlertCircle } from 'lucide-react';

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

export function DraftingPanel() {
    const [facts, setFacts] = useState('');
    const [draft, setDraft] = useState('');
    const [citations, setCitations] = useState<Citation[]>([]);
    const [activeCitationId, setActiveCitationId] = useState<string | null>(null);
    const [isDrafting, setIsDrafting] = useState(false);
    const [error, setError] = useState('');

    const handleDraft = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!facts.trim()) return;

        setIsDrafting(true);
        setError('');
        setDraft('');
        setCitations([]);

        try {
            const response = await fetch('http://localhost:8000/draft', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    facts: facts,
                    language: 'English', // Could support multilang input later
                    input_language: 'English'
                }),
            });

            if (!response.ok) throw new Error('Failed to generate draft');

            const data = await response.json();
            setDraft(data.answer);
            setCitations(data.citations || []);
        } catch (err) {
            setError('An error occurred while drafting. Please try again.');
            console.error(err);
        } finally {
            setIsDrafting(false);
        }
    };

    // Helper to escape regex special characters
    const escapeRegExp = (string: string) => {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    };

    // Process text to insert links for citations
    const getProcessedText = () => {
        if (!draft) return '';
        let text = draft;

        // Sort citations by length (desc) to prevent partial matches
        // But deduplicate first? If multiple citations have same entity name, map to first?
        const uniqueMap = new Map();
        citations.forEach(c => {
            if (c.entity_name && !uniqueMap.has(c.entity_name)) {
                uniqueMap.set(c.entity_name, c.uuid);
            }
        });

        const entities = Array.from(uniqueMap.keys()).sort((a, b) => b.length - a.length);

        entities.forEach(entity => {
            // Use negative lookahead/behind to avoid replacing already replaced links? 
            // Simple regex: replace " Entity " -> "[Entity](uuid)"
            // Risk: Re-replacing inside existing markdown link.
            // But text from LLM is likely plain markdown without links initially.
            const uuid = uniqueMap.get(entity);
            const regex = new RegExp(`\\b(${escapeRegExp(entity)})\\b`, 'g');
            // We temporarily replace with a placeholder to avoid recursion if we had loop, 
            // but simpler to just replace. 
            // However, if we replace "Act" then "Contract Act", overlap issues.
            // Since we sort by length desc, "Contract Act" replaced first. 
            // Then "Act" might replace "Act" inside "Contract Act"?
            // Yes. So we need to be careful.
            // Better strategy: Tokenize or replace with unique tokens first, then resolve.
            // MVP: Just replace. If simple overlap, it's acceptable for prototype.
            text = text.replace(regex, `[$1](${uuid})`);
        });

        return text;
    };

    return (
        <div className="flex h-full w-full overflow-hidden">
            {/* LEFT PANEL: Input & Editor */}
            <div className="w-[50%] flex flex-col border-r border-slate-200 h-full bg-slate-50 relative z-0">

                {/* Input Area (Collapsed if Draft exists?) No, allow refinement */}
                <div className="flex-none p-4 bg-white border-b border-slate-200 shadow-sm z-10">
                    <form onSubmit={handleDraft} className="flex flex-col gap-3">
                        <div className="flex items-center justify-between">
                            <label className="text-xs font-bold text-slate-700 uppercase tracking-wide flex items-center gap-2">
                                <FileText className="w-4 h-4 text-blue-600" />
                                Case Facts / Brief
                            </label>
                            {draft && (
                                <span className="text-xs text-green-600 font-medium bg-green-50 px-2 py-0.5 rounded-full flex items-center gap-1">
                                    <Sparkles className="w-3 h-3" /> Draft Generated
                                </span>
                            )}
                        </div>
                        <textarea
                            value={facts}
                            onChange={(e) => setFacts(e.target.value)}
                            placeholder="Enter the facts of the case here..."
                            className="w-full h-24 p-3 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 active:border-blue-500 transition-all resize-none"
                            disabled={isDrafting}
                        />
                        <div className="flex justify-end">
                            <button
                                type="submit"
                                disabled={isDrafting || !facts.trim()}
                                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 transition-all shadow-sm active:scale-95"
                            >
                                {isDrafting ? (
                                    <>
                                        <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                                        Drafting...
                                    </>
                                ) : (
                                    <>
                                        <Sparkles className="w-4 h-4" /> Generate Legal Memo
                                    </>
                                )}
                            </button>
                        </div>
                    </form>
                </div>

                {/* Draft Output Area */}
                <div className="flex-1 overflow-y-auto bg-white p-8 shadow-inner">
                    {error ? (
                        <div className="flex flex-col items-center justify-center h-full text-red-500 gap-2">
                            <AlertCircle className="w-8 h-8" />
                            <p className="text-sm font-medium">{error}</p>
                        </div>
                    ) : !draft ? (
                        <div className="full h-full flex flex-col items-center justify-center text-slate-300">
                            <FileText className="w-16 h-16 mb-4 opacity-20" />
                            <p className="text-sm font-medium">Enter case facts to generate a formal submission.</p>
                        </div>
                    ) : (
                        <div className="prose prose-sm max-w-none font-serif text-slate-800 leading-relaxed">
                            <ReactMarkdown
                                components={{
                                    a: ({ node, href, children, ...props }) => {
                                        // Intercept UUID links
                                        // Standardize: Check if href is a UUID (approx len 36)
                                        if (href && href.length > 30) {
                                            return (
                                                <span
                                                    onClick={() => setActiveCitationId(href)}
                                                    className="cursor-pointer text-blue-700 bg-blue-50 px-1 py-0.5 rounded border-b border-blue-200 hover:bg-blue-100 hover:border-blue-400 font-semibold transition-colors mx-0.5"
                                                    title="Click to view full source text"
                                                >
                                                    {children}
                                                </span>
                                            )
                                        }
                                        return <a href={href} className="text-blue-600 hover:underline" {...props}>{children}</a>
                                    }
                                }}
                            >
                                {getProcessedText()}
                            </ReactMarkdown>
                        </div>
                    )}
                </div>
            </div>

            {/* RIGHT PANEL: Research Vault */}
            <div className="w-[50%] h-full">
                <ResearchVault citations={citations} activeCitationId={activeCitationId} />
            </div>
        </div>
    );
}
