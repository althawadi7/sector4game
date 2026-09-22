"""Zombie HP: normal guns 4-10 shots; shotgun+sniper one-shot. Stage2 respawn when <2 alive."""
from __future__ import annotations

import unreal
from cursor_unreal_bridge import blueprint_ops as ops

PAWN = "/Game/Zombie/Blueprints/BP_Zombie_Pawn"
PROJ = "/Game/XRFramework/Blueprints/BP_Projectile"
PVE = "/Game/Sector4/Shared/Gameplay/BP_Stage2_PVE"
SHOTGUN = "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Shotgun"
SNIPER = "/Game/XRFramework/Blueprints/SciFiWeapons/BP_XR_SciFi_Sniper"
ZOMBIE_C = "/Game/Zombie/Blueprints/BP_Zombie_Pawn.BP_Zombie_Pawn_C"
LOG = []


def log(m):
    LOG.append(str(m))
    unreal.log(f"[ZombieHP] {m}")


def load_bp(path: str):
    name = path.rsplit("/", 1)[-1]
    bp = unreal.load_asset(f"{path}.{name}")
    if not bp:
        bp = unreal.EditorAssetLibrary.load_asset(path)
    if not bp:
        raise RuntimeError(f"missing {path}")
    return bp


ops._load_bp = load_bp


def bel():
    return ops._bel()


def pinlib():
    return ops._pinlib()


def find(ed, title=None, title_substr=None, cls=None):
    for n in ed.list_all_nodes() or []:
        t = ops._node_title(n)
        if title and t == title:
            if cls is None or n.get_class().get_name() == cls:
                return n
        if title_substr and title_substr in t:
            if cls is None or n.get_class().get_name() == cls:
                return n
    return None


def find_all(ed, title=None, title_substr=None):
    out = []
    for n in ed.list_all_nodes() or []:
        t = ops._node_title(n)
        if title and t == title:
            out.append(n)
        elif title_substr and title_substr in t:
            out.append(n)
    return out


def pin(n, name):
    if not n:
        return None
    for p in bel().list_all_pins(n) or []:
        if ops._pin_name(p) == name:
            return p
    return None


def connect(a, ap, b, bp):
    pa, pb = pin(a, ap), pin(b, bp)
    if not pa or not pb:
        return f"miss {ap}->{bp}"
    return "ok" if pinlib().try_create_connection(pa, pb) else f"no {ap}->{bp}"


def setv(n, pname, val):
    p = pin(n, pname)
    if not p:
        return f"miss {pname}"
    try:
        pinlib().set_pin_value(p, str(val))
        return "ok"
    except Exception:
        try:
            pinlib().set_pin_default_value(p, str(val))
            return "ok"
        except Exception as e:
            return str(e)


def breakp(n, pname):
    p = pin(n, pname)
    if p:
        try:
            pinlib().break_pin_links(p)
        except Exception:
            pass


def end_pie():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if les.is_in_play_in_editor():
        try:
            les.editor_request_end_play()
        except Exception:
            pass


def save_bp(bp, path):
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    try:
        unreal.EditorAssetLibrary.save_asset(path)
    except Exception:
        unreal.EditorLoadingAndSavingUtils.save_packages([bp.get_package()], True)
    log(("saved", path, str(bp.status)))


def fix_damage_select():
    """Stop MaxHealth/2 one-two-shot: always subtract real Damage."""
    bp = load_bp(PAWN)
    ed, _ = ops._editor_for(bp, "HandleDamageTaken")
    cmp = find(ed, title="float > float")
    if not cmp:
        log("no float>float")
        return
    # Never pick half-health path (A = MaxHealth/2); always use B = Damage
    log(("threshold", setv(cmp, "B", "999999.0")))
    save_bp(bp, PAWN)


