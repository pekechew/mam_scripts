#!/usr/bin/env python3
"""qbit-mam-deleted
version 1.08

Scan qBittorrent and tag (optionally stop / delete) torrents that have been deleted from MAM.
Check for tracker errors of "torrent not registered with this tracker"
Filter by category to avoid removing fresh uploads

Dependencies
------------
    pip install qbittorrent-api requests

Automation (cron)
------------
    crontab -e
    # Run at 6:00 am everyday.
    0 6 * * * /usr/bin/python3 /opt/MAM/qbit-mam-deleted.py >> /var/log/qbit-mam-deleted.log 2>&1

"""

# ── CONFIGURATION - EDIT THIS ────────────────────────────────────────────────

# Many of thsee can be set / overridden at the command line level.  See --help

# When using https with a reverse proxy use port 443
# otherwise use the port specified in qbittorrent (https is disabled in qbittorrent by default)
# use --no-verify if connecting to an unsigned https webui
DEFAULT_HOST        = "http://192.168.1.100" 
DEFAULT_PORT        = 8090
DEFAULT_USERNAME    = "admin"
DEFAULT_PASSWORD    = "admin"

# FILTERS - Category, Tag and Status.  Use None for no filtering.
DEFAULT_CATEGORY    = "archive"
DEFAULT_FILTER_TAG  = None
DEFAULT_STATUSES    =  "Stalled,Downloading,Seeding"

# Tag to apply to torrents deleted from MAM
DEFAULT_TAG         = "deleted"

# ntfy push settings
NTFY_SERVER = "https://ntfy.sh"
NTFY_TOPIC  = "qbittorrent"
# Maximum chars to show per torrent in the push notification
NAME_TRUNC = 45

# ── DO NOT EDIT BEYOND THIS POINT ────────────────────────────────────────────

# ── Imports ──────────────────────────────────────────────────────────────────
import argparse
import logging
import sys
from typing import List, Optional

import qbittorrentapi
import requests

# ── Logging setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ── Help Formatter ───────────────────────────────────────────────────────────
class CustomFormatter(argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter):
    def __init__(self, prog):
        # Increase max_help_position for wider option columns
        super().__init__(prog, max_help_position=35, width=100)

EXAMPLES = """
Examples:
  - Tag torrents deleted from MAM using the tag "deleted"
    - creates the tag in qBittorrent if it doesn't exist
    - Uses all other defaults specified in the script
    - Sends a ntfy notification if any are tagged
    - Doesn't delete anything
    python3 qbit-mam-deleted.py
     - or
    ./qbit-mam-deleted.py

  - Tag and delete torrent AND files from qBittorrent / the hard drive
    - use --delete to only delete the torrent and keep the data
    ./qbit-mam-deleted.py --delete-data

  - Find all torrents with:
    - a status of Stalled or Seeding,
    - a category of 'archive'
    - a tag of 'mam'
    - then add the tag 'deleted' to it, creating the tag if it doesn't exist
    ./qbit-mam-deleted.py --status Stalled,Seeding --category archive --filter-tag mam --tag deleted

  - Test only the ntfy function to verify configuration
    ./qbit-mam-deleted.py --test-ntfy

  - Don't send a ntfy notification
    ./qbit-mam-deleted.py --no-ntfy
"""

