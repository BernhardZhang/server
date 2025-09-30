# -*- coding:utf-8 -*-
# using package 'pycryptodome' for encryption and decryption
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
import base64
from . import params

def AES_Encrypt(key, text):
    my_aes=AES.new(base64.b64decode(key), AES.MODE_CFB, iv=params.AES_IV, segment_size=8)
    cipher_text=my_aes.encrypt(text)
    return base64.b64encode(cipher_text)

def AES_Decrypt(key, cipher):
    my_aes=AES.new(base64.b64decode(key), AES.MODE_CFB, iv=params.AES_IV, segment_size=8)
    text=my_aes.decrypt(base64.b64decode(cipher))
    return text

def RSA_Encrypt(text, public_key):
    key=RSA.importKey(public_key)
    cipher=PKCS1_v1_5.new(key)
    cipher_text=cipher.encrypt(text)
    return base64.b64encode(cipher_text)

def RSA_Decrypt(cipher_text, private_key):
    key=RSA.importKey(private_key)
    cipher=PKCS1_v1_5.new(key)
    cipher_text=cipher.decrypt(base64.b64decode(cipher_text), 'error')
    return cipher_text