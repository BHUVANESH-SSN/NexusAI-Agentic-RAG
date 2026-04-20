import React from 'react';
import { Database, FolderHeart, Users, FileSearch, ShieldCheck, Cpu, Bot } from 'lucide-react';

export function ArchitectureDiagram() {
    return (
        <div className="w-full max-w-6xl mx-auto py-16 relative">
            <div className="text-center mb-12">
                <h3 className="text-3xl font-display font-semibold text-white mb-2">System Architecture</h3>
                <p className="text-white/40">Multi-Agent Workflow connecting unstructured and structured knowledge.</p>
            </div>

            {/* Container mapping the Rasa-pro style layout */}
            <div className="relative w-full aspect-auto md:aspect-[16/10] bg-gradient-to-br from-[#121a2f] to-[#0f1729] border border-white/[0.05] rounded-3xl p-8 lg:p-16 flex flex-col items-center justify-between shadow-2xl overflow-hidden backdrop-blur-md">

                {/* Top Dotted Box: Data Ingestion */}
                <div className="w-full max-w-4xl border border-dashed border-[#F59E0B]/30 rounded-2xl p-6 relative flex flex-col md:flex-row items-center justify-between z-10 bg-white/[0.02]">
                    <div className="flex flex-col items-center gap-2">
                        <div className="w-12 h-12 rounded-full border border-[#F59E0B]/30 bg-[#1e293b] flex items-center justify-center text-white/80">
                            <Database size={20} className="text-[#F59E0B]" />
                        </div>
                        <span className="text-white/80 text-sm font-medium">Data Source</span>
                    </div>

                    <div className="flex flex-col items-center gap-3 w-48 relative my-8 md:my-0">
                        {/* Connecting Lines Desktop */}
                        <div className="hidden md:block absolute top-[10px] -left-16 w-16 h-px bg-[#F59E0B]/30"></div>
                        <div className="hidden md:block absolute top-[36px] -left-24 w-12 h-px bg-[#F59E0B]/30 border-l border-t border-[#F59E0B]/30 translate-y-[-50%] p-3" style={{ borderBottomLeftRadius: '8px', borderTopLeftRadius: '8px' }}></div>

                        <div className="hidden md:block absolute top-[10px] -right-16 w-16 h-px bg-[#F59E0B]/30"></div>
                        <div className="hidden md:block absolute top-[36px] -right-24 w-12 h-px bg-[#F59E0B]/30 border-r border-t border-[#F59E0B]/30 translate-y-[-50%] p-3" style={{ borderBottomRightRadius: '8px', borderTopRightRadius: '8px' }}></div>

                        <PipelineBadge text="extract" />
                        <PipelineBadge text="chunk" />
                        <PipelineBadge text="vectorize" />
                    </div>

                    <div className="flex flex-col items-center gap-2 relative">
                        <div className="w-12 h-12 rounded-full border border-[#F59E0B]/30 bg-[#1e293b] flex items-center justify-center text-white/80">
                            <FolderHeart size={20} className="text-[#F59E0B]" />
                        </div>
                        <span className="text-white/80 text-sm font-medium">Vector Database</span>
                    </div>
                </div>

                {/* Arrow pointing down from Vector DB to the Agents */}
                <div className="h-16 border-l border-dashed border-[#F59E0B]/40 relative">
                    <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 border-b border-r border-[#F59E0B]/60 rotate-45"></div>
                </div>

                {/* Middle Row: Specialized Agents */}
                <div className="flex flex-wrap justify-center gap-4 z-10 w-full mb-8 relative">
                    <AgentNode icon={<FileSearch size={18} />} title="RetrieverAgent" />
                    <AgentNode icon={<Database size={18} />} title="DBAgent" />
                    <AgentNode icon={<Cpu size={18} />} title="ToolAgent" />
                    <AgentNode icon={<Users size={18} />} title="ChatAgent" />
                </div>

                {/* Central NexusAI - AgenticRAG Engine */}
                <div className="relative flex w-full max-w-4xl justify-center items-center z-10">
                    <div className="flex gap-4 items-center">
                        <div className="hidden lg:block w-32 border-b border-[#F59E0B]/30"></div>

                        <div className="relative bg-gradient-to-br from-amber-500 to-orange-600 rounded-[20px] p-6 shadow-[0_0_50px_rgba(245,158,11,0.25)] border border-[#F59E0B]/40 backdrop-blur-xl min-w-[280px] text-center transform transition-all duration-300 hover:scale-105">
                            <div className="text-white font-display text-4xl font-extrabold tracking-tight">NexusAI</div>
                            <div className="text-white/90 font-mono text-sm uppercase tracking-widest mt-1 font-bold">AgenticRAG</div>

                            {/* Inner Badge for routing supervisor */}
                            <div className="mt-4 inline-flex items-center gap-2 bg-[#0a0f1a] px-3 py-1.5 rounded-lg border border-[#F59E0B]/20 text-xs font-semibold text-white/80">
                                <Cpu size={14} className="text-[#F59E0B]" />
                                Supervisor Router
                            </div>
                        </div>

                        <div className="hidden lg:flex w-32 border-b border-[#F59E0B]/30 relative items-center">
                            <div className="absolute right-0 w-2 h-2 border-t border-r border-[#F59E0B]/50 rotate-45 -translate-y-1/2 top-1/2"></div>
                            <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs text-white/40 whitespace-nowrap">prompt + docs</span>
                        </div>

                        {/* Right LLM Engine */}
                        <div className="hidden lg:flex flex-col items-center gap-2 relative bg-white/[0.02] border border-[#F59E0B]/20 rounded-xl p-4">
                            <div className="w-12 h-12 rounded border border-[#F59E0B]/30 text-white flex items-center justify-center bg-[#0a0f1a]">
                                <Bot size={24} className="text-[#F59E0B]" />
                            </div>
                            <span className="text-[#F59E0B] text-sm font-medium">LLM Engine</span>
                        </div>
                    </div>
                </div>

                {/* Arrow from Validation to User */}
                <div className="w-px h-12 bg-[#F59E0B]/30 relative my-4 flex items-center justify-center">
                    <div className="absolute bg-[#0f1729] px-2 py-1 border border-[#F59E0B]/20 rounded text-[10px] text-[#F59E0B] uppercase flex items-center gap-1 z-10 whitespace-nowrap font-semibold">
                        <ShieldCheck size={12} className="text-green-400" />
                        ValidationAgent
                    </div>
                </div>

                {/* Bottom: User Node */}
                <div className="flex flex-col items-center gap-2 z-10 bg-[#F59E0B] text-black px-8 py-3 rounded-xl border border-[#F59E0B] font-bold shadow-[0_10px_25px_rgba(245,158,11,0.3)]">
                    <div className="flex items-center gap-2">
                        <Users size={18} className="text-black" />
                        User Interface
                    </div>
                </div>
            </div>
        </div>
    );
}

function AgentNode({ icon, title }: { icon: React.ReactNode, title: string }) {
    return (
        <div className="bg-[#1e293b]/90 border border-[#F59E0B]/20 rounded-lg py-2 px-4 flex items-center gap-3 shadow-lg hover:border-[#F59E0B] transition-colors">
            <span className="text-[#F59E0B]">{icon}</span>
            <span className="text-[#F59E0B] font-mono font-semibold text-xs">{title}</span>
        </div>
    );
}

function PipelineBadge({ text }: { text: string }) {
    return (
        <div className="bg-[#F59E0B] text-black font-bold text-[11px] uppercase tracking-wider px-4 py-1.5 rounded w-full text-center shadow-sm relative z-10">
            {text}
        </div>
    );
}
