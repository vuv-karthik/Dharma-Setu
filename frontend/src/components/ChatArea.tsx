'use client';

import { ScrollArea } from '@radix-ui/react-scroll-area';
import { Citation } from './Citation';
import { Bot, User, Sparkles } from 'lucide-react';
import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Mermaid } from './Mermaid';
import { motion, AnimatePresence } from 'framer-motion';
import { TypingIndicator } from './TypingIndicator';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    citations?: Array<{
        uuid: string;
        text: string;
        entity_name?: string;
        source_doc: string;
        page_number: number;
        summary: string;
        score: number;
    }>;
}

interface ChatAreaProps {
    messages: Message[];
}

export function ChatArea({ messages, isLoading }: ChatAreaProps & { isLoading?: boolean }) {
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages, isLoading]);

    return (
        <div className="h-full overflow-y-auto px-4 py-6 scroll-smooth custom-scrollbar">
            <div className="flex flex-col gap-6">
                {messages.length === 0 && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ duration: 0.5 }}
                        className="flex flex-col items-center justify-center h-full text-center text-slate-400 mt-20"
                    >
                        <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center mb-4 text-blue-500">
                            <Sparkles className="w-6 h-6" />
                        </div>
                        <h3 className="text-sm font-medium text-slate-900 mb-1">Welcome to Dharma-Setu</h3>
                        <p className="text-xs max-w-xs leading-relaxed">
                            State your legal query detailing the situation to get relevant laws, case precedents, and comprehensive analysis.
                        </p>
                    </motion.div>
                )}

                <AnimatePresence mode='popLayout'>
                    {messages.map((message, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 20, scale: 0.98 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            transition={{ duration: 0.4, ease: "easeOut" }}
                            className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            {message.role === 'assistant' && (
                                <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0 shadow-sm mt-1">
                                    <Bot className="w-5 h-5 text-white" />
                                </div>
                            )}

                            <div className={`flex flex-col gap-2 max-w-[85%] ${message.role === 'user' ? 'items-end' : 'items-start'}`}>
                                <div
                                    className={`px-5 py-3.5 rounded-2xl text-[15px] leading-relaxed shadow-sm transition-all duration-300 ${message.role === 'user'
                                        ? 'bg-slate-800 text-white rounded-tr-sm shadow-md'
                                        : 'bg-white border border-slate-100 text-slate-800 rounded-tl-sm w-full hover:shadow-md'
                                        }`}
                                >
                                    {message.role === 'user' ? (
                                        <div className="whitespace-pre-wrap">{message.content}</div>
                                    ) : (
                                        <div className="prose prose-sm prose-slate max-w-none prose-headings:font-bold prose-headings:text-slate-900 prose-p:text-slate-800 prose-li:text-slate-800 prose-strong:text-slate-900">
                                            <ReactMarkdown
                                                remarkPlugins={[remarkGfm]}
                                                components={{
                                                    code({ node, className, children, ...props }) {
                                                        const match = /language-(\w+)/.exec(className || '');
                                                        if (match && match[1] === 'mermaid') {
                                                            return <Mermaid chart={String(children).replace(/\n$/, '')} />;
                                                        }
                                                        return (
                                                            <code className={className} {...props}>
                                                                {children}
                                                            </code>
                                                        );
                                                    },
                                                    h3: ({ node, ...props }) => <h3 className="text-sm font-bold mt-4 mb-2 text-slate-900 uppercase tracking-wide" {...props} />,
                                                    ul: ({ node, ...props }) => <ul className="list-disc pl-4 space-y-1 my-2" {...props} />,
                                                    ol: ({ node, ...props }) => <ol className="list-decimal pl-4 space-y-1 my-2" {...props} />,
                                                    li: ({ node, ...props }) => <li className="pl-1" {...props} />,
                                                }}
                                            >
                                                {message.content}
                                            </ReactMarkdown>
                                        </div>
                                    )}
                                </div>

                                {message.citations && message.citations.length > 0 && (
                                    <motion.div
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: 'auto' }}
                                        transition={{ delay: 0.2, duration: 0.3 }}
                                        className="flex flex-col gap-2 w-full mt-1"
                                    >
                                        <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-1 flex items-center gap-2">
                                            <div className="h-px bg-slate-200 flex-1"></div>
                                            References & Citations
                                            <div className="h-px bg-slate-200 flex-1"></div>
                                        </div>
                                        <div className="grid grid-cols-1 gap-2">
                                            {message.citations.map((citation) => (
                                                <Citation
                                                    key={citation.uuid}
                                                    uuid={citation.uuid}
                                                    text={citation.text}
                                                    entityName={citation.entity_name}
                                                    sourceDoc={citation.source_doc}
                                                    pageNumber={citation.page_number}
                                                    summary={citation.summary}
                                                    score={citation.score}
                                                />
                                            ))}
                                        </div>
                                    </motion.div>
                                )}
                            </div>

                            {message.role === 'user' && (
                                <div className="w-8 h-8 rounded-lg bg-slate-200 flex items-center justify-center flex-shrink-0 mt-1">
                                    <User className="w-5 h-5 text-slate-500" />
                                </div>
                            )}
                        </motion.div>
                    ))}

                    {isLoading && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 10 }}
                        >
                            <TypingIndicator />
                        </motion.div>
                    )}
                </AnimatePresence>
                <div ref={scrollRef} />
            </div>
        </div>
    );
}
