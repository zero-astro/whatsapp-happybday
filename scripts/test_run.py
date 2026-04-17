#!/usr/bin/env python3
import os, sys
os.environ["BIRTHDAY_SIMULATE"] = "true"
sys.path.insert(0, os.path.dirname(__file__))
from whatsapp_happybday import main
main()
