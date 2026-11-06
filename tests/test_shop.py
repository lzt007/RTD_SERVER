"""Local shop purchases and replay on explicitly funded disposable accounts."""
import concurrent.futures
import copy
import pathlib
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch
from rtd.common import ProtocolError
from rtd.services.api import API


class ShopTest(unittest.TestCase):
    def test_ap_recovery_keeps_active_battle_and_retries_without_second_charge(self):
        state=self.state()
        state['battle']=dict(quest_id=20842,quest_status=1,quest_continue=0,
                             enemy_info_list=[dict(enemy_id=0,flag=1)])
        state['battle_party_instance_ids']=[1,2,3,4,5,0]
        state['battle_order_token']='frozen-order'
        self.api.store.save(state)
        before=copy.deepcopy(self.state())
        result=self.call('buy_recover_ap')['result']
        after=self.state()
        self.assertEqual(result['action_point'],result['max_action_point'])
        self.assertEqual(result['total_paid_point'],before['player']['total_paid_point']-1)
        self.assertEqual(after['battle'],before['battle'])
        self.assertEqual(after['battle_party_instance_ids'],before['battle_party_instance_ids'])
        self.assertEqual(after['battle_order_token'],before['battle_order_token'])
        self.assertEqual(self.call('buy_recover_ap',api=API(self.path),retry=1)['result'],result)
        self.assertEqual(self.state(),after)

    def test_capacity_purchases_with_retained_battle_keep_snapshot_and_retry(self):
        state=self.state()
        state['battle']=dict(quest_id=20710,quest_status=1)
        state['battle_order_token']='retained-order'
        self.api.store.save(state)
        frozen=copy.deepcopy(self.state()['battle'])
        for operation,field in [('buy_max_unit','max_unit'),('buy_max_friend','max_friend')]:
            before=self.state()
            old=before['player'][field]
            result=self.call(operation,**{field:old})['result']
            self.assertEqual(result[field],old+5)
            after=copy.deepcopy(self.state())
            self.assertEqual(after['battle'],frozen)
            self.assertEqual(after['battle_order_token'],'retained-order')
            self.assertEqual(after['units'],before['units'])
            retry=self.call(operation,api=API(self.path),retry=1,**{field:old})['result']
            self.assertEqual(retry[field],old+5)
            self.assertEqual(self.state(),after)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'shop.sqlite3';self.api=API(self.path)
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=3,user_name='Shop'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        self.player(free_paid_point=2,paid_point=1,total_paid_point=3,
                    action_point=10,action_point_recover=int(time.time()))

    def state(self):return self.api.store.session(self.token)
    def player(self,**kw):
        s=self.state();s['player'].update(kw);self.api.store.save(s)
    def call(self,op,api=None,**kw):
        req=dict(ver='2.4.0',retry=0);req.update(kw)
        return (api or self.api).call(op,req,self.token)
    def error(self,code,op,**kw):
        before=copy.deepcopy(self.state())
        with self.assertRaises(ProtocolError) as e:self.call(op,**kw)
        self.assertEqual(e.exception.args[0],code);self.assertEqual(self.state(),before)

    def test_three_original_operations_dto_free_first_and_exact_effects(self):
        fields={'user_id','user_name','action_point','action_point_recover','max_action_point',
                'game_money','total_paid_point','paid_point','free_paid_point','friend_point',
                'rank','exp','max_unit','max_cost','max_friend','login_days','sequence_login_days'}
        before=self.state();p=self.call('buy_recover_ap')['result']
        self.assertEqual(set(p),fields)
        self.assertEqual((p['action_point'],p['free_paid_point'],p['paid_point'],p['total_paid_point']),
                         (p['max_action_point'],1,1,2))
        p=self.call('buy_max_unit',max_unit='20')['result']
        self.assertEqual((p['max_unit'],p['free_paid_point'],p['paid_point']),(25,0,1))
        p=self.call('buy_max_friend',max_friend='10')['result']
        self.assertEqual((p['max_friend'],p['free_paid_point'],p['paid_point'],p['total_paid_point']),
                         (15,0,0,0))
        self.assertEqual(self.state()['units'],before['units'])
        self.assertEqual(self.state()['player']['game_money'],before['player']['game_money'])

    def test_old_capacity_replay_returns_current_state_after_later_purchase_and_restart(self):
        self.call('buy_max_unit',max_unit='20')
        self.call('buy_max_unit',max_unit='25')
        self.player(game_money=123,action_point=7,action_point_recover=int(time.time()))
        before=self.state();p=self.call('buy_max_unit',api=API(self.path),max_unit=20)['result']
        self.assertEqual((p['max_unit'],p['game_money'],p['action_point'],p['total_paid_point']),
                         (30,123,7,1));self.assertEqual(self.state(),before)
        self.error(8197,'buy_max_unit',max_unit='10')

    def test_ap_network_retry_does_not_charge_or_restore_later_spent_stamina(self):
        self.error(8197,'buy_recover_ap',retry='1')
        self.call('buy_recover_ap')
        self.player(action_point=8,action_point_recover=int(time.time()),game_money=321)
        before=self.state();p=self.call('buy_recover_ap',api=API(self.path),retry='1')['result']
        self.assertEqual((p['action_point'],p['total_paid_point'],p['game_money']),(8,2,321))
        self.assertEqual(self.state(),before)
        self.call('buy_recover_ap');self.assertEqual(self.state()['player']['total_paid_point'],1)

    def test_malformed_capacity_retry_or_currency_never_spends(self):
        for value in (True,0,-1,1.0,None,'020','+20',' 20','20.0','2e1','２０',[],{}):
            with self.subTest(value=value):self.error(8194,'buy_max_unit',max_unit=value)
        for retry in (-1,True,'01','+1',' 1',1.0):
            with self.subTest(retry=retry):self.error(8194,'buy_max_friend',max_friend='10',retry=retry)
        self.player(total_paid_point=9)
        self.error(8197,'buy_max_unit',max_unit=20)

    def test_limits_balance_full_ap_and_active_battle_leave_state_unchanged(self):
        self.player(action_point=self.state()['player']['max_action_point'])
        self.error(9216,'buy_recover_ap')
        self.player(max_unit=1000,max_friend=99)
        self.error(9217,'buy_max_unit',max_unit=1000)
        self.error(9217,'buy_max_friend',max_friend=99)
        self.player(max_friend=95)
        self.assertEqual(self.call('buy_max_friend',max_friend=95)['result']['max_friend'],100)
        self.player(free_paid_point=0,paid_point=0,total_paid_point=0)
        self.error(8961,'buy_max_unit',max_unit=1000)
        s=self.state();s['battle']=dict(quest_id=11000);self.api.store.save(s)
        self.error(8961,'buy_recover_ap')
        self.error(8961,'buy_max_friend',max_friend=100)

    def test_concurrent_expansion_old_capacity_and_ap_buy_charge_once(self):
        other=API(self.path)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda api:self.call('buy_max_unit',api=api,max_unit='20'),[self.api,other]))
        self.assertTrue(all(r['result']['max_unit']==25 for r in results))
        self.assertEqual(self.state()['player']['total_paid_point'],2)
        def buy(api):
            try:return self.call('buy_recover_ap',api=api)['code']
            except ProtocolError as e:return e.args[0]
        with concurrent.futures.ThreadPoolExecutor(2) as pool:codes=list(pool.map(buy,[self.api,other]))
        self.assertEqual(sorted(codes),[4096,9216])
        self.assertEqual(self.state()['player']['total_paid_point'],1)

    def test_save_failure_rolls_back_debit_capacity_and_receipt(self):
        before=self.state();save=self.api.store.save
        def fail(s):save(s);raise RuntimeError('after save')
        with patch.object(self.api.store,'save',side_effect=fail),self.assertRaises(RuntimeError):
            self.call('buy_max_unit',max_unit='20')
        self.assertEqual(self.state(),before)
        self.assertEqual(self.call('buy_max_unit',max_unit='20')['result']['max_unit'],25)


if __name__=='__main__':unittest.main()
