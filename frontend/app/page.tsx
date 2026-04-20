import React from 'react';

export default function Home() {
    return (
        <div className="relative min-h-screen bg-[#0f1729] overflow-x-hidden p-8 lg:p-12">
            {/* Background blobs from HTML dump */}
            <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden" aria-hidden="true">
                <div className="absolute -top-1/4 left-1/4 w-[1000px] h-[800px] -translate-x-1/2">
                    <div className="w-full h-full rounded-full bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-amber-600/15 via-amber-600/5 to-transparent blur-3xl"></div>
                </div>
            </div>

            <div className="relative z-10 max-w-[1400px] mx-auto">
                <header className="mb-16">
                    <div className="inline-flex items-center gap-3 mb-4">
                        <div className="w-8 h-px bg-[#F59E0B]"></div>
                        <span className="font-mono text-sm text-[#F59E0B] tracking-widest uppercase">System Dashboard</span>
                        <div className="w-8 h-px bg-[#F59E0B]"></div>
                    </div>
                    <h2 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight leading-tight">
                        Enterprise AI <span className="text-[#F59E0B]">—Overview</span>
                    </h2>
                    <p className="mt-4 text-xl text-white/50 leading-relaxed max-w-2xl">
                        Manage your knowledge base, chat interfaces, and observability data in one centralized dashboard.
                    </p>
                </header>

                <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
                    <DashboardOverview />
                </section>
            </div>
        </div>
    );
}

function DashboardOverview() {
    return (
        <>
            <StatCard label="Avg Confidence" value="94%" desc="Accuracy across latest queries" />
            <StatCard label="Docs Indexed" value="142" desc="Total files in knowledge base" />
            <StatCard label="Success Rate" value="98.2%" desc="Retrieval success rate" />
        </>
    );
}

function StatCard({ label, value, desc }: { label: string, value: string, desc: string }) {
    return (
        <div className="relative w-full group cursor-pointer">
            <div className="absolute -inset-4 bg-gradient-to-r from-amber-600/20 to-amber-500/20 rounded-[32px] blur-xl opacity-0 group-hover:opacity-50 transition-opacity duration-500"></div>
            <div className="relative backdrop-blur-xl bg-[#0d1424]/70 border border-white/[0.08] rounded-[28px] overflow-hidden shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_8px_32px_rgba(0,0,0,0.4)] flex flex-col p-8 h-full transition-all duration-300 group-hover:-translate-y-1 group-hover:border-[#F59E0B]/30">
                <h3 className="font-display text-lg font-semibold text-white/80 mb-6">{label}</h3>
                <div className="mt-auto">
                    <div className="text-5xl font-bold text-white mb-2">{value}</div>
                    <p className="text-sm font-mono text-white/40">{desc}</p>
                </div>
            </div>
        </div>
    );
}
