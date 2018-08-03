# coding: utf8

from datetime import datetime
import json
import re

from config import config
from models import Album, Photo

from .utils import get_image, get_comments, get_likes


crawler = config.crawler


def get_album_summary(album_id):
    resp = crawler.get_url(config.ALBUM_SUMMARY_URL.format(uid=crawler.uid, album_id=album_id))
    first_photo_id = re.findall(r'"photoId":"(\d+)",', resp.text)[0]

    layer = crawler.get_json(config.PHOTO_INFO_URL.format(uid=crawler.uid, photo_id=first_photo_id))

    album = {
        'id': album_id,
        'name': layer['album']['name'],
        'desc': layer['album']['description'],
        'cover': get_image(layer['album']['fullLargeUrl']),
        'count': layer['album']['photoCount'],
        'comment': layer['album']['commentcount'],
        'share': layer['album']['shareCount'],
        'like': get_likes(album_id, 'album')
    }
    Album.insert(**album).on_conflict('replace').execute()
    if album['comment']:
        get_comments(album_id, 'album')
    if album['comment'] or album['share']:
        get_comments(album_id, 'album', global_comment=True)

    print(f'    fetch album {album_id} {album["name"]} ({album["desc"]}), {album["comment"]}/{album["share"]}/{album["like"]}')

    photo_list = layer['list']
    photo_count = len(photo_list)
    for idx, p in enumerate(photo_list):
        id = int(p['id'])
        photo = {
            'id': id,
            'album_id': album_id,
            'pos': idx,
            'prev': int(photo_list[idx-1]['id']),
            'next': int(photo_list[idx-photo_count+1]['id']),
            't': datetime.strptime(p['date'], '%Y年%m月%d日'),
            'title': p['title'],
            'src': get_image(p['large']),
            'comment': p['commentCount'],
            'share': p['shareCount'],
            'like': get_likes(id, 'photo'),
            'view': p['viewCount']
        }
        Photo.insert(**photo).on_conflict('replace').execute()
        if photo['comment']:
            get_comments(id, 'photo')
        if photo['comment'] or photo['share']:
            get_comments(id, 'photo', global_comment=True)

        print(f'      photo {id}: {p["title"][:24]}, {photo["comment"]}/{photo["share"]}/{photo["like"]}/{photo["view"]}')

    return album['count']


def get_album_list_page(page):
    param = {
        'offset': page*config.ITEMS_PER_PAGE,
        'limit': config.ITEMS_PER_PAGE 
    }
    resp = crawler.get_url(config.ALBUM_LIST_URL.format(uid=crawler.uid), param)
    albums = json.loads(re.findall(r"'albumList': (\[.*\]),", resp.text)[0])

    for a in albums:
        id = int(a['albumId'])
        print(f'    album {id}: {a["albumName"]}, has {a["photoCount"]} photos')
        if a["photoCount"]:
            get_album_summary(id)

    print(f'  get {len(albums)} albums on list page {page}')
    return len(albums)


def get_albums():
    cur_page = 0
    total = 1
    while cur_page*config.ITEMS_PER_PAGE < total:
        print(f'start crawl album list page {cur_page}')
        total += get_album_list_page(cur_page)
        cur_page += 1

    return total