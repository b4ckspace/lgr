from re import compile as r
from collections import namedtuple

from django.core.exceptions import ValidationError

from lgr import models


BarcodeTuple = namedtuple('BarcodeTuple',
                          ['code', 'item', 'parent', 'owner', 'description'])


# build regex
# pylint: disable=invalid-name
level = r'[ -]*'
single = r'[a-zA-Z]*[0-9]+'
multiple = r'(?P<prefix>[a-zA-Z]*)(?P<start>[0-9]+)\.\.(?P=prefix)(?P<end>[0-9]+)'
barcode = r'(?:(?P<single>{single})|(?P<multiple>{multiple}))'.format(
    single=single, multiple=multiple
)
optionals = r':(?P<item>[^:]+)(?::(?P<description>.*))?'
codeline = r'(?P<level>{level})(?P<barcode>{barcode})(?:{optionals})?'.format(
    level=level, barcode=barcode, optionals=optionals
)
quickadd_regex = r(r'^(?:# *(?P<owner>.+)|{codeline})$'.format(codeline=codeline))


def barcode_quickadd(value: str) -> list:
    """Validate and cleanup quickadd form input."""

    barcodes = list()
    last_owner = None
    levelmap = [None, ]
    for linenr, line in enumerate(value.splitlines(), 1):
        match = quickadd_regex.match(line)
        if not match:
            raise ValidationError(f'Unable to parse line {linenr}')
        match = match.groupdict()

        # use owner, lastowner or default owner
        if match['owner']:
            match['owner'] = match['owner'].strip()
            last_owner = match['owner']
            continue

        match['owner'] = last_owner or models.Person.objects.first()

        if match['barcode']:
            # just a single barcode
            if match['single']:
                code_range = [match['barcode']]
            # a range of barcodes
            elif match['multiple']:
                prefix = match['prefix']
                start = int(match['start'])
                end = int(match['end'])

                start_len = len(match['start'])
                end_len = len(match['end'])
                max_len = start_len if start_len > end_len else end_len

                if start >= end:
                    raise ValueError(f'Start of range is >= end (line: {linenr})')

                for _barcode in range(start, end + 1):
                    _barcode = str(_barcode).zfill(max_len)

                code_range = ('%s%s' % (prefix, str(i).zfill(max_len))
                              for i in range(start, end + 1))
        else:
            raise ValidationError('Line does not contain Owner or Barcode '
                                  f'(line: {linenr})')

        # validate current level
        match['level'] = len(match['level'] or '')
        if match['level'] % 2 != 0:
            raise ValidationError(f'Idents must be a multiple of 2 (line: {linenr})')
        match['level'] = int(match['level'] / 2)
        if len(levelmap) - match['level'] < 1:
            raise ValidationError('You can only ident one step (2 chars) at a time '
                                  f'(line: {linenr})')

        parent = levelmap[match['level']]
        for code in code_range:
            # if item is set create new barcode, else look in database if it exists.
            if match['item']:
                match['item'] = match['item'].strip()
                barcode_db = models.Barcode.objects.filter(code=code)
                barcode_db = barcode_db.first()
                if barcode_db:
                    raise ValidationError('Barcode is already known, remove '
                                          f'item (line: {linenr})')
                barcode_tuple = BarcodeTuple(
                    code=code,
                    item=match['item'],
                    parent=parent,
                    owner=match['owner'],
                    description=match['description'] or '',
                )
                barcodes.append(barcode_tuple)
            else:
                barcode_db = models.Barcode.objects.filter(code=code).first()
                if barcode_db is None:
                    raise ValidationError(f'Barcode {code} not found and no item given. '
                                          f'(line: {linenr})')
                parent_db = models.Barcode.objects.filter(code=parent).first()
                barcode_db.parent = parent_db
                barcodes.append(barcode_db or code)

            levelmap = levelmap[0:match['level'] + 1]
            levelmap.append(code)

    return barcodes
