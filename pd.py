##
## Copyright (C) 2019 Vladimir Novikov <oxore@protonmail.com>
##
## WTFPL
##

# TODO: UIH frame types: PSC, CLD, Test, MSC, FCoff, FCon
# TODO: Calculate Frame Checksum
# TODO: OUTPUT_PYTHON

import sigrokdecode as srd

STATES = [
        'OPEN'
        'ADDR'
        'CONTROL'
        'LEN'
        'LEN2'
        'DATA'
        'FCS'
        'CLOSE'
        ]

def decode_control(byte):
    if byte == 0x2F or byte == 0x3F:
        return 'SABM'
    elif byte == 0x63 or byte == 0x73:
        return 'UA'
    elif byte == 0x0F or byte == 0x1F:
        return 'DM'
    elif byte == 0x43 or byte == 0x53:
        return 'DISC'
    elif byte == 0xEF or byte == 0xFF:
        return 'UIH'
    elif byte == 0x03 or byte == 0x13:
        return 'UI'
    return ''

class Decoder(srd.Decoder):
    api_version = 3
    id = 'simcom-0710'
    name = 'GSM0710'
    longname = 'Simcom GSM0710'
    desc = 'Simcom GSM0710 Multiplexer'
    license = 'wtfpl'
    inputs = ['uart']
    outputs = ['uart']
    tags = []
    annotations = (
        ('debug-rx', 'Rx Debug output'),
        ('debug-tx', 'Tx Debug output'),
        ('dlc0-rx', 'DLC 0 Rx'),
        ('dlc0-tx', 'DLC 0 Tx'),
        ('dlc2-rx', 'DLC 2 Rx'),
        ('dlc2-tx', 'DLC 2 Tx'),
        ('dlc1-rx', 'DLC 1 Rx'),
        ('dlc1-tx', 'DLC 1 Tx'),
        ('dlc3-rx', 'DLC 3 Tx'),
        ('dlc3-tx', 'DLC 3 Rx'),
    )
    annotation_rows = (
        ('row-debug-rx', 'Rx Debug', (0,)),
        ('row-debug-tx', 'Tx Debug', (1,)),
        ('row-dlc0-rx', 'DLC 0 Rx', (2,)),
        ('row-dlc0-tx', 'DLC 0 Tx', (3,)),
        ('row-dlc1-rx', 'DLC 1 Rx', (4,)),
        ('row-dlc1-tx', 'DLC 1 Tx', (5,)),
        ('row-dlc2-rx', 'DLC 2 Rx', (6,)),
        ('row-dlc2-tx', 'DLC 2 Tx', (7,)),
        ('row-dlc3-rx', 'DLC 3 Rx', (8,)),
        ('row-dlc3-tx', 'DLC 3 Tx', (9,)),
    )
    options = (
        {
            'id': 'format',
            'desc': 'Data format',
            'default': 'hex',
            'values': ('ascii', 'dec', 'hex', 'oct', 'bin'),
        },
        {
            'id': 'debug',
            'desc': 'Enable Debug',
            'default': 'no',
            'values': ('yes', 'no'),
        },
    )

    state = ['OPEN', 'OPEN']
    length = [0, 0]
    control = ['', '']

    def __init__(self):
        self.reset()

    def reset(self):
        self.reset_state(0)
        self.reset_state(1)


    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)

    def reset_state(self, rxtx):
        self.state[rxtx] = 'OPEN'
        self.length[rxtx] = 0
        self.control[rxtx] = ''

    def format_value(self, v):
        fmt = self.options['format']

        if fmt == 'ascii':
            if v in range(32, 126 + 1):
                return chr(v)
            hexfmt = "[{:02X}]"
            return hexfmt.format(v)

        if fmt == 'dec':
            return "{:d}".format(v)

        if fmt == 'hex':
            fmtchar = "X"
        elif fmt == 'oct':
            fmtchar = "o"
        elif fmt == 'bin':
            fmtchar = "b"
        else:
            fmtchar = None
        if fmtchar is not None:
            fmt = "{{:02{:s}}}".format(fmtchar)
            return fmt.format(v)

        return None

    def put_debug(self, rxtx, ss, es, data):
        if self.options['debug'] == 'yes':
            self.put(ss, es, self.out_ann, [rxtx, data])

    def decode(self, ss, es, data):
        if data[0] != 'DATA':
            return

        if data[1] == 0:
            rxtx = 0
        elif data[1] == 1:
            rxtx = 1
        else:
            return

        byte = data[2][0]

        if self.state[rxtx] == 'OPEN':
            if byte == 0xF9:
                self.state[rxtx] = 'ADDR'
                self.put_debug(rxtx, ss, es, ['Opening Flag', 'Open Flag',
                    'Open', 'OF'])
            else:
                self.put_debug(rxtx, ss, es, ['!'])
                self.reset_state(rxtx);

        elif self.state[rxtx] == 'ADDR':
            addr = byte // 4
            self.addr = addr;
            self.state[rxtx] = 'CONTROL'
            self.put_debug(rxtx, ss, es, ['DLC {0}'.format(addr), str(addr)])

        elif self.state[rxtx] == 'CONTROL':
            c = decode_control(byte)
            if c != '':
                self.control[rxtx] = c
                self.state[rxtx] = 'LEN'
                self.put_debug(rxtx, ss, es, [c])
            else:
                self.put_debug(rxtx, ss, es, ['!'])
                self.reset_state(rxtx)

        elif self.state[rxtx] == 'LEN':
            length = byte // 2
            self.length[rxtx] = length
            self.put_debug(rxtx, ss, es, [
                'Length {0}'.format(self.length[rxtx]),
                'L {0}'.format(self.length[rxtx])
                ])
            if byte % 2:
                if length > 0:
                    self.state[rxtx] = 'DATA'
                else:
                    self.state[rxtx] = 'FCS'
            else:
                self.state[rxtx] = 'LEN2'

        elif self.state[rxtx] == 'LEN2':
            length = byte * 128 + self.length[rxtx]
            self.length[rxtx] = length
            self.put_debug(rxtx, ss, es, [
                'Length {0}'.format(self.length[rxtx]),
                'L {0}'.format(self.length[rxtx])
                ])
            if length > 0:
                self.state[rxtx] = 'DATA'
            else:
                self.state[rxtx] = 'FCS'

        elif self.state[rxtx] == 'DATA':
            self.put_debug(rxtx, ss, es, [self.format_value(byte)])
            self.put(ss, es, self.out_ann, [(self.addr + 1) * 2 + rxtx,
                [self.format_value(byte)]])

            if self.length[rxtx] <= 1:
                self.state[rxtx] = 'FCS'
            else:
                self.length[rxtx] -= 1;

        elif self.state[rxtx] == 'FCS':
            self.put_debug(rxtx, ss, es, [
                'FCS {0:02X}'.format(byte),
               'Checksum {0:02X}'.format(byte),
               'Frame Checksum {0:02X}'.format(byte),
               ])
            self.state[rxtx] = 'CLOSE'

        elif self.state[rxtx] == 'CLOSE':
            if byte == 0xF9:
                self.state[rxtx] = 'OPEN'
                self.put_debug(rxtx, ss, es, ['Closing Flag', 'Close Flag',
                    'Close', 'CF'])
            else:
                self.put_debug(rxtx, ss, es, ['!'])

            self.reset_state(rxtx)

        else:
            self.reset_state(rxtx)
