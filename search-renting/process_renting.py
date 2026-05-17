import json
import csv
import re
import subprocess
from datetime import datetime

# Path to the results file
input_file = 'results.json'
output_file = 'zhoupu_renting_detailed.csv'

# Threshold date: 2 months before 2026-05-17 is 2026-03-17
threshold_date = datetime.strptime('2026-03-17', '%Y-%m-%d')

def get_note_content(url):
    print(f"Fetching content for: {url}")
    try:
        result = subprocess.run(
            ['opencli', 'xiaohongshu', 'note', url, '-f', 'json'],
            capture_output=True, text=True, check=True
        )
        data = json.loads(result.stdout)
        content = ""
        if isinstance(data, list):
            for item in data:
                if item.get('field') == 'desc' or item.get('field') == 'content':
                    content = item.get('value')
                    break
        elif isinstance(data, dict):
            content = data.get('desc') or data.get('content', '')
        return content
    except Exception as e:
        print(f"Error fetching content: {e}")
        return ""

def extract_details(title, content):
    text = (title + " " + content).lower()
    
    # 1. Price (价格)
    price = ""
    # Try with suffixes first
    price_match = re.search(r'(\d{3,5})(?:元|k|/月|rmb|块)', text)
    if price_match:
        price = price_match.group(1)
        if 'k' in price_match.group(0):
            price = str(int(float(price) * 1000))
    else:
        # Fallback: look for 4-digit numbers that are likely prices
        # Avoid years like 2024, 2025, 2026
        price_matches = re.findall(r'(?<!\d)(?!202[456])(\d{4})(?!\d)', text)
        if price_matches:
            price = price_matches[0]

    # 2. Compound (小区)
    compound = ""
    # Common Zhoupu compounds
    known_compounds = ['印象春城', '浦发东悦城', '逸致璟庭', '中环一号', '菱翔苑', '繁荣华庭', '繁荣馨苑', '沈梅家园', '瑞阳苑', '汇腾', '明天华城', '周康新村', '林海', '美林']
    for c in known_compounds:
        if c in text:
            compound = c
            break
    if not compound:
        # Regex for generic compound names: look for patterns ending in typical suffixes
        comp_match = re.search(r'([^\s,，。!！、]{2,10}(?:苑|名邸|家园|公寓|雅苑|华庭|悦城|春城|新村|小区))', text)
        if comp_match:
            compound = comp_match.group(1)

    # 3. Layout (户型)
    layout = ""
    # Look for "X房", "X室", "X居"
    layout_match = re.search(r'([一二三两\d][室房厅居][一二三两\d]?[室房厅居]?)', text)
    if layout_match:
        layout = layout_match.group(1)

    # 4. Pet Friendly (是否可养宠物)
    pet = "未知"
    if any(kw in text for kw in ['不养宠', '不能养宠', '严禁养宠', '禁止养宠', '无宠', '不可以养宠', '拒宠', '不宠']):
        pet = "否"
    elif any(kw in text for kw in ['可养宠', '宠物友好', '可以养宠', '猫咪', '狗狗', '养宠']):
        pet = "是"

    # 5. Rental Type (租赁方式)
    rental_type = "中介/未知"
    if any(kw in text for kw in ['房东直租', '业主直租', '一手房东', '个人房源', '自住房', '我家']):
        rental_type = "直租"
    elif any(kw in text for kw in ['中介', '佣金', '中介费', '费']):
        rental_type = "中介"

    return price, compound, layout, pet, rental_type

def filter_results():
    all_notes = []
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_content = f.read()
        
    matches = re.findall(r'\[\s*\{.*?\}\s*\]', raw_content, re.DOTALL)
    for match in matches:
        try:
            all_notes.extend(json.loads(match))
        except Exception as e:
            print(f"Error parsing match: {e}")

    unique_notes = {note['url']: note for note in all_notes}
    print(f"Total unique notes found: {len(unique_notes)}")
    
    candidates = []
    for url, note in unique_notes.items():
        title = note.get('title', '').lower()
        published_at_str = note.get('published_at', '')
        
        try:
            pub_date = datetime.strptime(published_at_str, '%Y-%m-%d')
            if pub_date < threshold_date:
                continue
        except:
            continue
            
        if '求租' in title:
            continue
            
        candidates.append(note)

    print(f"Found {len(candidates)} potential notes. Starting detailed processing...")
    
    final_results = []
    for note in candidates: # Process all candidates
        url = note['url']
        note_content = get_note_content(url)
        if not note_content:
            note_content = ""
            
        price, compound, layout, pet, rental_type = extract_details(note.get('title', ''), note_content)
        
        # Applying requested filters from previous steps
        # 1. Layout must be 2 or 3 bedroom (roughly)
        # Relaxing this a bit to catch more variations or if layout is missing but title/content implies it
        # Actually, let's keep it but make sure '两房' etc works.
        if layout and not any(kw in layout for kw in ['2', '3', '两', '三', '二']):
            continue
        
        # 2. Zhoupu check (if compound is known or Zhoupu mentioned)
        if '周浦' not in (note.get('title', '') + note_content) and not compound:
            continue

        final_results.append({
            'Title': note.get('title'),
            'Published At': note.get('published_at'),
            'Price (价格)': price,
            'Compound (小区)': compound,
            'Layout (户型)': layout,
            'Pet Friendly (是否可养宠物)': pet,
            'Rental Type (租赁方式)': rental_type,
            'Author': note.get('author'),
            'Content': note_content.replace('\n', ' '),
            'URL': url
        })

    # Write to CSV
    fieldnames = ['Title', 'Published At', 'Price (价格)', 'Compound (小区)', 'Layout (户型)', 'Pet Friendly (是否可养宠物)', 'Rental Type (租赁方式)', 'Author', 'Content', 'URL']
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_results)
        
    print(f"Successfully exported {len(final_results)} records to {output_file}")

    # Sync to Feishu Sheet
    if final_results:
        print("Syncing to Feishu Sheet...")
        sheet_token = "L4xPswHvXhQYAAtOzNYc5D4ynmg"
        values = []
        for r in final_results:
            values.append([
                r['Title'], r['Published At'], r['Price (价格)'], r['Compound (小区)'],
                r['Layout (户型)'], r['Pet Friendly (是否可养宠物)'], r['Rental Type (租赁方式)'],
                r['Author'], r['Content'], r['URL']
            ])
        
        try:
            subprocess.run([
                'lark-cli', 'sheets', '+append', 
                '--spreadsheet-token', sheet_token,
                '--values', json.dumps(values)
            ], check=True)
            print("Successfully synced to Feishu.")
        except Exception as e:
            print(f"Sync failed: {e}")

if __name__ == '__main__':
    filter_results()
