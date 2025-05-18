# create_mam_torrent.sh

This script creates a `.torrent` file for a specified file or folder, places it in a designated output directory, 
and automatically adds it to **qBittorrent** using qbittorrent-cli's [qbt](https://github.com/ludviglundgren/qbittorrent-cli) based on the folder's `category` location.

## Description

`create_mam_torrent.sh` uses 
* shell script language
* [`mktorrent`](https://github.com/pobrn/mktorrent) to generate the `.torrent` file with a private tracker inserted
* [`qbittorrent-cli`](https://github.com/ludviglundgren/qbittorrent-cli) (qbt) to add the torrent to qBittorrent
* [`Mediainfo`](https://github.com/MediaArea/MediaInfo) to output bitrate and length info

## Installation

```bash
mkdir /opt/MAM/
cd /opt/MAM
wget https://raw.githubusercontent.com/pekechew/mam_scripts/refs/heads/main/create_mam_torrent/create_mam_torrent.sh
chmod +x create_mam_torrent.sh
nano create_mam_torrent.sh
```

## Config

Update the configuration at the beginning of the script

```bash
# Get this url from Torrents -> Upload Torrents -> info
TRACKERS="https://example.com/announce"
PIECE=""                                  # 2 MiB pieces (2^21). Set empty ("") for auto-size.
PRIVATE=true                              # mark torrent private (no DHT/PEX)
OUTPUT_DIR="/data/torrents"               # where .torrent files are stored
CATEGORY="archive"                        # Script uses categories to set the torrent path
QBT_BIN="/opt/qbittorrent-cli/qbt"        # path to the qbt executable
```

## Prereqs

Before running this script, ensure the following dependencies are installed and configured:

*   **`mktorrent`**:  This tool is used to create the `.torrent` file.  Install it using your system's package manager:
    ```bash
    sudo apt install mktorrent  # Debian/Ubuntu
    ```
*   **`mediainfo`**: This utility is used to extract metadata from the input file(s).
    ```bash
    sudo apt install mediainfo  # Debian/Ubuntu
    ```
*   **`qbittorrent-cli` (qbt)**:  The command-line interface for qBittorrent
    *   **Installation:**  Refer to the official repository for installation instructions: [https://github.com/ludviglundgren/qbittorrent-cli/](https://github.com/ludviglundgren/qbittorrent-cli/)
    *   Alternatively, install it this way:
    ```bash
    mkdir /opt/qbittorrent-cli
    cd /opt/qbittorrent-cli
    wget https://github.com/ludviglundgren/qbittorrent-cli/releases/download/v2.2.0/qbittorrent-cli_2.2.0_linux_amd64.tar.gz
    tar -xzvf qbittorrent-cli_2.2.0_linux_amd64.tar.gz
    rm qbittorrent-cli_2.2.0_linux_amd64.tar.gz
    wget https://raw.githubusercontent.com/ludviglundgren/qbittorrent-cli/refs/heads/master/.qbt.toml.example
    mv .qbt.toml.example ~/.config/qbt/.qbt.toml
    nano ~/.config/qbt/.qbt.toml
    ```
    *   **Configuration:** Ensure `qbittorrent-cli` is properly configured. Configuration file is typically located at `~/.config/qbt/qbt.toml`.
*   **qBittorrent Configuration:**  
    *   Open qBittorrent's settings.
    *   Navigate to **Options -> Downloads**.
    *   Ensure **"Use Category paths in Manual Mode"** is checked.
    *   Create category(s) with a path for the torrent data to seed from

## Usage

```bash
./create_mam_torrent.sh [-c|-m] /full/path/to/file_or_folder
```

*   `-c`:  Automatically copy files to the qBittorrent category folder when their original path doesn’t match.
*   `-m`:  Automatically move files to the qBittorrent category folder when their original path doesn’t match.

**Example:**

```bash
./create_mam_torrent.sh -c /mnt/media/Audiobooks/The_Adventures_of_Tom_Sawyer
./create_mam_torrent.sh -m /mnt/media/eBooks/The_Anarchist_Cookbook.pdf
```


## Output

*   The generated `.torrent` file will be placed in the `$OUTPUT_DIR` directory (set by the script itself).
*   The torrent will automatically be added to qBittorrent and start seeding.
*   Upload the torrent to the site, then go back to qBittorrent, right click the torrent then Force Reannounce
