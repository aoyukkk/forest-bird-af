"""Start/stop a password-protected temporary HTTPS link to the local annotator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

CF_SHA256 = '76b2805253d0d6ffacb092a7acfbee99e7af6917835c0c5410e23f3ef5052da2'


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)


def matches(pid, needle):
    """Check saved PIDs before reusing/stopping a Windows process."""
    if type(pid) is not int or pid <= 0:
        return False
    if os.name != 'nt':
        return False
    command = f'(Get-CimInstance Win32_Process -Filter "ProcessId = {pid}").CommandLine'
    result = subprocess.run(['powershell', '-NoProfile', '-Command', command],
                            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    return result.returncode == 0 and needle.casefold() in result.stdout.casefold()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'status', 'stop'])
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--cloudflared', type=Path)
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--upstream-port', type=int, default=8765)
    args = parser.parse_args()
    root = args.workspace.resolve()
    private = root / 'remote-access'
    private.mkdir(exist_ok=True)
    state_file = private / 'processes.json'
    config = private / 'access.json'
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    active = {name: matches(state.get(name + '_pid'), str(config) if name == 'gateway'
                            else state.get('cloudflared', '<missing>')) for name in ['gateway', 'tunnel']}
    if args.action == 'status':
        print(json.dumps({'url': state.get('url'), 'running': all(active.values()),
                          'processes': active, 'credentials_file': str(private / 'SHARE.txt')}))
        return
    if args.action == 'stop':
        for name in ['tunnel', 'gateway']:
            if active[name]:
                os.kill(state[name + '_pid'], signal.SIGTERM)
        state['stopped'] = True
        write(state_file, state)
        print(json.dumps({'stopped': True, 'local_annotator_kept': True}))
        return
    if all(active.values()):
        print(json.dumps({'url': state['url'], 'running': True, 'reused': True,
                          'credentials_file': str(private / 'SHARE.txt')}))
        return
    if any(active.values()):
        raise SystemExit('Partial previous share is still running. Use stop before starting a new one.')
    with urlopen(f'http://127.0.0.1:{args.upstream_port}/api/health', timeout=5) as response:
        health = json.load(response)
    expected = hashlib.sha256(str(root).casefold().encode('utf-8')).hexdigest()[:16]
    if not health.get('ok') or health.get('workspace_id') != expected:
        raise SystemExit('Upstream service does not belong to this annotation workspace.')
    binary = args.cloudflared.resolve() if args.cloudflared else None
    if not binary or not binary.is_file() or hashlib.sha256(binary.read_bytes()).hexdigest() != CF_SHA256:
        raise SystemExit('Provide the verified official cloudflared 2026.10.3 Windows AMD64 executable.')
    password_file = private / 'password.secret'
    if password_file.exists():
        password = password_file.read_text(encoding='utf-8').strip()
    else:
        password = secrets.token_urlsafe(18)
        password_file.write_text(password, encoding='utf-8')
    write(config, {'password_sha256': hashlib.sha256(password.encode()).hexdigest(), 'public_hosts': []})
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    processes = []
    state = {'cloudflared': str(binary), 'upstream_port': args.upstream_port, 'gateway_port': args.port}
    try:
        with (private/'gateway.stdout.log').open('ab') as out, (private/'gateway.stderr.log').open('ab') as err:
            gateway = subprocess.Popen([sys.executable, str(Path(__file__).with_name('remote_annotator.py')),
                '--config', str(config), '--port', str(args.port), '--upstream-port', str(args.upstream_port)],
                stdin=subprocess.DEVNULL, stdout=out, stderr=err, creationflags=flags)
        processes.append(gateway)
        state['gateway_pid'] = gateway.pid
        write(state_file, state)
        for _ in range(40):
            if gateway.poll() is not None:
                raise RuntimeError('Gateway exited. Check its stderr log.')
            try:
                with urlopen(f'http://127.0.0.1:{args.port}/login', timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(.15)
        else:
            raise RuntimeError('Gateway did not become ready.')
        log = private / 'tunnel.log'
        with log.open('wb') as out:
            tunnel = subprocess.Popen([str(binary), 'tunnel', '--no-autoupdate', '--protocol', 'http2',
                '--url', f'http://127.0.0.1:{args.port}'], stdin=subprocess.DEVNULL,
                stdout=out, stderr=subprocess.STDOUT, creationflags=flags)
        processes.append(tunnel)
        state['tunnel_pid'] = tunnel.pid
        write(state_file, state)
        for _ in range(240):
            if tunnel.poll() is not None:
                raise RuntimeError('Tunnel exited. Check tunnel.log.')
            match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', log.read_text(encoding='utf-8', errors='replace'))
            if match:
                url = match.group(0)
                break
            time.sleep(.25)
        else:
            raise RuntimeError('No temporary URL was assigned. Check tunnel.log.')
        write(config, {'password_sha256': hashlib.sha256(password.encode()).hexdigest(),
                       'public_hosts': [urlsplit(url).netloc]})
        state.update(url=url, images=health['images'], workspace_id=expected, stopped=False)
        write(state_file, state)
        (private/'SHARE.txt').write_text(
            f'URL: {url}\nPassword: {password}\n\nTemporary link; keep this computer and its services running.\n'
            'Reviewers can view images and edit the shared review database.\n', encoding='utf-8')
        print(json.dumps({'url': url, 'images': health['images'], 'running': True,
                          'credentials_file': str(private/'SHARE.txt')}))
    except BaseException:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        state['stopped'] = True
        write(state_file, state)
        raise


if __name__ == '__main__':
    main()
