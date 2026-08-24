"""Load-time data tables from ASM100.FTN's TABLES subroutine.

TABLES is never CALLed anywhere in the source -- like OPTAB, it is a
BLOCK-DATA-style subprogram whose sole purpose is DATA statements that
initialize COMMON /SYM/ and /EXPRST/. In FORTRAN, DATA statements that
initialize COMMON members take effect at program load time regardless of
whether the containing subroutine is ever called; Python has no equivalent,
so init() must be called explicitly once, before anything else runs
(see main.py).

Values were extracted mechanically from the original DATA statements
(see the extraction script noted in the port README) rather than
hand-transcribed, to avoid transposition errors across ~400 constants.
"""

from .common import G
from .hollerith import holl


def init() -> None:
    # fmt: off
    G.USRMAX = 200
    G.EXPRMX = 12
    G.CHARMX = 37
    G.BRKMX = 23
    G.CHARS[1] = holl('  ')
    G.CHARS[2] = 0
    G.CHARS[3] = 0
    G.CHARS[4] = holl('+ ')
    G.CHARS[5] = holl('- ')
    G.CHARS[6] = holl('* ')
    G.CHARS[7] = holl('/ ')
    G.CHARS[8] = holl('. ')
    G.CHARS[9] = holl('$ ')
    G.CHARS[10] = holl('= ')
    G.CHARS[11] = holl('( ')
    G.CHARS[12] = holl(') ')
    G.CHARS[13] = holl('< ')
    G.CHARS[14] = holl('; ')
    G.CHARS[15] = holl(', ')
    G.CHARS[16] = holl(': ')
    G.CHARS[17] = holl('" ')
    G.CHARS[18] = holl('# ')
    G.CHARS[19] = holl('& ')
    G.CHARS[20] = holl('% ')
    G.CHARS[21] = holl("' ")
    G.CHARS[22] = holl('> ')
    G.CHARS[23] = holl('@ ')
    G.CHARS[24] = holl('! ')
    G.CHARS[25] = holl('K ')
    G.CHARS[26] = holl('B ')
    G.CHARS[27] = holl('E ')
    G.CHARS[28] = holl('X ')
    G.CHARS[29] = holl('T ')
    G.CHARS[30] = holl('N ')
    G.CHARS[31] = holl('H ')
    G.CHARS[32] = holl('0 ')
    G.CHARS[33] = holl('9 ')
    G.CHARS[34] = holl('A ')
    G.CHARS[35] = holl('Z ')
    G.CHARS[36] = 0
    G.CHARS[37] = holl('[ ')
    G.DIGITS[1] = holl('0 ')
    G.DIGITS[2] = holl('1 ')
    G.DIGITS[3] = holl('2 ')
    G.DIGITS[4] = holl('3 ')
    G.DIGITS[5] = holl('4 ')
    G.DIGITS[6] = holl('5 ')
    G.DIGITS[7] = holl('6 ')
    G.DIGITS[8] = holl('7 ')
    G.DIGITS[9] = holl('8 ')
    G.DIGITS[10] = holl('9 ')
    G.DIGITS[11] = holl('A ')
    G.DIGITS[12] = holl('B ')
    G.DIGITS[13] = holl('C ')
    G.DIGITS[14] = holl('D ')
    G.DIGITS[15] = holl('E ')
    G.DIGITS[16] = holl('F ')
    G.BLANK = holl('  ')

    _EXPRTB_DATA = [
        (holl('+ '), holl('- '), holl('* '), holl('/ '), holl('( '), holl(') '), holl('& '), holl('% '), holl('= '), holl('> '), holl('< '), holl("' ")),
        (5, 5, 7, 7, 2, 1, 3, 3, 3, 3, 3, 9),
        (1, 2, 3, 4, 0, 0, 7, 8, 9, 10, 11, 12),
    ]
    for _n, _row in enumerate(_EXPRTB_DATA, start=1):
        for _k, _v in enumerate(_row, start=1):
            G.EXPRTB[_k, _n] = _v

    _MASKTB_DATA = [
        (-4, -4, -64, -4, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (0, 480, 0, 0, -512, 480, 0, 0, 0, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 0, -16384, 12288, 3584, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 7936, 192, 48, 3, 12),
    ]
    for _n, _row in enumerate(_MASKTB_DATA, start=1):
        for _k, _v in enumerate(_row, start=1):
            G.MASKTB[_k, _n] = _v

    _ARGSYM_DATA = [
        (holl('NC'), holl('  '), 0, 0),
        (holl('FM'), holl('  '), 1, 0),
        (holl('DP'), holl('X '), 2, 2),
        (holl('DP'), holl('Y '), 3, 1),
        (holl('TM'), holl('  '), 4, 0),
        (holl('ZE'), holl('RO'), 5, 0),
        (holl('NC'), holl('  '), 0, 0),
        (holl('FA'), holl('  '), 1, 0),
        (holl('DP'), holl('X '), 2, 2),
        (holl('DP'), holl('Y '), 3, 1),
        (holl('MD'), holl('  '), 4, 0),
        (holl('ZE'), holl('RO'), 5, 0),
        (holl('MD'), holl('PX'), 6, 2),
        (holl('ED'), holl('PX'), 7, 2),
        (holl('FM'), holl('  '), 0, 0),
        (holl('DP'), holl('X '), 1, 2),
        (holl('DP'), holl('Y '), 2, 1),
        (holl('TM'), holl('  '), 3, 0),
        (holl('FA'), holl('  '), 0, 0),
        (holl('DP'), holl('X '), 1, 2),
        (holl('DP'), holl('Y '), 2, 1),
        (holl('MD'), holl('  '), 3, 0),
        (holl('ZE'), holl('RO'), 0, 0),
        (holl('IN'), holl('BS'), 1, 0),
        (holl('DP'), holl('X '), 3, 2),
        (holl('DP'), holl('Y '), 4, 1),
        (holl('MD'), holl('  '), 5, 0),
        (holl('SP'), holl('FN'), 6, 0),
        (holl('TM'), holl('  '), 7, 0),
        (holl('DB'), holl('  '), 1, 0),
        (holl('FA'), holl('  '), 2, 0),
        (holl('FM'), holl('  '), 3, 0),
        (holl('FA'), holl('  '), 1, 0),
        (holl('FM'), holl('  '), 2, 0),
        (holl('DB'), holl('  '), 3, 0),
    ]
    for _n, _row in enumerate(_ARGSYM_DATA, start=1):
        for _k, _v in enumerate(_row, start=1):
            G.ARGSYM[_k, _n] = _v

    _PSUSYM_DATA = [
        (holl('TI'), holl('TL'), holl('E ')),
        (holl('EN'), holl('TR'), holl('Y ')),
        (holl('VA'), holl('L '), holl('  ')),
        (holl('EQ'), holl('U '), holl('  ')),
        (holl('LO'), holl('C '), holl('  ')),
        (holl('FP'), holl('  '), holl('  ')),
        (holl('EN'), holl('D '), holl('  ')),
        (holl('EX'), holl('T '), holl('  ')),
        (holl('IN'), holl('SE'), holl('RT')),
        (holl('IF'), holl('  '), holl('  ')),
        (holl('EN'), holl('DI'), holl('F ')),
        (holl('BO'), holl('X '), holl('  ')),
        (holl('EN'), holl('DB'), holl('OX')),
        (holl('LI'), holl('B '), holl('  ')),
        (holl('EN'), holl('DL'), holl('IB')),
        (holl('RA'), holl('DI'), holl('X ')),
        (holl('PA'), holl('GE'), holl('  ')),
        (holl('LI'), holl('ST'), holl('  ')),
        (holl('NO'), holl('LI'), holl('ST')),
        (holl('IN'), holl('TE'), holl('GE')),
        (holl('RE'), holl('AL'), holl('  ')),
        (holl('CO'), holl('MM'), holl('ON')),
        (holl('DA'), holl('TA'), holl('  ')),
        (holl('CO'), holl('MI'), holl('O ')),
        (holl('SU'), holl('BR'), holl('  ')),
        (holl('PA'), holl('RA'), holl('M ')),
        (holl('CA'), holl('LL'), holl('  ')),
        (holl('GL'), holl('OB'), holl('AL')),
        (holl('TR'), holl('IP'), holl('LE')),
        (holl('TA'), holl('SK'), holl('  ')),
        (holl('IS'), holl('R '), holl('  ')),
    ]
    for _n, _row in enumerate(_PSUSYM_DATA, start=1):
        for _k, _v in enumerate(_row, start=1):
            G.PSUSYM[_k, _n] = _v
    # fmt: on
