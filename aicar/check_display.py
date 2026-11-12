"""하드웨어 없이 실제 마우스 콜백 검사: python3 check_display.py"""

import ast
from pathlib import Path
from types import SimpleNamespace


source = ast.parse(Path(__file__).with_name('gi.py').read_text(encoding='utf-8-sig'))
callback = next(node for node in source.body
                if isinstance(node, ast.FunctionDef) and node.name == 'controlMain')
namespace = {
    'cv': SimpleNamespace(EVENT_LBUTTONDOWN=1, EVENT_RBUTTONDOWN=2,
                          EVENT_MBUTTONDOWN=3),
}
exec(compile(ast.Module(body=[callback], type_ignores=[]), 'gi.py', 'exec'), namespace)
for width, height in [(800, 480), (1280, 720), (1024, 768)]:
    namespace.update(DISPLAY_X=width, DISPLAY_Y=height)
    for x, y, expected in [
        (0, 0, (0, 0)),
        (width // 2, height // 2, (400, 240)),
        (width - 1, height - 1, (799, 479)),
        (-1, -1, (0, 0)),
        (width, height, (799, 479)),
    ]:
        namespace['controlMain'](0, x, y, 0, None)
        actual = namespace['mouseX'], namespace['mouseY']
        assert actual == expected, (width, height, x, y, actual, expected)
print('화면 좌표 검사 성공: 800x480, 1280x720, 1024x768')
