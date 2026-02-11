import xbmc
import xbmcaddon
import xbmcvfs
import socket
import os

POLL_INTERVAL = 5

monitor = xbmc.Monitor()
addon = xbmcaddon.Addon()

log_path = xbmcvfs.translatePath("special://logpath/kodi.log")
last_pos = 0

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
last_target = None

xbmc.log("[Syslog] Service started", xbmc.LOGINFO)

try:
    while not monitor.abortRequested():
        enabled = addon.getSettingBool("enabled")

        if not enabled:
            monitor.waitForAbort(POLL_INTERVAL)
            continue

        syslog_host = addon.getSetting("syslog_host")
        syslog_port = addon.getSettingInt("syslog_port")
        tag_text = addon.getSetting("tag")
        target = (syslog_host, syslog_port)

        # Recreate socket if the ip address/port changes
        if target != last_target:
            sock.close()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            last_target = target

        if xbmcvfs.exists(log_path):
            try:
                size = os.path.getsize(log_path)

                # New lines
                if size < last_pos:
                    last_pos = 0

                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    f.seek(last_pos)
                    lines = f.readlines()
                    last_pos = f.tell()

                for line in lines:
                    msg = f'{tag_text}{line.strip()}'
                    sock.sendto(msg.encode('utf-8'), target)

            except Exception as e:
                xbmc.log(f'[Syslog] Error: {e}', xbmc.LOGERROR)

        monitor.waitForAbort(POLL_INTERVAL)

finally:
    sock.close()
    xbmc.log('[Syslog] Service stopped', xbmc.LOGINFO)
