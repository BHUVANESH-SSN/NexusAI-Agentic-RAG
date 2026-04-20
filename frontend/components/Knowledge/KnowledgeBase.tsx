"use client";

import React, { useState, useEffect, useRef } from 'react';
import { UploadCloud, Search, FileText, Trash2 } from 'lucide-react';

type Document = {
    name: string;
    status: string;
    size: number;
};

export default function KnowledgeBase() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const fetchDocuments = async () => {
        try {
            const res = await fetch('http://127.0.0.1:8000/documents');
            if (res.ok) {
                const data = await res.json();
                setDocuments(data.documents || []);
            }
        } catch (err) {
            console.error("Failed to fetch documents", err);
        }
    };

    useEffect(() => {
        fetchDocuments();

        const interval = setInterval(fetchDocuments, 5000);
        return () => clearInterval(interval);
    }, []);

    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0) return;
        const file = e.target.files[0];

        const formData = new FormData();
        formData.append('file', file);

        setIsUploading(true);
        try {
            const res = await fetch('http://127.0.0.1:8000/upload', {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                await fetchDocuments();
            } else {
                alert("Upload failed.");
            }
        } catch (err) {
            console.error("Upload error", err);
            alert("Network error during upload. Make sure uvicorn is running.");
        } finally {
            setIsUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const handleDelete = async (filename: string) => {
        if (!window.confirm(`Are you sure you want to delete ${filename}? This will trigger a re-indexing of the remaining documents.`)) return;

        try {
            const res = await fetch(`http://127.0.0.1:8000/documents/${filename}`, {
                method: 'DELETE'
            });
            if (res.ok) {
                await fetchDocuments();
            } else {
                alert("Failed to delete document.");
            }
        } catch (err) {
            console.error("Delete error", err);
            alert("Network error during deletion.");
        }
    };

    const handleClearAll = async () => {
        if (!window.confirm("WARNING: This will delete ALL documents and completely wipe the Knowledge Base index. Are you sure?")) return;

        try {
            const res = await fetch('http://127.0.0.1:8000/documents', {
                method: 'DELETE'
            });
            if (res.ok) {
                await fetchDocuments();
            } else {
                alert("Failed to clear knowledge base.");
            }
        } catch (err) {
            console.error("Clear error", err);
            alert("Network error during clear operation.");
        }
    };

    const filteredDocs = documents.filter(doc =>
        doc.name.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="relative min-h-screen bg-[#0f1729] overflow-x-hidden p-8 lg:p-12">
            <div className="relative z-10 max-w-[1400px] mx-auto">
                <header className="mb-12 flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div>
                        <div className="inline-flex items-center gap-3 mb-4">
                            <div className="w-8 h-px bg-[#F59E0B]"></div>
                            <span className="font-mono text-sm text-[#F59E0B] tracking-widest uppercase">Knowledge Base</span>
                        </div>
                        <h2 className="font-display text-4xl sm:text-5xl font-bold text-white tracking-tight">
                            Document <span className="text-[#F59E0B]">Index</span>
                        </h2>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="relative group w-full md:w-80">
                            <div className="absolute -inset-1 bg-gradient-to-r from-white/10 via-white/5 to-white/10 rounded-[14px] blur opacity-0 group-focus-within:opacity-100 transition-opacity duration-500"></div>
                            <div className="relative flex items-center bg-[#0d1424] border border-white/[0.08] rounded-[12px] px-4 py-3 focus-within:border-[#F59E0B]/40 transition-colors">
                                <Search size={18} className="text-white/40 mr-3" />
                                <input
                                    type="text"
                                    placeholder="Search documents..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="bg-transparent border-none outline-none text-white text-sm w-full placeholder:text-white/30 font-body"
                                />
                            </div>
                        </div>

                        <input
                            type="file"
                            accept=".pdf"
                            ref={fileInputRef}
                            onChange={handleFileChange}
                            className="hidden"
                        />
                        <button
                            onClick={handleClearAll}
                            className="flex items-center gap-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 px-5 py-3.5 rounded-[12px] font-semibold text-sm transition-all hover:-translate-y-0.5"
                        >
                            <Trash2 size={18} />
                            Clear Knowledge Base
                        </button>

                        <button
                            onClick={handleUploadClick}
                            disabled={isUploading}
                            className="flex items-center gap-2 bg-[#F59E0B] hover:bg-amber-600 disabled:opacity-50 text-black px-6 py-3.5 rounded-[12px] font-semibold text-sm transition-all hover:-translate-y-0.5 hover:shadow-[0_4px_15px_rgba(251,191,36,0.3)] whitespace-nowrap"
                        >
                            <UploadCloud size={18} />
                            {isUploading ? "Uploading..." : "Upload PDF"}
                        </button>
                    </div>
                </header>

                <div className="backdrop-blur-xl bg-[#0d1424]/70 border border-white/[0.08] rounded-[28px] overflow-hidden shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_8px_32px_rgba(0,0,0,0.4)]">
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr>
                                    <th className="font-mono text-[11px] text-white/40 uppercase tracking-widest px-8 py-6 border-b border-white/[0.05] bg-[#0a0f1a]/50">Document Name</th>
                                    <th className="font-mono text-[11px] text-white/40 uppercase tracking-widest px-8 py-6 border-b border-white/[0.05] bg-[#0a0f1a]/50">Status</th>
                                    <th className="font-mono text-[11px] text-white/40 uppercase tracking-widest px-8 py-6 border-b border-white/[0.05] bg-[#0a0f1a]/50 text-right">Size</th>
                                    <th className="font-mono text-[11px] text-white/40 uppercase tracking-widest px-8 py-6 border-b border-white/[0.05] bg-[#0a0f1a]/50 text-right w-[100px]">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredDocs.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} className="px-8 py-10 text-center text-white/50 font-body">
                                            {searchTerm ? `No documents matching "${searchTerm}"` : "No documents uploaded yet."}
                                        </td>
                                    </tr>
                                ) : (
                                    filteredDocs.map((doc, i) => (
                                        <tr key={i} className="hover:bg-white/[0.02] transition-colors group">
                                            <td className="px-8 py-6 border-b border-white/[0.05]">
                                                <div className="flex items-center gap-4">
                                                    <div className="w-10 h-10 rounded-[12px] bg-[#0a0f1a] border border-white/10 flex items-center justify-center text-white/60 shadow-inner group-hover:text-[#F59E0B] transition-colors">
                                                        <FileText size={18} />
                                                    </div>
                                                    <span className="font-medium text-white/90 text-[15px] font-body">{doc.name}</span>
                                                </div>
                                            </td>
                                            <td className="px-8 py-6 border-b border-white/[0.05]">
                                                {doc.status === 'Indexed' ? (
                                                    <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono text-[10px] uppercase tracking-wider font-semibold">
                                                        {doc.status}
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-400 font-mono text-[10px] uppercase tracking-wider font-semibold">
                                                        <div className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></div>
                                                        {doc.status}
                                                    </span>
                                                )}
                                            </td>
                                            <td className="px-8 py-6 border-b border-white/[0.05] text-right">
                                                <span className="font-mono text-[13px] text-white/50 bg-[#0a0f1a] border border-white/5 px-3 py-1.5 rounded-md">
                                                    {(doc.size / 1024).toFixed(1)} KB
                                                </span>
                                            </td>
                                            <td className="px-8 py-6 border-b border-white/[0.05] text-right">
                                                <button
                                                    onClick={() => handleDelete(doc.name)}
                                                    className="p-2.5 rounded-lg bg-red-500/5 hover:bg-red-500/10 text-red-400 border border-red-500/10 hover:border-red-500/20 transition-all opacity-0 group-hover:opacity-100"
                                                    title="Delete document"
                                                >
                                                    <Trash2 size={16} />
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}
