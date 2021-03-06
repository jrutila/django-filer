#-*- coding: utf-8 -*-
from django.template import Library
from django import template
import math

register = Library()

# The templatetag below is copied from sorl.thumbnail

filesize_formats = ['k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
filesize_long_formats = {
    'k': 'kilo', 'M': 'mega', 'G': 'giga', 'T': 'tera', 'P': 'peta',
    'E': 'exa', 'Z': 'zetta', 'Y': 'yotta',
}


def filesize(bytes, format='auto1024'):
    """
    Returns the number of bytes in either the nearest unit or a specific unit
    (depending on the chosen format method).

    Acceptable formats are:

    auto1024, auto1000
      convert to the nearest unit, appending the abbreviated unit name to the
      string (e.g. '2 KiB' or '2 kB').
      auto1024 is the default format.
    auto1024long, auto1000long
      convert to the nearest multiple of 1024 or 1000, appending the correctly
      pluralized unit name to the string (e.g. '2 kibibytes' or '2 kilobytes').
    kB, MB, GB, TB, PB, EB, ZB or YB
      convert to the exact unit (using multiples of 1000).
    KiB, MiB, GiB, TiB, PiB, EiB, ZiB or YiB
      convert to the exact unit (using multiples of 1024).

    The auto1024 and auto1000 formats return a string, appending the correct
    unit to the value. All other formats return the floating point value.

    If an invalid format is specified, the bytes are returned unchanged.
    """
    format_len = len(format)
    # Check for valid format
    if format_len in (2, 3):
        if format_len == 3 and format[0] == 'K':
            format = 'k%s' % format[1:]
        if not format[-1] == 'B' or format[0] not in filesize_formats:
            return bytes
        if format_len == 3 and format[1] != 'i':
            return bytes
    elif format not in ('auto1024', 'auto1000',
                        'auto1024long', 'auto1000long'):
        return bytes
    # Check for valid bytes
    try:
        bytes = long(bytes)
    except (ValueError, TypeError):
        return bytes

    # Auto multiple of 1000 or 1024
    if format.startswith('auto'):
        if format[4:8] == '1000':
            base = 1000
        else:
            base = 1024
        logarithm = bytes and math.log(bytes, base) or 0
        index = min(int(logarithm) - 1, len(filesize_formats) - 1)
        if index >= 0:
            if base == 1000:
                bytes = bytes and bytes / math.pow(1000, index + 1)
            else:
                bytes = bytes >> (10 * (index))
                bytes = bytes and bytes / 1024.0
            unit = filesize_formats[index]
        else:
            # Change the base to 1000 so the unit will just output 'B' not 'iB'
            base = 1000
            unit = ''
        if bytes >= 10 or ('%.1f' % bytes).endswith('.0'):
            bytes = '%.0f' % bytes
        else:
            bytes = '%.1f' % bytes
        if format.endswith('long'):
            unit = filesize_long_formats.get(unit, '')
            if base == 1024 and unit:
                unit = '%sbi' % unit[:2]
            unit = '%sbyte%s' % (unit, bytes != '1' and 's' or '')
        else:
            unit = '%s%s' % (base == 1024 and unit.upper() or unit,
                             base == 1024 and 'iB' or 'B')

        return '%s %s' % (bytes, unit)

    if bytes == 0:
        return bytes
    base = filesize_formats.index(format[0]) + 1
    # Exact multiple of 1000
    if format_len == 2:
        return bytes / (1000.0 ** base)
    # Exact multiple of 1024
    elif format_len == 3:
        bytes = bytes >> (10 * (base - 1))
        return bytes / 1024.0
register.filter(filesize)

from looptags import Loop
from ..models.filemodels import File

@register.tag('fileloop')
class WhileNode(template.Node):
    child_nodelists = ('nodelist_loop',)

    def __init__(self, parser, token):
        bits = token.split_contents()[1:]
        self.var = template.defaulttags.TemplateIfParser(parser, bits).parse()
        self.nodelist_loop = parser.parse(('endfileloop',))
        parser.delete_first_token()

    def __rer__(self):
        return "<While node>"

    def __iter__(self):
        return self.nodelist_loop

    def render(self, context):
        loop = Loop('fileloop', context, self.nodelist_loop)
        eval_var = self.var.eval
        tags = eval_var(context)
        for f in File.objects.filter(tags__in=tags.all()).distinct('id'): #[ t.name for t in tags.all() ]):
          context['file'] = f
          loop.next()
        return loop.render(close=True)
