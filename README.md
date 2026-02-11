# Claude Conversation Explorer 🗨️

Browse your Claude conversation exports in a beautiful, privacy-first interface.

**🌐 [Live Demo](https://0x-auth.github.io/claude-explorer/)**

## Features

- 📁 **Drag & Drop** - Load your Claude JSON exports instantly
- 🔍 **Full Search** - Search through conversation titles and message content
- 🌙 **Dark Theme** - Easy on the eyes
- 🔒 **Privacy-First** - All data stays in your browser. Nothing uploaded anywhere.
- 📱 **Responsive** - Works on desktop and mobile

## Usage

### Online (GitHub Pages)

1. Go to https://0x-auth.github.io/claude-explorer/
2. Drag & drop your Claude `conversations *.json` files
3. Browse your conversations!

### Local (Python Server)

For faster loading of large files:

```bash
git clone https://github.com/0x-auth/claude-explorer.git
cd claude-explorer

# Edit DATA_DIR in server.py to point to your JSON files
python3 server.py

# Open http://localhost:8888
```

## Getting Your Claude Data

1. Go to [claude.ai](https://claude.ai)
2. Settings → Account → Export Data
3. You'll receive JSON files with your conversations

## Privacy

Your conversation data **never leaves your browser**. This is a pure client-side application - there's no server, no database, no tracking. Your data is yours.

## License

MIT

---

Built with φ-coherence by [Space (Abhishek)](https://github.com/0x-auth)
