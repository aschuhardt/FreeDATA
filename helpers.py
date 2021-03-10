#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 25 21:25:14 2020

@author: DJ2LS
"""

import time
import threading
import logging
import crcengine
import pyaudio
import asyncio

import data_handler

import static



   
    
def get_crc_8(data):
    crc_algorithm = crcengine.new('crc8-ccitt') #load crc8 library
    crc_data = crc_algorithm(data)
    crc_data = crc_data.to_bytes(1, byteorder='big') 
    return crc_data

def get_crc_16(data):
    crc_algorithm = crcengine.new('crc16-ccitt-false') #load crc16 library
    crc_data = crc_algorithm(data)
    crc_data = crc_data.to_bytes(2, byteorder='big') 
    return crc_data   

async def set_after_timeout():
    while True:
        logging.info("HALLO?!?")
        time.sleep(1)
        print("HALLOIOIOIOIOIOI")
        static.ARQ_RX_ACK_TIMEOUT = True
        await asyncio.sleep(1.1)
    #await asyncio.sleep(timeout) 
    #vars()[variable] = value

    
    
def arq_disconnect_timeout():
    static.ARQ_WAIT_FOR_DISCONNECT = True
    logging.debug("ARQ_WAIT_FOR_DISCONNECT")       
       
       
def arq_ack_timeout():
    if static.CHANNEL_STATE == 'RECEIVING_SIGNALLING':
        static.ARQ_RX_ACK_TIMEOUT = True
        logging.debug("ARQ_RX_ACK_TIMEOUT")
    
def arq_rpt_timeout():
    if static.CHANNEL_STATE == 'RECEIVING_SIGNALLING':
        static.ARQ_RX_RPT_TIMEOUT = True    
        logging.debug("ARQ_RX_RPT_TIMEOUT")    

def arq_frame_timeout():
    if static.CHANNEL_STATE == 'RECEIVING_SIGNALLING':
        static.ARQ_RX_FRAME_TIMEOUT = True    
        logging.debug("ARQ_RX_FRAME_TIMEOUT")     
                
def arq_reset_timeout(state):
    static.ARQ_RX_ACK_TIMEOUT = state
    static.ARQ_RX_FRAME_TIMEOUT = state
    static.ARQ_RX_RPT_TIMEOUT = state
    
def arq_reset_ack(state):  
    static.ARQ_ACK_RECEIVED = state
    static.ARQ_RPT_RECEIVED = state
    static.ARQ_FRAME_ACK_RECEIVED = state
    
def arq_reset_frame_machine():
    arq_reset_timeout(False)
    arq_reset_ack(False)
    static.TX_N_RETRIES = 0
    static.ARQ_N_SENT_FRAMES = 0
    static.ARQ_TX_N_FRAMES_PER_BURST = 0
    static.ARQ_TX_N_CURRENT_ARQ_FRAME = 0
    static.ARQ_TX_N_TOTAL_ARQ_FRAMES = 0
    static.ARQ_TX_N_CURRENT_ARQ_FRAME = 0
    
    static.ARQ_RX_N_CURRENT_ARQ_FRAME = 0
    static.ARQ_N_ARQ_FRAMES_PER_DATA_FRAME = 0
    static.ARQ_FRAME_BOF_RECEIVED = False
    static.ARQ_FRAME_EOF_RECEIVED = False  
    
                 

    
    static.TNC_STATE = 'IDLE'                
    static.ARQ_SEND_KEEP_ALIVE = True
    static.CHANNEL_STATE = 'RECEIVING_SIGNALLING'
    static.ARQ_READY_FOR_DATA = False
    
    #start sending keep alive after some seconds
    #acktimer = threading.Timer(3.0, data_handler.arq_connect)
    #acktimer.start()
    #await asyncio.sleep(2)
    #modem.transmit_arq_connect()
def setup_logging():
    
    logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s', datefmt='%H:%M:%S', level=logging.INFO)

    logging.addLevelName( logging.DEBUG, "\033[1;36m%s\033[1;0m" % logging.getLevelName(logging.DEBUG))
    logging.addLevelName( logging.INFO, "\033[1;37m%s\033[1;0m" % logging.getLevelName(logging.INFO))
    logging.addLevelName( logging.WARNING, "\033[1;33m%s\033[1;0m" % logging.getLevelName(logging.WARNING))
    logging.addLevelName( logging.ERROR, "\033[1;31m%s\033[1;0m" % "FAILED")
    #logging.addLevelName( logging.ERROR, "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.ERROR))
    logging.addLevelName( logging.CRITICAL, "\033[1;41m%s\033[1;0m" % logging.getLevelName(logging.CRITICAL))
    
    logging.addLevelName( 25, "\033[1;32m%s\033[1;0m" % "SUCCESS")
    logging.addLevelName( 24, "\033[1;34m%s\033[1;0m" % "DATA")

    
    # https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
    #'DEBUG'   : 37, # white
    #'INFO'    : 36, # cyan
    #'WARNING' : 33, # yellow
    #'ERROR'   : 31, # red
    #'CRITICAL': 41, # white on red bg    

