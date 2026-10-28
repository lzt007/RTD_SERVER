import copy
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch
from rtd.common import ProtocolError
from rtd.services.api import API


class ProfileTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'profile.sqlite3';self.api=API(self.path)
        self.tokens=[]
        for name in ('Original','Peer'):
            key=str(uuid.uuid4())
            self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name=name))
            self.tokens.append(self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id'])

    def state(self):return self.api.store.session(self.tokens[0])
    def rename(self,name,retry='0'):
        return self.api.call('change_user_name',dict(ver='2.4.0',retry=retry,user_name=name),self.tokens[0])

    def test_original_empty_array_response_only_changes_name_and_survives_restart(self):
        for name in ('LocalRevived','復活ドラゴン','复活之路'):
            before=self.state();result=self.rename(name)
            expected=copy.deepcopy(before);expected['player']['user_name']=name
            self.assertEqual(self.state(),expected)
            self.assertEqual(result,dict(code=4096,session_id=self.tokens[0],result=[]))
            self.assertEqual(self.rename(name,retry='1'),result)
            self.assertEqual(self.state(),expected)
            self.api=API(self.path);self.assertEqual(self.state(),expected)

    def test_current_friend_search_and_list_read_renamed_profile(self):
        self.api.call('send_friend_request',dict(ver='2.4.0',friend_user_id='2'),self.tokens[0])
        self.api.call('accept_friend_request',dict(ver='2.4.0',friend_user_id=[1]),self.tokens[1])
        self.rename('LocalRevived')
        search=self.api.call('select_user_code',dict(ver='2.4.0',user_id=1),self.tokens[1])['result']
        friends=self.api.call('get_friends',dict(ver='2.4.0'),self.tokens[1])['result']
        self.assertEqual(search['user_name'],'LocalRevived')
        self.assertEqual(friends[0]['user_name'],'LocalRevived')

    def test_invalid_names_are_original_ng_name_and_atomic(self):
        for name in ('','   ','a'*33,'a\nb','a\x00b','\ud800',None,[],4,True):
            before=self.state()
            with self.subTest(name=repr(name)),self.assertRaises(ProtocolError) as error:self.rename(name)
            self.assertEqual(error.exception.code,8448)
            self.assertEqual(self.state(),before)
        self.rename('a'*32)
        self.assertEqual(self.state()['player']['user_name'],'a'*32)

    def test_write_failure_rolls_back_and_unsupported_migration_stays_explicit(self):
        before=self.state();save=self.api.store.save
        def fail(state):save(state);raise RuntimeError('injected rename failure')
        with patch.object(self.api.store,'save',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'injected rename failure'):self.rename('NewName')
        self.assertEqual(self.state(),before)
        for operation in ('make_password','move_save_data','accept_invite_usercode'):
            with self.assertRaises(ProtocolError) as error:
                self.api.call(operation,dict(ver='2.4.0'),self.tokens[0])
            self.assertEqual(error.exception.code,8197);self.assertEqual(self.state(),before)


if __name__=='__main__':unittest.main()
