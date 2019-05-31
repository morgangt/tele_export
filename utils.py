from .options import *
from django.conf import settings
from telethon import TelegramClient
from telethon.tl.functions.users import GetFullUserRequest
from telethon.utils import get_display_name
from telethon.tl.functions.channels import JoinChannelRequest, GetFullChannelRequest
from django.core.files import File
import os

import Image
import numpy as np
import scipy.cluster

NUM_CLUSTERS = 5

client = TelegramClient('session_name', api_id, api_hash,
                        spawn_read_thread=False, proxy=None, update_workers=4)

assert client.connect()
if not client.is_user_authorized():
    phone_number = phone
    client.send_code_request(phone_number)
    myself = client.sign_in(phone_number, input('Enter code: '))

client.start(phone=phone)


def get_msg_user(username='DimboDancer'):
    messages = client.get_messages(username)
    response = {}

    full = client(GetFullUserRequest(username))
    bio = full.about

    for msg in messages:
        response[str(msg.id)] = {"author": get_display_name(msg.sender), "message": msg.message}
    return response


def download_content(msg):
    res = {}
    try:
        res['post_author'] = msg.post_author
    except AttributeError:
        # не загрузили и ладно
        pass

    res["id"] = str(msg.id)
    res["author"] = get_display_name(msg.sender)
    res["message"] = msg.message
    try:
        if getattr(msg.media, "document", None):
            mime_type = msg.media.document.mime_type
        elif getattr(msg.media, "photo", None):
            mime_type = "photo"
        else:
            mime_type = ""

        if "audio" in mime_type:
            is_audio = client.download_media(msg, file=settings.TMP_FILE)
            if is_audio and is_audio.split(".")[-1] in ["mp3", "wav", "amr", "acc"]:
                res["audio"] = is_audio

        if "video" in mime_type:
            is_video = client.download_media(msg, file=settings.TMP_FILE)
            if is_video and is_video.split(".")[-1] in ['mp4']:
                res["video"] = is_video

        if "photo" in mime_type:
            is_photo = client.download_media(msg, file=settings.TMP_FILE)
            if is_photo and is_photo.split(".")[-1] in ['jpg', 'jpeg', 'png', 'gif']:
                res["photo"] = is_photo

    except AttributeError:
        # ToDo: add deleted file
        pass


def get_channel(channel, limit=settings.LIMIT_POST):
    """ geting date from telegram """
    try:
        bio = client(JoinChannelRequest(channel))
    except ValueError:
        return None

    full = client(GetFullChannelRequest(channel))
    bio_channel = full
    response = {"msg": []}
    response['username'] = bio.chats[0].username
    response['date'] = bio.chats[0].date
    response['title'] = bio.chats[0].title
    if bio.chats[0].photo:
        response['photo'] = client.download_profile_photo(bio.chats[0].username, file=settings.TMP_FILE)
    else:
        response['photo'] = None
    response['members'] = bio_channel.full_chat.participants_count
    response['bio'] = bio_channel.full_chat.about
    response['access_hash'] = bio.chats[0].access_hash
    response['id'] = bio.chats[0].id
    response['update'] = False if (bio.updates == []) else True
    
    messages = client.get_messages(channel, limit=limit)
    response['count'] = len(messages)
    for msg in messages:
        res = {}
        try:
            res['post_author'] = msg.post_author
        except AttributeError:
            pass

        res["id"] = str(msg.id)
        res["author"] = get_display_name(msg.sender)
        res["message"] = msg.message

        try:
            if getattr(msg.media, "document", None):
                mime_type = msg.media.document.mime_type
            elif getattr(msg.media, "photo", None):
                mime_type = "photo"
            else:
                mime_type = ""

            if "audio" in mime_type:
                is_audio = client.download_media(msg, file=settings.TMP_FILE)
                if is_audio and is_audio.split(".")[-1] in ["mp3", "wav", "amr", "acc"]:
                    res["audio"] = is_audio

            if "video" in mime_type:
                is_video = client.download_media(msg, file=settings.TMP_FILE)
                if is_video and is_video.split(".")[-1] in ['mp4']:
                    res["video"] = is_video

            if "photo" in mime_type:
                is_photo = client.download_media(msg, file=settings.TMP_FILE)
                if is_photo and is_photo.split(".")[-1] in ['jpg', 'jpeg', 'png', 'gif']:
                    res["photo"] = is_photo

        except AttributeError:
            # ToDo: add deleted file
            pass

        try:
            res["views"] = msg.views
        except AttributeError:
            res["views"] = 0
        
        try:
            res["date"] = msg.date
        except AttributeError:
            res["date"] = None
        
        try:
            res["edit_date"]= msg.edit_date
        except AttributeError:
            res["edit_date"] = None
        
        try:
            res["via_bot"] = msg.via_bot_id
        except AttributeError:
            res["via_bot"] = None
        
        response['msg'].append(res)
    return response


def download_pic(obj, msg_photo):
    if obj:
        reopen = open(msg_photo, 'rb')
        django_file = File(reopen)
        if msg_photo.split(".")[-1] in ["png", "jpg", "jepg", "gif"]:
            obj.photo.save(msg_photo.replace(str(settings.TMP_FILE), ""), django_file, save=True)
            os.remove(msg_photo)


def download_audio(obj, msg_audio):
    if obj:
        reopen = open(msg_audio, 'rb')
        django_file = File(reopen)
        if msg_audio.split(".")[-1] in ["mp3", "wav", "amr", "acc"]:
            obj.audio.save(msg_audio.replace(str(settings.TMP_FILE), ""), django_file, save=True)
            os.remove(msg_audio)


def download_video(obj, msg_video):
    if obj:
        reopen = open(msg_video, 'rb')
        django_file = File(reopen)
        if msg_video.split(".")[-1] in ["mp4"]:
            obj.video.save(msg_video.replace(str(settings.TMP_FILE), ""), django_file, save=True)
            os.remove(msg_video)


def average_color(name_file):

    im = Image.open(name_file)
    im = im.resize((150, 150))      # optional, to reduce time
    ar = np.asarray(im)
    shape = ar.shape
    ar = ar.reshape(scipy.product(shape[:2]), shape[2]).astype(float)

    codes, dist = scipy.cluster.vq.kmeans(ar, NUM_CLUSTERS)

    vecs, dist = scipy.cluster.vq.vq(ar, codes)         # assign codes
    counts, bins = scipy.histogram(vecs, len(codes))    # count occurrences

    index_max = scipy.argmax(counts)                    # find most frequent
    peak = codes[index_max]
    colour = ''.join(chr(int(c)) for c in peak).encode('hex')
    return colour


