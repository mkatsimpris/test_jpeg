#!/usr/bin/env python
# coding=utf-8

import numpy as np

from itertools import chain

import myhdl
from myhdl import (StopSimulation, block, Signal, ResetSignal, intbv,
                   delay, instance, always_comb, always_seq)
from myhdl.conversion import verify
from jpegenc.testing import sim_available, run_testbench
from jpegenc.testing import clock_driver, reset_on_start, pulse_reset

from jpegenc.subblocks.common import block_buffer_in, block_buffer_out
from jpegenc.subblocks.block_buffer import block_buffer

class InputsAndOutputs(object):

    def __init__(self, rows=24, cols=24):
        self.rows = rows
        self.cols = cols
        self.matrix = self.random_matrix(rows, cols)
        self.inputs = []
        self.outputs = []

    def initialize(self):
        self.inputs = list(chain.from_iterable(self.matrix.tolist()))
        blocks_x = int(self.rows/8.0)
        blocks_y = int(self.cols/8.0)
        for i in range(blocks_x):
            for j in range(blocks_y):
                sub_matrix = self.matrix[i*8:(i+1)*8, j*8:(j+1)*8]
                self.outputs += list(chain.from_iterable(sub_matrix.tolist())) * 3

    def random_matrix(self, rows, cols):
        random_matrix = np.random.rand(rows, cols)
        random_matrix = np.rint(255*random_matrix)
        random_matrix = random_matrix.astype(int)
        return random_matrix

def test_block_buffer():

    clock = Signal(bool(0))
    reset = ResetSignal(1, active=True, async=True)

    inputs = block_buffer_in()
    outputs = block_buffer_out()

    rows, cols = 8, 32
    inandouts = InputsAndOutputs(rows, cols)
    inandouts.initialize()

    input_list = inandouts.inputs
    output_list = inandouts.outputs

    print(input_list)
    print(output_list)

    @block
    def bench_block_buffer():
        tdut = block_buffer(inputs, outputs, clock, reset, cols)
        tbclock = clock_driver(clock)

        @instance
        def tbstim():
            yield pulse_reset(reset, clock)
            inputs.data_valid.next = True
            inputs.ready_to_output_data.next = True

            data = 0
            while(data != len(input_list)):
                inputs.data_in.next = input_list[data]
                data += 1
                yield clock.posedge
            inputs.data_valid.next = False

        @instance
        def monitor():
            yield outputs.data_valid.posedge
            yield delay(1)
            for i in range(len(output_list)):
                print("%d %d" %(int(outputs.data_out), output_list[i]))
                assert outputs.data_out == output_list[i]
                yield clock.posedge
                yield delay(1)
            raise StopSimulation

        return tdut, tbstim, tbclock, monitor

    run_testbench(bench_block_buffer)

test_block_buffer()
