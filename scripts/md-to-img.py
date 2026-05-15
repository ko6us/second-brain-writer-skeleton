import os
import sys
import re
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import hashlib
from io import StringIO

import textwrap

def md_table_to_png(md_table, output_path):
    # Clean up and split lines
    md_table = md_table.strip()
    lines = md_table.split('\n')
    
    # Filter out alignment row (e.g. |---|---)
    clean_lines = []
    for line in lines:
        l = line.strip()
        if not l: continue
        if re.match(r'^\|?[\s\-\:\|]+\|?$', l):
            continue
        clean_lines.append(l)
    
    csv_data = "\n".join(clean_lines)
    
    # Read as pipe-separated values
    try:
        df = pd.read_csv(StringIO(csv_data), sep="\\|", engine="python", skipinitialspace=True)
        
        # Robustly drop "Unnamed" columns at the edges
        cols = df.columns.tolist()
        start_idx = 0
        while start_idx < len(cols) and "Unnamed" in str(cols[start_idx]):
            start_idx += 1
        
        end_idx = len(cols)
        while end_idx > start_idx and "Unnamed" in str(cols[end_idx - 1]):
            end_idx -= 1
            
        df = df.iloc[:, start_idx:end_idx]
        df.columns = [str(c).strip() for c in df.columns]
        df = df.map(lambda x: str(x).strip() if pd.notnull(x) else "")
    except Exception as e:
        raise ValueError(f"Failed to parse table with pandas: {e}")

    # Text wrapping and dimensions calculation
    MAX_CHARS_PER_LINE = 18
    def wrap_text(text, width=MAX_CHARS_PER_LINE):
        if not text: return ""
        # textwrap handles Japanese characters well in Python 3
        return "\n".join(textwrap.wrap(str(text), width=width))

    df_wrapped = df.map(wrap_text)
    cols_wrapped = [wrap_text(c, width=12) for c in df.columns] # Headers can be narrower
    
    num_cols = len(df.columns)
    num_rows = len(df)
    
    # Calculate column widths and row heights
    # Estimating width: 0.15 inch per character (approx)
    col_widths = []
    for i, col in enumerate(df.columns):
        # Find max lines and max chars in wrapped content
        all_vals = [cols_wrapped[i]] + df_wrapped.iloc[:, i].tolist()
        max_line_width = 0
        for val in all_vals:
            lines = val.split('\n')
            max_line_width = max(max_line_width, max([len(l) for l in lines] + [0]))
        
        col_widths.append(max(max_line_width * 0.14, 1.2))

    row_heights = []
    # Header
    header_max_lines = max([c.count('\n') for c in cols_wrapped] + [0]) + 1
    row_heights.append(header_max_lines * 0.3 + 0.2)
    # Body
    for i in range(num_rows):
        row_max_lines = max([str(val).count('\n') for val in df_wrapped.iloc[i]] + [0]) + 1
        row_heights.append(row_max_lines * 0.3 + 0.2)

    total_width = sum(col_widths)
    total_height = sum(row_heights)
    
    fig, ax = plt.subplots(figsize=(total_width, total_height))
    ax.axis("off")
    
    table = ax.table(
        cellText=df_wrapped.values,
        colLabels=cols_wrapped,
        cellLoc="left",
        loc="center",
        colWidths=col_widths
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    
    # Styling and applying calculated heights
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor('#dddddd')
        cell.set_linewidth(0.8)
        
        # Set height
        cell.set_height(row_heights[row] / total_height)
        
        if row == 0:
            # Header styling
            cell.set_facecolor('#404040')
            cell.get_text().set_color('white')
            cell.set_text_props(weight='bold', ha='center')
        else:
            # Body styling
            if row % 2 == 0:
                cell.set_facecolor('#f9f9f9')
            else:
                cell.set_facecolor('white')
            
            # Padding-like effect using alignment
            cell.get_text().set_ha('left')
            # Small horizontal offset for better readability
            # (Note: set_position is relative to cell, but tricky in matplotlib table)

    plt.savefig(output_path, dpi=200, bbox_inches="tight", transparent=False)
    plt.close()
    return True


def process_file(file_path):
    print(f"Processing: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern for new tables (not yet converted)
    # We use a negative lookahead to avoid matching tables already inside <!-- -->
    # However, a simpler way is to just find all tables and check if they are already processed.
    
    # 1. First, handle already converted tables to allow updates
    # Pattern: ![table](...) followed by <!-- table -->
    update_pattern = re.compile(r'!\[table\]\((table_[a-f0-9]+\.png)\)\s*<!--\s*(\n\|.*?\|[\s\S]*?\n)\s*-->', re.MULTILINE)
    
    def update_existing(match):
        old_img_name = match.group(1)
        table_text = match.group(2).strip()
        table_hash = hashlib.md5(table_text.encode('utf-8')).hexdigest()[:8]
        new_img_name = f"table_{table_hash}.png"
        img_path = os.path.join(os.path.dirname(file_path), new_img_name)
        
        print(f"  Updating: {new_img_name}")
        try:
            md_table_to_png(table_text, img_path)
            # If the hash changed, we might want to delete the old image, 
            # but for now let's just return the new content.
            return f"![table]({new_img_name})\n\n<!--\n{table_text}\n-->"
        except Exception as e:
            print(f"  Warning: {e}")
            return match.group(0)

    # 2. Then, handle new tables
    # To avoid matching tables inside comments, we can mask comments temporarily,
    # BUT we want to avoid masking the ones we just updated or might update.
    # Actually, let's just mask ALL comments that DON'T look like our table-storage comments.
    
    # Mask non-table comments
    other_comments = []
    def mask_other_comment(m):
        comment_text = m.group(0)
        # If it's a table-storage comment, don't mask it yet (or mask it specifically)
        if re.search(r'^\s*\|.*\|', m.group(1), re.MULTILINE):
            return comment_text 
        other_comments.append(comment_text)
        return f"__OTHER_COMMENT_MASK_{len(other_comments)-1}__"
    
    masked_content = re.sub(r'<!--(.*?)-->', mask_other_comment, content, flags=re.DOTALL)

    # Now find new tables in the remaining content
    table_pattern = re.compile(r'((?:^|\n)\|.*?\|[ \t]*\n\|[ \-\:\|]+\|[ \t]*\n(?:\|.*?\|[ \t]*(?:\n|$))+)', re.MULTILINE)

    def replace_with_img(match):
        table_text = match.group(1).strip()
        table_hash = hashlib.md5(table_text.encode('utf-8')).hexdigest()[:8]
        img_name = f"table_{table_hash}.png"
        img_path = os.path.join(os.path.dirname(file_path), img_name)
        
        print(f"  Generating: {img_name}")
        try:
            md_table_to_png(table_text, img_path)
            return f"\n\n![table]({img_name})\n\n<!--\n{table_text}\n-->\n"
        except Exception as e:
            print(f"  Warning: {e}")
            return match.group(0)

    # Process updates first, then new tables
    content_with_updates = update_pattern.sub(update_existing, masked_content)
    final_updated_content = table_pattern.sub(replace_with_img, content_with_updates)

    # Unmask other comments
    def unmask_other_comment(m):
        idx = int(m.group(1))
        return other_comments[idx]
    final_content = re.sub(r'__OTHER_COMMENT_MASK_(\d+)__', unmask_other_comment, final_updated_content)

    if final_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print(f"  Updated: {file_path}")


def main():
    target = "articles"
    if len(sys.argv) > 1:
        target = sys.argv[1]
    
    if not os.path.exists(target):
        print(f"Error: {target} not found")
        sys.exit(1)

    if os.path.isfile(target):
        process_file(target)
    else:
        for root, dirs, files in os.walk(target):
            for file in files:
                if file.endswith(".md"):
                    process_file(os.path.join(root, file))
    print("Done.")

if __name__ == "__main__":
    main()
