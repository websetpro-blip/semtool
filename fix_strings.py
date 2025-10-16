import ast
from pathlib import Path

BAD_MARKERS = {'Ð', 'Ñ', 'Ò', 'Â', 'Ã', 'Ê', 'Ì', 'È', 'Ë', 'Ô', 'Þ', 'Ý'}

class MojibakeFixer(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str):
            candidate = self._fix(node.value)
            if candidate != node.value:
                node = ast.copy_location(ast.Constant(value=candidate), node)
        return node

    def _fix(self, value: str) -> str:
        try:
            converted = value.encode('cp1251').decode('utf-8')
        except UnicodeEncodeError:
            return value
        except UnicodeDecodeError:
            return value
        if any(ch in BAD_MARKERS for ch in converted):
            return value
        # also check if original seems mojibake: look for sequences like 'Р' followed by ' ' or 'С'
        suspicious = any(ord(ch) in range(0x400, 0x460) and ch not in 'Ёё' for ch in value)
        if not suspicious:
            return value
        return converted

for rel_path in ['app/accounts_tab_extended.py', 'app/keys_panel.py']:
    path = Path(rel_path)
    source = path.read_text(encoding='utf-8')
    tree = ast.parse(source)
    fixer = MojibakeFixer()
    new_tree = fixer.visit(tree)
    ast.fix_missing_locations(new_tree)
    new_code = ast.unparse(new_tree)
    if source != new_code:
        path.write_text(new_code, encoding='utf-8')
        print(f'Updated {rel_path}')
    else:
        print(f'No change for {rel_path}')
