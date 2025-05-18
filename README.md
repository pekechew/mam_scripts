# qBit-MAM-Deleted Script

This script is useful when running autobrr to grab new releases that get nuked shortly after for various reasons, or when seeding old torrents that get removed when it's discovered that they broke some rule.

It checks qBittorrent for the tracker error "torrent not registered with this tracker" and tags it so it can be easily found and deleted. Then it sends an ntfy notification of what it tagged.

Optionally, it can also stop or delete the torrent, with another option to also delete the data.

## Prerequisites

* qBittorrent 5.x with the WebUI enabled
* Python 3
* pip
* Run the following command to install required Python libraries:
    ```bash
    pip install qbittorrent-api requests
    ```

## Install on Linux

1.  Create the directory:
    ```bash
    mkdir /opt/MAM
    ```
2.  Create and open the script file for editing:
    ```bash
    nano /opt/MAM/qbit-mam-deleted.py
    ```
3.  Paste the script content into the file.
4.  **Important:** Change the configuration variables at the start of the script to match your setup.
5.  Save and exit the editor (`CTRL+X`, then `Y`, then `ENTER`).
6.  Make the script executable:
    ```bash
    chmod +x /opt/MAM/qbit-mam-deleted.py
    ```
7.  Run the script to test (it will use defaults or settings from the script):
    ```bash
    ./qbit-mam-deleted.py
    ```

## Options

### Options (CLI or set in script)

These options can be set as default values directly within the script or overridden via the command line.

| Argument          | Description                                           | Default                       |
| ----------------- | ----------------------------------------------------- | ----------------------------- |
| `-h`, `--help`    | Show the help message and exit.                       | N/A                           |
| `--host HOST`     | WebUI host/IP (http or https URL allowed).            | `http://192.168.1.100`        |
| `--port PORT`     | WebUI port.                                           | `8090`                        |
| `--username USERNAME` | WebUI username.                                   | `admin`                       |
| `--password PASSWORD` | WebUI password.                                   | `admin`                       |
| `--category CATEGORY` | Only scan this category (None = all).               | `archive`                     |
| `--filter-tag FILTER_TAG` | Only process torrents that already have this tag. | `None`                        |
| `--status STATUS` | Comma-separated torrent statuses to include.          | `Stalled,Downloading,Seeding` |
| `--tag TAG`       | Name of the tag to apply to orphaned torrents.        | `deleted`                     |

### Options (CLI only)

These options can only be used via the command line.

| Argument        | Description                                                    | Default |
| --------------- | -------------------------------------------------------------- | ------- |
| `--stop`        | Stop torrents that are flagged as deleted.                     | `False` |
| `--delete`      | Delete torrent (NOT data). Implies `--stop`.                  | `False` |
| `--delete-data` | Delete torrent AND data. Implies `--stop`.                    | `False` |
| `--no-verify`   | Disable SSL certificate verification for HTTPS WebUI.          | `False` |
| `--no-ntfy`     | Disable ntfy push notifications.                               | `False` |
| `--verbose`     | Enable DEBUG logging.                                          | `False` |
| `--test-ntfy`   | Send a test ntfy notification and exit.                        | `False` |

## Examples

* **Tag torrents deleted from MAM using the tag "deleted"**
    * Creates the tag in qBittorrent if it doesn't exist.
    * Uses all other defaults specified in the script.
    * Sends an ntfy notification if any are tagged.
    * Doesn't delete anything.
    ```bash
    python3 qbit-mam-deleted.py
    ```
    or
    ```bash
    ./qbit-mam-deleted.py
    ```

* **Tag and delete torrent AND files from qBittorrent / the hard drive**
    * Use `--delete` to only delete the torrent and keep the data.
    ```bash
    ./qbit-mam-deleted.py --delete-data
    ```

* **Find all torrents with:**
    * A status of `Stalled` or `Seeding`,
    * A category of `archive`,
    * A tag of `mam`.
    * Then add the tag `deleted` to it, creating the tag if it doesn't exist.
    ```bash
    ./qbit-mam-deleted.py --status Stalled,Seeding --category archive --filter-tag mam --tag deleted
    ```

* **Test only the ntfy function to verify configuration**
    ```bash
    ./qbit-mam-deleted.py --test-ntfy
    ```

* **Don't send an ntfy notification**
    ```bash
    ./qbit-mam-deleted.py --no-ntfy
    ```

## Run the script daily

You can schedule the script to run automatically using `cron`.

1.  Open your crontab for editing:
    ```bash
    crontab -e
    ```
2.  Add a line to schedule the script. For example, to run at 6:00 AM every day and save a log:
    ```cron
    # Run at 6:00 am everyday and save a log
    0 6 * * * /usr/bin/python3 /opt/MAM/qbit-mam-deleted.py >> /var/log/qbit-mam-deleted.log 2>&1
    ```
    Adjust the path to `python3` and the script if necessary.
