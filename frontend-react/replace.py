import os
import glob

for file in glob.glob('src/pages/*.jsx'):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Target 1: The outer wrapper replacement
    content = content.replace('bg-slate-900 text-slate-50', 'bg-transparent text-slate-50')
    
    # Target 2: The headers, we want them semi-transparent or transparent so they don't block
    content = content.replace('bg-slate-900/75', 'bg-slate-900/40')
    
    # Target 3: Footers
    content = content.replace('bg-slate-900 dark:bg-emerald-600', 'bg-slate-900/40 dark:bg-emerald-600/40')
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
