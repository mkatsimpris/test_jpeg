#!/usr/bin/env python
# coding=utf-8

from myhdl import Signal, always_comb, always_seq, block, intbv, ResetSignal
from jpegenc.subblocks.common import ram_in, ram_out
from myhdl.conversion import analyze

@block
def RAM(ram_in, ram_out, clock, reset, data_num):

    data_width = ram_in.data_width
    addr_width = ram_in.address_width

    mem = [Signal(intbv(0)[data_width:]) for i in range(data_num)]
    read_addr = Signal(intbv(0)[addr_width:])

    @always_comb
    def out():
        ram_out.data_out.next = mem[read_addr]

    @always_seq(clock.posedge, reset=reset)
    def write():
        read_addr.next = ram_in.read_addr
        if ram_in.write_en:
            mem[ram_in.write_addr].next = ram_in.data_in

    return out, write

def convert():

    inputs = ram_in()
    outputs = ram_out()
    clock = Signal(bool(0))
    reset = ResetSignal(1, True, True)

    inst = RAM(inputs, outputs, clock, reset)

    analyze.simulator = "ghdl"
    assert inst.analyze_convert() == 0

#convert()


