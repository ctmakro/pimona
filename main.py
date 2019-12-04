import requests as r
import traceback, time, sys

class bot:
    def __init__(self, token):
        self.token = token
        self.offset = 0

    def query(self, endp, dict={}, **kw):
        dict.update(kw)
        while 1:
            try:
                resp = r.request(
                    'POST',
                    'https://api.telegram.org/bot' + self.token + endp,
                    json = dict,
                    timeout=60,
                ).json()
            except r.exceptions.Timeout as e:
                print('Timeout, retry...')
            except r.exceptions.SSLError as e: # common as we're in fucking China
                print('SSLError', e)
            except r.exceptions.ProxyError as e: # common as we're in fucking China
                print('ProxyError', e)
            except KeyboardInterrupt as e:
                sys.exit()
            except:
                traceback.print_exc()
            else:
                if 'ok' in resp:
                    if resp['ok']:
                        result = resp['result']
                        return result
                    else:
                        print('response not ok')
                        continue
                else:
                    print('field ok not in response json')
                    continue

    def who_am_i(self):
        print('Getting bot info...')
        res = self.query('/getMe')
        print(res)
        print('Ready.')

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

    def send_message(self, chat_id, text, reply_id=None):
        self.query('/sendMessage',
            chat_id = chat_id,
            text = text,
            reply_to_message_id = reply_id,
        )
        print('sent: (to){}: {}'.format(chat_id, text.replace('\n',' ')))

    def eat_updates(self):
        updates = self.get_updates()
        for u in updates:
            self.on_update(u)

    def on_update(self, u):
        if 'message' in u:
            message = u['message']
            self.on_message(message)
        else:
            print(u)

    def on_message(self, msg):
        cid = msg['chat']['id']
        mid = msg['message_id']
        fr = msg['from'] # user obj
        firstname = fr['first_name']
        uname = fr['username']
        text = msg['text']

        print('recv: {}: {}'.format(uname, text))

        self.send_message(
            cid,
            'Okay, {}. Let me repeat, you just said:\n{}'.format(firstname, text.replace('\n',' ')),
            reply_id=mid,
        )

    def on_chat_msg(self, msg):
        pass

from creds import token

b = bot(token)
b.who_am_i()
while 1:
    b.eat_updates()
