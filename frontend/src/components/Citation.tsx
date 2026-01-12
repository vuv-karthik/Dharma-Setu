'use client';

import { useAppStore } from '@/store/appStore';
import { Scale, ArrowRight, X } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';

interface CitationProps {
    uuid: string;
    text: string;
    entityName?: string;
    sourceDoc: string;
    pageNumber: number;
    summary: string;
    score: number;
}

export function Citation({ uuid, text, entityName, sourceDoc, pageNumber, summary, score }: CitationProps) {
    const activeNodeId = useAppStore((state) => state.activeNodeId);
    const isActive = activeNodeId === uuid;

    return (
        <Dialog.Root>
            <Dialog.Trigger asChild>
                <div
                    className={`
            relative group flex flex-col gap-2 p-3 rounded-xl border transition-all duration-300 cursor-pointer text-left w-full
            ${isActive
                            ? 'bg-blue-50/50 border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.15)] ring-1 ring-blue-500/20'
                            : 'bg-white border-slate-200 hover:border-blue-300 hover:shadow-sm'
                        }
          `}
                >
                    {/* Header */}
                    <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2">
                            <div className={`p-1.5 rounded-md ${isActive ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-500 group-hover:bg-blue-50 group-hover:text-blue-500 transition-colors'}`}>
                                <Scale className="w-3.5 h-3.5" />
                            </div>
                            <div>
                                {entityName && (
                                    <h4 className={`text-sm font-semibold leading-none mb-1 ${isActive ? 'text-blue-700' : 'text-slate-800'}`}>
                                        {entityName}
                                    </h4>
                                )}
                                <span className="text-[10px] text-slate-500 flex items-center gap-1 font-medium">
                                    {sourceDoc}
                                    <span className="w-0.5 h-0.5 rounded-full bg-slate-300"></span>
                                    pg. {pageNumber}
                                </span>
                            </div>
                        </div>
                        <div className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${isActive ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'}`}>
                            {Math.round(score * 100)}% Match
                        </div>
                    </div>

                    {/* Body */}
                    <div className={`text-xs leading-relaxed ${isActive ? 'text-slate-700' : 'text-slate-600'}`}>
                        {summary}
                    </div>

                    {/* Action Hint */}
                    <div className={`flex items-center gap-1 text-[10px] font-medium transition-colors ${isActive ? 'text-blue-600' : 'text-slate-400 group-hover:text-blue-500'}`}>
                        <span>View context</span>
                        <ArrowRight className="w-3 h-3" />
                    </div>

                    {/* Active Indicator Line */}
                    {isActive && (
                        <div className="absolute left-0 top-3 bottom-3 w-0.5 bg-blue-500 rounded-r-full"></div>
                    )}
                </div>
            </Dialog.Trigger>

            <Dialog.Portal>
                <Dialog.Overlay className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 transition-all duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
                <Dialog.Content className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg max-h-[85vh] bg-white rounded-2xl shadow-2xl z-50 overflow-hidden flex flex-col border border-slate-200 transition-all duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]">
                    {/* Dialog Header */}
                    <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                        <div className="flex items-center gap-2.5">
                            <div className="bg-blue-50 p-2 rounded-lg text-blue-600">
                                <Scale className="w-5 h-5" />
                            </div>
                            <div>
                                <Dialog.Title className="text-base font-bold text-slate-900 leading-none">
                                    Citation Details
                                </Dialog.Title>
                                <Dialog.Description className="text-xs text-slate-500 mt-1">
                                    {sourceDoc} • Page {pageNumber}
                                </Dialog.Description>
                            </div>
                        </div>
                        <Dialog.Close className="p-2 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors">
                            <X className="w-4 h-4" />
                        </Dialog.Close>
                    </div>

                    {/* Dialog Content */}
                    <div className="p-6 overflow-y-auto custom-scrollbar">
                        {entityName && (
                            <div className="mb-4">
                                <span className="inline-block px-2 py-1 bg-blue-50 text-blue-700 text-xs font-semibold rounded-md border border-blue-100">
                                    {entityName}
                                </span>
                            </div>
                        )}
                        <div className="prose prose-sm prose-slate max-w-none">
                            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 text-slate-700 text-sm leading-relaxed whitespace-pre-wrap font-serif">
                                {text}
                            </div>
                        </div>
                    </div>
                </Dialog.Content>
            </Dialog.Portal>
        </Dialog.Root>
    );
}