def fix_random_hp():
    """BeginPlay: Health = MaxHealth = RandomInteger(4,10) * 3 (matches BulletDamage 3)."""
    bp = load_bp(PAWN)
    ed, _ = ops._editor_for(bp, "EventGraph")

    # Mark existing random HP nodes if re-run
    marker = None
    for n in ed.list_all_nodes() or []:
        if ops._node_title(n) == "PrintString":
            p = pin(n, "InString")
            try:
                v = pinlib().get_pin_value(p) if p else ""
            except Exception:
                v = ""
            if v == "HP_RAND_MARK":
                marker = n
                break
    if marker:
        log("random HP already present")
        return

    begin = find(ed, title="Event BeginPlay")
    init = None
    for n in ed.list_all_nodes() or []:
        if ops._node_title(n) == "InitRunType" and n.get_class().get_name() == "K2Node_CallFunction":
            # the one connected from BeginPlay
            init = n
            break
    if not begin:
        log("no BeginPlay")
        return

    # Insert after BeginPlay: random HP, then original InitRunType
    created = ops.add_blueprint_nodes(
        asset_path=PAWN,
        graph_name="EventGraph",
        nodes=[
            {
                "id": "ri",
                "type": "call",
                "function_path": "/Script/Engine.KismetMathLibrary.RandomIntegerInRange",
                "x": 200,
                "y": -200,
                "pin_defaults": {"Min": "4", "Max": "10"},
            },
            {
                "id": "mul",
                "type": "call",
                "function_path": "/Script/Engine.KismetMathLibrary.Multiply_IntInt",
                "x": 450,
                "y": -200,
                "pin_defaults": {"B": "3"},
            },
            {
                "id": "tof",
                "type": "call",
                "function_path": "/Script/Engine.KismetMathLibrary.Conv_IntToDouble",
                "x": 700,
                "y": -200,
            },
            {"id": "set_max", "type": "palette", "palette": "Variables|Set MaxHealth", "x": 950, "y": -250},
            {"id": "set_hp", "type": "palette", "palette": "Variables|Set Health", "x": 1200, "y": -250},
            {
                "id": "mark",
                "type": "call",
                "function_path": "/Script/Engine.KismetSystemLibrary.PrintString",
                "x": 1450,
                "y": -400,
                "pin_defaults": {
                    "InString": "HP_RAND_MARK",
                    "bPrintToScreen": "false",
                    "bPrintToLog": "false",
                    "Duration": "0.1",
                },
            },
        ],
        compile=False,
        save=False,
    )
    log(("hp_nodes", str(created)[:400]))

    ed, _ = ops._editor_for(bp, "EventGraph")
    ri = find(ed, title="RandomIntegerInRange")
    # Prefer the new one near our mark - get last RandomInteger with Min=4 if possible
    rands = find_all(ed, title="RandomIntegerInRange")
    ri = None
    for n in rands:
        if setv(n, "Min", "4") == "ok" and setv(n, "Max", "10") == "ok":
            # check if connected to Multiply
            p = pin(n, "ReturnValue")
            linked = False
            if p:
                for cp in pinlib().list_connected_pins(p) or []:
                    if "Multiply" in ops._node_title(pinlib().get_owning_node(cp)) or "int * int" in ops._node_title(
                        pinlib().get_owning_node(cp)
                    ):
                        linked = True
                if not linked and not ri:
                    ri = n
            if linked:
                ri = n
                break
    if not ri and rands:
        ri = rands[-1]
        setv(ri, "Min", "4")
        setv(ri, "Max", "10")

    muls = find_all(ed, title_substr="int * int") or find_all(ed, title_substr="Multiply_IntInt")
    mul = muls[-1] if muls else None
    tofs = find_all(ed, title_substr="To Float (Integer)") or find_all(ed, title_substr="Conv_IntToDouble") or find_all(
        ed, title_substr="integer to float"
    )
    tof = tofs[-1] if tofs else None
    set_max = find(ed, title="Set MaxHealth")
    set_hp = find(ed, title="Set Health")
    mark = None
    for n in find_all(ed, title="PrintString"):
        p = pin(n, "InString")
        try:
            v = pinlib().get_pin_value(p) if p else ""
        except Exception:
            v = ""
        if v == "HP_RAND_MARK":
            mark = n
            break

    if mul:
        setv(mul, "B", "3")

    # Rewire BeginPlay -> set_max -> set_hp -> (mark) -> original InitRunType
    breakp(begin, "then")
    wires = []
    if set_max and set_hp and ri and mul and tof:
        wires.append(connect(begin, "then", set_max, "execute"))
        wires.append(connect(ri, "ReturnValue", mul, "A"))
        wires.append(connect(mul, "ReturnValue", tof, "InInt") if pin(tof, "InInt") else connect(mul, "ReturnValue", tof, "In"))
        # try common pin names for to-float
        if "ok" not in wires[-1]:
            for pn in ("InInt", "In", "Value"):
                r = connect(mul, "ReturnValue", tof, pn)
                wires.append(r)
                if r == "ok":
                    break
        out_pin = "ReturnValue"
        wires.append(connect(tof, out_pin, set_max, "MaxHealth"))
        wires.append(connect(set_max, "then", set_hp, "execute"))
        wires.append(connect(tof, out_pin, set_hp, "Health"))
        if mark:
            wires.append(connect(set_hp, "then", mark, "execute"))
            if init:
                wires.append(connect(mark, "then", init, "execute"))
        elif init:
            wires.append(connect(set_hp, "then", init, "execute"))
    else:
        log(("hp_wire_missing", bool(set_max), bool(set_hp), bool(ri), bool(mul), bool(tof), bool(init)))
        # restore begin->init
        if init:
            connect(begin, "then", init, "execute")

    log(("hp_wires", wires))
    save_bp(bp, PAWN)


