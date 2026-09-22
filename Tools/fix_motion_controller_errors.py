"""Strip broken SteamVR/Nav nodes from unused BP_MotionController."""
import unreal
import cursor_unreal_bridge.blueprint_ops as bo

PATH = '/Game/VirtualRealityBP/Blueprints/BP_MotionController'
BAD = (
    'SteamVR', 'Project Point to Navigation', 'ProjectPointToNavigation',
    'Get Bounds', 'MinAreaRectangle', 'Set Hand', 'Begin Spraying', 'Stop Spraying',
)

bp = unreal.load_asset(PATH)
removed = 0
for graph_name in unreal.BlueprintEditorLibrary.get_all_graph_names(bp) or []:
    try:
        ed, _ = bo._editor_for(bp, graph_name)
    except Exception:
        continue
    for node in list(ed.list_all_nodes() or []):
        title = bo._node_title(node)
        if any(b in title for b in BAD):
            ed.remove_node(node)
            removed += 1

unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.EditorAssetLibrary.save_asset(PATH)
print(f'removed {removed} broken nodes; status={bp.status}')
