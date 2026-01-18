# pyrun.py ---
# Author: Subhasis Ray
# Maintainer: Dilawar Singh

# See https://github.com/BhallaLab/moose-examples/blob/b2e77237ef36e47d0080cc8c4fb6bb94313d2b5e/snippets/pyrun.py
# for details.

import os
import moose
from contextlib import redirect_stdout
import sys
import io
import difflib

# Removed first 3 lines since they change during each run.
expected_hello_world = """Init /test[0]/Hello[0]
Init World
Running Hello
Hello count = 0
Running World
World count = 0
Running Hello
Hello count = 1
Running World
World count = 1
Running Hello
Hello count = 2
Running World
World count = 2"""

expected_input_output_end = """input = 3.0
output = 9.0
input = 0.0
output = 0.0
input = 0.0
output = 0.0
input = 0.0
output = 0.0
input = 0.0
output = 0.0
input = 1.0
output = 1.0
input = 1.0
output = 1.0
input = 1.0
output = 1.0
input = 1.0
output = 1.0
input = 2.0
output = 4.0"""


def make_container(path='/test'):
    if moose.exists(path):
        moose.delete(path)
    return moose.Neutral(path)


def test_run():
    model = make_container()
    test_runner = moose.PyRun(f'{model.path}/test_run')
    test_runner.run('from datetime import datetime')
    test_runner.run('print("Hello: current time:", datetime.now().isoformat())')
    test_runner.run('output = 1.141592')
    assert test_runner.outputValue == 1.141592


def test_sequence():
    model = make_container()

    # First python runner
    hello_runner = moose.PyRun(f'{model.path}/Hello')
    hello_runner.initString = f"""
import sys
print('Init', moose.element('{model.path}/Hello').path)
hello_count = 0
"""
    hello_runner.runString = """

print('Running Hello')
print('Hello count =', hello_count)
hello_count += 1
sys.stdout.flush()
"""
    # Second python runner
    world_runner = moose.PyRun(f'{model.path}/World')
    world_runner.initString = """
import sys
print('Init World')
world_count = 0
def incr_count():
    global world_count
    world_count += 1
"""
    world_runner.runString = """
print('Running World')
print('World count =', world_count )
incr_count()
sys.stdout.flush()
"""
    world_runner.run('from datetime import datetime')
    world_runner.run('print( "World: current time:", datetime.now().isoformat())')
    moose.setClock(0, 3e-4)
    moose.setClock(1, 3e-4)
    hello_runner.tick = 0
    world_runner.tick = 1
    with io.StringIO() as buf, redirect_stdout(buf):
        moose.reinit()
        moose.start(1e-3)  # 1e-3//3e-4 = 3
        got = buf.getvalue().strip()
    assert got == expected_hello_world


def test_input_output():
    """In this test we connect PulseGen's output to a PyRun's input.

    The PyRun is set to triggered mode, so that it only executes the
    `runString` when a value is pushed by the PulseGen.

    """
    model = make_container()

    # Create a pulse generator that outputs 0 as baseline, 1 from 1 s
    # till 2 s, 2 from 2 s till 3 s, and 3 from 3 s till 4 s.
    input_pulse = moose.PulseGen(f'{model.path}/pulse')
    # set the baseline output 0
    input_pulse.baseLevel = 0.0
    # We make it generate three pulses
    input_pulse.count = 3
    input_pulse.level[0] = 1.0
    input_pulse.level[1] = 2.0
    input_pulse.level[2] = 3.0
    # Each pulse will appear 1 s after the previous one
    input_pulse.delay[0] = 1.0
    input_pulse.delay[1] = 1.0
    input_pulse.delay[2] = 1.0
    # Each pulse is 1 s wide
    input_pulse.width[0] = 1.0
    input_pulse.width[1] = 1.0
    input_pulse.width[2] = 1.0

    # Now create the PyRun object
    pyrun = moose.PyRun(f'{model.path}/pyrun')
    pyrun.runString = """
output = input_ * input_
print('input =', input_ )
print('output =', output )
"""
    pyrun.mode = moose.PYRUN_TRIG # do not run process method
    moose.connect(input_pulse, 'output', pyrun, 'trigger')
    output_table = moose.Table(f'{model.path}/output')
    moose.connect(pyrun, 'output', output_table, 'input')
    input_table = moose.Table(f'{model.path}/input')
    moose.connect(input_pulse, 'output', input_table, 'input')
    dt = 0.25
    simtime = 10.0
    moose.setClock(0, 0.25)
    moose.setClock(1, 0.25)
    moose.setClock(2, 0.25)
    moose.useClock(0, input_pulse.path, 'process')
    moose.useClock(1, pyrun.path, 'process')
    moose.useClock(2, f'{model.path}/#[ISA=Table]', 'process')
    with io.StringIO() as buf, redirect_stdout(buf):
        moose.reinit()
        moose.start(10.0)
        got = buf.getvalue().strip()
    expected_lines = expected_input_output_end.split('\n')
    end_lines = got.split('\n')[-len(expected_lines):]
    assert '\n'.join(end_lines) == expected_input_output_end
    assert output_table.vector[-1] == 4.0
    assert output_table.vector[0] == 0.0



if __name__ == '__main__':
    test_run()
    test_sequence()
    test_input_output()