# ── ntfy ─────────────────────────────────────────────────────────────────────
def notify_ntfy(deleted_names: List[str], ntfy_enabled: bool, do_stop: bool, do_delete: bool, do_delete_data: bool) -> None:
    """Send an ntfy notification: title only mentions count; body lists names."""
    if not ntfy_enabled or not deleted_names:
            return

    # Pluralize "Torrent"
    count = len(deleted_names)
    noun_suff = "" if count == 1 else "s"

    # Determine action wording based on flags
    actions = ["tagged"]
    if do_stop:
        actions.append("stopped")
    if do_delete:
        actions.append(f"deleted")
    if do_delete_data:
        actions.append("deleted +data")
    
    if len(actions) > 1:
        action_str = ", ".join(actions[:-1]) + " and " + actions[-1]
    else:
        action_str = actions[0]

    title = "MAM Deleted Torrents Detected"

    # Body: header then one truncated name per line
    lines = [f"{count} Torrent{noun_suff} {action_str} in qBit"]
    for name in deleted_names:
        short = name if len(name) <= NAME_TRUNC else name[:NAME_TRUNC-3] + "..."
        lines.append(f"• {short}")
    body = "\n".join(lines)

    url = f"{NTFY_SERVER.rstrip('/')}/{NTFY_TOPIC}"
    headers = {
        "Title": title,
        "Priority": "default",
    }

    try:
        resp = requests.post(url, data=body.encode('utf-8'), headers=headers, timeout=10)
        if resp.ok:
            logging.info("ntfy notification sent: %s", title)
        else:
            logging.error("ntfy failed (%d): %s", resp.status_code, resp.text)
    except Exception:
        logging.exception("Error sending ntfy notification")


# ── qBittorrent tagging ──────────────────────────────────────────────────────
def tag_deleted(
    host: str,
    port: int,
    username: str,
    password: str,
    category: Optional[str],
    status_filter: str,
    filter_tag: Optional[str],
    deleted_tag: str,
    verify_cert: bool,
    ntfy_enabled: bool,
    do_stop: bool = False,
    do_delete: bool = False,
    do_delete_data: bool = False,
):
    # Connect to qBittorrent WebUI and flag torrents removed from tracker.
    client_kwargs = dict(
        host=host,
        port=port,
        username=username,
        password=password,
    )
    
    # Allow unsigned SSL connection based on --no-verify
    if not verify_cert:
        client_kwargs["VERIFY_WEBUI_CERTIFICATE"] = False

    try:
        client = qbittorrentapi.Client(**client_kwargs)
    except TypeError as exc:
        logging.error("Failed to initialize qbittorrent Client: %s", exc)
        sys.exit(1)
    
    # Login
    try:
        client.auth_log_in()
    except (qbittorrentapi.LoginFailed, requests.exceptions.ConnectionError, qbittorrentapi.exceptions.APIConnectionError) as exc:
        logging.error("Failed to connect or login to qBittorrent at %s:%d: %s", host, port, exc)
        sys.exit(1)

    logging.info("Connected to %s:%d as %r (verifySSL=%s)", host, port, username, verify_cert)

    # create tag for tagging deleted torrents if it doesn't exist
    try:
        existing = client.torrent_tags.tags
        logging.debug("Existing tags: %s", existing)
    except Exception:
        existing = []
    if deleted_tag not in existing:
        try:
            client.torrents_create_tags(tags=deleted_tag)
            logging.info("Created missing tag %r", deleted_tag)
        except Exception as e:
            logging.error("Failed to create missing tag %r: %s", deleted_tag, e)
            sys.exit(1)

    # Error and exit if specified category filter does not exist
    if category:
        try:
            cats_all = client.torrent_categories.categories
            cats = list(cats_all.keys())
            logging.debug("Existing categories: %s", cats)
        except Exception:
            cats = []
        if category not in cats:
            logging.error(
                "Category %r does not exist on the server. "
                "Please specify an existing category or 'None' to disable category filtering.", 
                category
            )
            sys.exit(1)

    # Error and exit if specified tag filter does not exist
    if filter_tag:
        if filter_tag not in existing:
            logging.error(
                "Filter tag %r does not exist on the server. "
                "Please specify an existing tag or 'None' to disable tag filtering.",
                filter_tag
            )
            sys.exit(1)

    # Fetch torrents
    torrents = client.torrents_info(
        status_filter=status_filter,
        private=True,
        category=category,
    )
    logging.info(
        "Scanning %d torrents with statuses [%s]%s",
        len(torrents), status_filter,
        f" in category {category!r}" if category else ""
    )

    deleted_names: List[str] = []
    skipped_tagged = 0
    for torrent in torrents:
        tags = [t.strip() for t in (torrent.tags or "").split(",") if t]

        # Skip if not matching filter tag
        if filter_tag and filter_tag not in tags:
            continue
        # Skip already tagged as deleted
        if deleted_tag in tags:
            skipped_tagged += 1
            continue
        
        # Check for MAM tracker removal message
        if any(
            "torrent not registered with this tracker" in tr.msg.lower()
            for tr in torrent.trackers
        ):
            client.torrents_add_tags(
                tags=deleted_tag, torrent_hashes=torrent.hash
            )
            if do_stop:
                client.torrents_pause(torrent_hashes=torrent.hash)
            if do_delete:
                client.torrents_delete(torrent_hashes=torrent.hash, delete_files=False)
            if do_delete_data:
                client.torrents_delete(torrent_hashes=torrent.hash, delete_files=True)
            deleted_names.append(torrent.name)
            logging.debug("Flagged: %s", torrent.name)

    logging.info("Skipped %d torrents already tagged", skipped_tagged)
    
    logging.info(
        "Tagged %d torrents%s%s%s", len(deleted_names),
        ", stopped" if do_stop else "",
        ", deleted" if do_delete else "",
        ", deleted + data" if do_delete_data else "",
    )
    
    # Send notification
    notify_ntfy(deleted_names, ntfy_enabled, do_stop, do_delete, do_delete_data)

