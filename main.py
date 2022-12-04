import argparse
import json
from typing import List, Dict
import requests
import asyncio
from pyppeteer import launch
from tqdm import tqdm
import re

SPOTIFY_PLAYLIST_LINK = 'https://open.spotify.com/playlist/6V2aRX79ReETLpZWL4fJ63?si=32a1d88ec58c4b2d'
playlist_id = '6V2aRX79ReETLpZWL4fJ63'
api_url = 'https://api.spotify.com/v1/playlists/' + playlist_id
spotify_token = 'XX'


# get API-token:
# https://developer.spotify.com/console/get-playlist/?playlist_id=3cEYpjA9oz9GiPac4AsH4n&market=ES&fields=items(added_by.id%2Ctrack(name%2Chref%2Calbum(name%2Chref)))&additional_types=


def get_spotify_playlist_details():
    """
    Return dict of all titles and their artists in the spotify playlist.

    :return:
    """
    r = requests.get('https://api.spotify.com/v1/playlists/'+playlist_id,
                     headers={
                         'Authorization': f'Bearer {spotify_token}'},
                     )

    content = json.loads(r.content)["tracks"]["items"]
    song_details = list(
        map(lambda item: {'title': item["track"]["name"], 'artist': item["track"]["artists"][0]["name"]}, content))

    return song_details


async def find_musescore_sheet(title: str, artist: str, s_instrument='piano', s_kind='solo'):
    browser = await launch()
    page = await browser.newPage()
    musescore_url = 'https://musescore.com/sheetmusic?text=' + f'{title} {artist}'.replace(' ', '%20')
    # print(musescore_url)
    await page.goto(musescore_url,
                    {'waitUntil': 'networkidle0'})

    sheet_nodes = await page.JJ('.EzJvq')

    results = []
    for node in sheet_nodes:
        votes: List[str] = await node.JJeval('.CuFrh', '(nodes => nodes.map(n => n.innerText))')
        link = await node.JJeval('.xrntp', '(nodes => nodes.map(n => n.href))')
        title = await node.JJeval('.xrntp', '(nodes => nodes.map(n => n.innerText))')
        kind = await node.JJeval('.C4LKv.fLob3.DIiWA', '(nodes => nodes.map(n => n.innerText))')
        instrument = await node.JJeval('.C4LKv.B6vE9.DIiWA.z99NF', '(nodes => nodes.map(n => n.innerText))')

        if s_kind.lower() == kind[0].lower() and s_instrument.lower() in instrument[0].lower() and len(votes) > 0:
            vote_count: int = int(votes[0].split(' ')[0])  # take the elem from list, remove redundant string and cast int
            results.append({'votes': vote_count, 'link': link, 'title': title, 'kind': kind, 'instrument': instrument})

    await browser.close()
    return results


async def find_musescore_sheets(song_details: List[Dict]):
    mappings = []
    for info in tqdm(song_details):
        sheet_recommendations = await find_musescore_sheet(**info)

        # filter all search results for which no results were found
        if len(sheet_recommendations) > 0:
            # only keep the sheet with the most votes
            sheet_recommendations = sheet_recommendations[0]

            mappings.append((info["title"], sheet_recommendations))

    return mappings


async def main():
    song_details = get_spotify_playlist_details()
    recommendations = await find_musescore_sheets(song_details[:2])
    recommendations.sort(key=lambda r: r[1]["votes"], reverse=True)

    for recommendation in recommendations:
        print(f'{recommendation[0]}: {recommendation[1]["link"][0]} ({recommendation[1]["votes"]} votes)')


if __name__ == '__main__':
    print(
        "get the spotify token here: \nhttps://developer.spotify.com/console/get-playlist/?playlist_id=3cEYpjA9oz9GiPac4AsH4n&market=ES&fields=items(added_by.id%2Ctrack(name%2Chref%2Calbum(name%2Chref)))&additional_types=")
    parser = argparse.ArgumentParser(
        prog='SpoticoreFinder',
        description='Search for the most voted music sheets on musescore for songs from a spotify playlist',
        epilog='Thanks')

    parser.add_argument('token', type=str)
    args = parser.parse_args()

    spotify_token = args.token

    res = re.search('/[^/]*\\?', SPOTIFY_PLAYLIST_LINK)
    playlist_id = res.group()[1:-1]

    asyncio.run(main())
