'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, AlertTriangle, CheckCircle, ArrowRight, X, Search } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface Finding {
    citation: string;
    status: 'OUTDATED' | 'WARNING' | 'OK';
    suggestion?: string;
    reasoning: string;
    severity: 'HIGH' | 'MEDIUM' | 'LOW';
}

interface AuditResult {
    filename: string;
    findings: Finding[];
    total_citations: number;
}

interface AuditPanelProps {
    onCitationClick?: (citation: string) => void;
}

export function AuditPanel({ onCitationClick }: AuditPanelProps) {
    const [file, setFile] = useState<File | null>(null);
    const [isAuditing, setIsAuditing] = useState(false);
    const [result, setResult] = useState<AuditResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setResult(null);
            setError(null);
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const droppedFile = e.dataTransfer.files[0];
            if (droppedFile.name.endsWith('.txt') || droppedFile.name.endsWith('.pdf')) {
                setFile(droppedFile);
                setResult(null);
                setError(null);
            } else {
                setError('Only .txt and .pdf files are supported.');
            }
        }
    };

    const handleAudit = async () => {
        if (!file) return;

        setIsAuditing(true);
        setError(null);
        setResult(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('http://localhost:8000/audit', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Audit failed');
            }

            const data = await response.json();
            setResult(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsAuditing(false);
        }
    };

    return (
        <div className="h-full flex flex-col bg-white">
            <div className="flex-1 p-8 overflow-y-auto custom-scrollbar">
                <div className="max-w-3xl mx-auto flex flex-col gap-8">

                    {/* Header */}
                    <div className="text-center">
                        <h2 className="text-2xl font-bold text-slate-900 mb-2">Legal Document Audit</h2>
                        <p className="text-slate-500 text-sm">
                            Upload your legal draft (PDF or Text) to check for outdated laws and get compliance suggestions.
                            We verify against the latest BNS regime.
                        </p>
                    </div>

                    {/* Upload Zone */}
                    <div
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        className={`border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center gap-4 transition-all duration-200
                            ${isDragging ? 'border-blue-500 bg-blue-50 scale-105' : 'border-slate-200 hover:border-blue-400 hover:bg-blue-50/10'}
                        `}
                    >
                        <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-2 transition-colors
                            ${isDragging ? 'bg-blue-200 text-blue-700' : 'bg-blue-50 text-blue-500'}
                        `}>
                            <Upload className="w-8 h-8" />
                        </div>

                        {file ? (
                            <div className="flex items-center gap-3 bg-white border border-slate-200 px-4 py-2 rounded-lg shadow-sm">
                                <FileText className="w-5 h-5 text-blue-500" />
                                <span className="text-sm font-medium text-slate-700">{file.name}</span>
                                <button onClick={() => setFile(null)} className="text-slate-400 hover:text-red-500">
                                    <X className="w-4 h-4" />
                                </button>
                            </div>
                        ) : (
                            <div className="text-center">
                                <label className="cursor-pointer bg-slate-900 text-white px-6 py-2.5 rounded-lg font-medium text-sm hover:bg-slate-800 transition-colors shadow-sm">
                                    Select Document
                                    <input type="file" className="hidden" accept=".txt,.pdf" onChange={handleFileChange} />
                                </label>
                                <p className="text-xs text-slate-400 mt-2">or drag and drop .txt/.pdf here</p>
                            </div>
                        )}

                        {file && (
                            <button
                                onClick={handleAudit}
                                disabled={isAuditing}
                                className={`w-full max-w-xs mt-4 py-3 rounded-xl font-bold shadow-sm transition-all text-white
                                    ${isAuditing ? 'bg-slate-400' : 'bg-blue-600 hover:bg-blue-700 hover:shadow-md hover:scale-[1.02]'}
                                `}
                            >
                                {isAuditing ? 'Auditing Document...' : 'Run Compliance Check'}
                            </button>
                        )}
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-xl text-sm flex items-center gap-2">
                            <AlertTriangle className="w-5 h-5" />
                            {error}
                        </div>
                    )}

                    {/* Results */}
                    {result && (
                        <div className="flex flex-col gap-6 animate-in slide-in-from-bottom-4 duration-500 pb-10">
                            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                                <h3 className="font-bold text-slate-900 flex items-center gap-2">
                                    <CheckCircle className="w-5 h-5 text-green-500" />
                                    Audit Findings
                                </h3>
                                <div className="text-xs font-semibold text-slate-500 bg-slate-50 px-3 py-1 rounded-full border border-slate-200">
                                    {result.total_citations} Citations Analysed
                                </div>
                            </div>

                            {result.findings.length === 0 ? (
                                <div className="bg-green-50 text-green-700 p-6 rounded-xl border border-green-200 text-center">
                                    <p className="font-medium">No outdated laws detected!</p>
                                    <p className="text-sm mt-1 opacity-80">Your document appears compliant with the current regime.</p>
                                </div>
                            ) : (
                                <div className="grid gap-4">
                                    {result.findings.map((finding, idx) => (
                                        <div
                                            key={idx}
                                            className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md hover:border-blue-300 transition-all cursor-pointer group"
                                            onClick={() => onCitationClick?.(finding.citation)}
                                        >
                                            <div className="flex items-start justify-between gap-4 mb-3">
                                                <div className="flex items-center gap-3">
                                                    <span className={`px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wide
                                                        ${finding.severity === 'HIGH' ? 'bg-red-100 text-red-600' :
                                                            finding.severity === 'MEDIUM' ? 'bg-orange-100 text-orange-600' : 'bg-blue-100 text-blue-600'}
                                                    `}>
                                                        {finding.status}
                                                    </span>
                                                    <h4 className="font-mono text-sm font-bold text-slate-800 border-b border-dotted border-slate-400 group-hover:text-blue-600 group-hover:border-blue-600 transition-colors">
                                                        {finding.citation}
                                                    </h4>
                                                </div>
                                                {finding.suggestion && (
                                                    <div className="flex items-center gap-2 text-sm font-bold text-blue-600 bg-blue-50 px-3 py-1.5 rounded-lg border border-blue-100">
                                                        <span>Replace with</span>
                                                        <ArrowRight className="w-4 h-4" />
                                                        <span>{finding.suggestion}</span>
                                                    </div>
                                                )}
                                            </div>

                                            <div className="bg-slate-50 rounded-lg p-3 text-sm text-slate-600 leading-relaxed border border-slate-100">
                                                <ReactMarkdown>{finding.reasoning}</ReactMarkdown>
                                                <div className="mt-2 flex items-center gap-1 text-[10px] font-bold text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <Search className="w-3 h-3" />
                                                    View in Knowledge Graph
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
