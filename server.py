#!/usr/bin/env python3
"""
Claude Conversation Explorer - Server
Serves Claude conversation data as a browsable web interface.
"""

import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import urllib.parse

# Configuration
DATA_DIR = Path("/Users/abhissrivasta/Downloads/279-Abhishek-bitsabhi-claude-account")
PORT = 8888

# Cache loaded conversations
conversations_cache = {}

def load_conversations():
    """Load all conversation files."""
    global conversations_cache

    if conversations_cache:
        return conversations_cache

    all_conversations = []

    for i in range(1, 5):
        filepath = DATA_DIR / f"conversations {i}.json"
        if filepath.exists():
            print(f"Loading {filepath.name}...")
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Try to parse, handle potential issues
                    try:
                        data = json.loads(content)
                        if isinstance(data, list):
                            all_conversations.extend(data)
                        else:
                            all_conversations.append(data)
                        print(f"  ✓ Loaded {len(data) if isinstance(data, list) else 1} conversations")
                    except json.JSONDecodeError as e:
                        print(f"  ⚠ JSON error in {filepath.name}: {e}")
                        # Try to salvage what we can
                        try:
                            # Sometimes the JSON is cut off - try to find valid objects
                            content = content.strip()
                            if content.startswith('['):
                                # Try removing last incomplete item
                                last_complete = content.rfind('},')
                                if last_complete > 0:
                                    fixed = content[:last_complete+1] + ']'
                                    data = json.loads(fixed)
                                    all_conversations.extend(data)
                                    print(f"  ✓ Recovered {len(data)} conversations")
                        except:
                            print(f"  ✗ Could not recover {filepath.name}")
            except Exception as e:
                print(f"  ✗ Error loading {filepath.name}: {e}")

    # Build index by UUID
    for conv in all_conversations:
        if 'uuid' in conv:
            conversations_cache[conv['uuid']] = conv

    print(f"\nTotal: {len(conversations_cache)} conversations loaded")
    return conversations_cache


def get_conversation_list():
    """Get list of all conversations with metadata."""
    convs = load_conversations()

    result = []
    for uuid, conv in convs.items():
        result.append({
            'uuid': uuid,
            'name': conv.get('name', 'Untitled'),
            'summary': conv.get('summary', ''),
            'created_at': conv.get('created_at', ''),
            'updated_at': conv.get('updated_at', ''),
            'message_count': len(conv.get('chat_messages', []))
        })

    # Sort by created_at descending (newest first)
    result.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return result


def get_conversation(uuid):
    """Get a single conversation by UUID."""
    convs = load_conversations()
    return convs.get(uuid)


def format_message_content(msg):
    """Format message content for display."""
    content_parts = []

    # Get text content
    if 'text' in msg and msg['text']:
        content_parts.append(msg['text'])

    # Get structured content
    if 'content' in msg and msg['content']:
        for item in msg['content']:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    content_parts.append(item.get('text', ''))
                elif item.get('type') == 'tool_use':
                    tool_name = item.get('name', 'unknown')
                    content_parts.append(f"\n[Tool: {tool_name}]\n")
                elif item.get('type') == 'tool_result':
                    content_parts.append(f"\n[Tool Result]\n{item.get('content', '')}")
            elif isinstance(item, str):
                content_parts.append(item)

    return '\n'.join(content_parts)