def fix_oneshot_guns():
    """On PoolActivate: shotgun/sniper set BulletDamage=999; else 3."""
    bp = load_bp(PROJ)
    ed, _ = ops._editor_for(bp, "PoolActivate")

    # Idempotent: look for Set BulletDamage already
    existing = find_all(ed, title="Set BulletDamage")
    if existing:
        log(("oneshot_already", len(existing)))
        # still ensure defaults
        for n in existing:
            setv(n, "BulletDamage", "3")
        return

    entry = find(ed, title="PoolActivate")
    cast_rifle = find(ed, title="Cast To BP_Rifle")
    if not entry or not cast_rifle:
        log("PoolActivate/Cast missing")
        return

    created = ops.add_blueprint_nodes(
        asset_path=PROJ,
        graph_name="PoolActivate",
        nodes=[
            {"id": "own", "type": "call", "function_path": "/Script/Engine.Actor.GetOwner", "x": -200, "y": 400},
            {
                "id": "cs",
                "type": "cast",
                "target_class": SHOTGUN + ".BP_XR_SciFi_Shotgun_C",
                "x": 50,
                "y": 350,
            },
            {
                "id": "cn",
                "type": "cast",
                "target_class": SNIPER + ".BP_XR_SciFi_Sniper_C",
                "x": 50,
                "y": 550,
            },
            {"id": "set_hi1", "type": "palette", "palette": "Variables|Set BulletDamage", "x": 400, "y": 350},
            {"id": "set_hi2", "type": "palette", "palette": "Variables|Set BulletDamage", "x": 400, "y": 550},
            {"id": "set_lo", "type": "palette", "palette": "Variables|Set BulletDamage", "x": 400, "y": 750},
            {
                "id": "seq",
                "type": "call",
                "function_path": "/Script/Engine.KismetMathLibrary.DoNothing",
                "x": -400,
                "y": 200,
            },
        ],
        compile=False,
        save=False,
    )
    log(("oneshot_create", str(created)[:500]))

    # Prefer Sequence node for branching exec
    ed, _ = ops._editor_for(bp, "PoolActivate")
    # Add Sequence via create_node_from_name if needed
    seq = None
    for n in ed.list_all_nodes() or []:
        if n.get_class().get_name() == "K2Node_ExecutionSequence":
            # use a dedicated one - check connections
            seq = n
            break
    if not seq:
        try:
            seq = ed.create_node_from_name("K2Node_ExecutionSequence", unreal.Vector2D(-300, 100))
        except Exception as e:
            log(("seq_fail", str(e)))
            try:
                seq = ed.add_node_to_graph.__func__  # noqa
            except Exception:
                pass

    # Rebuild cleanly with DynamicCast nodes
    # Remove failed DoNothing if any
    for n in list(ed.list_all_nodes() or []):
        if ops._node_title(n) == "DoNothing":
            try:
                ed.remove_nodes([n])
            except Exception:
                pass

    # Ensure Sequence exists
    sequences = [n for n in ed.list_all_nodes() or [] if n.get_class().get_name() == "K2Node_ExecutionSequence"]
    # Don't reuse the velocity Sequence - create new
    try:
        seq = ed.create_node_from_name("K2Node_ExecutionSequence", unreal.Vector2D(-350, 50))
        log(("seq_created", bool(seq)))
    except Exception as e:
        log(("seq_create_err", str(e)))
        seq = sequences[0] if sequences else None

    # Create casts via DynamicCast
    def make_cast(class_path, x, y):
        cls = unreal.load_object(None, class_path)
        if not cls:
            # try generated
            name = class_path.rsplit(".", 1)[-1]
            asset = class_path.split(".")[0]
            bp2 = load_bp(asset) if unreal.EditorAssetLibrary.does_asset_exist(asset) else None
            if bp2:
                cls = unreal.BlueprintEditorLibrary.generated_class(bp2)
        if not cls:
            log(("no_class", class_path))
            return None
        try:
            n = ed.create_node_from_name("K2Node_DynamicCast", unreal.Vector2D(x, y))
            n.set_editor_property("target_type", cls)
            return n
        except Exception as e:
            log(("cast_err", class_path, str(e)))
            return None

    # Clean previous incomplete Set BulletDamage from this run
    sets = find_all(ed, title="Set BulletDamage")
    owners = find_all(ed, title="GetOwner")
    # Keep original GetOwner used by mesh casts (first ones)
    # Add fresh owner for damage
    try:
        own = ed.create_node_from_name("K2Node_CallFunction", unreal.Vector2D(-200, 400))
        # set function GetOwner
        from unreal import EditorUtilityLibrary  # noqa

    except Exception:
        own = None

    # Use add_blueprint_nodes with proper cast type again after clearing bad nodes
    # Remove nodes we just added that aren't wired (Sets with no exec)
    to_remove = []
    for n in ed.list_all_nodes() or []:
        t = ops._node_title(n)
        if t == "Set BulletDamage":
            p = pin(n, "execute")
            linked = bool(p and (pinlib().list_connected_pins(p) or []))
            if not linked:
                to_remove.append(n)
        if t == "GetOwner":
            p = pin(n, "ReturnValue")
            linked = bool(p and (pinlib().list_connected_pins(p) or []))
            # careful not to remove mesh GetOwner
            # mesh GetOwner is connected to Cast Rifle - keep those
            if not linked:
                to_remove.append(n)
    if to_remove:
        try:
            ed.remove_nodes(to_remove)
            log(("removed_orphan", len(to_remove)))
        except Exception as e:
            log(("rm_err", str(e)))

    # Add via ops with cast
    r = ops.add_blueprint_nodes(
        asset_path=PROJ,
        graph_name="PoolActivate",
        nodes=[
            {"id": "own2", "type": "call", "function_path": "/Script/Engine.Actor.GetOwner", "x": -250, "y": 420},
            {
                "id": "cshot",
                "type": "cast",
                "class_path": SHOTGUN,
                "x": 0,
                "y": 320,
            },
            {
                "id": "csnip",
                "type": "cast",
                "class_path": SNIPER,
                "x": 0,
                "y": 520,
            },
            {
                "id": "shi",
                "type": "palette",
                "palette": "Variables|Set BulletDamage",
                "x": 350,
                "y": 320,
                "pin_defaults": {"BulletDamage": "999"},
            },
            {
                "id": "sni",
                "type": "palette",
                "palette": "Variables|Set BulletDamage",
                "x": 350,
                "y": 520,
                "pin_defaults": {"BulletDamage": "999"},
            },
            {
                "id": "slo",
                "type": "palette",
                "palette": "Variables|Set BulletDamage",
                "x": 350,
                "y": 720,
                "pin_defaults": {"BulletDamage": "3"},
            },
        ],
        compile=False,
        save=False,
    )
    log(("oneshot_add2", str(r)[:600]))

    ed, _ = ops._editor_for(bp, "PoolActivate")
    entry = find(ed, title="PoolActivate")
    cast_rifle = find(ed, title="Cast To BP_Rifle")

    # Find new casts
    cshot = find(ed, title_substr="Cast To BP_XR_SciFi_Shotgun") or find(ed, title_substr="SciFi_Shotgun")
    csnip = find(ed, title_substr="Cast To BP_XR_SciFi_Sniper") or find(ed, title_substr="SciFi_Sniper")
    sets = find_all(ed, title="Set BulletDamage")
    # Classify sets by default value
    set_hi = []
    set_lo = []
    for n in sets:
        p = pin(n, "BulletDamage")
        try:
            v = pinlib().get_pin_value(p) if p else ""
        except Exception:
            v = ""
        if str(v) in ("999", "999.0"):
            set_hi.append(n)
        else:
            set_lo.append(n)
            setv(n, "BulletDamage", "3")
    for n in set_hi:
        setv(n, "BulletDamage", "999")

    # GetOwner nodes - pick one connected to new casts or last
    owners = find_all(ed, title="GetOwner")
    own = owners[-1] if owners else None

    # Wire: PoolActivate.then -> CastShotgun; CastFailed->CastSniper; CastFailed->SetLo
    # success paths -> SetHi; all Set*.then -> CastRifle (mesh chain)
    if entry and cast_rifle:
        breakp(entry, "then")
    wires = []
    if cshot and own and cast_rifle:
        wires.append(connect(entry, "then", cshot, "execute"))
        wires.append(connect(own, "ReturnValue", cshot, "Object"))
        if set_hi:
            wires.append(connect(cshot, "then", set_hi[0], "execute"))
            wires.append(connect(set_hi[0], "then", cast_rifle, "execute"))
        if csnip:
            wires.append(connect(cshot, "CastFailed", csnip, "execute"))
            wires.append(connect(own, "ReturnValue", csnip, "Object"))
            if len(set_hi) > 1:
                wires.append(connect(csnip, "then", set_hi[1], "execute"))
                wires.append(connect(set_hi[1], "then", cast_rifle, "execute"))
            elif set_hi:
                wires.append(connect(csnip, "then", set_hi[0], "execute"))
            if set_lo:
                wires.append(connect(csnip, "CastFailed", set_lo[0], "execute"))
                wires.append(connect(set_lo[0], "then", cast_rifle, "execute"))
            else:
                wires.append(connect(csnip, "CastFailed", cast_rifle, "execute"))
        elif set_lo:
            wires.append(connect(cshot, "CastFailed", set_lo[0], "execute"))
            wires.append(connect(set_lo[0], "then", cast_rifle, "execute"))
        else:
            wires.append(connect(cshot, "CastFailed", cast_rifle, "execute"))
    else:
        # fallback: restore mesh chain
        if entry and cast_rifle:
            wires.append(connect(entry, "then", cast_rifle, "execute"))
        log(("oneshot_wire_fallback", bool(cshot), bool(csnip), bool(own), len(set_hi), len(set_lo)))

    log(("oneshot_wires", wires))

    # Ensure CDO default BulletDamage = 3
    gen = unreal.BlueprintEditorLibrary.generated_class(bp)
    cdo = unreal.get_default_object(gen)
    try:
        cdo.set_editor_property("BulletDamage", 3)
        log(("proj_cdo", 3))
    except Exception as e:
        log(("proj_cdo_err", str(e)))

    save_bp(bp, PROJ)


