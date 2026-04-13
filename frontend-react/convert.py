import os
import re

html_files = [
    "index.html", "student-login.html", "student.html",
    "university-login.html", "university.html", "university-issue.html",
    "university-revoke.html", "employer.html"
]

color_map = {
    "bg-[#FAFAF8]": "bg-slate-900",
    "bg-[#FAFAF8]/75": "bg-slate-900/75",
    "bg-[#FAFAF8]/95": "bg-slate-900/95",
    "bg-[#F6F3F2]": "bg-slate-800",
    "bg-[#0F0F0F]": "bg-emerald-600",
    "bg-white": "bg-slate-800",
    "text-[#0F0F0F]": "text-slate-50",
    "text-[#534439]": "text-slate-400",
    "text-[#857467]": "text-slate-500",
    "text-[#FAFAF8]": "text-white",
    "text-[#C17A3A]": "text-emerald-500",
    "text-[#2A7A5A]": "text-emerald-500",
    "text-[#B03A2A]": "text-red-500",
    "border-[#E8E6E1]": "border-slate-800",
    "border-[#E8E6E1]/50": "border-slate-800/50",
    "border-[#E8E6E1]/40": "border-slate-800/40",
    "border-[#E8E6E1]/80": "border-slate-800/80",
    "border-[#C17A3A]/20": "border-emerald-500/20",
    "hover:text-[#C17A3A]": "hover:text-emerald-400",
    "hover:bg-[#C17A3A]": "hover:bg-emerald-500",
    "hover:bg-[#F6F3F2]": "hover:bg-slate-800",
    "hover:bg-[#0F0F0F]": "hover:bg-emerald-700",
    "hover:text-[#FAFAF8]": "hover:text-white",
    "hover:border-[#0F0F0F]": "hover:border-emerald-600",
    "selection:bg-[#C17A3A]": "selection:bg-emerald-500",
    "dark:bg-[#0F0F0F]": "bg-slate-900",
    "dark:bg-[#0F0F0F]/80": "bg-slate-900/80",
    "dark:text-[#FAFAF8]": "text-white",
    "dark:border-white/20": "border-white/20",
    "dark:hover:bg-white/10": "hover:bg-white/10",
    "dark:hover:border-[#FAFAF8]": "hover:border-white",
    "dark:hover:bg-[#FAFAF8]": "hover:bg-white",
    "dark:hover:text-[#0F0F0F]": "hover:text-slate-900",
}

def jsxify(content):
    # Rip out head, body tags, scripts
    content = re.sub(r'<!DOCTYPE.*?>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<html.*?>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'</html>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<head>.*?</head>', '', content, flags=re.DOTALL|re.IGNORECASE)
    content = re.sub(r'<body.*?>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'</body>', '', content, flags=re.IGNORECASE)
    content = re.sub(r'<script.*?>.*?</script>', '', content, flags=re.DOTALL|re.IGNORECASE)

    # Class to className
    content = content.replace('class=', 'className=')
    content = content.replace('for=', 'htmlFor=')
    
    # Fill colors
    for k, v in color_map.items():
        content = content.replace(k, v)

    # Convert self closing tags
    content = re.sub(r'<hr(.*?[^/])>', r'<hr\1/>', content)
    content = re.sub(r'<input(.*?[^/])>', r'<input\1/>', content)
    content = re.sub(r'<img(.*?[^/])>', r'<img\1/>', content)

    # Convert inline styles format
    def style_replacer(match):
        style_str = match.group(1)
        # simplistic conversion
        props = [p.strip() for p in style_str.split(';') if p.strip()]
        react_style = []
        for p in props:
            if ':' in p:
                k, v = p.split(':', 1)
                k = k.strip()
                v = v.strip().replace("'", "\\'") # escape quotes? Wait, react uses object
                # camelCase
                parts = k.split('-')
                k_camel = parts[0] + ''.join(x.title() for x in parts[1:])
                react_style.append(f"{k_camel}: '{v}'")
        return "style={{" + ", ".join(react_style) + "}}"

    content = re.sub(r'style="([^"]*)"', style_replacer, content)

    # Links to standard React Router Link
    content = re.sub(r'<a(.*?)href="([^"]+)\.html"(.*?)>', r'<Link\1to="/\2"\3>', content)
    content = content.replace('href="index.html"', 'to="/"')
    content = content.replace('</a>', '</Link>')

    # Convert inner HTML comments that might break JSX if they are inside elements? 
    # Usually <!-- --> breaks JSX if outside of {...} but standard standard is { /* */ }
    content = re.sub(r'<!--(.*?)-->', r'{/* \1 */}', content)

    # Because replace can leave multiple blank lines
    content = re.sub(r'\n\s*\n', '\n', content)

    return content.strip()

for fname in html_files:
    in_path = os.path.join('../frontend', fname)
    if not os.path.exists(in_path):
        continue
    with open(in_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    jsx = jsxify(html)
    
    comp_name = fname.replace('.html', '').title().replace('-', '')
    if comp_name == "Index":
        comp_name = "Landing"
    
    out_jsx = f"""import React from 'react';
import {{ Link }} from 'react-router-dom';

const {comp_name} = () => {{
  return (
    <div className="selection:bg-emerald-500 selection:text-white overflow-x-hidden min-h-screen bg-slate-900 text-slate-50">
      {{/* Header/Footer are left embedded to match EXACT structure */}}
      {jsx}
    </div>
  );
}};

export default {comp_name};
"""
    out_path = os.path.join('src/pages', f'{comp_name}.jsx')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(out_jsx)

print("Conversion complete.")
