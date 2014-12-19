from capnpy.ptr import StructPtr, ListPtr
from capnpy.blob import Blob


class Struct(Blob):
    """
    Abstract base class: a blob representing a struct.

    subclasses of Struct needs to provide two attributes: __data_size__ and
    __ptrs_size__; there are two alternatives:

    1) you put the as class attributes in your subclass

    2) you use GenericStruct, where they are instance attributes (and thus
       less space-efficient, but it's handy if you need to walk the buffer
       without knowing the schema
    """

    def _ptr_offset_by_index(self, i):
        return (self.__data_size__ + i) * 8

    def _get_body_range(self):
        return self._get_body_start(), self._get_body_end()

    def _get_extra_range(self):
        return self._get_extra_start(), self._get_extra_end()

    def _get_body_start(self):
        return self._offset

    def _get_body_end(self):
        return self._offset + (self.__data_size__ + self.__ptrs_size__) * 8

    def _get_extra_start(self):
        if self.__ptrs_size__ == 0:
            return self._get_body_end()
        ptr_offset = self._ptr_offset_by_index(0)
        ptr = self._read_ptr(ptr_offset)
        return self._offset + ptr.deref(ptr_offset)

    def _get_extra_end(self):
        if self.__ptrs_size__ == 0:
            return self._get_body_end()
        #
        # the end of our extra correspond to the end of our last pointer: see
        # doc/normalize.rst for an explanation of why we can compute the extra
        # range this way
        ptr_offset = self._ptr_offset_by_index(self.__ptrs_size__ - 1)
        blob = self._follow_generic_pointer(ptr_offset)
        return blob._get_end()

    def _get_end(self):
        return self._get_extra_end()

    def _get_key(self):
        # we take the whole data section, and the non-offset part of the ptrs
        # section
        return self._get_data_key(), self._get_ptrs_key(), self._get_extra_key()

    def _get_data_key(self):
        start = self._get_body_start()
        data_end = start + self.__data_size__*8
        return self._buf[start:data_end]

    def _get_ptrs_key(self):
        start = self._get_body_start()
        ptrs_start = start + self.__data_size__*8
        ptrs_key = ''
        i = ptrs_start
        for _ in range(self.__ptrs_size__):
            ptrs_key += self._buf[i+4:i+8]
            i += 8
        return ptrs_key

    def _get_extra_key(self):
        extra_start, extra_end = self._get_extra_range()
        return self._buf[extra_start:extra_end]

    def __eq__(self, other):
        if not isinstance(other, Struct):
            return False
        return self._get_key() == other._get_key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._get_key())

class GenericStruct(Struct):

    @classmethod
    def from_buffer_and_size(cls, buf, offset, data_size, ptrs_size):
        self = cls.from_buffer(buf, offset)
        self.__data_size__ = data_size
        self.__ptrs_size__ = ptrs_size
        return self

