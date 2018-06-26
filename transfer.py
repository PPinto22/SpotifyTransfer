import json
import urllib2
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

from util import chunks

# Get tokens read/modify tokens from, e.g.,
# https://developer.spotify.com/web-api/console/put-following/#complete

# Permissions: user-follow-read, user-library-read, playlist-read-private, playlist-read-collaborative
READ_AUTH_TOKEN = "TOKEN A"  # Authentication token with read permissions for the sender account
# Permissions: user-follow-modify, user-library-modify, playlist-modify-public, playlist-modify-private
MODIFY_AUTH_TOKEN = "TOKEN B"  # Authentication token with modify permissions for the receiver account


def run_transfer():
    print "Transferring artists..."
    artist_list = fetch_artists()
    put_artists(artist_list)

    print "Transferring songs..."
    song_list = fetch_songs()
    put_songs(song_list)

    print "Transferring playlists..."
    playlist_list = fetch_playlists()
    put_playlists(playlist_list)


class MethodRequest(urllib2.Request):
    """
    PUT request with urllib2
    
    From GitHub @logic: https://gist.github.com/logic/2715756
    """

    def __init__(self, *args, **kwargs):
        if 'method' in kwargs:
            self._method = kwargs['method']
            del kwargs['method']
        else:
            self._method = None
        return urllib2.Request.__init__(self, *args, **kwargs)

    def get_method(self, *args, **kwargs):
        if self._method is not None:
            return self._method
        return urllib2.Request.get_method(self, *args, **kwargs)


# Find a value in a dictionary
def find(key, dict):
    if key in dict:
        return dict[key]
    else:
        return dict['artists'][key]


def fetch_data(url, query='', limit=50, output=None):
    total = 10000
    offset = 0
    first = True
    all_data = []

    query = '?' + '&'.join([query, 'limit={}'.format(limit)])
    url = url + query

    while offset < total:
        print 'Fetching items [{}, {}] of {}'.format(offset, offset + limit, '?' if first else total)

        request = urllib2.Request(url)
        request.add_header("Authorization", "Bearer %s" % READ_AUTH_TOKEN)
        request.add_header("Accept", "application/json")

        response = urllib2.urlopen(request)
        response_data = json.load(response)

        if first:
            total = find('total', response_data)
            first = False

        all_data.extend(find('items', response_data))
        offset += limit
        url = find('next', response_data)

    if output:
        fp = open(output, 'w')
        json.dump(all_data, fp, indent=2)
        fp.close()

    return all_data


def fetch_artists(limit=50, output='my_spotify_artists.json'):
    return fetch_data('https://api.spotify.com/v1/me/following', query='type=artist', limit=limit, output=output)


def fetch_songs(limit=50, output='my_spotify_songs.json'):
    return fetch_data('https://api.spotify.com/v1/me/tracks', limit=limit, output=output)


def fetch_playlists(limit=5, output='my_spotify_playlists.json'):
    return fetch_data('https://api.spotify.com/v1/me/playlists', limit=limit, output=output)


def put_artists(artist_list, batch_size=50):
    assert 0 < batch_size <= 50

    for idx, batch in enumerate(chunks(artist_list, batch_size)):
        if batch_size > 1:
            print "Saving artists [{}, {}] of {}".format(idx * batch_size, idx * batch_size + batch_size - 1,
                                                         len(artist_list))
        else:
            print "Saving artist {} of {}".format(idx + 1, len(artist_list))
        artist_ids = [str(artist['id']) for artist in batch]
        artist_ids_str = ','.join(artist_ids)

        url = "https://api.spotify.com/v1/me/following?type=artist&ids={}".format(artist_ids_str)
        request = MethodRequest(url, method='PUT')
        request.add_header("Authorization", "Bearer %s" % MODIFY_AUTH_TOKEN)
        request.add_header("Content-Type", "application/json")

        response = urllib2.urlopen(request)


def put_songs(song_list, batch_size=50):
    assert 0 < batch_size <= 50

    # Sort songs by added_date so they maintain (roughly) the same order
    # If batches are used (batch_size > 1), order won't be preserved within batches
    song_list = sorted(song_list, key=lambda x: x['added_at'])

    for idx, batch in enumerate(chunks(song_list, batch_size)):
        if batch_size > 1:
            print "Saving songs [{}, {}] of {}".format(idx * batch_size, idx * batch_size + batch_size - 1,
                                                       len(song_list))
        else:
            print "Saving song {} of {}".format(idx + 1, len(song_list))

        song_ids = [str(song['track']['id']) for song in batch]

        url = "https://api.spotify.com/v1/me/tracks"
        request = MethodRequest(url, method='PUT', data=json.dumps({'ids': song_ids}))
        request.add_header("Authorization", "Bearer %s" % MODIFY_AUTH_TOKEN)
        request.add_header("Content-Type", "application/json")

        response = urllib2.urlopen(request)


def put_playlists(playlist_list):
    for idx, playlist in enumerate(playlist_list):
        print "Saving playlist {} of {}".format(idx, len(playlist_list))
        url = "https://api.spotify.com/v1/users/{}/playlists/{}/followers" \
            .format(playlist['owner']['id'],
                    playlist['id'])
        request = MethodRequest(url, method='PUT', data=json.dumps({"public": playlist['public']}))
        request.add_header("Authorization", "Bearer %s" % MODIFY_AUTH_TOKEN)
        request.add_header("Content-Type", "application/json")

        response = urllib2.urlopen(request)


if __name__ == '__main__':
    run_transfer()
