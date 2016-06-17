#!/usr/bin/python3.5
# -*- coding: utf-8 -*-

'''
    Author: max.lager
    E-mail: tadambot@gmail.com
    @Version: 1.0
    @Release date: June 20/2016
    www.tadambot.xyz
'''

import os
import time
import json
import datetime
import sqlite3
import cherrypy
import telebot
import config
from acrcloud.recognizer import ACRCloudRecognizer

'''
    telebot from PyTelegramBotAPI
    Web-Framework: CherryPy
    Data-Base: SQLite3
    Audio Recognition: ACRCloud (www.acrcloud.com)
'''


WEBHOOK_HOST    = config.WHOST
WEBHOOK_PORT    = config.WPORT
WEBHOOK_LISTEN  = config.WLISTEN

WEBHOOK_SSL_CERT = config.WSSLCERT
WEBHOOK_SSL_PRIV = config.WSSLPRIV

WEBHOOK_URL_BASE = "https://%s:f%s" % (WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/%s/" % (config.token)

bot  = telebot.TeleBot(config.token)


class WebhookServer(object):
    @cherrypy.expose
    def index(self):
        if "content-length" in cherrypy.request.headers and \
            "content-type" in cherrypy.request.headers and  \
            cherrypy.request.headers["content-type"] == "application/json":

            length = int(cherrypy.request.headers["content-length"])
            json_string = cherrypy.request.body.read(length).decode("utf-8")
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return ''
        else:
            raise cherrypy.HTTPError(403)


def data_income(file_id, result):
    '''
    Creating DB with a results of recognition in format:
    FILE_ID | YY-MM-DD HH:MM:SS | RESULT [Recognized/Unrecocgnized]

    :param file_id:
    :param result:
    '''
    conn    = sqlite3.connect("%sfiles_data.db"%(config.db_dir))
    curs    = conn.cursor()
    tms     = time.time()
    date    = str(datetime.datetime.fromtimestamp(tms).strftime("%Y-%m-%d %H:%M:%S"))
    curs.execute("CREATE TABLE IF NOT EXISTS file_data(file_id TEXT, "
                "date TEXT, result TEXT)")
    curs.execute("INSERT INTO file_data(file_id, date, result) VALUES(?, ?, ?)",
                (file_id, date, result))
    conn.commit()


def file_down(file_id):
    '''
    Simply voice download function from Telegram

    :param file_id:
    :return: inputFile
    '''
    file_info       = bot.get_file(file_id)
    file_path       = file_info.file_path
    downloaded_file = bot.download_file(file_path)
    index           = str(file_id)
    inputFile       = ("%sAUDIO-%s.ogg" % (config.audio_dir, index))
    try:
        with open(inputFile, "wb") as new_file:
            new_file.write(downloaded_file)
    except NameError:
        pass
    return inputFile


def data_collector(result_dict):
    '''
    Simply data collector from dictionary.
    Returns list of necessary data.

    :param result_dict: dictionary created from JSON-object.
    :return: list
    '''
    list = []
    try:
        artist = result_dict['metadata']['music'][0]['artists'][0]['name']
    except KeyError:
        artist = False
    list.append(artist)

    try:
        title = result_dict['metadata']['music'][0]['title']
    except KeyError:
        title = False
    list.append(title)

    try:
        album = result_dict['metadata']['music'][0]['album']['name']
    except KeyError:
        album = False
    list.append(album)

    try:
        lable = result_dict['metadata']['music'][0]['label']
    except KeyError:
        lable = False
    list.append(lable)

    try:
        release_date = result_dict['metadata']['music'][0]['release_date']
    except KeyError:
        release_date = False
    list.append(release_date)

    try:
        youtube = result_dict['metadata']['music'] \
            [-1]['external_metadata']['youtube']['vid']
    except KeyError:
        youtube = False
    list.append(youtube)

    try:
        spotify = result_dict['metadata']['music']  \
                [-1]['external_metadata']['spotify']\
                ['track']['id']
    except KeyError:
        spotify = False
    list.append(spotify)

    try:
        deezer = result_dict['metadata']['music']  \
                [-1]['external_metadata']['deezer']\
                ['track']['id']
    except KeyError:
        deezer = False
    list.append(deezer)

    return list


@bot.message_handler(commands=["start"])
def handler_start(message):
    bot.send_message(message.chat.id, "I will help you to recognize the music."
                                      " Just send me the audio file, which is "
                                      "recorded by you, with using a voice rec"
                                      "ording button in the right corner at th"
                                      "e bottom. For more detailed instruction"
                                      "s type /help. Please, do not test bot u"
                                      "sing VK or other untrusted source!"
                                      "\nMusic Recognition by ACRCloud"
                     )


@bot.message_handler(commands=['help'])
def handler_help(message):
    bot.send_message(message.chat.id, "Send the audio file with duration from "
                                      "5 to 30 seconds to use the function of "
                                      "music recognition. Do it by pressing th"
                                      "e button of recording in the right corn"
                                      "er at the bottom. Press and hold this b"
                                      "utton to record and send the audio file"
                                      ". The recommended length of the file is"
                                      " 10 seconds."
                     )


@bot.message_handler(commands=['acrcloud'])
def handler_acrc(message):
    bot.send_message(message.chat.id, "ACRCloud utilises patented Automatic Co"
                                      "ntent Recognition (ACR) technology to e"
                                      "nable the generation of a unique real-t"
                                      "ime fingerprint to identify in a matter"
                                      " of seconds, the content being played v"
                                      "ia an audio or video source which is ty"
                                      "pically a first screen, in order to tri"
                                      "gger an action. With proprietary audio "
                                      "identification technology, ACRCloud’s i"
                                      "s able to identify millions of hours of"
                                      " content in both a manageable and effic"
                                      "ient manner that is highly relevant for"
                                      " advertisers, broadcasters, video strea"
                                      "ming providers, music services, consume"
                                      "r electronics manufacturers and app dev"
                                      "elopers. ACR’s fingerprint library incl"
                                      "udes 40 million audio tracks, which is "
                                      "one of the biggest in the world."
                                      "\nwww.acrcloud.com"
                     )

@bot.message_handler(func=lambda message: True, content_types=['voice'])
def handler_voice(message):
    '''
    Main function:
    1.Length checker (audio files should be from 5 to 30 seconds)
    2.file_down - downloading file that suitable for this condition
    3.rec       - recognizing music using ACRCloud script
    4.data_collector - creating list of necessary data from result of recognition

    :param message:
    '''
    user_id    = message.chat.id
    duration   = message.voice.duration
    message_id = message.message_id
    bot.send_chat_action(user_id, 'typing')
    if duration < 5:
        bot.send_message(user_id,
                         '<i>'
                         'The file is too short, '
                         'type /help to get instructions.'
                         '</i>',
                         parse_mode="HTML")
    elif duration > 30:
        bot.send_message(user_id,
                         '<i>'
                         'The file is too long, '
                         'type /help to get instructions'
                         '</i>',
                         parse_mode="HTML")
    else:
        inputFile   = file_down(message.voice.file_id)
        rec         = ACRCloudRecognizer(config.cfg)
        result      = rec.recognize_by_file(inputFile, 0)
        os.remove(inputFile)
        result_p    = json.loads(result)
        list        = data_collector(result_p)
        print(result_p)
        if result_p['status']['msg'] == 'Success':
            '''
            Flexible creation of output.
            Some data in the response may be absent.
            '''
            if list[0]: #artist
                output_0 = list[0]

            if list[1]: #title
                if 'output_0' in locals():
                    output_0 +=" - %s" % (list[1])
                else:
                    output_0 ="%s" % (list[1])

            if list[2]: #album
                output_2 = "Album: '%s'" % (list[2])

            if list[3]: #lable
                if 'output_2' in locals():
                    output_2 += "\nLable: %s" % (list[3])
                else:
                    output_2 = "Lable: %s" % (list[3])

            if list[4]: #release_date
                if 'output_2' in locals():
                    output_2 += "\nReleased: %s" % (list[4])
                else:
                    output_2 = "Released: %s" % (list[4])

            if list[5]: #youtube
                if 'output_2' in locals():
                    output_2 += "\n%s%s" % (config.yt_link, list[5])
                else:
                    output_2 = "%s%s" % (config.yt_link, list[5])

            if list[6] or list[7]: #spotify, deezer
                button_1 = telebot.types.InlineKeyboardButton('Buy %s' % (output_0),
                                                              callback_data=(str(list[6])
                                                              + ',' + str(list[7]) + ','
                                                              + str(user_id)))
                user_markup = telebot.types.InlineKeyboardMarkup(button_1)
                user_markup.row(button_1)
            else:
                tadambutton = telebot.types.InlineKeyboardButton(
                                                'TadamBot website',
                                                config.tadamweb)
                user_markup = telebot.types.InlineKeyboardMarkup(tadambutton)
                user_markup.row(tadambutton)

            bot.send_message(user_id, '<b>%s</b>' % (output_0),
                             parse_mode="HTML")
            bot.send_message(user_id, output_2,
                             reply_markup=user_markup)
        else:
            tadambutton = telebot.types.InlineKeyboardButton(
                'TadamBot website', config.tadamweb)
            user_markup = telebot.types.InlineKeyboardMarkup(tadambutton)
            user_markup.row(tadambutton)
            bot.send_message(user_id, 'Sorry, no result. You can try again or give us feedback.',
                             reply_markup=user_markup)
        return list


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    '''
    This handler allows to handle callback data from Inline Keyboards
    in Telegram. Necessary data contains in "callback_data" :parameter

    :param call:
    '''
    cald = call.data
    list = cald.split(',')
    if list[0] != 'False':
        spotify = config.spotify_link + list[0]
        button_spot = telebot.types.InlineKeyboardButton('Spotify',
                                                         spotify)
        user_markup_2 = telebot.types.InlineKeyboardMarkup()
        user_markup_2.row(button_spot)
        bot.send_photo(list[2], config.photo_id_s,
                       reply_markup=user_markup_2)

    if list[1] != 'False':
        deezer = config.deezer_link + list[1]
        button_dez = telebot.types.InlineKeyboardButton('Deezer',
                                                        deezer)
        user_markup_3 = telebot.types.InlineKeyboardMarkup()
        user_markup_3.row(button_dez)
        bot.send_photo(list[2], config.photo_id_d,
                       reply_markup=user_markup_3)

# Webhook removing eliminates some of the problems
bot.remove_webhook()

# Webhook installing
bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))

# CherryPy server settings
cherrypy.config.update({
    'server.socket_host': WEBHOOK_LISTEN,
    'server.socket_port': WEBHOOK_PORT,
    'server.ssl_module': 'builtin',
    'server.ssl_certificate': WEBHOOK_SSL_CERT,
    'server.ssl_private_key': WEBHOOK_SSL_PRIV
})

# Server start
cherrypy.quickstart(WebhookServer(), WEBHOOK_URL_PATH, {'/': {}})

