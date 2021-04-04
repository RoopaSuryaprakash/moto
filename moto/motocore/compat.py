import collections
import inspect
import sys

py2k = sys.version_info.major < 3
py3k = sys.version_info.major >= 3
py36 = sys.version_info >= (3, 6)


# https://github.com/sqlalchemy/alembic/commit/41b100e6300e0680e9457149ac6f36ad7f78909e
# https://github.com/sqlalchemy/sqlalchemy/commit/df99e1ef5f334ce7f4c8118c3e0bdf2949f54de3
ArgSpec = collections.namedtuple("ArgSpec", ["args", "varargs", "keywords", "defaults"])


def inspect_getargspec(func):
    """getargspec based on fully vendored getfullargspec from Python 3.3."""

    if inspect.ismethod(func):
        func = func.__func__
    if not inspect.isfunction(func):
        raise TypeError("{!r} is not a Python function".format(func))

    co = func.__code__
    if not inspect.iscode(co):
        raise TypeError("{!r} is not a code object".format(co))

    nargs = co.co_argcount
    names = co.co_varnames
    nkwargs = co.co_kwonlyargcount if py3k else 0
    args = list(names[:nargs])

    nargs += nkwargs
    varargs = None
    if co.co_flags & inspect.CO_VARARGS:
        varargs = co.co_varnames[nargs]
        nargs = nargs + 1
    varkw = None
    if co.co_flags & inspect.CO_VARKEYWORDS:
        varkw = co.co_varnames[nargs]

    return ArgSpec(args, varargs, varkw, func.__defaults__)
