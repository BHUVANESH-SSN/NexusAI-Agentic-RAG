"use client";

import React, { useState, useEffect } from 'react';

export default function SettingsPage() {
    const [status, setStatus] = useState<string>('');
    const [isSaving, setIsSaving] = useState(false);

    const [formData, setFormData] = useState({
        mysql_uri: '',
        email_smtp: '',
        email_user: '',
        email_password: ''
    });

    useEffect(() => {
        fetch('http://127.0.0.1:8000/settings')
            .then(res => res.json())
            .then(data => {
                if (data) {
                    setFormData({
                        mysql_uri: data.mysql_uri || '',
                        email_smtp: data.email_smtp || '',
                        email_user: data.email_user || '',
                        email_password: data.email_password || ''
                    });
                }
            })
            .catch(err => console.error("Could not fetch settings", err));
    }, []);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        setStatus('Saving securely to Database...');

        try {
            const res = await fetch('http://127.0.0.1:8000/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            if (res.ok) {
                setStatus('Settings saved securely (Symmetrically Encrypted) ✅');
            } else {
                setStatus('Failed to save settings ❌');
            }
        } catch (error) {
            setStatus('Connection Error ❌');
        }
        setIsSaving(false);
    };

    return (
        <div className="relative min-h-screen bg-[#0f1729] overflow-x-hidden p-8 lg:p-12">
            <div className="relative z-10 max-w-[800px] mx-auto">
                <header className="mb-12">
                    <h2 className="font-display text-4xl font-bold text-white tracking-tight leading-tight">
                        Integration <span className="text-amber-500">Settings</span>
                    </h2>
                    <p className="mt-4 text-white/50 leading-relaxed max-w-2xl">
                        Securely provide your MySQL and Email properties. They are symmetrically encrypted at rest seamlessly connecting to our Agentic RAG architecture.
                    </p>
                </header>

                <div className="relative backdrop-blur-xl bg-[#0d1424]/70 border border-white/[0.08] rounded-[28px] overflow-hidden shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] p-8">
                    <form onSubmit={handleSave} className="flex flex-col gap-6">

                        <div>
                            <h3 className="text-lg font-semibold text-white/90 mb-4">Database Settings</h3>
                            <div className="flex flex-col gap-2">
                                <label className="text-sm text-white/60">MySQL Connection URI</label>
                                <input
                                    name="mysql_uri"
                                    value={formData.mysql_uri}
                                    onChange={handleChange}
                                    placeholder="mysql+pymysql://user:password@localhost/dbname"
                                    className="bg-[#0f1729] border border-white/10 rounded-[12px] px-4 py-3 text-white placeholder-white/20 focus:border-amber-500/50 outline-none transition-colors"
                                />
                            </div>
                        </div>

                        <div className="h-px bg-white/5 w-full my-2"></div>

                        <div>
                            <h3 className="text-lg font-semibold text-white/90 mb-4">Email Tool Settings (SMTP)</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="flex flex-col gap-2">
                                    <label className="text-sm text-white/60">SMTP Server (host:port)</label>
                                    <input
                                        name="email_smtp"
                                        value={formData.email_smtp}
                                        onChange={handleChange}
                                        placeholder="smtp.gmail.com:587"
                                        className="bg-[#0f1729] border border-white/10 rounded-[12px] px-4 py-3 text-white placeholder-white/20 focus:border-amber-500/50 outline-none transition-colors"
                                    />
                                </div>
                                <div className="flex flex-col gap-2">
                                    <label className="text-sm text-white/60">Email Username</label>
                                    <input
                                        name="email_user"
                                        value={formData.email_user}
                                        onChange={handleChange}
                                        placeholder="user@example.com"
                                        className="bg-[#0f1729] border border-white/10 rounded-[12px] px-4 py-3 text-white placeholder-white/20 focus:border-amber-500/50 outline-none transition-colors"
                                    />
                                </div>
                                <div className="flex flex-col gap-2 md:col-span-2">
                                    <label className="text-sm text-white/60">Email Password / App Password</label>
                                    <input
                                        type="password"
                                        name="email_password"
                                        value={formData.email_password}
                                        onChange={handleChange}
                                        placeholder="••••••••••••"
                                        className="bg-[#0f1729] border border-white/10 rounded-[12px] px-4 py-3 text-white placeholder-white/20 focus:border-amber-500/50 outline-none transition-colors"
                                    />
                                </div>
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={isSaving}
                            className="mt-4 bg-gradient-to-r from-amber-400 to-amber-600 hover:opacity-90 text-black px-6 py-3.5 rounded-[12px] font-semibold transition-all disabled:opacity-50"
                        >
                            {isSaving ? "Encrypting & Saving..." : "Save Credentials"}
                        </button>

                        {status && (
                            <div className="text-sm font-mono text-amber-500 bg-amber-500/10 px-4 py-3 rounded-[8px] mt-2 border border-amber-500/20">
                                {status}
                            </div>
                        )}
                    </form>
                </div>
            </div>
        </div>
    );
}
