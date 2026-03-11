import argparse
import csv
import json
import os

from datetime import datetime

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# AUTHENTICATION (env vars)
CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')
SCOPE = 'playlist-read-private playlist-read-collaborative'

# INIT
sp = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        open_browser=False
    )
)

# UTILS
def get_all_playlists():
    playlists = []
    results = sp.current_user_playlists()

    while results:
        playlists.extend(results['items'])
        results = sp.next(results) if results['next'] else None

    return playlists

def list_playlists():
    playlists= get_all_playlists()

    print ("\nAvailable Playlists:\n")

    for i, p in enumerate(playlists):
        print(f"[{i}] {p['name']}")

    print("\nTotal:", len(playlists))


def parse_playlist_selection(selection, playlists):
    indexi = [int(x.strip()) for x in selection.split(",")]
    return [playlists[i] for i in indexi]


# EXPORT
def export_playlists(selected_playlists):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")

    json_file = f"{timestamp}_spotify_export_tracks.json"
    csv_file = f"{timestamp}_spotify_export_tracks.csv"
    log_file = f"{timestamp}_spotify_export_tracks.jsonl"

    all_data = []
    global_track_index = 0

    for playlist in selected_playlists:
        playlist_id = playlist['id']
        playlist_name = playlist['name']

        print(f"\nFetching playlist: {playlist_name}")

        results = sp.playlist_items(playlist_id)

        while results:
            for item in results['items']:
                global_track_index += 1
                track = item.get("track")

                if not isinstance(track, dict):
                    log_entry = {
                        "global_track_index": global_track_index,
                        "playlist": playlist_name,
                        "raw_track": track,
                        "reason": "invalid or missing track object"
                    }
                    with open(log_file, "a", encoding="utf-8") as f:
                        json.dump(log_entry, f, ensure_ascii=False, indent=4)
                        f.write("\n")
                    continue

                track_name = track.get("name", "")
                artist_names = ", ".join(
                    [a.get("name", "") for a in track.get("artists", [])]
                )

                album_name = (track.get("album") or {}).get("name", "")
                track_url = (track.get("external_urls") or {}).get("spotify", "")
                playlist_url = (playlist.get("external_urls") or {}).get("spotify", "")
                added_at = item.get("added_at", "")
                added_by = item.get("added_by", "")
                is_local = item.get("local", False)

                all_data.append({
                    "global_index": global_track_index,
                    "playlist": playlist_name,
                    "track_name": track_name,
                    "artist": artist_names,
                    "album": album_name,
                    "track_url": track_url,
                    "playlist_url": playlist_url,
                    "added_at": added_at,
                    "added_by": added_by,
                    "is_local": is_local
                })

            results = sp.next(results) if results.get("next") else None

    print("\nWriting playlists to files...")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "global_index",
            "playlist",
            "track_name",
            "artist",
            "album",
            "track_url",
            "playlist_url",
            "added_at",
            "added_by",
            "is_local"
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for row in all_data:
            # Flatten added_by dict to user id string or empty
            added_by_val = ''
            if isinstance(row['added_by'], dict):
                added_by_val = row['added_by'].get('id', '')
            writer.writerow({
                'global_index': row.get('global_index', ''),
                'playlist': row.get('playlist', ''),
                'track_name': row.get('track_name', ''),
                'artist': row.get('artist', ''),
                'album': row.get('album', ''),
                'track_url': row.get('track_url', ''),
                'playlist_url': row.get('playlist_url', ''),
                'added_at': row.get('added_at', ''),
                'added_by': added_by_val,
                'is_local': row.get('is_local', False)
            })

    print("\nExport complete.")
    print("JSON:", json_file)
    print("CSV:", csv_file)

# CLI
def main():
    parser = argparse.ArgumentParser(
        description='Extract Playlists from Spotify'
    )

    subparsers = parser.add_subparsers(dest='command')
    subparsers.add_parser('list', help='List playlists')
    export_parser = subparsers.add_parser('export', help='Export playlists')

    group = export_parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        '--playlists',
        type=str,
        help='range of playlist indexes (e.g. 0-5)'
    )
    group.add_argument(
        '--all',
        action="store_true",
        help='export all playlists'
    )

    args = parser.parse_args()

    if args.command == 'list':
        list_playlists()
    elif args.command == 'export':
        playlists = get_all_playlists()

        if args.all:
            selected = playlists
        elif args.playlists:
            selected = parse_playlist_selection(args.playlists, playlists)
        else:
            print('specify which playlists to export')
            return
        export_playlists(selected)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()