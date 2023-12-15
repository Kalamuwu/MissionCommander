# 
# networking utility functions and classes
# 

from typing import Union

class IP:
    """
    Represents an IP address.

    Static methods:

        >>> IP.str_to_int('127.0.0.1')
        2130706433
        
        >>> IP.int_to_str(2130706433)
        '127.0.0.1'

    Instance methods:

        >>> ip = IP.from_str('127.0.0.1')

        >>> str(ip)
        '127.0.0.1'
        
        >>> int(ip)
        2130706433
    """
    def __init__(self, arg: Union[int, str]):
        if isinstance(int, arg):
            self.__str = self.__class__.int_to_str(arg)
            self.__int = arg
        elif isinstance(str, arg):
            self.__str = arg
            self.__int = self.__class__.str_to_int(arg)
        else:
            raise ValueError("Argument is not a str nor int")
    
    def __str__(self):
        return self.__str
    def to_str(self):
        return self.__str
    
    def __int__(self):
        return self.__int
    def to_int(self):
        return self.__int
    
    def __bytes__(self):
        return self.__int.to_bytes(4)
    
    @staticmethod
    def str_to_int(ip: str) -> int:
        """ Returns integer representation of x.x.x.x style IP address. """
        p1,p2,p3,p4 = [int(p)&0xFF for p in ip.split('.')]
        return (p1 << 24) | (p2 << 16) | (p3 << 8) | (p4)

    @staticmethod
    def int_to_str(dec: int) -> str:
        """ Returns x.x.x.x representation of integer-encoded IP address. """
        p1 = (dec & 0xFF000000) >> 24
        p2 = (dec & 0x00FF0000) >> 16
        p3 = (dec & 0x0000FF00) >> 8
        p4 = (dec & 0x000000FF)
        return f"{p1}.{p2}.{p3}.{p4}"

    @classmethod
    def from_str(cls, ip: str):
        return cls(ip, cls.str_to_int(ip))
    
    @classmethod
    def from_int(cls, ip: int):
        return cls(cls.int_to_str(ip), ip)
