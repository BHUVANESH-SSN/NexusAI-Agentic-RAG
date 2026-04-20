import os
import glob

replacements = {
    "#FF6B35": "#F59E0B",   # Golden/Amber 500
    "orange-500": "amber-600",
    "Huntd RAG": "Agentic RAG"
}

files = glob.glob("/home/bhuvi/Desktop/acer/PROJECTS/company-chatbot-langchain/frontend/**/*.tsx", recursive=True)

for path in files:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {path}")
