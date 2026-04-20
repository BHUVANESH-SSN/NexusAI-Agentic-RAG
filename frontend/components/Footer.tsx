import React from 'react';

const FOOTER_LINKS = [
    {
        title: "Products & Tech",
        links: ["Agentic Framework", "Vector Databases", "Embedding Models", "Real-time Chat", "Custom Tools API", "Observability"]
    },
    {
        title: "Solutions",
        links: ["Enterprise Search", "Data Analytics", "Document QA", "Automated Workflows", "Customer Support"]
    },
    {
        title: "Developers",
        links: ["Documentation", "API Reference", "GitHub Repository", "Architecture Guide", "Status API"]
    },
    {
        title: "Company",
        links: ["About Us", "Security", "Privacy Policy", "Terms of Service", "Contact Team"]
    }
];

export function Footer() {
    return (
        <footer className="w-full bg-[#0d1424] border-t border-white/5 pt-16 pb-8 px-8 md:px-16 lg:px-24 rounded-t-[40px] mt-12 relative z-10 shadow-[0_-10px_40px_rgba(0,0,0,0.2)]">
            <div className="max-w-[1400px] mx-auto grid grid-cols-2 md:grid-cols-4 gap-8 mb-16">
                {FOOTER_LINKS.map((column, idx) => (
                    <div key={idx} className="flex flex-col gap-4">
                        <h4 className="text-white text-sm font-semibold mb-2">{column.title}</h4>
                        <ul className="flex flex-col gap-3">
                            {column.links.map((link, j) => (
                                <li key={j}>
                                    <a href="#" className="text-white/50 text-sm hover:text-[#F59E0B] transition-colors duration-200 block">
                                        {link}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </div>
                ))}
            </div>

            <div className="max-w-[1400px] mx-auto flex gap-4 items-center justify-between pt-8 border-t border-white/10 text-white/40 text-sm w-full">
                <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded-full bg-[#F59E0B] flex items-center justify-center">
                        <div className="w-1.5 h-1.5 bg-[#0d1424] rounded-full"></div>
                    </div>
                    <span className="font-semibold text-white/60">NexusAI</span> Agentic RAG
                </div>
                <div className="flex gap-6">
                    <a href="#" className="hover:text-white transition-colors">Twitter</a>
                    <a href="#" className="hover:text-white transition-colors">GitHub</a>
                    <a href="#" className="hover:text-white transition-colors">Discord</a>
                </div>
            </div>
        </footer>
    );
}
