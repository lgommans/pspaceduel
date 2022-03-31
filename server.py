#!/usr/bin/env python3

import socket, os, hashlib, time
import mplib

def genToken():
    return hashlib.sha256(os.urandom(12)).digest()[0 : 12]


TIMEOUT = 600
MAXPLAYERS = 100
STATE_POLITELY_GREETED = 1
STATE_SHOWN_WORTHINESS = 2
STATE_MATCHED_TOGETHER = 3

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('0.0.0.0', 9473))

clients = {}

while True:
    try:  # wrap this whole thing in a try so bugs are not immediately fatal
        msg, addr = sock.recvfrom(mplib.maximumsize)

        timed_out = [client for client in clients if clients[client]['lastseen'] < time.time() - TIMEOUT]
        for client in timed_out:
            # if 'partner' in clients[client]:  # honestly, the timeout is such that the 'partner' is long aware of their absence...
            del clients[client]
            print('a client timed out. Current player count:', len(clients))

        if addr not in clients:
            if msg != mplib.clienthello:
                print('Received garbage from', addr)
                continue  # we are not home

            if len(clients) >= MAXPLAYERS:
                print('Returning "server full" to', addr)
                sock.sendto(mplib.playerlimit, addr)
                continue

            clients[addr] = {
                'token': genToken(),
                'state': STATE_POLITELY_GREETED,
                'lastseen': time.time(),
            }
            sock.sendto(mplib.serverhello + clients[addr]['token'], addr)

            print('New client from', addr, 'joined. Number of players, including them:', len(clients))

        else:
            # sender is known client
            if msg.startswith(mplib.playerquits):
                # do not ack this message as it might be unconfirmed
                if addr in clients:
                    if 'partner' in clients[addr]:
                        sock.sendto(msg, clients[addr]['partner'])
                        print(addr, 'quit. We also terminated their partner at', clients[addr]['partner'], '  Current player count:', len(clients))
                        del clients[clients[addr]['partner']]
                        del clients[addr]
                    else:
                        del clients[addr]
                        print(addr, 'quit. Current player count:', len(clients))
                continue

            clients[addr]['lastseen'] = time.time()

            if clients[addr]['state'] == STATE_POLITELY_GREETED:
                if msg != clients[addr]['token']:
                    # handshake failure. Send reset because we have enough bytes remaining before amplification
                    sock.sendto(mplib.protocolerr, addr)
                else:
                    clients[addr]['state'] = STATE_SHOWN_WORTHINESS
                    found = False
                    for client in clients:
                        if clients[client]['state'] == STATE_SHOWN_WORTHINESS and client != addr:  # if there is another client waiting, match them up!
                            found = True
                            clients[client]['partner'] = addr
                            clients[client]['state'] = STATE_MATCHED_TOGETHER
                            clients[addr]['partner'] = client
                            clients[addr]['state'] = STATE_MATCHED_TOGETHER
                            sock.sendto(mplib.urplayertwo, addr)
                            sock.sendto(mplib.playerfound, client)

                    if not found:
                        sock.sendto(mplib.urplayerone, addr)

            elif clients[addr]['state'] == STATE_MATCHED_TOGETHER:
                sock.sendto(msg, clients[addr]['partner'])
    except Exception as e:
        print('{} in {} line {}'.format(
                type(e).__name__,
                __file__,
                e.__traceback__.tb_lineno
            )
        )

