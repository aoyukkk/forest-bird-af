# Temporary remote review access

**English** | [简体中文](remote-review.zh-CN.md)

The annotation service and SQLite database run on the owner's computer. A password-protected gateway exposes only Z8 review pages, images and review APIs through a Cloudflare Quick Tunnel. No custom domain or server deployment is needed.

## Start and share

Start the local annotator first, then use Python 3.11+:

```powershell
python scripts/share_annotator.py start --workspace <annotation-workspace> --cloudflared <verified-cloudflared.exe>
python scripts/share_annotator.py status --workspace <annotation-workspace>
```

The launcher verifies cloudflared 2026.10.3 for Windows AMD64 against its official release SHA-256. It starts hidden background processes, waits for the gateway and records the assigned HTTPS URL. Repeated starts reuse an active share. The owner receives the URL and password in `<annotation-workspace>/remote-access/SHARE.txt`; do not commit that directory or share the password file publicly.

Send collaborators the URL and password. After login, they should set their own reviewer ID in Help. Everyone edits the same dataset; revision checks reject stale changes. Opening an image or autosaving a draft does not confirm it. The remote gateway excludes the historical `/annotate` editor and bulk-import APIs. **Sign out** ends the current browser session after saving its draft.

## Stop and restart

```powershell
python scripts/share_annotator.py stop --workspace <annotation-workspace>
```

This stops only the matching gateway and tunnel processes, leaving the local annotator available. Stop/restart clears login sessions. The assigned hostname changes when a new tunnel is created. Keep the computer awake and connected while collaborators use the link. Closing a browser tab does not stop sharing.

Files in `remote-access/` hold the access configuration, password, process IDs and tunnel logs. The launcher checks saved process command lines before stopping them. Model files, firmware, private source paths and arbitrary filesystem routes are not exposed by the gateway. The server continues to verify image hashes on reads.

Reference: [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).
