import argparse
import logging
import marshal
import opcode
import os
import py_compile
import sys
import math
import string
import types

if sys.version_info < (3, 6):
    sys.exit("Stegosaurus requires Python 3.6 or later")


class MutableBytecode():
    def __init__(self, code):
        self.originalCode = code
        self.bytes = bytearray(code.co_code)
        self.consts = [MutableBytecode(const) if isinstance(const, types.CodeType) else const for const in code.co_consts]


def _bytesAvailableForPayload(mutableBytecodeStack, explodeAfter, logger=None):
    for mutableBytecode in reversed(mutableBytecodeStack):
        bytes = mutableBytecode.bytes
        consecutivePrintableBytes = 0
        for i in range(0, len(bytes)):
            if chr(bytes[i]) in string.printable:
                consecutivePrintableBytes += 1
            else:
                consecutivePrintableBytes = 0

            if i % 2 == 0 and bytes[i] < opcode.HAVE_ARGUMENT:
                if consecutivePrintableBytes >= explodeAfter:
                    if logger:
                        logger.debug("Skipping available byte to terminate string leak")
                    consecutivePrintableBytes = 0
                    continue
                yield (bytes, i + 1)


def _createMutableBytecodeStack(mutableBytecode):
    def _stack(parent, stack):
        stack.append(parent)

        for child in [const for const in parent.consts if isinstance(const, MutableBytecode)]:
            _stack(child, stack)

        return stack

    return _stack(mutableBytecode, [])


def _dumpBytecode(header, code, carrier, logger):
    try:
        f = open(carrier, "wb")
        f.write(header)
        marshal.dump(code, f)
        logger.info("Wrote carrier file as %s", carrier)
    finally:
        f.close()


def _embedPayload(mutableBytecodeStack, payload, explodeAfter, logger):
    payloadBytes = bytearray(payload, "utf8")
    payloadIndex = 0
    payloadLen = len(payloadBytes)

    for bytes, byteIndex in _bytesAvailableForPayload(mutableBytecodeStack, explodeAfter):
        if payloadIndex < payloadLen:
            bytes[byteIndex] = payloadBytes[payloadIndex]
            payloadIndex += 1
        else:
            bytes[byteIndex] = 0

    print("Payload embedded in carrier")


def _extractPayload(mutableBytecodeStack, explodeAfter, logger):
    payloadBytes = bytearray()

    for bytes, byteIndex in _bytesAvailableForPayload(mutableBytecodeStack, explodeAfter):
        byte = bytes[byteIndex]
        if byte == 0:
            break
        payloadBytes.append(byte)

    payload = str(payloadBytes, "utf8")

    print("Extracted payload: {}".format(payload))


def _getCarrierFile(args, logger):
    carrier = args.carrier
    _, ext = os.path.splitext(carrier)

    if ext == ".py":
        carrier = py_compile.compile(carrier, doraise=True)
        logger.info("Compiled %s as %s for use as carrier", args.carrier, carrier)

    return carrier


def _initLogger(args):
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    logger = logging.getLogger("stegosaurus")
    logger.addHandler(handler)

    if args.verbose:
        if args.verbose == 1:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)

    return logger


def _loadBytecode(carrier, logger):
    try:
        f = open(carrier, "rb")
        header = f.read(12)
        code = marshal.load(f)
        logger.debug("Read header and bytecode from carrier")
    finally:
        f.close()

    return (header, code)


def _logBytesAvailableForPayload(mutableBytecodeStack, explodeAfter, logger):
    for bytes, i in _bytesAvailableForPayload(mutableBytecodeStack, explodeAfter, logger):
        logger.debug("%s (%d)", opcode.opname[bytes[i - 1]], bytes[i])


def _maxSupportedPayloadSize(mutableBytecodeStack, explodeAfter, logger):
    maxPayloadSize = 0

    for bytes, i in _bytesAvailableForPayload(mutableBytecodeStack, explodeAfter):
        maxPayloadSize += 1

    logger.info("Found %d bytes available for payload", maxPayloadSize)

    return maxPayloadSize


