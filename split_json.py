#!/usr/bin/env python3
"""
Split large JSON conversation files into smaller chunks for GitHub.
Each chunk will be under 50MB.
"""

import json
import os
from pathlib import Path

SOURCE_DIR = Path("/Users/abhissrivasta/Downloads/279-Abhishek-bitsabhi-claude-account")
OUTPUT_DIR = Path("/Users/abhissrivasta/github-repos-bitsabhi/claude-explorer/data")

MAX_CHUNK_SIZE = 45 * 1024 * 1024  # 45MB to be safe

def split_conversations():
    OUTPUT_DIR.mkdir(exist_ok=True)

    all_conversations = []

    # Load all conversation files
    for i in range(1, 5):
        filepath = SOURCE_DIR / f"conversations {i}.json"
        if filepath.exists():
            print(f"Loading {filepath.name}...")
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    try:
                        data = json.loads(content)
                        if isinstance(data, list):
                            all_conversations.extend(data)
                            print(f"  ✓ {len(data)} conversations")
                        else:
                            all_conversations.append(data)
                            print(f"  ✓ 1 conversation")
                    except json.JSONDecodeError as e:
                        print(f"  ⚠ JSON error, attempting recovery...")
                        # Try to recover truncated JSON
                        last_complete = content.rfind('},')
                        if last_complete > 0 and content.strip().startswith('['):
                            fixed = content[:last_complete+1] + ']'
                            data = json.loads(fixed)
                            all_conversations.extend(data)
                            print(f"  ✓ Recovered {len(data)} conversations")
            except Exception as e:
                print(f"  ✗ Error: {e}")

    print(f"\nTotal: {len(all_conversations)} conversations")

    # Sort by date
    all_conversations.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    # Split into chunks
    chunks = []
    current_chunk = []
    current_size = 0

    for conv in all_conversations:
        conv_json = json.dumps(conv)
        conv_size = len(conv_json.encode('utf-8'))

        if current_size + conv_size > MAX_CHUNK_SIZE and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_size = 0

        current_chunk.append(conv)
        current_size += conv_size

    if current_chunk:
        chunks.append(current_chunk)

    print(f"Split into {len(chunks)} chunks")

    # Write chunks
    manifest = {
        'total_conversations': len(all_conversations),
        'chunks': []
    }

    for i, chunk in enumerate(chunks):
        filename = f"conversations_{i+1:02d}.json"
        filepath = OUTPUT_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chunk, f, separators=(',', ':'))  # Compact JSON

        size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"  {filename}: {len(chunk)} conversations, {size_mb:.1f}MB")

        manifest['chunks'].append({
            'file': filename,
            'count': len(chunk),
            'size_mb': round(size_mb, 1)
        })

    # Write manifest
    manifest_path = OUTPUT_DIR / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)

    print(f"\n✓ Manifest written to {manifest_path}")
    print(f"✓ Total size: {sum(c['size_mb'] for c in manifest['chunks']):.1f}MB")

if __name__ == '__main__':
    split_conversations()
