"""Place kit guns on VR table — run via py.file in Unreal Python console."""
import unreal

SCRIPT = r"C:/Users/Rashid AlAwadhi/Documents/Unreal Projects/demovr/Tools/add_kit_guns_demovr.py"

unreal.log("=== PLACE KIT GUNS NOW ===")
exec(open(SCRIPT, encoding="utf-8").read(), {"__name__": "__main__"})
if "RESULT" in dir():
    for line in RESULT:
        unreal.log(str(line))
unreal.log("=== DONE PLACE KIT GUNS ===")
