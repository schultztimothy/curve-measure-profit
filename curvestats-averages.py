#!/usr/bin/env python3

import lmdb
import json

DB_NAME = 'curvestats.lmdb'  # <- DB [block][pool#]{...}
START_BLOCK = 9554041
TICKS = [1, 5, 10, 30]  # min

summarized_data = {}
db = lmdb.open(DB_NAME)
db.set_mapsize(2 ** 29)


def int2uid(value):
    return int.to_bytes(value, 4, 'big')


def get_block(b):
    with db.begin(write=False) as tx:
        obj = tx.get(int2uid(b))
        if not obj:
            return False
        return json.loads(obj)


if __name__ == "__main__":
    b = START_BLOCK
    decimals = {
            'compound': [18, 6, 6],
            'usdt': [18, 6, 6],
            'y': [18, 6, 6, 18],
            'busd': [18, 6, 6, 18]
    }
    while True:
        block = get_block(b)
        if not block:
            break

        for pool in block:
            if pool not in summarized_data:
                summarized_data[pool] = {}

            for tick in TICKS:
                ts = block[pool]['timestamp'] // (tick * 60) * (tick * 60)
                if tick not in summarized_data[pool]:
                    summarized_data[pool][tick] = {}
                if ts not in summarized_data[pool][tick]:
                    summarized_data[pool][tick][ts] = {}
                obj = block[pool].copy()
                obj['volume'] = summarized_data[pool][tick][ts].get('volume', {})
                obj['prices'] = summarized_data[pool][tick][ts].get('prices', {})
                for t in obj['trades']:
                    pair = sorted([(t['sold_id'], t['tokens_sold']), (t['bought_id'], t['tokens_bought'])])
                    pair, tokens = list(zip(*pair))  # (id1, id2), (vol1, vol2)
                    jpair = '{}-{}'.format(*pair)
                    t0 = tokens[0] * 10 ** (18 - decimals[pool][pair[0]])
                    t1 = tokens[1] * 10 ** (18 - decimals[pool][pair[1]])
                    if t1 > 0:
                        price = t1 / t0
                        if jpair not in obj['prices']:
                            obj['prices'][jpair] = []
                        obj['prices'][jpair].append(price)
                    if jpair in obj['volume']:
                        obj['volume'][jpair] = (obj['volume'][jpair][0] + tokens[0]), (obj['volume'][jpair][1] + tokens[1])
                    else:
                        obj['volume'][jpair] = tokens
                del obj['trades']
                summarized_data[pool][tick][ts] = obj

        b += 1

    for pool in summarized_data:
        for t in summarized_data[pool]:
            data = list(summarized_data[pool][t].values())[-1000:]
            with open(f'json/{pool}-{t}m.json', 'w') as f:
                json.dump(data, f)
