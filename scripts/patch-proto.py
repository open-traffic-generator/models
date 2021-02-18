#!/usr/bin/python
"""
This file performs following transformation on gnostic-generated .proto:
- wrap `enum` around `message` to facilitate scoped/namespaced enum
- comment out all google.api annotations
- replace int64 with int32 in order to support numeric JSON value instead
  of string (TODO: we might wanna stop doing this)
- replace package name with the one provided
"""

import os
import sys

def patch_proto(input_proto, pkg, out_dir):
    with open(input_proto) as op:
        with open(os.path.join(out_dir, pkg + '.proto'), 'w', newline='\n') as out:
            on_enum = False
            message = []
            enums = []
            for line in op.read().splitlines():
                if message:
                    if line.startswith('}'):
                        message.append(line + os.linesep)
                        for msg_line in message:
                            msg_line = msg_line.replace('int64', 'int32')
                            msg_line_split = msg_line.split()
                            for e in enums:
                                if msg_line_split and msg_line_split[0] == e:
                                    msg_line = msg_line.replace(e, e + '.Enum', 1)
                            out.write(msg_line)
                        message = []
                        enums = []
                    else:
                        if on_enum:
                            if '}' in line:
                                on_enum = False
                                message.append(line + ' }' + os.linesep)
                            else:
                                message.append(line.lower() + os.linesep)
                        else:
                            if 'enum' in line:
                                on_enum = True
                                enums.append(line.split()[1])
                                line = line.replace('enum', 'message') + ' enum Enum {'
                            message.append(line + os.linesep)
                else:
                    if line.startswith('message'):
                        message.append(line + os.linesep)
                    else:
                        if 'google/api' in line or 'google.api' in line:
                            line = '// ' + line
                        elif 'package' in line:
                            line = 'package %s;' % pkg
                        out.write(line + os.linesep)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise Exception('usage: python %s <input_proto> <pkg> <out_dir>' % __file__)
    patch_proto(*sys.argv[1:])
