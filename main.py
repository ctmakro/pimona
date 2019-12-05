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

from threading import Lock

class bot:
    def __init__(self, token, proxies):
        self.token = token
        self.offset = 0
        self.proxies = proxies

        self.to_be_deleted = {}
        self.async_queue = {}
        self.ql = Lock()

    def async_do(self, f, t):
        asq = self.async_queue
        while t in asq:
            t+=1
        self.ql.acquire()
        asq[t] = f
        self.ql.release()
        print_debug('async_queue length:', len(asq))

    def async_update(self):
        asq = self.async_queue
        now = time.time()

        rl = remove_list = []

        self.ql.acquire()
        for t in asq:
            if now>t:
                rl.append(t)
        self.ql.release()

        for t in rl:
            f = asq[t]
            f()

        for t in rl:
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
                        result = {}
                        break
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
        ):

        result = self.query('/sendMessage',
            chat_id = chat_id,
            text = text,
            reply_to_message_id = reply_id,
            disable_notification = silent,
        )
        print_info('sent: (to){}: {}'.format(chat_id, text.replace('\n',' ')))

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

        # bot messages should vanish after a certain period of time
        vanish = 20 # seconds
        tail = '\n[\u23f1{:d}s]'.format(vanish)

        # bot should only respond to messages that starts with a slash
        regex = r"^\/([a-z]+)(\ ?.*)"
        match = re.match(regex, text)
        if match is None:
            return # no response should be made
            response = 'Sorry, but commands should look like "/<cmd> [params]".'
        else:
            cmd, param = match.group(1,2)
            response = self.get_response(cmd, param)

        result = self.send_message(
            cid,
            response + tail,
            reply_id=mid,
            silent=True,
        )

        vanish += time.time()
        # date = result['date']
        res_mid = result['message_id']
        res_cid = result['chat']['id']

        # delete the asking message
        self.del_message_after(cid, mid, vanish)

        # delete the response message to prevent polluting the group
        self.del_message_after(res_cid, res_mid, vanish)

    def get_response(self, cmd, param):
        if not hasattr(self, 'qatable'):
            self.qatable = {
                'help':lambda x: 'help what? I\'m busy right now',
                'warn':lambda x: 'I know how much you want to use this, but this is yet to be implemented.',
            }

        qt = self.qatable

        if cmd in qt:
            return qt[cmd](param)
        else:
            return 'my designer is so lazy, he hasn\'t teach me what "{}" means yet.'.format(cmd)

from creds import token, proxies

b = bot(token, proxies)
b.who_am_i()

from threading import Thread
def q_clearer():
    while 1:
        b.async_update()
        time.sleep(0.5)
Thread(target=q_clearer, daemon=True).start()

while 1:
    b.eat_updates()
