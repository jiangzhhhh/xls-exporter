excel配置表导出工具<br>

# 特点
- 详细的报错
- 支持列约束
- 支持嵌套数据定义
- 严格类型检查
- 支持自定义Formatter输出其他语法
- 保持源数据顺序输出
- 支持注释行
- 支持多sheet
- 三种结构模式:定义、列表、字典

# 内部执行流程
```
xls file->TypeTree->ValueTree-->LuaFormatter->lua file
                             |->JsonFormatter->json file
                             |->...

```

# 注释
- 以//开头的行会被过滤
- 空白行会被过滤
- 名字以=开头的sheet会被过滤
- 约束和类型同时为空的列不参与导出

# 约束
- unique
约束同一列的值不能重复
- required
约束该列的值不能为空
- def:{value}
设置默认值，如果单元格没有填写会以指定的默认值代替输出
- list
第一列的约束类型为list的话，整个表格会以列表形式输出

# 基础数据类型
- int
- float
- bool
- string


# 嵌套数据定义
- 字典
```
--------------------
|int     |string   |
--------------------
|user.age|user.name|
--------------------
|14      |haha     |
--------------------
生成:
user={age=14,name="haha"}
```

- 数组
```
-----------------------------------------------------
|int         |int         |int         |int         |
-----------------------------------------------------
|skills[0].cd|skills[0].id|skills[1].cd|skills[1].id|
-----------------------------------------------------
|1           |2           |3           |4           |
-----------------------------------------------------
生成:
skills=[{cd=1,id=2},{cd=3,id=4}]
```

- 内嵌数组
```
---------------
|int[]        |
---------------
|skills       |
---------------
|1,2,3        |
---------------
生成：
skills=[1,2,3]
```

- 元组
```
---------------
|(string,int) |
---------------
|tuple        |
---------------
|("haha",123)   |
---------------
生成：
tuple=("haha",123)
```

- 类型组合
```
------------------
|(float,float)[] |
------------------
|points          |
------------------
|(0,0),(1,1)     |
------------------
生成：
points=[(0,0),(1,1)]
```

# 其他注意事项
- 结构体/数组的成员定义必须连续定义在一起

# 构建
```
用
pyinstaller -F xls2lua.py --distpath example/Tools
构建xls2lua.exe
```

# 文法说明
## 成员id文法
```
expr = id expr_tail*
expr_tail = (struct_visit / array_visit)
struct_visit = space '.' space id
array_visit = space '[' space numeral space ']'
id = ~'[^\[\.]+'
numeral = ~'[0-9]+'
space = ~'\s*'
```

## 类型声明文法
```
type = array / tuple / base_type
array = (tuple / base_type) '[]'+
base_type = 'int' / 'bool' / 'float' / 'string'
tuple = '(' tuple_members ')'
tuple_members = type (',' space type)*
space = ~'\s*'
```

## 类型值定义文法
### 整数
```
int = space sig? (hex / bin / dec)
hex = '0x' ~r'[0-9a-fA-F]+'
bin = '0b' ~r'[0-1]+'
dec = ~r'[0-9]+'
sig = '-' / '+'
space = ~'\s*'
```

### 浮点
```
float = space sig? (floor_float / fact_float)
floor_float = numerals fact?
fact_float = numerals? fact
fact = '.' numerals
numerals = ~r'[0-9]+'
sig = '-' / '+'
space = ~'\s*'
```


### 布尔
```
bool = space (true / false / '1' / '0')
true = ('T' / 't') ('R' / 'r') ('U' / 'u') ('E' / 'e')
false = ('F' / 'f') ('A' / 'a') ('L' / 'l') ('S' / 's') ('E' / 'e')
space = ~'\s*'
```

### 字符串
```
string = double_quote_string / single_quote_string
double_quote_string = space double_quote (escaping_double_quote / double_quote_literal)*  double_quote space
single_quote_string = space single_quote (escaping_single_quote / single_quote_literal)*  single_quote space
double_quote_literal = ~'[^"]'
single_quote_literal = ~'[^\']'
escaping_double_quote = backslash double_quote
escaping_single_quote = backslash single_quote
double_quote = '"'
single_quote = "'"
backslash = '\\'
space = ~'[\s]*'
```
*如果解析字符串时，以上文法都解析失败，会将原始字符串返回