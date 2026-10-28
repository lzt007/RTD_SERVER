# 10001 settlement: bounded evidence (2026-10-25)

This pass only reads existing exported C# and writes this report. Assembly identity inherited from the investigation: SHA256 `c83aea19ee65ae973815daf6a04e430d9e87b8426b6180c1fe507e4260763ecc`. All C# citations below are relative to `analysis/decompiled/`. Static consumer evidence establishes the client contract, not original-server reward validation. No device, service, or server-code action was performed by this worker.

## Confirmed client contract

`CommunicationRTD/ResponseClearQuest2.cs:6-28`: top-level `code`, `session_id`, **array** `result`; each entry contains `user:ComPlayerDataQC`, `present_type:int`, `present_param:int`, `present_param_1:int`, **`get_units:UnitInfo[]`**, `yorisiro_instance_id:ulong`. It is not `UnitData[]`. `CommunicationRTD/UnitInfo.cs:6-32` defines `instance_id,user_id,unit_id,member_id,leader,level,exp,bonus_life,bonus_attack,bonus_heal,bonus_limit,attribute_exp`.

`ComManager.cs:2844-2869` directly accesses first and last result elements; result must be non-null and nonempty. User identity comes from last element, initial displayed balances/rank/exp from first, final clear/new/tutorial flags from last (`2870` also copies tutorial flags). Each result's user values are saved for later result animation (`2914-2930`). `MMResult.cs:1180-1196` eventually replaces player balance/rank/exp/capacity values with those server snapshots. Return coherent complete user snapshots; merely setting present metadata does not provide the resulting account balances.

## get_units must include the granted yorishiro

The clear_quest2 branch calls `ClientData.AddUnits(result[i].get_units)` at `ComManager.cs:2913`, and never separately creates/adds a yorishiro in that branch (`2844-2932`). Contrast legacy clear_quest: after AddUnits it explicitly constructs unit_id=50000, level=1, exp=MMResult.GetYorishiroExp(), instance ID from response, then AddUnit (`2589-2601`). Therefore, if the clear_quest2 settlement grants a yorishiro and expects it immediately in client inventory, it must be represented in get_units alongside granted book units. Supplying yorisiro_instance_id alone is insufficient in this consumer. This is a client-contract inference, not proof all original-server outcomes always award a yorishiro.

`ClientData.cs:946-978` adds UnitInfo array items; `981-1009` shows single-item mapping. `info.exp` is assigned to `UnitData.total_exp` (`997`), and unit master is resolved (`1003`). Distinct nonzero instance IDs and valid unit master IDs matter. Do not return UnitData JSON with only total_exp in place of the UnitInfo exp field.

## Unit experience and level

`MasterDataRTD/UnitData.cs:49-61`: total_exp aliases exp; `cur_exp = total_exp - GetLevelExp(level-1)`. Thus UnitInfo.exp is cumulative unit experience, not experience gained since the current level began. Minimal cumulative experience for an ordinary unit at level L is its previous-level threshold `GetLevelExp(L-1)`; level alone does not uniquely determine exp because progress within that level is possible.

`UnitData.cs:269-277` computes threshold as `(int)(float)(pow(lv, GlobalDefines.UnitParam_NextExp_Per[master.category-1]) * (float)master.grow)` (preserve float conversion/truncation if reproducing precisely); no master yields 0. Exponent array is at `GlobalDefines.cs:418`. This is a formula using unit master category/grow, not a single global level→exp table. For ordinary level-1 book drops, previous-level threshold is GetLevelExp(0), ordinarily zero for positive exponent. This does not imply all level-1 units must have exp=0.

Yorishiro is explicitly exceptional: unit_id==50000 returns total_exp as UnionPoint (`UnitData.cs:280-287`), while ordinary units return master.mix * sqrt(level). Consequently a level-1 yorishiro carrying exp=105 is meaningful; replacing it with ordinary level-1 minimum exp=0 destroys its fusion value. Client request calculation is `floor(pow(partySoul * questMaster.reward_soul,0.65))*15` (`ComManager.cs:1421-1427`), but client submission is not an independent server-authoritative entitlement.

## present_type 3 is display metadata; account reward belongs in server snapshot

`ComManager.cs:2910-2912` stores present metadata. `MMResult.cs:742-760` opens/closes the reward dialog; `DialogQuestClearReward.cs:27-65`, especially `42-44`, shows type 3 selects the stone sprite and formats the amount. It does not increment balance, AddUnit, or call a reward-claim network operation. `MMResult.SetPlayerData` copies total_paid_point/paid_point/free_paid_point from settlement snapshots (`1186-1188`).

Therefore, within this traced settlement flow, if first-clear type 3 grants a stone, server settlement must already persist it and include the post-grant account point values. Returning only present_type=3/present_param=1 can display a reward without crediting it. The static evidence does not prove which 10001 completion qualifies, whether the reward is tied to quest/category first-clear state, or the original server's paid/free allocation. Those must be established from master configuration plus account transition evidence. No new reward-claim endpoint should be invented from this dialog.

## Rank flags / narrow accepted 10001 case

No `rankflags`, `rank_flags`, or `rankFlags` field was found in the bounded exported-C# search used here; inspected RequestClearQuest2 and ComPlayerDataQC expose no field under those names. If “rankflags2” names a master/configuration reward flag, its bit interpretation and original-server effect remain **unknown in this report**. A rank-2 response or UI transition alone does not establish its flag semantics, AP refill policy, or a generally applicable rank formula. Do not relabel an unproven flag as an automatic grant rule.

Runtime evidence supplied by the primary executor (not independently replayed by this worker): real 10001 completion submitted exp=50, money=500, yorisiro_exp=105, book units 10020/10023 at level 1, and six party_instance_id slots. Primary executor reports 15 passing tests, repeat/restart idempotence checks, and diagnostic settlement replay resulting in rank=2, account exp=100, AP=21, stone=1. These observations support that specific implementation/account case; they are not observations of the retired original server.

The narrow verifiable rule is to validate this exact completion against known account/quest state; return one coherent nonempty settlement array entry, full post-settlement user snapshot, UnitInfo records for the two validated drops plus awarded yorishiro with cumulative exp=105, and first-clear presentation only when the server actually commits the corresponding reward once. Accept the observed six-slot party shape rather than assuming the older five-slot save format. Preserve replay/restart idempotence for the tested operation identity. Generalizing drop eligibility, rank thresholds/AP refill, first-clear flags/reward allocation, arbitrary soul/exp submissions, and alternate party shapes requires more evidence; this report intentionally does not expand that investigation.