class ConversationHandler(SimpleHTTPRequestHandler):
    """HTTP handler for conversation explorer."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == '/':
            self.serve_index()
        elif path == '/api/conversations':
            self.serve_conversation_list()
        elif path == '/api/conversation':
            uuid = query.get('id', [None])[0]
            if uuid:
                self.serve_conversation(uuid)
            else:
                self.send_error(400, 'Missing conversation ID')
        elif path == '/api/search':
            q = query.get('q', [''])[0]
            self.serve_search(q)
        else:
            # Serve static files
            super().do_GET()

    def serve_index(self):
        """Serve the main HTML page."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        html = self.get_html_template()
        self.wfile.write(html.encode('utf-8'))

    def serve_conversation_list(self):
        """Serve list of conversations as JSON."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        convs = get_conversation_list()
        self.wfile.write(json.dumps(convs).encode('utf-8'))

    def serve_conversation(self, uuid):
        """Serve a single conversation."""
        conv = get_conversation(uuid)

        if not conv:
            self.send_error(404, 'Conversation not found')
            return

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        # Format messages for display
        messages = []
        for msg in conv.get('chat_messages', []):
            messages.append({
                'uuid': msg.get('uuid', ''),
                'sender': msg.get('sender', 'unknown'),
                'created_at': msg.get('created_at', ''),
                'content': format_message_content(msg),
                'attachments': msg.get('attachments', []),
                'files': msg.get('files', [])
            })

        result = {
            'uuid': conv.get('uuid', ''),
            'name': conv.get('name', 'Untitled'),
            'summary': conv.get('summary', ''),
            'created_at': conv.get('created_at', ''),
            'updated_at': conv.get('updated_at', ''),
            'messages': messages
        }

        self.wfile.write(json.dumps(result).encode('utf-8'))

    def serve_search(self, query):
        """Search conversations."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        if not query:
            self.wfile.write(json.dumps([]).encode('utf-8'))
            return

        query_lower = query.lower()
        results = []
        convs = load_conversations()

        for uuid, conv in convs.items():
            # Search in name and summary
            name = conv.get('name', '').lower()
            summary = conv.get('summary', '').lower()

            if query_lower in name or query_lower in summary:
                results.append({
                    'uuid': uuid,
                    'name': conv.get('name', 'Untitled'),
                    'summary': conv.get('summary', ''),
                    'created_at': conv.get('created_at', ''),
                    'match_type': 'title/summary'
                })
                continue

            # Search in messages
            for msg in conv.get('chat_messages', []):
                text = msg.get('text', '').lower()
                if query_lower in text:
                    results.append({
                        'uuid': uuid,
                        'name': conv.get('name', 'Untitled'),
                        'summary': conv.get('summary', ''),
                        'created_at': conv.get('created_at', ''),
                        'match_type': 'message'
                    })
                    break

        # Sort by date
        results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        self.wfile.write(json.dumps(results[:100]).encode('utf-8'))  # Limit to 100 results

    def get_html_template(self):
        """Return the main HTML template."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Conversation Explorer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            height: 100vh;
            display: flex;
        }

        /* Sidebar */
        .sidebar {
            width: 350px;
            background: #16213e;
            border-right: 1px solid #0f3460;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }

        .sidebar-header {
            padding: 20px;
            border-bottom: 1px solid #0f3460;
        }

        .sidebar-header h1 {
            font-size: 1.4em;
            color: #e94560;
            margin-bottom: 15px;
        }

        .search-box {
            width: 100%;
            padding: 10px 15px;
            border: 1px solid #0f3460;
            border-radius: 8px;
            background: #1a1a2e;
            color: #eee;
            font-size: 14px;
        }

        .search-box:focus {
            outline: none;
            border-color: #e94560;
        }

        .stats {
            padding: 10px 20px;
            background: #0f3460;
            font-size: 12px;
            color: #888;
        }

        .conversation-list {
            flex: 1;
            overflow-y: auto;
        }

        .conversation-item {
            padding: 15px 20px;
            border-bottom: 1px solid #0f3460;
            cursor: pointer;
            transition: background 0.2s;
        }

        .conversation-item:hover {
            background: #1a1a2e;
        }

        .conversation-item.active {
            background: #0f3460;
            border-left: 3px solid #e94560;
        }

        .conversation-item h3 {
            font-size: 14px;
            margin-bottom: 5px;
            color: #fff;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .conversation-item .meta {
            font-size: 11px;
            color: #666;
        }

        .conversation-item .summary {
            font-size: 12px;
            color: #888;
            margin-top: 5px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        /* Main content */
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }

        .conversation-header {
            padding: 20px;
            background: #16213e;
            border-bottom: 1px solid #0f3460;
        }

        .conversation-header h2 {
            font-size: 1.3em;
            color: #fff;
            margin-bottom: 5px;
        }

        .conversation-header .meta {
            font-size: 12px;
            color: #666;
        }

        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }

        .message {
            margin-bottom: 20px;
            max-width: 85%;
        }

        .message.human {
            margin-left: auto;
        }

        .message.assistant {
            margin-right: auto;
        }

        .message-bubble {
            padding: 15px 20px;
            border-radius: 15px;
            line-height: 1.6;
        }

        .message.human .message-bubble {
            background: #0f3460;
            border-bottom-right-radius: 5px;
        }

        .message.assistant .message-bubble {
            background: #1a1a2e;
            border: 1px solid #0f3460;
            border-bottom-left-radius: 5px;
        }

        .message-sender {
            font-size: 11px;
            color: #e94560;
            margin-bottom: 5px;
            text-transform: uppercase;
            font-weight: 600;
        }

        .message-time {
            font-size: 10px;
            color: #555;
            margin-top: 8px;
        }

        .message-content {
            white-space: pre-wrap;
            word-wrap: break-word;
            font-size: 14px;
        }

        .message-content code {
            background: #0a0a15;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 13px;
        }

        .message-content pre {
            background: #0a0a15;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 10px 0;
        }

        .message-content pre code {
            background: none;
            padding: 0;
        }

        /* Empty state */
        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #555;
        }

        .empty-state h2 {
            font-size: 1.5em;
            margin-bottom: 10px;
        }

        .empty-state p {
            font-size: 14px;
        }

        /* Loading */
        .loading {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #666;
        }

        .loading::after {
            content: '';
            width: 30px;
            height: 30px;
            border: 3px solid #0f3460;
            border-top-color: #e94560;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 10px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: #1a1a2e;
        }

        ::-webkit-scrollbar-thumb {
            background: #0f3460;
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #e94560;
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h1>🗨️ Claude Explorer</h1>
            <input type="text" class="search-box" id="search" placeholder="Search conversations...">
        </div>
        <div class="stats" id="stats">Loading conversations...</div>
        <div class="conversation-list" id="conversation-list">
            <div class="loading">Loading</div>
        </div>
    </div>

    <div class="main">
        <div class="conversation-header" id="conv-header" style="display: none;">
            <h2 id="conv-title">Select a conversation</h2>
            <div class="meta" id="conv-meta"></div>
        </div>
        <div class="messages" id="messages">
            <div class="empty-state">
                <h2>Welcome!</h2>
                <p>Select a conversation from the sidebar to view it.</p>
            </div>
        </div>
    </div>

    <script>
        let conversations = [];
        let currentConvId = null;

        // Format date
        function formatDate(dateStr) {
            if (!dateStr) return '';
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        }

        // Load conversation list
        async function loadConversations() {
            try {
                const res = await fetch('/api/conversations');
                conversations = await res.json();
                renderConversationList(conversations);
                document.getElementById('stats').textContent =
                    `${conversations.length} conversations`;
            } catch (err) {
                document.getElementById('conversation-list').innerHTML =
                    '<div class="loading">Error loading conversations</div>';
            }
        }

        // Render conversation list
        function renderConversationList(convs) {
            const list = document.getElementById('conversation-list');

            if (convs.length === 0) {
                list.innerHTML = '<div class="loading">No conversations found</div>';
                return;
            }

            list.innerHTML = convs.map(conv => `
                <div class="conversation-item ${conv.uuid === currentConvId ? 'active' : ''}"
                     onclick="loadConversation('${conv.uuid}')">
                    <h3>${escapeHtml(conv.name || 'Untitled')}</h3>
                    <div class="meta">${formatDate(conv.created_at)} • ${conv.message_count} messages</div>
                    ${conv.summary ? `<div class="summary">${escapeHtml(conv.summary)}</div>` : ''}
                </div>
            `).join('');
        }

        // Load single conversation
        async function loadConversation(uuid) {
            currentConvId = uuid;

            // Update sidebar
            document.querySelectorAll('.conversation-item').forEach(el => {
                el.classList.remove('active');
            });
            event.currentTarget?.classList.add('active');

            // Show loading
            document.getElementById('messages').innerHTML = '<div class="loading">Loading</div>';
            document.getElementById('conv-header').style.display = 'block';

            try {
                const res = await fetch(`/api/conversation?id=${uuid}`);
                const conv = await res.json();

                // Update header
                document.getElementById('conv-title').textContent = conv.name || 'Untitled';
                document.getElementById('conv-meta').textContent =
                    `Created: ${formatDate(conv.created_at)} • ${conv.messages.length} messages`;

                // Render messages
                const messagesEl = document.getElementById('messages');
                messagesEl.innerHTML = conv.messages.map(msg => `
                    <div class="message ${msg.sender}">
                        <div class="message-bubble">
                            <div class="message-sender">${msg.sender}</div>
                            <div class="message-content">${escapeHtml(msg.content)}</div>
                            <div class="message-time">${formatDate(msg.created_at)}</div>
                        </div>
                    </div>
                `).join('');

                // Scroll to top
                messagesEl.scrollTop = 0;

            } catch (err) {
                document.getElementById('messages').innerHTML =
                    '<div class="loading">Error loading conversation</div>';
            }
        }

        // Search
        let searchTimeout;
        document.getElementById('search').addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            const query = e.target.value.trim();

            searchTimeout = setTimeout(async () => {
                if (query.length === 0) {
                    renderConversationList(conversations);
                    return;
                }

                if (query.length < 2) return;

                // Local filter first (for speed)
                const localResults = conversations.filter(conv =>
                    (conv.name || '').toLowerCase().includes(query.toLowerCase()) ||
                    (conv.summary || '').toLowerCase().includes(query.toLowerCase())
                );

                renderConversationList(localResults);

                // Then server search for message content
                try {
                    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                    const results = await res.json();
                    renderConversationList(results);
                } catch (err) {
                    console.error('Search error:', err);
                }
            }, 300);
        });

        // Escape HTML
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Initial load
        loadConversations();
    </script>
</body>
</html>
'''


def main():
    """Run the server."""
    print(f"\n{'='*60}")
    print("  Claude Conversation Explorer")
    print(f"{'='*60}\n")

    # Pre-load conversations
    load_conversations()

    print(f"\n🚀 Starting server at http://localhost:{PORT}")
    print(f"   Press Ctrl+C to stop\n")

    os.chdir(Path(__file__).parent)
    server = HTTPServer(('localhost', PORT), ConversationHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
        server.shutdown()


if __name__ == '__main__':
    main()