def _parseArgs():
    argParser = argparse.ArgumentParser()
    argParser.add_argument("carrier", help="Carrier py, pyc or pyo file")
    argParser.add_argument("-p", "--payload", help="Embed payload in carrier file")
    argParser.add_argument("-r", "--report", action="store_true", help="Report max available payload size carrier supports")
    argParser.add_argument("-s", "--side-by-side", action="store_true", help="Do not overwrite carrier file, install side by side instead.")
    argParser.add_argument("-v", "--verbose", action="count", help="Increase verbosity once per use")
    argParser.add_argument("-x", "--extract", action="store_true", help="Extract payload from carrier file")
    argParser.add_argument("-e", "--explode", type=int, default=math.inf, help="Explode payload into groups of a limited length if necessary")
    args = argParser.parse_args()

    return args


def _toCodeType(mutableBytecode):
    return types.CodeType(
        mutableBytecode.originalCode.co_argcount,
        mutableBytecode.originalCode.co_kwonlyargcount,
        mutableBytecode.originalCode.co_nlocals,
        mutableBytecode.originalCode.co_stacksize,
        mutableBytecode.originalCode.co_flags,
        bytes(mutableBytecode.bytes),
        tuple([_toCodeType(const) if isinstance(const, MutableBytecode) else const for const in mutableBytecode.consts]),
        mutableBytecode.originalCode.co_names,
        mutableBytecode.originalCode.co_varnames,
        mutableBytecode.originalCode.co_filename,
        mutableBytecode.originalCode.co_name,
        mutableBytecode.originalCode.co_firstlineno,
        mutableBytecode.originalCode.co_lnotab,
        mutableBytecode.originalCode.co_freevars,
        mutableBytecode.originalCode.co_cellvars
        )


def _validateArgs(args, logger):
    def _exit(msg):
        msg = "Fatal error: {}\nUse -h or --help for usage".format(msg)
        sys.exit(msg)

    allowedCarriers = {".py", ".pyc", ".pyo"}

    _, ext = os.path.splitext(args.carrier)

    if ext not in allowedCarriers:
        _exit("Carrier file must be one of the following types: {}, got: {}".format(allowedCarriers, ext))

    if args.payload is None:
        if not args.report and not args.extract:
            _exit("Unless -r or -x are specified, a payload is required")

    if args.extract or args.report:
        if args.payload:
            logger.warn("Payload is ignored when -x or -r is specified")
        if args.side_by_side:
            logger.warn("Side by side is ignored when -x or -r is specified")

    if args.explode and args.explode < 1:
        _exit("Values for -e must be positive integers")

    logger.debug("Validated args")


def main():
    args = _parseArgs()
    logger = _initLogger(args)

    _validateArgs(args, logger)

    carrier = _getCarrierFile(args, logger)
    header, code = _loadBytecode(carrier, logger)

    mutableBytecode = MutableBytecode(code)
    mutableBytecodeStack = _createMutableBytecodeStack(mutableBytecode)
    _logBytesAvailableForPayload(mutableBytecodeStack, args.explode, logger)

    if args.extract:
        _extractPayload(mutableBytecodeStack, args.explode, logger)
        return

    maxPayloadSize = _maxSupportedPayloadSize(mutableBytecodeStack, args.explode, logger)

    if args.report:
        print("Carrier can support a payload of {} bytes".format(maxPayloadSize))
        return

    payloadLen = len(args.payload)
    if payloadLen > maxPayloadSize:
        sys.exit("Carrier can only support a payload of {} bytes, payload of {} bytes received".format(maxPayloadSize, payloadLen))

    _embedPayload(mutableBytecodeStack, args.payload, args.explode, logger)
    _logBytesAvailableForPayload(mutableBytecodeStack, args.explode, logger)

    if args.side_by_side:
        logger.debug("Creating new carrier file name for side-by-side install")
        base, ext = os.path.splitext(carrier)
        carrier = "{}-stegosaurus{}".format(base, ext)

    code = _toCodeType(mutableBytecode)

    _dumpBytecode(header, code, carrier, logger)


if __name__ == "__main__":
    main()
