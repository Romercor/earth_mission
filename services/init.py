import ee
import os

def init_earth_engine():
    if not ee.data._credentials:
        ee.Initialize()