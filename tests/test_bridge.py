import importlib.util,pathlib,unittest
from unittest.mock import patch
R=pathlib.Path(__file__).resolve().parents[1];S=importlib.util.spec_from_file_location("b",R/"bridge"/"tos7_bridge.py");b=importlib.util.module_from_spec(S);S.loader.exec_module(b)
class T(unittest.TestCase):
 def test_name(self):self.assertEqual(b.name("Example App_1"),"Example App_1")
 def test_bad_names(self):
  for x in ("x;id","$(id)","../secret","x|cat"):
   with self.assertRaises(ValueError):b.name(x)
 def test_no_mutators(self):self.assertFalse({"reboot","restart","delete","install","update","poweroff","exec","shell"}.intersection(b.A))
 @patch.object(b,"tos")
 def test_storage(self,m):m.return_value={"ok":True};b.storage({"section":"disks"});m.assert_called_once_with("disk","list","--detail")
 def test_limit(self):
  with self.assertRaises(ValueError):b.logs({"limit":201})
