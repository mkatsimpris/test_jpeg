#!/usr/bin/env python
# coding=utf-8

from myhdl import Signal, always_comb, always_seq, block, intbv, ResetSignal
from jpegenc.subblocks.common import ram_in, ram_out, block_buffer_in, block_buffer_out
from myhdl.conversion import analyze
from math import log2, ceil
from jpegenc.subblocks.block_buffer import RAM
from jpegenc.subblocks.common import assign

@block
def block_buffer(inputs, outputs, clock, reset, line_width=16):
    """Block Buffer Module

    This modules consists of 8 rams. The size of the rams is define by The
    parameter line_width.

    Inputs:
        data_in, data_valid, ready_to_output_data
    Outputs:
        data_out, data_valid, write_all, readd_all
    """
    addr_width = int(ceil(log2(line_width)))
    block_number = int(line_width/8.0)
    data_width = inputs.data_width

    row_select = Signal(intbv(0, min=0, max=8))
    row_read =  Signal(intbv(0, min=0, max=8))
    row_read_reg =  Signal(intbv(0, min=0, max=8))
    current_block = Signal(intbv(0, min=0, max=line_width))
    current_block_1 = Signal(intbv(0, min=0, max=line_width))
    read_all_reg = Signal(bool(0))

    pixel_row_write = Signal(intbv(0, min=0, max=line_width))
    pixel_row_read = Signal(intbv(0, min=0, max=line_width))
    start_to_output_data = Signal(bool(0))

    data_in_temp = [Signal(intbv(0)[data_width:]) for _ in range(8)]
    write_en_temp = [Signal(bool(0)) for _ in range(8)]
    write_addr_temp = [Signal(intbv(0)[addr_width:]) for _ in range(8)]
    ram_data_out_temp = [Signal(intbv(0)[data_width:]) for _ in range(8)]

    left_index = Signal(intbv(0, min=0, max=line_width))
    left_index_1 = Signal(intbv(0, min=0, max=line_width))
    left_index_2 = Signal(intbv(0, min=0, max=line_width))
    right_index = Signal(intbv(0, min=0, max=line_width))

    pass_num = Signal(intbv(0, min=0, max=3))

    data_valid_reg_1, data_valid_reg_2 = [Signal(bool(0)) for _ in range(2)]

    # list of interfaces for the rams
    ram_inputs = []
    ram_outputs = []
    for i in range(8):
        ram_inputs += [ram_in(data_width, addr_width)]
        ram_outputs += [ram_out(data_width)]

    #list of the ram modules and assignments
    ram_insts = []
    for i in range(8):
        ram_insts += [RAM(ram_inputs[i], ram_outputs[i], clock, reset, line_width)]
        ram_insts += [assign(ram_inputs[i].data_in, data_in_temp[i])]
        ram_insts += [assign(ram_inputs[i].write_en, write_en_temp[i])]
        ram_insts += [assign(ram_inputs[i].write_addr, write_addr_temp[i])]
        ram_insts += [assign(ram_data_out_temp[i], ram_outputs[i].data_out)]
        ram_insts += [assign(ram_inputs[i].read_addr, pixel_row_read)]

    @always_seq(clock.posedge, reset=reset)
    def ram_input_assign():
        """store inputs in a temporary array"""
        for i in range(8):
            data_in_temp[i].next = inputs.data_in

    @always_seq(clock.posedge, reset=reset)
    def pixel_write_update():
        """write signals update"""
        if inputs.data_valid:
            if pixel_row_write == line_width - 1:
                pixel_row_write.next = 0
                if row_select == 7:
                    row_select.next = 0
                    outputs.write_all.next = True
                else:
                    row_select.next = row_select + 1
                    outputs.write_all.next = False
            else:
                pixel_row_write.next = pixel_row_write + 1
        else:
            outputs.write_all.next = False

    @always_seq(clock.posedge, reset=reset)
    def write_enable_update():
        """write enable update"""
        if inputs.data_valid:
            for i in range(8):
                if row_select == i:
                    write_en_temp[i].next = True
                else:
                    write_en_temp[i].next = False
        else:
            for i in range(8):
                write_en_temp[i].next = False

    @always_seq(clock.posedge, reset=reset)
    def write_addr_update():
        """write address update"""
        if inputs.data_valid:
            write_addr_temp[row_select].next = pixel_row_write

    @always_seq(clock.posedge, reset=reset)
    def output_assign():
        """from the temporary data out array to output signal assign"""
        outputs.data_out.next = ram_data_out_temp[row_read_reg]

    @always_seq(clock.posedge, reset=reset)
    def pixel_read_update():
        """update the read signals"""
        row_read_reg.next = row_read
        outputs.read_all.next = read_all_reg
        if start_to_output_data and inputs.ready_to_output_data:
            if pixel_row_read == right_index:
                pixel_row_read.next = left_index
                if row_read == 7:
                    row_read.next = 0
                    if pass_num == 2:
                        pass_num.next = 0
                        if current_block == block_number - 1:
                            current_block.next = 0
                            read_all_reg.next = True
                        else:
                            current_block.next = current_block + 1
                    else:
                        pass_num.next = pass_num + 1
                else:
                    row_read.next = row_read + 1
            else:
                pixel_row_read.next = pixel_row_read + 1
        else:
            pixel_row_read.next = 0
            row_read.next = 0
            pass_num.next = 0
            current_block.next = 0
            read_all_reg.next = False

    @always_seq(clock.posedge, reset=reset)
    def block_update():
        """block counter update"""
        if pixel_row_read == right_index - 4:
            if row_read == 7:
                if pass_num == 2:
                    if current_block_1 == block_number - 1:
                        current_block_1.next = 0
                    else:
                        current_block_1.next = current_block_1 + 1

    @always_seq(clock.posedge, reset=reset)
    def index_muls():
        """compute the indeces for the block indexing"""
        left_index_1.next = current_block * 8
        left_index_2.next = current_block_1 * 8
        right_index.next = (current_block + 1) * 8 - 1

    @always_comb
    def right_index_mux():
        """count the number of passes"""
        if pass_num == 2:
            left_index.next = left_index_2
        else:
            left_index.next = left_index_1

    @always_seq(clock.posedge, reset=reset)
    def start_to_output():
        """start to output data"""
        if row_select == 7 and pixel_row_write == 7:
            start_to_output_data.next = True

    @always_seq(clock.posedge, reset=reset)
    def start_to_output_1():
        """data valid signal assert"""
        outputs.data_valid.next = data_valid_reg_1
        if start_to_output_data and inputs.ready_to_output_data:
            data_valid_reg_1.next = True
            outputs.data_valid.next = data_valid_reg_1
        else:
            data_valid_reg_1.next = False
            outputs.data_valid.next = data_valid_reg_1

    return (ram_insts, ram_input_assign, pixel_write_update, write_enable_update, index_muls,
            write_addr_update, output_assign, start_to_output, pixel_read_update, block_update,
            right_index_mux, start_to_output_1)

def convert():

    inputs = block_buffer_in()
    outputs = block_buffer_out()
    clock = Signal(bool(0))
    reset = ResetSignal(1, True, True)
    inst = block_buffer(inputs, outputs, clock, reset)
    inst.convert(hdl="vhdl")
    analyze.simulator="ghdl"
    assert inst.analyze_convert() == 0

#convert()






