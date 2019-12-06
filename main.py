import requests as r
import traceback, time, sys

from colors import prettify as pfy
from colors import *

import re
import random

from threading import Lock

print_info('init connection to ArangoDB...')
from aql import aql

class bot:
    def __init__(self, token, proxies):
        self.token = token
        self.offset = 0
        self.proxies = proxies

        self.to_be_deleted = {}
        # self.async_queue = {}
        # self.ql = Lock()

    def aql_queue_append(self, t, endp, **kw):
        aql('insert @k into queue', k={
            't':t,
            'operation':endp,
            'params':kw,
        })

    def aql_queue_update(self):
        # get expiring(to be executed) queue items
        res = aql('for i in queue filter @now > i.t return i', now=time.time(), silent=True)

        if len(res):
            print_debug('aql_queue length:', len(res))

        for i in res:
            # execute
            self.aql_queue_execute(i)
            # discard
            aql('for i in queue filter i._id == @k remove i in queue', k=i['_id'])

    def aql_queue_execute(self, item):
        endp = item['operation']
        kw = item['params']
        result = self.query(endp, **kw)

    def query(self, endp, **kw):
        print_up('TELEGRAM >>', endp,'\n'+ pfy(kw))

        def denone(d):
            a = []
            for k in d:
                if d[k] is None:
                    a.append(k)
            for k in a:
                del d[k]

        denone(kw)

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
                        print_err('response not ok', resp)
                        result = {}
                        break
                else:
                    print_err('field ok not in response json')
                    continue
        print_down('TELEGRAM <<', '\n'+pfy(result))
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
            markup=None,
        ):

        result = self.query('/sendMessage',
            chat_id = chat_id,
            text = text,
            reply_to_message_id = reply_id,
            disable_notification = silent,
            reply_markup=markup
        )
        print_info('sent: (to){}: {}'.format(chat_id, text.replace('\n',' ')))
        return result

    def del_message_after(self, cid, mid, t):
        self.aql_queue_append(t, '/deleteMessage',
            chat_id=cid,
            message_id=mid,
        )

    def eat_updates(self):
        updates = self.get_updates()
        for u in updates:
            self.on_update(u)

    def on_update(self, u):
        print_info('UPDATE:', '\n'+pfy(u))
        if 'message' in u:
            message = u['message']
            self.on_message(message)
        elif 'callback_query' in u:
            query = u['callback_query']
            self.on_callback(query)
        else:
            pass

    # receive a callback (user clicked a button)
    def on_callback(self, query):
        data = query['data'] # data from that button
        uid = query['from']['id'] # uid who clicked the button
        uname = query['from']['username']
        cbid = query['id'] # cbid of this callback

        cid = query['message']['chat']['id']

        print_info('callback: (from)@{}({}): {}'. format(uname, uid, data))

        self.aql_queue_append(0, '/answerCallbackQuery',
            callback_query_id = cbid,
            text = 'ok, i see {} clicked {}'.format(uname,data),
            show_alert=False,
        )

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
        # (contains commands)

        # # test if 'entities' exist
        # if 'entities' in 'msg':
        #     cmds = {}
        #     last = 0
        #     entities = msg['entities']
        #     for e in entities:
        #         if e['type'] == 'bot_command':
        #             offset = e['offset']
        #             length = e['length']

        regex = r"^\/([a-z]+)(\ ?.*)"
        match = re.match(regex, text)
        if match is None:
            return # no response should be made
            response = {'text':'Sorry, but commands should look like "/<cmd> [params]".'}
        else:
            cmd, param = match.group(1,2)
            response = self.get_response(cmd, param)

        result = self.send_message(
            cid,
            response['text'] + tail,
            reply_id=mid,
            silent=True,
            markup = response['markup'] if 'markup' in response else None
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
        response = {}
        def t(s):response['text'] = s

        if cmd == 'boxes':
            response['markup'] = {
                'inline_keyboard': [[
                    {'text':'1', 'callback_data':'1'},
                    {'text':'4', 'callback_data':'3'},
                    {'text':'7', 'callback_data':'5'},
                ]]
            }
            t('this is a box test.')
        elif cmd == 'help':
            t('help what? I\'m busy right now')
        elif cmd == 'warn':
            t('I know how much you want to use this, but this is yet to be implemented.')
        else:
            t('my designer is so lazy, he hasn\'t teach me what "{}" means yet.'.format(cmd))

        return response


from creds import token, proxies

b = bot(token, proxies)
b.who_am_i()

from threading import Thread
def q_clearer():
    while 1:
        b.aql_queue_update()
        time.sleep(0.1)
Thread(target=q_clearer, daemon=True).start()

while 1:
    b.eat_updates()
