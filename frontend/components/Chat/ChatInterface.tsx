"use client";

import React, { useState, useEffect } from 'react';
import { Send, Sparkles } from 'lucide-react';

type Message = {
    role: 'user' | 'bot';
    text: string;
    source?: string;
};

export default function ChatInterface() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isIdReady, setIsIdReady] = useState(false);

    // Load session and messages from localStorage on mount
    useEffect(() => {
        let currentSession = localStorage.getItem('nexus_session_id');
        if (!currentSession) {
            currentSession = 'session_' + Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
            localStorage.setItem('nexus_session_id', currentSession);
        }
        setSessionId(currentSession);
        setIsIdReady(true);

        const savedMessages = localStorage.getItem('nexus_chat_messages');
        if (savedMessages) {
            try {
                setMessages(JSON.parse(savedMessages));
            } catch (e) {
                console.error("Failed to parse saved messages");
            }
        }
    }, []);

    // Save messages to localStorage whenever they change
    useEffect(() => {
        if (messages.length > 0) {
            localStorage.setItem('nexus_chat_messages', JSON.stringify(messages));
        }
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || !isIdReady || !sessionId) return;

        const userMessage = input.trim();
        setMessages(prev => [...prev, { role: 'user', text: userMessage }]);
        setInput('');
        setIsLoading(true);

        try {
            const res = await fetch('http://127.0.0.1:8000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: 'guest_user', // Will handle proper logins later
                    session_id: sessionId,
                    message: userMessage
                })
            });

            if (res.ok) {
                const data = await res.json();
                setMessages(prev => [...prev, {
                    role: 'bot',
                    text: data.answer,
                    source: data.source
                }]);
            } else {
                const errData = await res.json().catch(() => ({ detail: "Unknown error" }));
                console.error("Chat Error Response:", errData);
                setMessages(prev => [...prev, {
                    role: 'bot',
                    text: `Error: ${errData.detail || "Connection failed to backend"}`
                }]);
            }
        } catch (error) {
            setMessages(prev => [...prev, {
                role: 'bot',
                text: "Network error. Is the backend server running at http://127.0.0.1:8000?"
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    // Helper to clear chat session
    const clearSession = () => {
        if (window.confirm("Are you sure you want to clear your chat history?")) {
            setMessages([]);
            localStorage.removeItem('nexus_chat_messages');

            // Optionally cycle the session ID so backend starts fresh too
            const newSession = 'session_' + Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
            localStorage.setItem('nexus_session_id', newSession);
            setSessionId(newSession);
        }
    };

    return (
        <div className="relative min-h-screen bg-[#0f1729] overflow-x-hidden p-8 lg:p-12">
            <div className="relative z-10 max-w-[1200px] mx-auto h-[calc(100vh-140px)] flex flex-col">
                <header className="mb-10 flex items-center justify-between">
                    <div>
                        <div className="inline-flex items-center gap-3 mb-2">
                            <div className="w-8 h-px bg-[#F59E0B]"></div>
                            <span className="font-mono text-xs text-[#F59E0B] tracking-widest uppercase">Chat Interface</span>
                        </div>
                        <h2 className="font-display text-4xl font-bold text-white tracking-tight">
                            NexusAI <span className="text-[#F59E0B]">Chat</span>
                        </h2>
                    </div>
                    {messages.length > 0 && (
                        <button
                            onClick={clearSession}
                            className="bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                        >
                            Clear History
                        </button>
                    )}
                </header>

                <div className="flex-1 flex flex-col bg-[#0d1424]/70 backdrop-blur-xl border border-white/[0.08] rounded-[32px] overflow-hidden shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_8px_32px_rgba(0,0,0,0.4)] relative">

                    <div className="flex-1 overflow-y-auto p-8 lg:p-10 flex flex-col gap-8">
                        {messages.length === 0 ? (
                            <div className="flex-1 flex flex-col items-center justify-center text-center opacity-80 mt-10">
                                <div className="w-16 h-16 rounded-[20px] bg-[#F59E0B]/10 flex items-center justify-center mb-6 border border-[#F59E0B]/20 shadow-[0_0_30px_rgba(255,107,53,0.15)]">
                                    <Sparkles className="text-[#F59E0B]" size={28} />
                                </div>
                                <h2 className="font-display text-2xl font-bold text-white mb-2">How can I help you today?</h2>
                                <p className="text-white/50 max-w-md font-body">Search your connected databases, send emails, or ask general questions.</p>
                            </div>
                        ) : (
                            messages.map((msg, idx) => (
                                <div key={idx} className={`${msg.role === 'user' ? 'self-end bg-gradient-to-br from-[#F59E0B] to-amber-600 text-black max-w-[80%]' : 'self-start bg-[#121c2d]/80 text-white/90 border border-white/10 max-w-[85%]'} font-medium px-6 py-4 rounded-[24px] ${msg.role === 'user' ? 'rounded-br-[8px]' : 'rounded-bl-[8px]'} shadow-[0_8px_20px_rgba(0,0,0,0.25)] text-[15px] leading-relaxed relative font-body`}>
                                    {msg.role === 'bot' && (
                                        <div className="absolute -left-12 top-0 w-10 h-10 rounded-xl bg-[#0a0f1a] border border-white/10 flex items-center justify-center shrink-0 shadow-lg">
                                            <Sparkles className="text-[#F59E0B]" size={18} />
                                        </div>
                                    )}
                                    <p>{msg.text}</p>

                                    {msg.source && msg.source !== "generic" && (
                                        <div className="mt-3 pt-3 border-t border-white/10">
                                            <span className="font-mono text-[10px] bg-white/5 border border-white/10 px-2 py-1 rounded text-[#F59E0B]">
                                                Source: {msg.source}
                                            </span>
                                        </div>
                                    )}
                                </div>
                            ))
                        )}

                        {isLoading && (
                            <div className="self-start flex items-end gap-4 max-w-[85%] mt-4">
                                <div className="w-10 h-10 rounded-xl bg-[#0a0f1a] border border-white/10 flex items-center justify-center shrink-0 shadow-lg">
                                    <Sparkles className="text-[#F59E0B] animate-pulse" size={18} />
                                </div>
                                <div className="px-6 py-4 rounded-[24px] rounded-bl-[8px] bg-[#121c2d]/80 text-white/50 animate-pulse text-[15px]">
                                    Thinking...
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="p-6 bg-[#0a0f1a]/80 border-t border-white/[0.08] backdrop-blur-xl">
                        <div className="relative group max-w-5xl mx-auto">
                            <div className="absolute -inset-1 bg-gradient-to-r from-[#F59E0B]/20 via-amber-600/20 to-[#F59E0B]/20 rounded-[20px] blur opacity-0 group-focus-within:opacity-100 transition-opacity duration-500"></div>
                            <div className="relative flex items-center bg-[#0d1424] border border-white/[0.08] rounded-[16px] overflow-hidden shadow-inner transition-all focus-within:border-[#F59E0B]/50 focus-within:bg-[#0d1424]">
                                <input
                                    type="text"
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                                    placeholder="Ask anything..."
                                    className="flex-1 bg-transparent border-none text-white px-6 py-5 outline-none placeholder:text-white/30 text-[15px] font-body"
                                />
                                <div className="pr-4">
                                    <button
                                        onClick={handleSend}
                                        disabled={isLoading || !input.trim()}
                                        className="bg-[#F59E0B] disabled:opacity-50 text-black w-12 h-12 flex items-center justify-center rounded-[14px] font-bold transition-all hover:-translate-y-0.5 hover:shadow-[0_4px_15px_rgba(251,191,36,0.4)]"
                                    >
                                        <Send size={18} className="ml-0.5" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
