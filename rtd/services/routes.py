from . import accounts, units, quests, rewards, social, masters, unit_sale, unit_compose, unit_evolve
from . import presents, challenge_rewards, shop, gacha, unit_gifts, battle_continue

from . import special_units

from . import simulated_store

ROUTES = {
    'sp_compose_unit': special_units.sp_compose_unit,
    'ultimate_evolve': unit_evolve.evolve_unit,
    'change_user_name': accounts.change_user_name,
    'continue_quest': battle_continue.continue_quest,
    'buy_recover_ap': shop.purchase,
    'buy_max_unit': shop.purchase,
    'buy_max_friend': shop.purchase,
    'open_present': presents.open_present,
    'post_quest_challenge_reward': challenge_rewards.post_quest_challenge_reward,
    'evolve_unit': unit_evolve.evolve_unit,
    'compose_unit': unit_compose.compose_unit,
    'sale_unit': unit_sale.sale_unit,
    'login': accounts.login,
    'get_units': units.get_units,
    'get_quest_info': quests.get_quest_info,
    'get_helpers': quests.get_helpers,
    'clear_quest': quests.clear_quest,
    'clear_quest2': quests.clear_quest,
    'buy_gacha': gacha.purchase,
    'buy_gacha_special': gacha.purchase,
    'simulate_purchase': simulated_store.purchase,
    'google_play_bill_begin': simulated_store.purchase,
    'google_play_bill_point': simulated_store.purchase,
    'app_store_purchase_begin': simulated_store.purchase,
    'app_store_purchase_point': simulated_store.purchase,
    'get_friends': social.get_friends,
    'select_user_code': social.search,
    'send_friend_request': social.relation,
    'accept_friend_request': social.relation,
    'delete_friend': social.relation,
    'send_present': unit_gifts.send,
    'get_presents': presents.get_presents,
    'save_unit_favorite_flags': units.save_unit_favorite_flags,
    'save_quest_new_flags': quests.save_quest_new_flags,
    'get_level_master': masters.get_level_master,
    'order_quest': quests.order_quest,
    'form_units': units.form_units,
    'save_local_flags': units.save_local_flags,
    'get_master': masters.get_master,
}
