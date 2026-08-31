"""Fix BP_GrenadeLauncher HideUnhideHand MotionControllerRef None on barrel grab.

Root cause: grab input reads MotionControllerRef from GrabComponentSnap, but the
player grabs BP_GrabComponent (barrel). Retarget those gets and let only
BP_GrabComponent drive EnableInput/DisableInput.
"""
import unreal
import cursor_unreal_bridge.blueprint_ops as bo

ASSET = '/Game/XRFramework/Blueprints/BP_GrenadeLauncher'
OLD_GETS = (
    'K2Node_VariableGet_0',
    'K2Node_VariableGet_2',
    'K2Node_VariableGet_3',
    'K2Node_VariableGet_6',
)
SNAP_EVENTS = ('K2Node_ComponentBoundEvent_0', 'K2Node_ComponentBoundEvent_1')


def find_node(editor, name):
    for node in editor.list_all_nodes() or []:
        if node.get_name() == name:
            return node
    return None


def find_pin(node, pin_name):
    for pin in bo._bel().list_all_pins(node) or []:
        if str(pin.get_pin_name()) == pin_name:
            return pin
    return None


def main():
    bp = unreal.load_asset(ASSET + '.BP_GrenadeLauncher')
    editor, _ = bo._editor_for(bp, 'EventGraph')
    pinlib = bo._pinlib()
    bel = bo._bel()

    remove_old = []
    for old_name in OLD_GETS:
        old = find_node(editor, old_name)
        if not old or bo._node_title(old) != 'Get GrabComponentSnap':
            continue

        out_old = find_pin(old, 'GrabComponentSnap')
        if not out_old:
            continue

        targets = [
            (cp.get_owning_node(), str(cp.get_pin_name()))
            for cp in (pinlib.list_connected_pins(out_old) or [])
        ]
        pinlib.break_pin_links(out_old)

        pos = bel.get_node_pos(old)
        new = editor.add_get_member_variable_node('BP_GrabComponent')
        bo._set_node_pos(new, pos.x, pos.y)
        out_new = find_pin(new, 'BP_GrabComponent')

        for target_node, target_pin_name in targets:
            target_pin = find_pin(target_node, target_pin_name)
            if target_pin:
                pinlib.try_create_connection(out_new, target_pin)

        remove_old.append(old)

    if remove_old:
        editor.remove_nodes(remove_old)

    for evt_name in SNAP_EVENTS:
        evt = find_node(editor, evt_name)
        if not evt:
            continue
        then_pin = find_pin(evt, 'then')
        if then_pin and pinlib.list_connected_pins(then_pin):
            pinlib.break_pin_links(then_pin)

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset(ASSET)
    print(f'fixed MotionControllerRef grab path; status={bp.status}')


if __name__ == '__main__':
    main()
