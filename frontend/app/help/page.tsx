"use client";

import React from 'react';

export default function HelpPage() {
    return (
        <div className="relative min-h-screen bg-[#0f1729] overflow-x-hidden p-8 lg:p-12">
            <div className="relative z-10 max-w-[800px] mx-auto">
                <header className="mb-12">
                    <h2 className="font-display text-4xl font-bold text-white tracking-tight leading-tight">
                        Agentic RAG <span className="text-amber-500">Help</span>
                    </h2>
                    <p className="mt-4 text-white/50 leading-relaxed max-w-2xl">
                        A quick guide to utilizing your full-stack AI platform.
                    </p>
                </header>

                <div className="relative backdrop-blur-xl bg-[#0d1424]/70 border border-white/[0.08] rounded-[28px] overflow-hidden shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] p-8">
                    <article className="prose prose-invert prose-amber max-w-none">
                        <h3 className="text-2xl font-bold mb-4">Architecture Overview</h3>
                        <p className="text-white/70 mb-6 leading-relaxed">
                            This application is powered by a multi-agent LangGraph system consisting of specialized agents:
                            <br /><br />
                            <strong className="text-white">1. Validation Agent:</strong> Ensures final chatbot responses don't include hallucinations or expose unauthorized information.<br />
                            <strong className="text-white">2. DB Agent:</strong> Safely queries your mapped MySQL databases directly via Natural Language to SQL.<br />
                            <strong className="text-white">3. Tool Agent:</strong> Utilizes custom tools, for example directly sending emails securely using configured SMTP.<br />
                            <strong className="text-white">4. Retriever Agent:</strong> Performs similarity searches on company documents and PDFs.
                        </p>

                        <h3 className="text-2xl font-bold mb-4 mt-8">Secure Configuration</h3>
                        <p className="text-white/70 leading-relaxed">
                            Under the <strong>Settings</strong> page, you can dynamically upload your API and DB credentials.
                            These are encrypted heavily at rest using Symmetric Fernet Encryption to ensure that any data stored in our internal SQLite cache cannot be intercepted.
                        </p>
                    </article>
                </div>
            </div>
        </div>
    );
}
