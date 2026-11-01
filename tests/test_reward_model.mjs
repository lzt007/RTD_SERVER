import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {rewardRequestId} from '../rtd/web/admin-model.mjs';
test('HTTP management origins generate unique durable batch IDs without randomUUID',()=>{
 const fallback={getRandomValues:a=>webcrypto.getRandomValues(a)};
 const ids=Array.from({length:100},()=>rewardRequestId(fallback));
 assert.equal(new Set(ids).size,100);
 assert.ok(ids.every(id=>/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$/.test(id)));
});
