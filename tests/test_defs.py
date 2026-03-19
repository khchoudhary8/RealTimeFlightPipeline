from dagster_app import defs

def test_defs_can_load():
    assert defs.defs
    assert len(defs.defs.assets) > 0
    assert "silver_flights" in [key.to_user_string() for key in defs.defs.get_repository_def().get_all_asset_keys()]
