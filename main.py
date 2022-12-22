import argparse
import asyncio
import json
import re
from typing import List, Tuple

import pandas as pd
import requests
from pyppeteer import launch
from tqdm import tqdm

from customtypes import SpotifySongInfo, MusescoreSongInfo, SongSearch

playlist_id = '6V2aRX79ReETLpZWL4fJ63'
spotify_token = ''


# get API-token:
# https://developer.spotify.com/console/get-playlist/


def get_spotify_playlist_details(playlist_url: str) -> List[SpotifySongInfo]:
    """
    Return dict of all titles and their artists in the spotify playlist.

    :return:
    """

    r = requests.get(playlist_url,
                     headers={
                         'Authorization': f'Bearer {spotify_token}'},
                     )

    content = json.loads(r.content)

    if "tracks" in content:
        tracks = content["tracks"]
    else:
        tracks = content

    items = tracks["items"]
    next_url = tracks["next"]
    song_details = list(
        map(lambda item: {'title': item["track"]["name"], 'artist': item["track"]["artists"][0]["name"]}, items))

    if next_url is not None:
        song_details.extend(get_spotify_playlist_details(next_url))

    return song_details


async def find_musescore_sheet(search: SongSearch) -> List[MusescoreSongInfo]:
    browser = await launch()
    page = await browser.newPage()
    musescore_url = f'https://musescore.com/sheetmusic?text={search["title"]} {search["artist"]}' \
        .replace(' ', '%20')

    # wait for the page to be fully loaded
    await page.goto(musescore_url, {'waitUntil': 'networkidle0'})

    # search the sheet music on the page
    sheet_nodes = await page.JJ('.EzJvq')

    results = []
    for node in sheet_nodes:
        votes: List[str] = await node.JJeval('.CuFrh', '(nodes => nodes.map(n => n.innerText))')
        link = await node.JJeval('.xrntp', '(nodes => nodes.map(n => n.href))')
        title = await node.JJeval('.xrntp', '(nodes => nodes.map(n => n.innerText))')
        kind = await node.JJeval('.C4LKv.fLob3.DIiWA', '(nodes => nodes.map(n => n.innerText))')
        instrument = await node.JJeval('.C4LKv.B6vE9.DIiWA.z99NF', '(nodes => nodes.map(n => n.innerText))')

        if len(votes) > 0 and search["kind"].lower() == kind[0].lower() and search["instrument"].lower() in instrument[
            0].lower():
            # format votes accordingly (possible e.g. 1K oder 1.7K)
            vote_formatted = votes[0].split(' ')[0]
            match = re.search('\\.[0-9]K', vote_formatted)
            if match != None:
                vote_formatted = vote_formatted.replace('.', '')
                vote_formatted = vote_formatted.replace('K', '00')

            vote_formatted = vote_formatted.replace('K', '000')

            vote_count: int = int(vote_formatted)  # take the elem from list, remove redundant string and cast int
            results.append(
                {'votes': vote_count, 'link': link[0], 'title': title, 'kind': kind, 'instrument': instrument})

    await browser.close()
    return results


async def find_musescore_sheets(song_details: List[SpotifySongInfo], instrument: str, kind: str) \
        -> List[Tuple[SongSearch, MusescoreSongInfo]]:
    mappings = []

    for info in tqdm(song_details):
        sheet_recommendations = await find_musescore_sheet(info | {'instrument': instrument, 'kind': kind})

        # filter all search results for which no results were found
        if len(sheet_recommendations) > 0:
            # only keep the sheet with the most votes
            sheet_recommendations = sheet_recommendations[0]

            mappings.append((info, sheet_recommendations))

    return mappings


def recommendations_to_df(recommendations: List[Tuple[SongSearch, MusescoreSongInfo]]) -> pd.DataFrame:
    data = {
        "title": [],
        "artist": [],
        "link": [],
        "votes": []
    }

    for recommendation in recommendations:
        data["title"].append(recommendation[0]["title"])
        data["artist"].append(recommendation[0]["artist"])
        data["link"].append(recommendation[1]["link"])
        data["votes"].append(recommendation[1]["votes"])

    return pd.DataFrame(data)


async def main(instrument='piano', kind='solo'):
    song_details = get_spotify_playlist_details('https://api.spotify.com/v1/playlists/' + playlist_id)
    recommendations = await find_musescore_sheets(song_details[:5], instrument, kind)

    df = recommendations_to_df(recommendations)
    df.sort_values(by='votes', ascending=False, inplace=True)
    df.to_csv('sheets2.csv', ';', index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='SpoticoreFinder',
        description='Search for the most voted music sheets on musescore for songs from a spotify playlist')

    parser.add_argument('token', type=str,
                        help='get the spotify token here: \n https://developer.spotify.com/console/get-playlist')
    parser.add_argument('playlist', type=str,
                        help='the link to the spotify playlist')
    # TODO add args for instrument and kind

    args = parser.parse_args()

    spotify_token = args.token

    res = re.search('/[^/]*\\?', args.playlist)
    playlist_id = res.group()[1:-1]

    asyncio.run(main())
