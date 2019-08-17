##
## Copyright (C) 2019 Vladimir Novikov <oxore@protonmail.com>
##
## WTFPL
##

'''
This decoder stacks on top of the 'UART' and decodes the SIMCOM 0710 CMUX
protocol.

See https://simcom.ee/documents/SIM900/SIM900_Multiplexer%20User%20Manual_Application%20Note_V1.3.pdf
'''

from .pd import Decoder
