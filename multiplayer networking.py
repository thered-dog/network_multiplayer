import socket
import threading
import select
import os
import threading
import time
import random
import base64
import numpy as np
import sys
import argparse
import tempfile
import queue
import sounddevice as sd
import soundfile as sf
import zipfile
import pyaudio

from kivy.app import App
from kivy.core.window import Window 
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.config import Config
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock, mainthread
from kivy.animation import Animation
from kivy.uix.progressbar import ProgressBar
from kivy.uix.videoplayer import VideoPlayer
from kivy.core.audio import SoundLoader
from PIL import Image as PILImage

#Variables
window_size = 1000,600
host = socket.gethostname()
player_dict = {}
message_list = []

def get_ip():
    try: # For Raspberry Pi
        os.uname()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(('10.254.254.254', 1))
            IP = s.getsockname()[0]
        except:
            IP = '127.0.0.1'
        finally:
            s.close()
    except: # For Windows
        IP = socket.gethostbyname(socket.gethostname()) # For Windows

    tmp = IP.split('.')
    tmp[3] = '255'
    gateway = ''
    for i, idx in enumerate(tmp): gateway = gateway + idx + ('.' if i != 3 else '')
    return IP, gateway

local_ip = get_ip()[0]
gateway = get_ip()[1]

DEVICE_TYPE = 0 # 1 if Windows | 2 if Raspberry Pi
try: #Pi
    os.uname()
    DEVICE_TYPE = 2
except: #Windows
    DEVICE_TYPE = 1

server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
server.bind((local_ip if DEVICE_TYPE == 1 else gateway, 5001))

def send_message():
    global message_list
    while True:
        if len(message_list) > 0:
            for i,idx in enumerate(message_list):
                read_address.sendto(idx.encode(),(gateway,5000))
                print("sent", idx)
                message_list.remove(idx)

send_thread = threading.Thread(target=send_message)
send_thread.daemon = True
send_thread.start()

def read_message():
    print("Reading Messages")
    if local_ip != '127.0.0.1' and local_ip != '0.0.0.0':
        print("passed check")
        while True:
            r, _, _ = select.select([read_address], [], [], 0)
            if r:
                rec_msg, rec_ip = read_address.recvfrom(65507)
                message = rec_msg.decode('utf-8').split("|")
                print("Message recieved:", message)
                #print("Recieved message", message, "from", rec_ip[0])
                if rec_ip[0] != local_ip:
                    if rec_ip[0] not in player_dict:
                        print("New player has joined")
                        colour = []
                        colour.append(float(message[3]))
                        colour.append(float(message[4]))
                        colour.append(float(message[5]))
                        colour.append(1)
                        global_create_player(colour, rec_ip[0], int(message[1]), int(message[2]))
                        player_moved(rec_ip[0],int(message[1]), int(message[2]))

read_address = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
read_address.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
read_address.bind((local_ip if DEVICE_TYPE == 1 else gateway, 5000))                

read_thread = threading.Thread(target=read_message)
read_thread.daemon = True
read_thread.start()

@mainthread
def player_moved(ip, x, y):
    global player_dict
    player_dict[ip].pos[0] = x
    player_dict[ip].pos[1] = y
    print(ip, "moved")

def join_server(btn):
    global player_dict, message_list
    main_layout.remove_widget(main_menu)
    if local_ip not in player_dict:
        create_player(color_picker(colour_gen()), local_ip,100,100)
        print(player_dict)
        player = player_dict[local_ip]
        #print(player_dict)
        message_list.append(str(local_ip)+"|"+str(player.pos[0])+"|"+str(player.pos[1]) + "|" + str(player.color[0])+ "|" + str(player.color[1])+ "|" + str(player.color[2]))

def colour_gen():
    colour = []
    for i in range(3):
        colour.append(random.randint(0,255))
    return colour

@mainthread
def global_create_player(c,ip,x,y):
    create_player(c,ip,x,y)

def create_player(c,ip,x,y):
    global player, player_dict 

    #print("COLOUR:", c)
    if ip not in player_dict:
        player = Image(size = (50,50),
                    pos = (x,y),
                    size_hint = [None, None],
                    color = c,
                    )    
        player_layout.add_widget(player)
        
        player_dict[ip] = player
        print(ip, "THIS IS PRINTED")
    else: print("BUG: IP is in list")
#Color Picker
def color_picker(c):
    rgb = colour_gen()
    #print(rgb)
    for i in range(len(rgb)):
        rgb[i]/=255
    final_rgb = (rgb[0],rgb[1],rgb[2],1)
    return final_rgb
class multiplayer(App):
    def build(self):
        global player_layout, main_layout, main_menu
        Window.size = window_size
        Window.bind(on_key_down=self.key_action)
        print(Window.size)

        main_layout = FloatLayout()
        player_layout = FloatLayout()
        main_menu = FloatLayout()

        main_layout.add_widget(player_layout)
        main_layout.add_widget(main_menu)
        
        join_btn = Button(size = (200, 100),
                          pos_hint = {"center_x":0.5, "center_y":0.5},
                          size_hint = [None, None],
                          on_release = join_server,
                          )

        main_menu.add_widget(join_btn)

        return main_layout
    def key_action(self, *args):
        global player
        if main_menu not in main_layout.children:
            moved = False
            if list(args)[3] == 'd':
                if player_dict[local_ip].pos[0] <= Window.size[0]-50:
                    player_dict[local_ip].pos[0] += 50
            if list(args)[3] == 'a':
                if player_dict[local_ip].pos[0] >= 0:
                    player_dict[local_ip].pos[0] -= 50  
            if list(args)[3] == 'w':
                if player_dict[local_ip].pos[1] <= Window.size[1]-50:
                    player_dict[local_ip].pos[1] += 50   
            if list(args)[3] == 's':
                if player_dict[local_ip].pos[1] >= 0:
                    player_dict[local_ip].pos[1] -= 50 
            if list(args)[3] == 'd' or list(args)[3] == 'a' or list(args)[3] == 'w' or list(args)[3] == 's': moved = True
            if moved == True: message_list.append(str(local_ip)+"|"+str(player.pos[0])+"|"+str(player.pos[1]) + "|" + str(player.color[0])+ "|" + str(player.color[1])+ "|" + str(player.color[2]))
multiplayer().run()