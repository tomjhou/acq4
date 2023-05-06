from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from six.moves import range

from acq4.util import Qt
from math import ceil, floor
from pyqtgraph import AxisItem

if TYPE_CHECKING:
    from acq4.Manager import Task

Ui_Form = Qt.importTemplate('.PatchTemplate')


def prettify_float(real: float, precision: int = 2) -> str:
    '''
    Prettify the passed floating-point number into a human-readable string,
    rounded and truncated to the passed number of decimal places.

    This converter prettifies floating-point numbers for human consumption,
    producing more readable results than the default :meth:`float.__str__`
    dunder method. Notably, this converter:

    * Strips all ignorable trailing zeroes and decimal points from this number
      (e.g., ``3`` rather than either ``3.`` or ``3.0``).
    * Rounds to the passed precision for perceptual uniformity.

    Parameters
    ----------
    real : float
        Arbitrary floating-point number to be prettified.
    precision : int, optional
        **Precision** (i.e., number of decimal places to round to). Defaults to
        a precision of 2 decimal places.

    Returns
    ----------
    str
        Human-readable string prettified from this floating-point number.

    Raises
    ----------
    ValueError
        If this precision is negative.
    '''

    # If this precision is negative, raise an exception.
    if precision < 0:
        raise ValueError(f'Negative precision {precision} unsupported.')
    # Else, this precision is non-negative.

    # String prettified from this floating-point number. In order:
    # * Coerce this number into a string rounded to this precision.
    # * Truncate all trailing zeroes from this string.
    # * Truncate any trailing decimal place if any from this string.
    result = f'{real:.{precision}f}'.rstrip('0').rstrip('.')

    # If rounding this string from a small negative number (e.g., "-0.001")
    # yielded the anomalous result of "-0", return "0" instead; else, return
    # this result as is.
    return '0' if result == '-0' else result


class CustomAxisItem(AxisItem):

    def logTickStrings(self, values, scale, spacing):

        def numStr(x):
            """
            Avoid scientific notation for small values
            :param x:
            :return:
            """
            if 0.0001 <= x <= 10000:
                return prettify_float(x, 4)

            return "%0.1g"%x

        estrings = [numStr(x) for x in 10 ** np.array(values).astype(float) * np.array(scale)]
        convdict = {"0": "⁰",
                    "1": "¹",
                    "2": "²",
                    "3": "³",
                    "4": "⁴",
                    "5": "⁵",
                    "6": "⁶",
                    "7": "⁷",
                    "8": "⁸",
                    "9": "⁹",
                    }
        dstrings = []

        units = ' %s%s' % (self.labelUnitPrefix, self.labelUnits)

        for e in estrings:
            if e.count("e"):
                v, p = e.split("e")
                sign = "⁻" if p[0] == "-" else ""
                pot = "".join([convdict[pp] for pp in p[1:].lstrip("0")])
                if v == "1":
                    v = ""
                else:
                    v = v + "·"
                dstrings.append(v + "10" + sign + pot + units)
            else:
                dstrings.append(e + units)

        return dstrings

    def logTickValues(self, minVal, maxVal, size, stdTicks):
        """
        Adds tick values between 1.0 and 2.0
        :param minVal:
        :param maxVal:
        :param size:
        :param stdTicks:
        :return:
        """
        ## start with the tick spacing given by tickValues().
        ## Any level whose spacing is < 1 needs to be converted to log scale

        ticks = []
        for (spacing, t) in stdTicks:
            if spacing >= 1.0:
                ticks.append((spacing, t))

        if len(ticks) < 3:
            v1 = int(floor(minVal))
            v2 = int(ceil(maxVal))
            #major = list(range(v1+1, v2))

            minor = []
            for v in range(v1, v2):
                # Make log scale with ticks at 1.5 and 2.5
                logTicks = np.concatenate(([1, 1.2, 1.4, 1.6, 1.8, 2, 2.5, 3, 3.5], np.arange(4, 10)))
                minor.extend(v + np.log10(logTicks))
            minor = [x for x in minor if minVal < x < maxVal]
            ticks.append((None, minor))
        return ticks
