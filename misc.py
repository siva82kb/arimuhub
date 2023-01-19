"""misc.py contains a assorted list of handy functions.

Author: Sivakumar Balasubramanian
Date: 25 July 2022
Email: siva82kb@gmail.com
"""

import sys
import time

class ProgressBar(object):
    """A console progress bar."""
    
    def __init__(self, params) -> None:
        self.params = params
        self._divsz = 100 / params['divs']
        self._n = 0
        
    def update(self, value):
        # Update progress bar
        _prgrs = 100 * value / self.params["max_val"]
        if _prgrs - (self._n + 1) * self._divsz > 0:
            self._n += 1
        return ("".join([chr(9608)] * self._n
                         + [chr(32)] * (self.params['divs'] - self._n - 1)),
                _prgrs)

def shorten_str(longstr, l1, l2):
    return longstr[:l1] + "..." + longstr[l2:]


if __name__ == "__main__":
    prgbar = ProgressBar(params={'divs': 40, 'max_val': 255})
    for i in range(256):
        _pb, _prcnt = prgbar.update(i)
        sys.stdout.write("\r" + _pb + f"{_prcnt:5.1f}%")
        time.sleep(0.02)