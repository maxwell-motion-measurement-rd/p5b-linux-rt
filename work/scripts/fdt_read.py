"""Minimal read-only parser for inline-data DTB/FIT images."""
import struct


def parse(data):
    if len(data) < 40:
        raise ValueError('Truncated FDT header')
    header = struct.unpack_from('>10I', data)
    magic, total, structure, strings = header[:4]
    if magic != 0xd00dfeed or total > len(data):
        raise ValueError('Invalid FDT header')
    names = data[strings:strings + header[8]]
    limit = structure + header[9]
    offset, stack, nodes = structure, [], {}
    while offset + 4 <= limit:
        token = struct.unpack_from('>I', data, offset)[0]
        offset += 4
        if token == 1:
            end = data.index(b'\0', offset)
            stack.append(data[offset:end].decode('ascii'))
            offset = (end + 4) & ~3
            path = '/' + '/'.join(stack[1:])
            nodes[path] = {}
        elif token == 2:
            stack.pop()
        elif token == 3:
            length, name_offset = struct.unpack_from('>II', data, offset)
            offset += 8
            end = names.index(b'\0', name_offset)
            name = names[name_offset:end].decode('ascii')
            value = data[offset:offset + length]
            if len(value) != length:
                raise ValueError('Truncated FDT property')
            nodes['/' + '/'.join(stack[1:])][name] = value
            offset = (offset + length + 3) & ~3
        elif token == 4:
            continue
        elif token == 9:
            if stack:
                raise ValueError('Unclosed FDT node')
            return nodes
        else:
            raise ValueError('Unexpected FDT token %d' % token)
    raise ValueError('Missing FDT end token')


def string(value):
    return value.rstrip(b'\0').decode('ascii')


def cell(value):
    if len(value) != 4:
        raise ValueError('Expected one 32-bit FDT cell')
    return struct.unpack('>I', value)[0]