def fix_stage2_respawn():
    """After Stage2 starts: if alive zombies < 2, spawn replacements + ForceAggro."""
    bp = load_bp(PVE)
    ed, _ = ops._editor_for(bp, "EventGraph")

    # Idempotent marker
    for n in find_all(ed, title="PrintString"):
        p = pin(n, "InString")
        try:
            v = pinlib().get_pin_value(p) if p else ""
        except Exception:
            v = ""
        if v == "Stage2: respawn":
            log("respawn already present")
            return

    # Ensure TargetAlive var
    try:
        ops.add_blueprint_variable(asset_path=PVE, var_name="TargetAlive", var_type="int", compile=False, save=False)
    except Exception as e:
        log(("var", str(e)))

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo = unreal.get_default_object(bp.generated_class())
    try:
        cdo.set_editor_property("TargetAlive", 2)
    except Exception:
        pass

    # Find first Branch (!bStarted) - its else should maintain
    tick = find(ed, title="Event Tick")
    branches = find_all(ed, title="Branch")
    br0 = branches[0] if branches else None
    if not tick or not br0:
        log("no tick/branch")
        return

    created = ops.add_blueprint_nodes(
        asset_path=PVE,
        graph_name="EventGraph",
        nodes=[
            {
                "id": "get_all",
                "type": "call",
                "function_path": "/Script/Engine.GameplayStatics.GetAllActorsOfClass",
                "x": 600,
                "y": 900,
                "pin_defaults": {"ActorClass": ZOMBIE_C},
            },
            {
                "id": "len",
                "type": "call",
                "function_path": "/Script/Engine.KismetArrayLibrary.Array_Length",
                "x": 900,
                "y": 900,
            },
            {
                "id": "lt",
                "type": "call",
                "function_path": "/Script/Engine.KismetMathLibrary.Less_IntInt",
                "x": 1150,
                "y": 900,
                "pin_defaults": {"B": "2"},
            },
            {"id": "brm", "type": "branch", "x": 1400, "y": 850},
            {
                "id": "spawn",
                "type": "call",
                "function_path": "/Script/Engine.GameplayStatics.SpawnActorFromClass",
                "x": 1700,
                "y": 850,
                "pin_defaults": {"Class": ZOMBIE_C},
            },
            {
                "id": "self_loc",
                "type": "call",
                "function_path": "/Script/Engine.Actor.K2_GetActorLocation",
                "x": 1400,
                "y": 1100,
            },
            {
                "id": "offset",
                "type": "call",
                "function_path": "/Script/Engine.KismetMathLibrary.Add_VectorVector",
                "x": 1650,
                "y": 1100,
            },
            {
                "id": "mk",
                "type": "call",
                "function_path": "/Script/Engine.KismetMathLibrary.MakeTransform",
                "x": 1900,
                "y": 1100,
            },
            {
                "id": "aggro",
                "type": "call",
                "function_path": "/Game/Zombie/Blueprints/BP_Zombie_Pawn.BP_Zombie_Pawn_C:Event_ForceAggroPlayer",
                "x": 2100,
                "y": 850,
            },
            {
                "id": "print",
                "type": "call",
                "function_path": "/Script/Engine.KismetSystemLibrary.PrintString",
                "x": 2400,
                "y": 850,
                "pin_defaults": {
                    "InString": "Stage2: respawn",
                    "bPrintToScreen": "true",
                    "Duration": "2.0",
                },
            },
        ],
        compile=False,
        save=False,
    )
    log(("respawn_create", str(created)[:500]))

    ed, _ = ops._editor_for(bp, "EventGraph")
    # Re-find
    get_alls = find_all(ed, title="GetAllActorsOfClass")
    # The maintain one should be the second (first is start aggro)
    get_all = get_alls[-1] if get_alls else None
    lens = find_all(ed, title_substr="Length")
    length_n = None
    for n in lens:
        if "Array" in ops._node_title(n) or "Length" in ops._node_title(n):
            length_n = n
    # prefer Array_Length style
    for n in ed.list_all_nodes() or []:
        t = ops._node_title(n)
        if t in ("Length", "Array_Length", "Length (Array)"):
            length_n = n

    lts = find_all(ed, title_substr="int < int") or find_all(ed, title_substr="Less_IntInt")
    lt = lts[-1] if lts else None
    branches = find_all(ed, title="Branch")
    br0 = branches[0]
    brm = branches[-1] if len(branches) > 1 else None
    spawns = find_all(ed, title_substr="SpawnActor")
    spawn = spawns[-1] if spawns else None
    mks = find_all(ed, title="Make Transform") or find_all(ed, title_substr="MakeTransform")
    mk = mks[-1] if mks else None
    locs = find_all(ed, title="Get Actor Location")
    self_loc = locs[-1] if locs else None
    adds = find_all(ed, title="vector + vector") or find_all(ed, title_substr="Add_VectorVector")
    addv = adds[-1] if adds else None
    aggros = find_all(ed, title_substr="ForceAggro")
    aggro = aggros[-1] if aggros else None
    printn = None
    for n in find_all(ed, title="PrintString"):
        p = pin(n, "InString")
        try:
            v = pinlib().get_pin_value(p) if p else ""
        except Exception:
            v = ""
        if v == "Stage2: respawn":
            printn = n
            break

    setv(get_all, "ActorClass", ZOMBIE_C) if get_all else None
    if spawn:
        for pn in ("Class", "ActorClass"):
            if pin(spawn, pn):
                setv(spawn, pn, ZOMBIE_C)
    if lt:
        setv(lt, "B", "2")
    if addv:
        # offset spawn ~200cm forward/right
        setv(addv, "B", "(X=250.000000,Y=150.000000,Z=20.000000)")

    wires = []
    # Branch0.else (started) -> GetAllActors -> Length < 2 -> Branch -> Spawn -> Aggro -> Print
    if br0 and get_all:
        wires.append(connect(br0, "else", get_all, "execute"))
    if get_all and length_n:
        wires.append(connect(get_all, "OutActors", length_n, "TargetArray") if pin(length_n, "TargetArray") else connect(get_all, "OutActors", length_n, "Array"))
        if "ok" not in wires[-1]:
            for pn in ("TargetArray", "Array", "A"):
                r = connect(get_all, "OutActors", length_n, pn)
                wires.append(r)
                if r == "ok":
                    break
    if get_all and brm:
        wires.append(connect(get_all, "then", brm, "execute"))
    if length_n and lt:
        wires.append(connect(length_n, "ReturnValue", lt, "A"))
    if lt and brm:
        wires.append(connect(lt, "ReturnValue", brm, "Condition"))
    if brm and spawn:
        wires.append(connect(brm, "then", spawn, "execute"))
    if self_loc and addv:
        wires.append(connect(self_loc, "ReturnValue", addv, "A"))
    if addv and mk:
        wires.append(connect(addv, "ReturnValue", mk, "Location") if pin(mk, "Location") else connect(addv, "ReturnValue", mk, "InLocation"))
        if "ok" not in wires[-1]:
            for pn in ("Location", "InLocation", "Translation"):
                r = connect(addv, "ReturnValue", mk, pn)
                wires.append(r)
                if r == "ok":
                    break
    if mk and spawn:
        for pn in ("SpawnTransform", "Transform"):
            if pin(spawn, pn):
                wires.append(connect(mk, "ReturnValue", spawn, pn))
                break
    if spawn and aggro:
        wires.append(connect(spawn, "then", aggro, "execute"))
        # self / Target
        for pn in ("self", "Target", "Zombie"):
            if pin(aggro, pn):
                wires.append(connect(spawn, "ReturnValue", aggro, pn))
                break
    if aggro and printn:
        wires.append(connect(aggro, "then", printn, "execute"))
    elif spawn and printn:
        wires.append(connect(spawn, "then", printn, "execute"))

    log(("respawn_wires", wires))
    save_bp(bp, PVE)


def main():
    end_pie()
    fix_damage_select()
    fix_random_hp()
    fix_oneshot_guns()
    fix_stage2_respawn()
    return {"log": LOG[-40:]}


RESULT = main()
