"""Protect names used by the engine's descendant-based ScrollView lookup."""
import unittest
from build_menu import settings_content, dropdown_content, CATALOG


class ScrollContentTests(unittest.TestCase):
    def test_content_cannot_shadow_native_scroll_parts(self):
        # common.scroll_view_control locates these controls by name, not by
        # an absolute path. A same-named Image can cause a native type error.
        reserved = {'track','box','scrolling_content','scrolling_view_port','bar_and_track'}

        def check(node):
            for child in node.get('controls',[]):
                for name,definition in child.items():
                    self.assertNotIn(name.split('@')[0],reserved)
                    check(definition)

        check(settings_content())
        for entries in CATALOG['ENTRIES'].values():
            check(dropdown_content(entries))


if __name__ == '__main__':
    unittest.main()
