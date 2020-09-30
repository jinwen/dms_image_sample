import os
import socket
import time
import sys
import logging
from PIL import Image
from crccheck.crc import Crc8, Crc16

def packagePayload(payload, 
                width, height, utc_ts, 
                image_size, payload_offset_in_image,
                compression_ratio, compression_algo):
    # init header
    header = bytearray(26)
    # putting data to header 
    header[0] = 0x47 # sop
    header[1] = 0x00 # camera id
    header[2] = 0x01 # image type
    header[3] = (width & 0xff) # width
    header[4] = (width >> 8) & 0xff
    header[5] = (height & 0xff) # height
    header[6] = (height >> 8) & 0xff
    header[7] = (utc_ts & 0xff) # utc timestamp
    header[8] = (utc_ts >> 8) & 0xff
    header[9] = (utc_ts >> 16) & 0xff
    header[10] = (utc_ts >> 24) & 0xff
    payload_size = len(payload)
    header[11] = (payload_size & 0xff) # payload size
    header[12] = (payload_size >> 8) & 0xff
    header[13] = (payload_size >> 16) & 0xff
    header[14] = (payload_size >> 24) & 0xff
    header[15] = (image_size & 0xff) # image_size size
    header[16] = (image_size >> 8) & 0xff
    header[17] = (image_size >> 16) & 0xff
    header[18] = (image_size >> 24) & 0xff
    header[19] = (payload_offset_in_image & 0xff) # payload offset in image
    header[20] = (payload_offset_in_image >> 8) & 0xff
    header[21] = (payload_offset_in_image >> 16) & 0xff
    header[22] = (payload_offset_in_image >> 24) & 0xff
    header[23] = compression_ratio
    header[24] = compression_algo
    header[25] = Crc8.calc(header[:25])

    data = header + payload 
    crc16 = Crc16.calc(data).to_bytes(2, byteorder="little")
    # append package crc16
    data += crc16
    return data

logging.basicConfig(level=logging.INFO)
UDP_IP = "localhost"
UDP_PORT = 5005
buf = 1024
file_name = sys.argv[1]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.sendto(bytearray(file_name, 'UTF-8'), (UDP_IP, UDP_PORT))
logging.info("Sending %s ..." % file_name)

with Image.open(file_name) as img:
    width, height = img.size
    image_size = os.path.getsize(file_name)
    logging.info("Image width: %d, height: %d, size: %d" % (width, height, image_size))

utc_ts = int(time.time())
payload_offset_in_image = 0
f = open(file_name, "rb")
package_sent = 0
payload = f.read(buf)
data = packagePayload(payload,
                      width, height, utc_ts, 
                      image_size, payload_offset_in_image,
                      0x50, 0x00)
while(payload):
    logging.debug("Sending payload at offset: %d, payload size: %d, package size: %d" % (payload_offset_in_image, len(payload), len(data)))
    if(sock.sendto(data, (UDP_IP, UDP_PORT))):
        payload_offset_in_image += len(payload)
        package_sent += 1
        payload = f.read(buf)
        data = packagePayload(payload, 
                              width, height, utc_ts, 
                              image_size, payload_offset_in_image,
                              0x50, 0x00)
        #time.sleep(0.01) # Give receiver a bit time to save

logging.info("package sent: %d" % package_sent)
f.close()
sock.close()
