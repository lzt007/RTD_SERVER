"""Local-only purchase settlement. Never contacts a payment provider."""
import base64
import json
import re
from ..config import ROOT
from ..common import ProtocolError

FIELDS=('total_paid_point','paid_point','free_paid_point','payment_total')


def purchase(api,state,req,token,operation):
    config=json.loads((ROOT/'config/simulated-store.json').read_text(encoding='utf-8'))
    if config.get('enabled') is not True:raise ProtocolError(8197,'Simulated purchases are disabled')
    product=req.get('product_id');transaction=req.get('transaction_id')
    if operation in ('google_play_bill_point','app_store_purchase_point'):
        try:
            if operation=='google_play_bill_point':
                receipt=json.loads(req['signedData'])
                product,transaction=receipt['productId'],receipt['orderId']
            else:
                receipt=json.loads(base64.b64decode(req['encoded_receipt'],validate=True))
                product,transaction=receipt['product_id'],receipt['transaction_id']
        except (ValueError,KeyError,TypeError):raise ProtocolError(8194,'Expected a local simulated receipt') from None
    if not isinstance(product,str) or product not in config['products']:
        raise ProtocolError(8194,'Unknown local product')
    if operation.endswith('_begin'):
        return dict(code=4096,session_id=token,result=[])
    if not isinstance(transaction,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}',transaction):
        raise ProtocolError(8194,'Expected a stable local transaction ID')
    offer=config['products'][product]
    if set(offer)!={'paid_point','free_paid_point'} or any(type(n) is not int or not 0<=n<=10000 for n in offer.values()) or not sum(offer.values()):
        raise ProtocolError(8197,'Invalid local product configuration')
    player=state['player']
    if any(type(player[k]) is not int or not 0<=player[k]<=2147483647 for k in FIELDS) or player['total_paid_point']!=player['paid_point']+player['free_paid_point']:
        raise ProtocolError(8197,'Invalid crystal balance')
    receipts=state.setdefault('simulated_purchase_receipts',{})
    old=receipts.get(transaction)
    if old is not None:
        if old!=product:raise ProtocolError(8194,'Transaction ID reused for another product')
    else:
        if player['total_paid_point']+sum(offer.values())>2147483647:raise ProtocolError(8197,'Crystal balance limit')
        for key,value in offer.items():player[key]+=value
        player['total_paid_point']+=sum(offer.values())
        receipts[transaction]=product
        api.store.save(state)
    return dict(code=4096,session_id=token,result={k:player[k] for k in FIELDS})
