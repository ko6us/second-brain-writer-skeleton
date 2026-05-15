import os
import sys
import re
import json
import hashlib
from urllib.request import Request, urlopen
from urllib.error import HTTPError

def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def gist_api_request(token, gist_id=None, method="POST", data=None):
    url = "https://api.github.com/gists"
    if gist_id:
        url = f"{url}/{gist_id}"
    
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json"
    }
    
    json_data = json.dumps(data).encode("utf-8")
    req = Request(url, data=json_data, headers=headers, method=method)
    
    try:
        with urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        print(f"API Error: {e.code} {e.reason}")
        print(e.read().decode("utf-8"))
        raise

def update_meta_json(meta_path, source_rel_path, gist_data):
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    else:
        # Create basic meta if not exists
        meta = {
            "article_title": os.path.basename(os.path.dirname(meta_path)),
            "article_folder": f"articles/{os.path.basename(os.path.dirname(meta_path))}",
            "note_url": "",
            "items": []
        }

    # Find existing item or create new
    found = False
    for item in meta.get("items", []):
        if item.get("source_file") == source_rel_path:
            item.update(gist_data)
            found = True
            break
    
    if not found:
        if "items" not in meta: meta["items"] = []
        new_item = {"source_file": source_rel_path}
        new_item.update(gist_data)
        meta["items"].append(new_item)
    
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=4, ensure_ascii=False)

def process_file(file_path, token):
    print(f"Processing: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern for tables
    table_pattern = re.compile(r'((?:^|\n)\|.*?\|[ \t]*\n\|[ \-\:\|]+\|[ \t]*\n(?:\|.*?\|[ \t]*(?:\n|$))+)', re.MULTILINE)
    
    # Pattern for table followed by a gist URL (our new format)
    # Group 1: Table, Group 2: Full URL, Group 3: Gist ID
    update_pattern = re.compile(r'((?:^|\n)\|.*?\|[ \t]*\n\|[ \-\:\|]+\|[ \t]*\n(?:\|.*?\|[ \t]*(?:\n|$))+)\n*(https://gist\.github\.com/.*?/([a-f0-9]+))', re.MULTILINE)

    def get_rel_path(p):
        # Convert absolute path to repo-relative path (articles/...) and normalize to forward slashes
        parts = p.replace("\\", "/").split("/articles/")
        if len(parts) > 1:
            return "articles/" + parts[1]
        return p.replace("\\", "/")

    def sync_table_to_gist(table_text, existing_gist_id=None):
        table_text = table_text.strip()
        table_hash = hashlib.md5(table_text.encode("utf-8")).hexdigest().upper()
        
        dir_name = os.path.dirname(file_path)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        meta_path = os.path.join(dir_name, "meta.json")

        # Check if hash matches to skip API call
        if existing_gist_id and os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                for item in meta.get("items", []):
                    if item.get("gist_id") == existing_gist_id:
                        if item.get("last_sync_hash") == table_hash:
                            print(f"  Table unchanged (ID: {existing_gist_id}), skipping sync.")
                            return item.get("gist_url"), table_text
        
        # Create separate table file
        table_filename = f"{base_name}_table_{table_hash[:8].lower()}.md"
        table_file_path = os.path.join(dir_name, table_filename)
        
        with open(table_file_path, "w", encoding="utf-8") as f:
            f.write(table_text)
        
        # Prepare Gist data
        gist_filename = f"{os.path.basename(dir_name)}__{table_filename}"
        gist_payload = {
            "description": f"note embed for {os.path.basename(dir_name)}",
            "public": True,
            "files": {
                gist_filename: {"content": table_text}
            }
        }
        
        # Sync
        print(f"  Syncing table to Gist...")
        res = gist_api_request(token, existing_gist_id, method="PATCH" if existing_gist_id else "POST", data=gist_payload)
        
        gist_id = res["id"]
        gist_url = res["html_url"]
        
        # Update meta.json
        update_meta_json(meta_path, get_rel_path(table_file_path), {
            "gist_filename": gist_filename,
            "gist_id": gist_id,
            "gist_url": gist_url,
            "last_sync_hash": table_hash
        })
        
        return gist_url, table_text

    # 1. Handle updates for existing gist-linked tables
    def update_existing(match):
        table_text = match.group(1).strip()
        gist_id = match.group(3)
        
        try:
            new_url, text = sync_table_to_gist(table_text, gist_id)
            return f"\n{text}\n\n{new_url}\n"
        except Exception as e:
            print(f"  Error updating gist {gist_id}: {e}")
            return match.group(0)

    # Pre-process: first handle tables that ALREADY have a URL line
    processed_content = update_pattern.sub(update_existing, content)

    # 2. Handle new tables (those without a URL line yet)
    final_content = processed_content
    
    new_tables = []
    for m in table_pattern.finditer(final_content):
        after = final_content[m.end():m.end()+100]
        if "https://gist.github.com" not in after:
            new_tables.append(m)
    
    # Replace from back to front
    for m in reversed(new_tables):
        table_text = m.group(1).strip()
        try:
            gist_url, text = sync_table_to_gist(table_text)
            replacement = f"\n{text}\n\n{gist_url}\n"
            final_content = final_content[:m.start()] + replacement + final_content[m.end():]
        except Exception as e:
            print(f"  Error creating gist: {e}")

    if final_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_content)
        print(f"  Updated: {file_path}")

def main():
    config = load_config()
    token = config.get("GistToken")
    if not token:
        print("Error: GistToken not found in config.json")
        sys.exit(1)

    target = "articles"
    if len(sys.argv) > 1:
        target = sys.argv[1]
    
    if os.path.isfile(target):
        process_file(target, token)
    else:
        for root, dirs, files in os.walk(target):
            for file in files:
                if file.endswith(".md"):
                    process_file(os.path.join(root, file), token)
    print("Done.")

if __name__ == "__main__":
    main()
