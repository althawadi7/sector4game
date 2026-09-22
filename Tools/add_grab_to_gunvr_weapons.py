"""
Add BP_GrabComponent to GunVR weapons so BP_XRPawn can grab them.
Run: py "C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/sector4v2/Tools/add_grab_to_gunvr_weapons.py"
"""
import unreal

WEAPONS = [
    '/Game/Weapons/AK47/Blueprint/Weapon_AK47',
    '/Game/Weapons/UMP45/Blueprint/Weapon_UMP45',
    '/Game/Weapons/Stakeout/Blueprint/Weapon_37Stakeout',
]

grab_cls = unreal.load_asset('/Game/XRFramework/Blueprints/BP_GrabComponent').generated_class()
sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
lib = unreal.SubobjectDataBlueprintFunctionLibrary

for path in WEAPONS:
    bp = unreal.load_asset(path)
    if not bp:
        print('MISSING', path)
        continue
    has_grab = False
    gunmesh_h = None
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        data = sub.k2_find_subobject_data_from_handle(h)
        name = str(lib.get_variable_name(data) or '')
        if 'Grab' in name:
            has_grab = True
        if name == 'GunMesh':
            gunmesh_h = h
    if has_grab:
        print(path, 'skip (grab exists)')
        continue
    if not gunmesh_h:
        print(path, 'no GunMesh parent')
        continue
    params = unreal.AddNewSubobjectParams()
    params.parent_handle = gunmesh_h
    params.new_class = grab_cls
    params.blueprint_context = bp
    new_h, err = sub.add_new_subobject(params)
    print(path, 'added', new_h, err)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(path)
    print(path, 'status', bp.status)

print('DONE')
