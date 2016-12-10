"""Old parser tests."""

import os
import re
import pytest
from pydocstyle.violations import Error, ErrorRegistry
from pydocstyle.checker import check
from pydocstyle.parser import (Parser, Module, Function, NestedFunction,
                               Method, Class, AllError, TokenStream, StringIO)

__all__ = ()
_ = type('', (), dict(__repr__=lambda *a: '_', __eq__=lambda *a: True))()


parse = Parser()
source_alt = '''
__all__ = ['a', 'b'
           'c',]
'''
source_alt_nl_at_bracket = '''
__all__ = [

    # Inconvenient comment.
    'a', 'b' 'c',]
'''
source_unicode_literals1 = """
from __future__ import unicode_literals
"""
source_unicode_literals2 = """
from __future__ import unicode_literals;
"""
source_unicode_literals3 = """
from \
__future__ \
import \
unicode_literals
"""
source_unicode_literals4 = """
from __future__ \
import unicode_literals \
;
"""
source_unicode_literals5 = """
from __future__ import unicode_literals as foo;
"""
source_unicode_literals6 = """
from __future__ import unicode_literals as foo; import string
"""
source_multiple_future_imports1 = """
from __future__ import (nested_scopes as ns,
                        unicode_literals)
"""
source_multiple_future_imports2 = """
from __future__ import nested_scopes as ns
from __future__ import unicode_literals
"""
source_multiple_future_imports3 = """
from __future__ import nested_scopes, unicode_literals
"""
source_multiple_future_imports4 = """
from __future__ import (nested_scopes as ns, )
from __future__ import (unicode_literals)
"""
source_multiple_future_imports5 = """
from __future__ \
import nested_scopes
from __future__ \
import unicode_literals
"""
source_multiple_future_imports6 = """
from __future__ import nested_scopes; from __future__ import unicode_literals
"""
# pep257 does not detect that 'import string' prevents
# unicode_literals from being a valid __future__.
# That is detected by pyflakes.
source_multiple_future_imports7 = """
from __future__ import nested_scopes; import string; from __future__ import \
    unicode_literals
"""

source_future_import_invalid1 = """
from __future__ import unicode_literals as;
"""
source_future_import_invalid2 = """
from __future__ import unicode_literals as \
;
"""
source_future_import_invalid3 = """
from __future__ import
"""
source_future_import_invalid4 = """
from __future__ import \

"""
source_future_import_invalid5 = """
from __future__ import \
;
"""
source_future_import_invalid6 = """
from __future__ import \
;
"""
source_future_import_invalid7 = """
from __future__ import unicode_literals, (\
nested_scopes)
"""
source_future_import_invalid8 = """
from __future__ import (, )
"""

source_invalid_syntax = """
while True:
\ttry:
    pass
"""

source_token_error = '['

source_complex_all = '''
import foo
import bar

__all__ = (foo.__all__ +
           bar.__all)
'''


def test_parser():
    dunder_all = ('a', 'bc')
    module = parse(StringIO(source_alt), 'file_alt.py')
    assert Module(name='file_alt.py',
                  _source=_,
                  start=1,
                  end=len(source_alt.split('\n')),
                  decorators=_,
                  docstring=None,
                  children=_,
                  parent=None,
                  _all=dunder_all,
                  future_imports={},
                  skipped_error_codes='') == module

    module = parse(StringIO(source_alt_nl_at_bracket), 'file_alt_nl.py')
    assert Module('file_alt_nl.py', _, 1,
                  len(source_alt_nl_at_bracket.split('\n')), _, None, _, _,
                  dunder_all, {}, '') == module

    with pytest.raises(AllError):
        parse(StringIO(source_complex_all), 'file_complex_all.py')


def test_import_parser():
    for i, source_ucl in enumerate((
            source_unicode_literals1,
            source_unicode_literals2,
            source_unicode_literals3,
            source_unicode_literals4,
            source_unicode_literals5,
            source_unicode_literals6,
            ), 1):
        module = parse(StringIO(source_ucl), 'file_ucl{}.py'.format(i))

        assert Module('file_ucl{}.py'.format(i), _, 1,
                      _, _, None, _, _,
                      _, {'unicode_literals': True}, '') == module
        assert module.future_imports['unicode_literals']

    for i, source_mfi in enumerate((
            source_multiple_future_imports1,
            source_multiple_future_imports2,
            source_multiple_future_imports3,
            source_multiple_future_imports4,
            source_multiple_future_imports5,
            source_multiple_future_imports6,
            source_multiple_future_imports7,
            ), 1):
        module = parse(StringIO(source_mfi), 'file_mfi{}.py'.format(i))
        assert Module('file_mfi{}.py'.format(i), _, 1,
                      _, _, None, _, _,
                      _, {'unicode_literals': True, 'nested_scopes': True},
                      '') == module
        assert module.future_imports['unicode_literals']

    # These are invalid syntax, so there is no need to verify the result
    for i, source_ucli in enumerate((
            source_future_import_invalid1,
            source_future_import_invalid2,
            source_future_import_invalid3,
            source_future_import_invalid4,
            source_future_import_invalid5,
            source_future_import_invalid6,
            source_future_import_invalid7,
            source_future_import_invalid8,
            source_token_error,
            source_invalid_syntax,
            ), 1):
        module = parse(StringIO(source_ucli), 'file_invalid{}.py'.format(i))

        assert Module('file_invalid{}.py'.format(i), _, 1,
                      _, _, None, _, _,
                      _, _, '') == module


def _test_module():

    module = Module(source, 'module.py')
    assert module.source == source
    assert module.parent is None
    assert module.name == 'module'
    assert module.docstring == '"""Module docstring."""'
    assert module.is_public

    function, = module.children
    assert function.source.startswith('def function')
    assert function.source.endswith('pass\n')
    assert function.parent is module
    assert function.name == 'function'
    assert function.docstring == '"""Function docstring."""'


def test_token_stream():
    stream = TokenStream(StringIO('hello#world'))
    assert stream.current.value == 'hello'
    assert stream.line == 1
    assert stream.move().value == 'hello'
    assert stream.current.value == '#world'
    assert stream.line == 1


@pytest.mark.parametrize('test_case', [
    'test',
    'unicode_literals',
    'nested_class',
    'capitalization',
    'comment_after_def_bug',
    'multi_line_summary_start',
    'all_import',
    'all_import_as',
    'superfluous_quotes',
])
def test_pep257(test_case):
    """Run domain-specific tests from test.py file."""
    case_module = __import__('test_cases.{}'.format(test_case),
                             globals=globals(),
                             locals=locals(),
                             fromlist=['expectation'],
                             level=1)
    test_case_dir = os.path.normcase(os.path.dirname(__file__))
    test_case_file = os.path.join(test_case_dir,
                                  'test_cases',
                                  test_case + '.py')
    results = list(check([test_case_file],
                         select=set(ErrorRegistry.get_error_codes()),
                         ignore_decorators=re.compile('wraps')))
    for error in results:
        assert isinstance(error, Error)
    results = set([(e.definition.name, e.message) for e in results])
    assert case_module.expectation.expected == results
