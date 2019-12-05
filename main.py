import requests as r
import traceback, time, sys

from colors import colored_print_generator as cpg

from aql import aql

import re

import random

print_info = cpg('green',)
print_debug = cpg('yellow')
print_up = cpg('yellow', attrs=['bold'])
print_down = cpg('cyan', attrs=['bold'])
print_err = cpg('red', attrs=['bold'])

class bot:
    def __init__(self, token, proxies):
        self.token = token
        self.offset = 0
        self.proxies = proxies

        self.to_be_deleted = {}
        self.async_queue = {}

    def async_do(self, f, t):
        asq = self.async_queue
        asq[t] = f
        print_debug('async_queue length:', len(asq))

    def async_update(self):
        asq = self.async_queue
        now = time.time()

        remove_list = []

        for t in asq:
            if now>t:
                f = asq[t]
                f()
                remove_list.append(t)

        for t in remove_list:
            del asq[t]

        if len(remove_list):
            print_debug('async_queue length:', len(asq))

    def query(self, endp, **kw):
        print_up('UP >>', endp, kw)
        while 1:
            try:
                resp = r.request(
                    'POST',
                    'https://api.telegram.org/bot' + self.token + endp,
                    json = kw,
                    timeout=30,
                    proxies = proxies,
                ).json()
            except r.exceptions.Timeout as e:
                print_err('Timeout, retry...')
            except r.exceptions.SSLError as e: # common as we're in fucking China
                print_err('SSLError', e)
            except r.exceptions.ProxyError as e: # common as we're in fucking China
                print_err('ProxyError', e)
            except r.exceptions.ConnectionError as e:
                print_err('ConnError', e)
            except KeyboardInterrupt as e:
                sys.exit()
            except:
                traceback.print_exc()
            else:
                if 'ok' in resp:
                    if resp['ok']:
                        result = resp['result']
                        break
                    else:
                        print_err('response not ok')
                        continue
                else:
                    print_err('field ok not in response json')
                    continue
        print_down('DN <<', result)
        return result

    def who_am_i(self):
        print_info('Getting bot info...')
        res = self.query('/getMe')
        self.username = res['username']
        print_info('username of this instance is @'+ self.username)
        print_info('Ready.')

    def get_updates(self):
        result = self.query('/getUpdates',
            offset = self.offset,
            limit = 100,
            timeout = 120, # 0 for short polling
        )

        # increment offset cntr if anything came in
        if len(result)>0:
            latest_offset = result[-1]['update_id']
            self.offset = latest_offset+1
        else:
            pass # nothing came in

        return result

    def send_message(self,
            chat_id, text,
            reply_id=None,
            silent=False,

            vanish=None,
        ):

        if vanish is not None:
            text += '\n[\u23f1{:d}s]'.format(vanish)

        result = self.query('/sendMessage',
            chat_id = chat_id,
            text = text,
            reply_to_message_id = reply_id,
            disable_notification = silent,
        )
        print_info('sent: (to){}: {}'.format(chat_id, text.replace('\n',' ')))

        if vanish is not None:
            # initiate a timed message
            now = time.time()
            date = result['date']

            # there will be timeshift between server and client

            mid = result['message_id']
            cid = result['chat']['id']
            self.del_message_after(cid, mid, now + vanish)

        return result

    def del_message(self, cid, mid):
        result = self.query('/deleteMessage',
            chat_id=cid,
            message_id = mid,
        )
        return result

    def del_message_after(self, cid, mid, t):
        def delete():
            self.del_message(cid, mid)
        self.async_do(delete, t)

    def eat_updates(self):
        updates = self.get_updates()
        for u in updates:
            self.on_update(u)

    def on_update(self, u):
        print_down('UPDATE:', u)
        if 'message' in u:
            message = u['message']
            self.on_message(message)
        else:
            pass

    def on_message(self, msg):

        # has text?
        if 'text' in msg:
            self.on_text_message(msg)
        else:
            pass

    def on_text_message(self, msg):
        cid = msg['chat']['id']
        mid = msg['message_id']
        fr = msg['from'] # user obj
        firstname = fr['first_name']
        uname = fr['username']
        text = msg['text']

        print_info('recv: (from)@{}: {}'.format(uname, text))

        # bot should only respond to messages that starts with a slash
        regex = r"^\/([a-z]+)\ (.*)"
        match = re.match(regex, text)
        if match is None:
            self.send_message(cid,
                'Sorry, but commands should look like "/<cmd> [params]".',
                reply_id=mid,
                vanish=10,
            )
        else:
            cmd, param = match.group(1,2)
            self.send_message(
                cid,
                'my designer is so lazy, he didn\'t teach me what "{}" and "{}" means.'.format(cmd, param),
                reply_id = mid,
                vanish = 30,
            )

from creds import token, proxies

b = bot(token, proxies)
b.who_am_i()

from threading import Thread
def q_clearer():
    while 1:
        b.async_update()
        time.sleep(0.5)

t = Thread(target=q_clearer, daemon=True)
t.start()

while 1:
    b.eat_updates()
