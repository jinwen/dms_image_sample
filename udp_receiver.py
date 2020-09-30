import socket
import select
import logging
from crccheck.crc import Crc8, Crc16

def parseData(data):
    byte_data = bytearray(data)
    header = byte_data[:26]
    sop                     = header[0]
    camera_id               = header[1]
    image_type              = header[2]
    width                   = (header[4] & 0xff) << 8 | \
                              (header[3] & 0xff)
    height                  = (header[6] & 0xff) << 8 | \
                              (header[5] & 0xff)
    utc_ts                  = (header[10] & 0xff) << 24 | \
                              (header[9] & 0xff) << 16 | \
                              (header[8] & 0xff) << 8 | \
                              (header[7] & 0xff)
    payload_size            = (header[14] & 0xff) << 24 | \
                              (header[13] & 0xff) << 16 | \
                              (header[12] & 0xff) << 8 | \
                              (header[11] & 0xff)
    image_size              = (header[18] & 0xff) << 24 | \
                              (header[17] & 0xff) << 16 | \
                              (header[16] & 0xff) << 8 | \
                              (header[15] & 0xff)
    payload_offset_in_image = (header[22] & 0xff) << 24 | \
                              (header[21] & 0xff) << 16 | \
                              (header[20] & 0xff) << 8 | \
                              (header[19] & 0xff)
    compression_ratio       = header[23]
    compression_algo        = header[24]
    header_crc8             = header[25]
    crc8 = Crc8.calc(header[:25])
    if crc8 != header_crc8:
        logging.error("Header CRC mismatch:\n  header crc8: %x\n  calculated crc8: %x" % (header_crc8, crc8))

    payload = data[26:payload_size + 26]
    package_crc16 = (byte_data[-1] & 0xff) << 8 | \
                    (byte_data[-2] & 0xff)
    crc16 = Crc16.calc(byte_data[:payload_size + 26])
    if crc16 != package_crc16:
        logging.error("Package CRC mismatch:\n package crc16: %x\n calculated crc16: %x" % (package_crc16, crc16))
    header_data = {
        'sop': sop,
        'camera_id': camera_id,
        'image_type': image_type,
        'width': width,
        'height': height,
        'utc_ts': utc_ts,
        'payload_size': payload_size,
        'image_size': image_size,
        'payload_offset_in_image': payload_offset_in_image,
        'compression_ratio': compression_ratio,
        'compression_algo': compression_algo,
        'header_crc8': header_crc8,
        'package_crc16': package_crc16
    }
    return header_data, payload

logging.basicConfig(level=logging.INFO)
UDP_IP = "localhost"
IN_PORT = 5005
timeout = 3

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, IN_PORT))
package_received = 0

while True:
    data, addr = sock.recvfrom(1024)
    if data:
        file_name = data.decode('UTF-8')
        logging.info("File name: %s" % file_name)
        file_name = file_name[file_name.rfind('/') + 1:]

    f = open(file_name, 'wb')

    while True:
        ready = select.select([sock], [], [], timeout)
        if ready[0]:
            package_received += 1
            data, addr = sock.recvfrom(4096)
            header, payload = parseData(data)
            logging.debug(header)
            f.write(payload)
            # if (header['payload_size'] + header['payload_offset_in_image'] == header['image_size']):
        else:
            logging.info("%s received, package received: %d" % (file_name, package_received))
            f.close()
            break

