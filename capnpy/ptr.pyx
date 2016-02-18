# This is the Cython version of ptr.py: the two versions should stay in-sync,
# as they are supposed to implement the same API. Make sure that every feature
# you add is tested by test_ptr.
#
# We need a separate version because cython is not able to fully optimize
# propertyso a pyx file allows us to play bit tricks more easily

import struct
import sys
from libc.limits cimport LONG_MAX
from libc.stdint cimport INT64_MAX

cdef long as_signed(long x, char bits):
    if x >= 1<<(bits-1):
        x -= 1<<bits
    return x

cdef class Ptr(int):
    ## lsb                      generic pointer                      msb
    ## +-+-----------------------------+-------------------------------+
    ## |A|             B               |               C               |
    ## +-+-----------------------------+-------------------------------+
    ##
    ## A (2 bits) = 0, pointer kind (0 for struct, 1 for list)
    ## B (30 bits) = Offset, in words, from the end of the pointer to the
    ##     start of the struct's data section.  Signed.
    ## C (32 bits) = extra info, depends on the kind

    @classmethod
    def new(cls, kind, offset, extra):
        ptr = 0
        ptr |= extra << 32
        ptr |= offset << 2
        ptr |= kind
        return cls(ptr)

    @classmethod
    def from_bytes(cls, s):
        ptr = struct.unpack('q', s)[0]
        return cls(ptr)

    def to_bytes(self):
        return struct.pack('q', self)

    property kind:
        def __get__(self):
            return self & 0x3

    property offset:
        def __get__(self):
            return as_signed(self>>2 & 0x3fffffff, 30)

    property extra:
        def __get__(self):
            return self>>32

    cpdef deref(self, long offset):
        """
        Compute the offset of the object pointed to, assuming that the Ptr itself
        is at ``offset``
        """
        # the +1 is needed because the offset is measured from the end of the
        # pointer itself
        return offset + (self.offset+1)*8

    cpdef specialize(self):
        """
        Return a StructPtr or ListPtr, depending on self.kind
        """
        kind = self.kind
        if kind == StructPtr.KIND:
            return StructPtr(self)
        elif kind == ListPtr.KIND:
            return ListPtr(self)
        elif kind == FarPtr.KIND:
            return FarPtr(self)
        else:
            raise ValueError("Unknown ptr kind: %d" % kind)


cdef class StructPtr(Ptr):
    ## lsb                      struct pointer                       msb
    ## +-+-----------------------------+---------------+---------------+
    ## |A|             B               |       C       |       D       |
    ## +-+-----------------------------+---------------+---------------+
    ##
    ## A (2 bits) = 0, to indicate that this is a struct pointer.
    ## B (30 bits) = Offset, in words, from the end of the pointer to the
    ##     start of the struct's data section.  Signed.
    ## C (16 bits) = Size of the struct's data section, in words.
    ## D (16 bits) = Size of the struct's pointer section, in words.

    KIND = 0

    @classmethod
    def new(cls, offset, data_size, ptrs_size):
        ptr = 0
        ptr |= ptrs_size << 48
        ptr |= data_size << 32
        ptr |= offset << 2
        ptr |= cls.KIND
        return cls(ptr)

    property data_size:
        def __get__(self):
            return self>>32 & 0xffff

    property ptrs_size:
        def __get__(self):
            return self>>48 & 0xffff


cdef class ListPtr(Ptr):
    ## lsb                       list pointer                        msb
    ## +-+-----------------------------+--+----------------------------+
    ## |A|             B               |C |             D              |
    ## +-+-----------------------------+--+----------------------------+
    ##
    ## A (2 bits) = 1, to indicate that this is a list pointer.
    ## B (30 bits) = Offset, in words, from the end of the pointer to the
    ##     start of the first element of the list.  Signed.
    ## C (3 bits) = Size of each element:
    ##     0 = 0 (e.g. List(Void))
    ##     1 = 1 bit
    ##     2 = 1 byte
    ##     3 = 2 bytes
    ##     4 = 4 bytes
    ##     5 = 8 bytes (non-pointer)
    ##     6 = 8 bytes (pointer)
    ##     7 = composite (see below)
    ## D (29 bits) = Number of elements in the list, except when C is 7

    KIND = 1

    # size tag
    SIZE_BIT = 1
    SIZE_8 = 2
    SIZE_16 = 3
    SIZE_32 = 4
    SIZE_64 = 5
    SIZE_PTR = 6
    SIZE_COMPOSITE = 7

    # map each size tag to the corresponding length in bytes. SIZE_BIT is
    # None, as it is handled specially
    SIZE_LENGTH = (None, None, 1, 2, 4, 8, 8)

    @classmethod
    def new(cls, ptr_offset, size_tag, item_count):
        ptr = 0
        ptr |= item_count << 35
        ptr |= size_tag << 32
        ptr |= ptr_offset << 2
        ptr |= cls.KIND
        return cls(ptr)

    property size_tag:
        def __get__(self):
            return self>>32 & 0x7

    property item_count:
        def __get__(self):
            return self>>35


cdef class FarPtr(Ptr):
    ## lsb                        far pointer                        msb
    ## +-+-+---------------------------+-------------------------------+
    ## |A|B|            C              |               D               |
    ## +-+-+---------------------------+-------------------------------+

    ## A (2 bits) = 2, to indicate that this is a far pointer.
    ## B (1 bit) = 0 if the landing pad is one word, 1 if it is two words.
    ## C (29 bits) = Offset, in words, from the start of the target segment
    ##     to the location of the far-pointer landing-pad within that
    ##     segment.  Unsigned.
    ## D (32 bits) = ID of the target segment.  (Segments are numbered
    ##     sequentially starting from zero.)

    KIND = 2

    @classmethod
    def new(cls, landing_pad, offset, target):
        ptr = 0
        ptr |= target << 32
        ptr |= offset << 3
        ptr |= landing_pad << 2
        ptr |= cls.KIND
        return cls(ptr)

    property landing_pad:
        def __get__(self):
            return self>>2 & 1

    property offset:
        def __get__(self):
            return self>>3 & 0x1fffffff

    property target:
        def __get__(self):
            return self>>32
