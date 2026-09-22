"""Activate ground guns — run via UE console: py C:/Users/.../run_activate_ground_guns.py"""
import importlib.util
import unreal

SCRIPT = r"C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/demovr/Tools/activate_ground_guns_demovr.py"

unreal.log("=== RUN ACTIVATE GROUND GUNS ===")
spec = importlib.util.spec_from_file_location("activate_ground_guns_demovr", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if hasattr(module, "RESULT"):
    for line in module.RESULT:
        unreal.log(str(line))
unreal.log("=== FINISHED ===")
