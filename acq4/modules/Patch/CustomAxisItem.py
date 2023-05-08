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

        prefix_list = ['e-27', 'y', 'z', 'a', 'f', 'p', 'n', 'µ', 'm', '', 'k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y', 'e27']

        def numStr(x):
            """
            Avoid scientific notation for small values
            :param x:
            :return: string, and prefix (if any)
            """

            if x > 10000:
                # Large numbers are just reported as scientific notation.
                return "%0.1g" % x, -1

            try:
                # Small numbers (< 1.0) are multiplied by 10^3 repeatedly until they are
                # # bigger, and prefix modified.

                # Find out what prefix is currently used. If not found, will cause exception
                prefix_index = prefix_list.index(self.labelUnitPrefix)
                new_x = float(x)
                adj = 0
                while new_x < 0.999:
                    new_x *= 1000
                    adj += 1

                prefix_index -= adj
                if prefix_index >= 0:
                    return prettify_float(new_x, 4), prefix_index
            except:
                pass

            # Unable to adjust. Just use normal heuristics
            if 0.0001 <= x <= 10000:
                return prettify_float(x, 4), -1

            return "%0.1g" % x, -1

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

        for x in estrings:
            e = x[0]
            prefix = x[1]

            units = ' %s%s' % (self.labelUnitPrefix if prefix < 0 else prefix_list[prefix], self.labelUnits)

            if e.count("e"):
                # Format scientific notation by replacing e with superscript
                v, p = e.split("e")
                sign = "⁻" if p[0] == "-" else ""
                pot = "".join([convdict[pp] for pp in p[1:].lstrip("0")])
                if v == "1":
                    v = ""
                else:
                    v = v + "·"
                dstrings.append(v + "10" + sign + pot + units)
            else:
                # Not scientific. Just append units to value
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
        # stdTicks is a list of tuples.
        # In each tuple, first value is spacing, second value is list of values
        # There are three tuples, corresonding to major, minor, and ... sub-minor?
        #
        # The default sub-minor ticks are evenly spaced in LOG space, which leads to CRAZY
        # actual values outside the powers of 10. So just keep the powers of 10,
        # then inserted our own values
        for (spacing, t) in stdTicks:
            if spacing >= 1:
                ticks.append((spacing, t))

        if len(ticks) < 3:
            # Not all possible tick positions (major, minor, sub-minor) are used.
            # Generate some more to fill in gaps between powers of 10

            # Note that only major and minor ticks have text. Subminor will show up as faint tiny ticks

            # Get integers that bracket the entire range
            v1 = int(floor(minVal))
            v2 = int(ceil(maxVal))
            #major = list(range(v1+1, v2))

            log_range = maxVal - minVal

            minor = []
            # List of "fill" values between powers of 10
            if log_range < 0.15:
                logTicks = np.concatenate((np.arange(1, 2, 0.05), np.arange(2, 3, 0.1), np.arange(3, 10, 0.2)))
            elif log_range < 0.3:
                logTicks = np.concatenate((np.arange(1, 2, 0.1), np.arange(2, 3, 0.2), np.arange(3, 10, 0.5)))
            elif log_range < 0.8:
                logTicks = np.concatenate(([1, 1.2, 1.4, 1.6, 1.8, 2, 2.5], np.arange(3, 10)))
            elif log_range < 2:
                logTicks = [1, 1.5, 2, 3, 4, 6, 8]
            else:
                logTicks = [1, 2, 5]

            # Create list of ticks with integers and "fill"
            for v in range(v1, v2):
                minor.extend(v + np.log10(logTicks))

            # Remove values outside y range
            minor = [x for x in minor if minVal < x < maxVal]
            ticks.append((None, minor))
        return ticks
