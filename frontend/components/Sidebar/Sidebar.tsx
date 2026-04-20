"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BarChart3, MessageSquare, Database, Settings, HelpCircle, LayoutDashboard, BrainCircuit } from 'lucide-react';

const navItems = [
    { icon: LayoutDashboard, label: "Dashboard", href: "/" },
    { icon: MessageSquare, label: "Chat Interface", href: "/chat" },
    { icon: Database, label: "Knowledge Base", href: "/knowledge" },
];

const secondaryItems = [
    { icon: Settings, label: "Settings", href: "/settings" },
    { icon: HelpCircle, label: "Help", href: "/help" },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="w-[280px] bg-[#0a0f1a] border-r border-[#ffffff1a] flex flex-col px-5 py-8 z-50 shadow-[10px_0_40px_rgba(0,0,0,0.2)]">
            <div className="flex items-center gap-3 mb-10 px-2 group cursor-pointer">
                <div className="relative w-10 h-10 flex items-center justify-center rounded-[14px] bg-[#0d1424] border border-[#ffffff1a] transition-transform group-hover:scale-105">
                    <BrainCircuit size={20} className="text-[#F59E0B] relative z-10" />
                    <div className="absolute inset-0 rounded-[14px] bg-[#F59E0B]/20 blur-md -z-0"></div>
                </div>
                <span className="font-display font-bold text-xl tracking-tight text-white drop-shadow-[0_2px_4px_rgba(0,0,0,0.8)]">Agentic RAG</span>
            </div>

            <nav className="flex-1 flex flex-col gap-6">
                <div className="flex flex-col gap-1.5">
                    {navItems.map((item) => {
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`flex items-center gap-3 px-5 py-3 rounded-[20px] text-sm font-medium transition-all duration-300 ${isActive
                                        ? "text-white bg-[#0d1424]/70 backdrop-blur-xl border border-white/[0.08] shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_8px_32px_rgba(0,0,0,0.4)]"
                                        : "text-white/50 hover:text-white hover:bg-white/[0.04] border border-transparent"
                                    }`}
                            >
                                <item.icon size={18} className={isActive ? "text-[#F59E0B]" : ""} />
                                <span>{item.label}</span>
                            </Link>
                        );
                    })}
                </div>

                <div className="mt-auto pt-6 border-t border-white/[0.08] flex flex-col gap-1.5">
                    {secondaryItems.map((item) => {
                        const isActive = pathname === item.href;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={`flex items-center gap-3 px-5 py-3 rounded-[20px] text-sm font-medium transition-all duration-300 ${isActive
                                        ? "text-white bg-[#0d1424]/70 backdrop-blur-xl border border-white/[0.08] shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]"
                                        : "text-white/50 hover:text-white hover:bg-white/[0.04] border border-transparent"
                                    }`}
                            >
                                <item.icon size={18} className={isActive ? "text-[#F59E0B]" : ""} />
                                <span>{item.label}</span>
                            </Link>
                        );
                    })}
                </div>
            </nav>
        </aside>
    );
}

