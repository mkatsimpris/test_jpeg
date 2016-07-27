#!/usr/bin/env python
# coding=utf-8

from myhdl import Signal, always_comb, always_seq, block, intbv, ResetSignal
from jpegenc.subblocks.common import triple_buffer_in, triple_buffer_out, block_buffer_in, block_buffer_out
from myhdl.conversion import analyze
from math import log2, ceil
from jpegenc.subblocks.block_buffer import block_buffer
from jpegenc.subblocks.common import assign

@block
def triple_block_buffer(inputs, outputs, clock, reset, line_width=16):

    data_in_each_buffer = line_width * 8
    data_to_read = data_in_each_buffer * 3

    """first block buffer"""
    block_buffer_in_1 = block_buffer_in()
    block_buffer_out_1 = block_buffer_out()
    block_buffer_1 = block_buffer(block_buffer_in_1, block_buffer_out_1, clock, reset, line_width)

    """second block buffer"""
    block_buffer_in_2 = block_buffer_in()
    block_buffer_out_2 = block_buffer_out()
    block_buffer_2 = block_buffer(block_buffer_in_2, block_buffer_out_2, clock, reset, line_width)

    """third block buffer"""
    block_buffer_in_3 = block_buffer_in()
    block_buffer_out_3 = block_buffer_out()
    block_buffer_3 = block_buffer(block_buffer_in_3, block_buffer_out_3, clock, reset, line_width)

    """fourth block buffer"""
    block_buffer_in_4 = block_buffer_in()
    block_buffer_out_4 = block_buffer_out()
    block_buffer_4 = block_buffer(block_buffer_in_4, block_buffer_out_4, clock, reset, line_width)


    buffer_select_write = Signal(intbv(0, min=0, max=4))
    buffer_select_read = Signal(intbv(0, min=0, max=4))
    buffer_select_read_1 = Signal(intbv(0, min=0, max=4))

    data_valid_or = Signal(bool(0))

    write_counter = Signal(intbv(0, min=0, max =data_in_each_buffer))
    read_counter = Signal(intbv(0, min=0, max =data_to_read))

    @always_comb
    def data_input():
        block_buffer_in_1.data_in.next = inputs.data_in
        block_buffer_in_2.data_in.next = inputs.data_in
        block_buffer_in_3.data_in.next = inputs.data_in
        block_buffer_in_4.data_in.next = inputs.data_in

    @always_comb
    def or_signals():
        data_valid_or.next = block_buffer_out_1.data_valid or block_buffer_out_2.data_valid or block_buffer_out_3.data_valid\
        or block_buffer_out_4.data_valid

    @always_seq(clock.posedge, reset=reset)
    def write_counter_update():
        if inputs.data_valid:
            if write_counter == data_in_each_buffer - 1:
                write_counter.next = 0
                if buffer_select_write == 3:
                    buffer_select_write.next = 0
                else:
                    buffer_select_write.next = buffer_select_write + 1
            else:
                write_counter.next = write_counter + 1

    @always_seq(clock.posedge, reset=reset)
    def read_counter_update():
        if data_valid_or:
            if read_counter == data_to_read - 3:
                read_counter.next = read_counter + 1
                if buffer_select_read == 3:
                    buffer_select_read.next = 0
                else:
                    buffer_select_read.next = buffer_select_read + 1
            elif read_counter == data_to_read - 1:
                read_counter.next = 0
                if buffer_select_read_1 == 3:
                    buffer_select_read_1.next = 0
                else:
                    buffer_select_read_1.next = buffer_select_read_1 + 1
            else:
                read_counter.next = read_counter + 1

    @always_comb
    def read_mux():
        if buffer_select_read == 0 and buffer_select_read == 0:
            block_buffer_in_1.ready_to_output_data.next = True
            block_buffer_in_2.ready_to_output_data.next = False
            block_buffer_in_3.ready_to_output_data.next = False
            block_buffer_in_4.ready_to_output_data.next = False
        elif buffer_select_read == 1 and buffer_select_read_1 == 0:
            block_buffer_in_1.ready_to_output_data.next = True
            block_buffer_in_2.ready_to_output_data.next = True
            block_buffer_in_3.ready_to_output_data.next = False
            block_buffer_in_4.ready_to_output_data.next = False
        elif buffer_select_read == 1 and buffer_select_read_1 == 1:
            block_buffer_in_1.ready_to_output_data.next = False
            block_buffer_in_2.ready_to_output_data.next = True
            block_buffer_in_3.ready_to_output_data.next = False
            block_buffer_in_4.ready_to_output_data.next = False
        elif  buffer_select_read == 2 and buffer_select_read_1 == 1:
            block_buffer_in_1.ready_to_output_data.next = False
            block_buffer_in_2.ready_to_output_data.next = True
            block_buffer_in_3.ready_to_output_data.next = True
            block_buffer_in_4.ready_to_output_data.next = False
        elif  buffer_select_read == 2 and buffer_select_read_1 == 2:
            block_buffer_in_1.ready_to_output_data.next = False
            block_buffer_in_2.ready_to_output_data.next = False
            block_buffer_in_3.ready_to_output_data.next = True
            block_buffer_in_4.ready_to_output_data.next = False
        elif  buffer_select_read == 3 and buffer_select_read_1 == 2:
            block_buffer_in_1.ready_to_output_data.next = False
            block_buffer_in_2.ready_to_output_data.next = False
            block_buffer_in_3.ready_to_output_data.next = True
            block_buffer_in_4.ready_to_output_data.next = True
        else:
            block_buffer_in_1.ready_to_output_data.next = False
            block_buffer_in_2.ready_to_output_data.next = False
            block_buffer_in_3.ready_to_output_data.next = False
            block_buffer_in_4.ready_to_output_data.next = True

    @always_comb
    def write_mux():
        if inputs.data_valid:
            if buffer_select_write == 0:
                block_buffer_in_1.data_valid.next = True
                block_buffer_in_2.data_valid.next = False
                block_buffer_in_3.data_valid.next = False
                block_buffer_in_4.data_valid.next = False
            elif buffer_select_write == 1:
                block_buffer_in_1.data_valid.next = False
                block_buffer_in_2.data_valid.next = True
                block_buffer_in_3.data_valid.next = False
                block_buffer_in_4.data_valid.next = False
            elif buffer_select_write == 2:
                block_buffer_in_1.data_valid.next = False
                block_buffer_in_2.data_valid.next = False
                block_buffer_in_3.data_valid.next = True
                block_buffer_in_4.data_valid.next = False
            else:
                block_buffer_in_1.data_valid.next = False
                block_buffer_in_2.data_valid.next = False
                block_buffer_in_3.data_valid.next = False
                block_buffer_in_4.data_valid.next = True
        else:
                block_buffer_in_1.data_valid.next = False
                block_buffer_in_2.data_valid.next = False
                block_buffer_in_3.data_valid.next = False
                block_buffer_in_4.data_valid.next = False

    @always_seq(clock.posedge, reset=reset)
    def output_assign():
        if buffer_select_read_1 == 0:
            outputs.data_out.next = block_buffer_out_1.data_out
        elif buffer_select_read_1 == 1:
            outputs.data_out.next = block_buffer_out_2.data_out
        elif buffer_select_read_1 == 2:
            outputs.data_out.next = block_buffer_out_3.data_out
        else:
            outputs.data_out.next = block_buffer_out_4.data_out

    @always_seq(clock.posedge, reset=reset)
    def data_valid_assign():
        if data_valid_or:
            outputs.data_valid.next = True
        else:
            outputs.data_valid.next = False

    return (block_buffer_1, block_buffer_2, block_buffer_3, block_buffer_4, data_valid_assign,
            output_assign, read_mux, write_mux, read_counter_update, write_counter_update,
            data_input, or_signals)

def convert():

    inputs = triple_buffer_in()
    outputs = triple_buffer_out()
    clock = Signal(bool(0))
    reset = ResetSignal(1, True, True)
    inst = triple_block_buffer(inputs, outputs, clock, reset)
    inst.convert(hdl="vhdl")
    analyze.simulator="ghdl"
    assert inst.analyze_convert() == 0

#convert()








