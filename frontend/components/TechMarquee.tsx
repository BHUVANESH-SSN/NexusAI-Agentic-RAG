"use client";

import React from 'react';


const TECH_LOGOS = [
    {
        name: 'FastAPI',
        url: 'https://cdn.worldvectorlogo.com/logos/fastapi-1.svg', grayscale: true
    },
    {
        name: 'Claude',
        url: 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTpqjBIEH4U2Y6xS1rmRJJh-ygpHjhBb_6x6A&s', grayscale: false
    },
    {
        name: 'OpenAI',
        url: '/openai-custom.svg', grayscale: false
    },
    {
        name: 'MariaDB',
        url: 'https://cdn.worldvectorlogo.com/logos/mariadb.svg', grayscale: true
    },
    {
        name: 'Redis',
        url: 'https://cdn.worldvectorlogo.com/logos/redis.svg', grayscale: true
    },
    {
        name: 'LangChain',
        url: '/langchain-custom.svg', grayscale: true
    },
] as const;

export function TechMarquee() {
    return (
        <div className="w-full relative overflow-hidden py-10 bg-transparent flex flex-col items-center">
            <h3 className="text-white/40 font-mono text-sm uppercase tracking-widest mb-8">Powered by Industry Leading Tech</h3>

            {/* Fade overlays */}
            <div className="absolute left-0 top-0 w-24 h-full bg-gradient-to-r from-[#0f1729] to-transparent z-10 pointer-events-none"></div>
            <div className="absolute right-0 top-0 w-24 h-full bg-gradient-to-l from-[#0f1729] to-transparent z-10 pointer-events-none"></div>

            <div className="flex w-full overflow-hidden whitespace-nowrap">
                <div className="flex shrink-0 animate-marquee items-center gap-20 md:gap-32 px-10">
                    {TECH_LOGOS.map((tech, idx) => (
                        <div key={`${tech.name}-1-${idx}`} className={`opacity-70 hover:opacity-100 transition-opacity duration-300 ${tech.name === 'Claude' ? 'drop-shadow-[0_0_15px_rgba(217,119,87,0.3)]' : ''}`}>
                            <img
                                src={tech.url}
                                alt={tech.name}
                                className={`h-10 md:h-12 object-contain transition-all duration-300 ${tech.grayscale ? 'filter grayscale hover:grayscale-0' : ''
                                    } ${'extraClass' in tech ? tech.extraClass : ''}`}
                            />
                        </div>
                    ))}
                </div>
                {/* Duplicate for seamless infinite scrolling */}
                <div aria-hidden="true" className="flex shrink-0 animate-marquee items-center gap-20 md:gap-32 px-10">
                    {TECH_LOGOS.map((tech, idx) => (
                        <div key={`${tech.name}-2-${idx}`} className={`opacity-70 hover:opacity-100 transition-opacity duration-300 ${tech.name === 'Claude' ? 'drop-shadow-[0_0_15px_rgba(217,119,87,0.3)]' : ''}`}>
                            <img
                                src={tech.url}
                                alt={tech.name}
                                className={`h-10 md:h-12 object-contain transition-all duration-300 ${tech.grayscale ? 'filter grayscale hover:grayscale-0' : ''
                                    } ${'extraClass' in tech ? tech.extraClass : ''}`}
                            />
                        </div>
                    ))}
                </div>
            </div>

            <style dangerouslySetInnerHTML={{
                __html: `
                @keyframes marquee {
                    0% { transform: translateX(0%); }
                    100% { transform: translateX(-100%); }
                }
                .animate-marquee {
                    animation: marquee 30s linear infinite;
                }
            `}} />
        </div>
    );
}
