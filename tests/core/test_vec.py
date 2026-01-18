# -*- coding: utf-8 -*-
from contextlib import contextmanager
import moose
import numpy as np


print(f"[INFO ] Using moose {moose.version()} from {moose.__file__}")


@contextmanager
def make_container(path='test'):
    """Create a temporary MOOSE element that's deleted after use."""
    obj = moose.Neutral(path)
    cwe = moose.getCwe()
    try:
        moose.ce(obj)
        yield obj
    finally:
        moose.ce(cwe)
        moose.delete(obj)


def test_vec_wrapping():
    with make_container() as model:
        foo = moose.Pool('foo1', 500)
        bar = moose.vec(foo)
        assert len(bar) == 500, len(bar)
    print('test_vec_wrapping', 'OK')


def test_vec_constructor():
    num = 10
    with make_container() as model:
        iaf = moose.vec('iaf', n=num, dtype='IntFire')
        assert len(iaf) == num, 'Size does not match'
    print("All done")
    print('test_vec_constructor', 'OK')


def test_setfield_array():
    num = 10
    with make_container() as model:
        iaf = moose.vec('iaf', n=num, dtype='IntFire')
        iaf.Vm = np.arange(num)
        for jj in range(num):
            assert iaf[jj].Vm == jj, f'Value mismatch in index {jj}'
    print('test_setfield_array', 'OK')


def test_setfield_broadcast():
    """Test broadcasting: if setting a value field of a vec with a scalar sticks, and all entries are the same"""
    with make_container() as model:
        foo = moose.Pool('foo3', 500)
        foo.vec.concInit = 0.123
        print(foo.vec)
        assert foo.concInit == 0.123, foo.concInit
        assert np.allclose(foo.vec.concInit, [0.123]*500)
    print('test_setfield_broadcast', "OK")


def test_veclookupfield_scalar_set():
    print('Testing VecLookupField')
    Avogadro = 6.022e23
    num = 10
    with make_container() as model:
        foo = moose.vec('fn',n=num,  dtype='Function')
        foo.c['A'] = Avogadro
        for ii in range(num):
            assert np.isclose(foo[ii].c['A'], Avogadro)
    print('test_veclookupfield_scalar_set', 'OK')


def test_veclookupfield_vector_set():
    print('Testing VecLookupField')
    num = 10
    with make_container() as model:
        foo = moose.vec('fn',n=num,  dtype='Function')
        val = np.arange(num)
        foo.c['A'] = val
        assert np.allclose(foo.c['A'], val)
    print('test_veclookupfield_vector_set', 'OK')


def test_vecelementfield_scalar_set():
    print('Testing VecElementField: scalar broadcast')
    num = 10
    numSyn = 5
    with make_container() as model:
        sh = moose.SimpleSynHandler('sh', n=num)
        sh.synapse.num = numSyn
        el = moose.element(sh.synapse.path)
        sh.numSynapses = numSyn
        assert len(sh.synapse.weight) == numSyn, 'Could not set num for elementfield'
        assert sh.vec[1].synapse.num == 0, 'Should not have set num for other element'
        sh.vec.synapse.num = numSyn
        assert np.allclose(sh.vec.synapse.num, np.ones(num) * numSyn), 'num not set correctly by scalar broadcast'
    print('test_vecelementfield_scalar_set', 'OK')

def test_vecelementfield_seq_set():
    print('Testing VecElementField: set field from sequence ')
    num = 10
    with make_container() as model:
        sh = moose.SimpleSynHandler('sh', n=num)
        sh.vec.synapse.num = np.arange(num)
        assert np.allclose(sh.vec.synapse.num, np.arange(num)), 'num not set correctly from sequence'
        sh.vec.synapse.delay = np.arange(num)
        for ii, inner in enumerate(sh.vec.synapse.delay):
            assert np.allclose(inner, ii), 'broadcast of inner scalars to field elements failed'
    print('test_vecelementfield_seq_set', 'OK')

if __name__ == '__main__':
    test_vec_wrapping()
    test_vec_constructor()
    test_setfield_array()
    test_setfield_broadcast()
    test_veclookupfield_scalar_set()
    test_veclookupfield_vector_set()
    test_vecelementfield_scalar_set()
    test_vecelementfield_seq_set()
