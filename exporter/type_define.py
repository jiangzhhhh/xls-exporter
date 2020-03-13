# 定义符号
class Types(object):
    int_t = 'int'
    bool_t = 'bool'
    string_t = 'string'
    float_t = 'float'
    struct_t = 'struct'
    array_t = 'array'
    embedded_array_t = 'embedded_array'
    dict_t = 'dict'
    tuple_t = 'tuple'


# 直接求值类型
value_types = (Types.int_t, Types.float_t, Types.bool_t, Types.string_t)
empty_values = ('', None)
