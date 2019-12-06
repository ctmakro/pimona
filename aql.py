from colors import colored_print_generator as cpg, prettify as pfy
from colors import *

import requests as r

dburl = 'http://127.0.0.1:8529'

def q(method,endp,raise_error=True,**kw):
    resp = r.request(
        method,
        dburl + endp,
        auth = r.auth.HTTPBasicAuth('root',''),
        json = kw,
        timeout=10,
        proxies = {},
    ).json()
    if resp['error'] == False:
        return resp
    else:
        if not raise_error:
            print(str(resp))
        else:
            raise Exception(str(resp))

# create database.
q('POST', '/_api/database', name='pimona', raise_error=False)

# create collections.
def cc(name):
    q('POST', '/_db/pimona/_api/collection',
    name=name, waitForSync=True, raise_error=False)

cc('chatlog')
cc('queue')

# mm hmm
def aql(query, silent=False, **bv):
    if not silent: print_up('AQL >>\n'+query,bv)
    resp = q(
        'POST', '/_db/pimona/_api/cursor',
        query = query,
        batchSize = 1000,
        bindVars = bv,
    )
    res = resp['result']
    if not silent: print_down('AQL <<\n', str(res))
    return res

if __name__ == '__main__':
    aql('insert {a:1} into queue')
    a = aql('for u in queue return u')

    aql('for u in queue filter u.a==1 remove u in queue')
    a = aql('for u in queue return u')

    print(a)
