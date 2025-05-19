# Outlook Web Application To Nextcloud Caldav Sync

This simple tool helps you syncronize anonimized calendar entries from an Exchagen OWA to your privat or work nextcloud while also anonymizing the entries. 

## Installation

TODO: .env File

### Python venv
```bash
git clone git@github.com:pheeef/owa2nc-sync.git
cd owa2nc-sync
python3 -m venv venv
source venv/bin/activate
```

### systemd-user Service

Example unit files and timer

#### Service
```systemd
[Unit]
Description=Systemd Service to Sync Calendar Entries to my private calendar
After=xdg-desktop-autostart.target

[Service]
ExecStart=path../to../repo../owa2nc-sync/venv/bin/python3 path../to../repo../repos/owa2nc-sync/sync.py
WorkingDirectory=path../to../repo../repos/owa2nc-sync
# Fill in proxy settings if needewd
# Environment=https_proxy=<ProxyIP>
# Environment=http_proxy=<ProxyIP>

[Install]
WantedBy=default.target

```
#### Timer
```systemd
[Unit]
Description=Systemd Timer to Sync Calendar Entries to my private calendar
After=xdg-desktop-autostart.target

[Timer]
OnCalendar=Mon-Fri *-*-* *:00:00
Unit=owa2nc-sync.service

[Install]
WantedBy=default.target
```

## Contributers

Special thx to everyone who helped build this:
- @Hedius
- @bzed
- @weaselp
