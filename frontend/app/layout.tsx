import type { Metadata } from "next";
import { Fira_Sans, Fira_Code } from "next/font/google";
import Sidebar from "@/components/Sidebar/Sidebar";
import "./globals.css";

const firaSans = Fira_Sans({
    weight: ['300', '400', '500', '600', '700'],
    subsets: ["latin"],
    variable: "--font-body"
});

const firaCode = Fira_Code({
    weight: ['400', '500', '700'],
    subsets: ["latin"],
    variable: "--font-mono"
});

export const metadata: Metadata = {
    title: "Enterprise AI | SaaS Dashboard",
    description: "Next-gen RAG Chatbot Interface",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className={`${firaSans.variable} ${firaCode.variable}`}>
            <body className="bg-[#0f1729] text-white font-body antialiased flex h-screen overflow-hidden">
                <Sidebar />
                <main className="flex-1 overflow-y-auto bg-[#0f1729] text-white antialiased relative">
                    {children}
                </main>
            </body>
        </html>
    );
}

