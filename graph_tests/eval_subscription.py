#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  musepa.py
#
#  Copyright (c) 2020
#  Francesco ANTONIAZZI     <francesco.antoniazzi@emse.fr>
#

import threading

from time import sleep
from multiprocessing.dummy import Pool as ThreadPool


def main(number):
    sleep(number)
    print("Ciao ({}) {}".format(number, threading.get_ident()))

if __name__ == "__main__":
    n = 6
    thPool = ThreadPool(n)
    results = thPool.imap_unordered(main, range(n))
    print("Before Close")
    thPool.close()
    print("Waiting for the last thread to finish")
    thPool.join()
    print("Last thread has finished")