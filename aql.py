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
q('POST', '/_db/pimona/_api/collection', name='chatlog', waitForSync=True, raise_error=False)

# mm hmm
def aql(query, **bv):
    resp = q(
        'POST', '/_db/pimona/_api/cursor',
        query = query,
        batchSize = 1000,
        bindVars = bv,
    )
    return resp['result']

if __name__ == '__main__':
    a = aql('for u in chatlog return @k', k={'a':'b'})
    print(a)
