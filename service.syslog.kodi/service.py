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

sock = None
last_target = None
last_protocol = None

xbmc.log("[Syslog] Service started", xbmc.LOGINFO)

def create_socket(log_protocol:int, log_target:tuple[str,int]):
    if log_protocol == 0:
        xbmc.log("[Syslog] TCP Protocol", xbmc.LOGINFO)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(log_target)
        return s

    elif log_protocol == 1:
        xbmc.log("[Syslog] UDP Protocol", xbmc.LOGINFO)
        return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    else:
        xbmc.log("[Syslog] Invalid Protocol Selected, defaulting to UDP", xbmc.LOGERROR)
        return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    while not monitor.abortRequested():
        enabled = addon.getSettingBool("enabled")

        if not enabled:
            monitor.waitForAbort(POLL_INTERVAL)
            continue

        syslog_host = addon.getSetting("syslog_host")
        syslog_port = addon.getSettingInt("syslog_port")
        tag_text = addon.getSetting("tag")
        # 0 for TCP, 1 for UDP
        protocol = int(addon.getSetting("protocol"))

        target = (syslog_host, syslog_port)

    # Recreate socket if target or protocol changes
        try:
            if (
                    sock is None
                    or target != last_target
                    or protocol != last_protocol
            ):
                if sock is not None:
                    sock.close()

                sock = create_socket(log_protocol=protocol, log_target=target)

                last_target = target
                last_protocol = protocol

            if xbmcvfs.exists(log_path):
                size = os.path.getsize(log_path)

                if size < last_pos:
                    last_pos = 0

                with open(
                        log_path,
                        "r",
                        encoding="utf-8",
                        errors="ignore"
                ) as f:
                    f.seek(last_pos)
                    lines = f.readlines()
                    last_pos = f.tell()

                for line in lines:
                    msg = f"{tag_text}{line}"

                    if protocol == 0:
                        data = msg.encode("utf-8")

                        # Ensure a delimiter exists for TCP
                        # Keep the original line exactly if it already ends with '\n'.
                        if not msg.endswith("\n"):
                            data += b"\n"

                        sock.sendall(data)
                    else:
                        sock.sendto(msg.encode("utf-8"), target)

        except Exception as e:
            xbmc.log(f"[Syslog] Error: {e}", xbmc.LOGERROR)

            # Force a reconnect on the next pass
            if sock:
                try:
                    sock.close()
                except Exception as e:
                    xbmc.log(f"[Syslog] Error: {e}", xbmc.LOGERROR)

            sock = None
            last_target = None
            last_protocol = None

        monitor.waitForAbort(POLL_INTERVAL)

finally:
    if sock:
        try:
            sock.close()
        except Exception as e:
            xbmc.log(f"[Syslog] Error: {e}", xbmc.LOGERROR)

    xbmc.log("[Syslog] Service stopped", xbmc.LOGINFO)