# ── CLI ──────────────────────────────────────────────────────────────────────
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Tag (and optionally stop/delete) qBittorrent torrents when they are deleted from MAM",
        formatter_class=CustomFormatter,
        epilog=EXAMPLES,
    )

    p.add_argument("--host",        default=DEFAULT_HOST,           help="WebUI host/IP (http or https URL allowed)")
    p.add_argument("--port",        type=int, default=DEFAULT_PORT, help="WebUI port")
    p.add_argument("--username",    default=DEFAULT_USERNAME,       help="WebUI username")
    p.add_argument("--password",    default=DEFAULT_PASSWORD,       help="WebUI password")

    p.add_argument("--category",    default=DEFAULT_CATEGORY,       help="Only scan this category (None = all)")
    p.add_argument("--filter-tag",  default=DEFAULT_FILTER_TAG,     help="Only process torrents that already have this tag")
    p.add_argument("--status",      default=DEFAULT_STATUSES,       help="Comma-separated torrent statuses to include")
    
    p.add_argument("--tag",         default=DEFAULT_TAG,            help="Name of the tag to apply to orphaned torrents")
    
    p.add_argument("--stop",        action="store_true",            help="Stop torrents that are flagged as deleted")
    p.add_argument("--delete",      action="store_true",            help="Delete torrent NOT data (implies --stop)")
    p.add_argument("--delete-data", action="store_true",            help="Delete torrent AND data (implies --stop)")
    p.add_argument("--no-verify",   action="store_true",            help="Disable SSL certificate verification for HTTPS WebUI")
    p.add_argument("--no-ntfy",     action="store_true",            help="Disable ntfy push notifications")
    p.add_argument("--verbose",     action="store_true",            help="Enable DEBUG logging")
    p.add_argument("--test-ntfy",   action="store_true",            help="Send a test ntfy notification and exit")
    return p

def main() -> None:
    args = build_arg_parser().parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.test_ntfy:
        notify_ntfy(["qbit‑mam‑deleted test message", "This is only a drill", "Nothing was actually tagged"], True, False, False, False)
        return

    tag_deleted(
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        category=(None if args.category and args.category.lower() == "none" else args.category),
        status_filter=args.status,
        filter_tag=(None if args.filter_tag and args.filter_tag.lower() == "none" else args.filter_tag),
        deleted_tag=args.tag,
        verify_cert=not args.no_verify,
        ntfy_enabled=not args.no_ntfy,
        do_stop=args.stop,
        do_delete=args.delete,
        do_delete_data=args.delete_data,
    )

if __name__ == "__main__":
    main()
