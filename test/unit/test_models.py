from datetime import datetime

from enums import AttackTypeEnum, PeriodType
from models import ClanBattleBossBook, ClanBattlePeriod, ServiceResult


def test_enum_serializer_mixin():
    model = ClanBattleBossBook(
        guild_id=1,
        attack_type="PATK",
    )
    db_dict = model.to_db_dict()
    assert db_dict["attack_type"] == "PATK"

    model = ClanBattleBossBook(
        guild_id=1,
        attack_type=AttackTypeEnum.PATK,
    )
    db_dict = model.to_db_dict()
    assert db_dict["attack_type"] == "PATK"

    model = ClanBattlePeriod(period_type="LIVE")
    db_dict = model.to_db_dict()
    assert db_dict["period_type"] == "LIVE"

    model = ClanBattlePeriod(period_type=PeriodType.LIVE)
    db_dict = model.to_db_dict()
    assert db_dict["period_type"] == "LIVE"


def test_clan_battle_period_merge():

    main = ClanBattlePeriod()
    class_merge = ClanBattlePeriod(
        boss1_id=1,
        boss2_id=2,
        boss3_id=3,
        boss4_id=4,
        boss5_id=5,
    )

    main.merge_bosses(class_merge)
    assert main.boss1_id == class_merge.boss1_id
    assert main.boss2_id == class_merge.boss2_id
    assert main.boss3_id == class_merge.boss3_id
    assert main.boss4_id == class_merge.boss4_id
    assert main.boss5_id == class_merge.boss5_id

    main = ClanBattlePeriod()
    dict_merge = {
        "boss1_id": 1,
        "boss2_id": 2,
        "boss3_id": 3,
        "boss4_id": 4,
        "boss5_id": 5,
    }
    main.merge_bosses(dict_merge)
    assert main.boss1_id == dict_merge["boss1_id"]
    assert main.boss2_id == dict_merge["boss2_id"]
    assert main.boss3_id == dict_merge["boss3_id"]
    assert main.boss4_id == dict_merge["boss4_id"]
    assert main.boss5_id == dict_merge["boss5_id"]


def test_service_result():
    service_result = ServiceResult[bool]()

    service_result.set_success(True)
    assert service_result.is_success == True
    assert service_result.error_messages is None
    assert service_result.result == True

    service_result = ServiceResult[bool]()
    service_result.set_error("Error")
    assert service_result.is_success == False
    assert service_result.error_messages == "Error"
    assert service_result.result is None
