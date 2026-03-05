cmake_minimum_required(VERSION 3.15)
project(cpp_engine VERSION 0.1.0 LANGUAGES CXX)

# C++17标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 查找Python和pybind11
find_package(Python 3.10 COMPONENTS Interpreter Development REQUIRED)

# 通过Python模块查找pybind11（更可靠）
execute_process(
    COMMAND "${Python_EXECUTABLE}" -c "import pybind11; print(pybind11.get_cmake_dir())"
    OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

if(EXISTS "${PYBIND11_CMAKE_DIR}")
    list(APPEND CMAKE_PREFIX_PATH "${PYBIND11_CMAKE_DIR}")
endif()

find_package(pybind11 REQUIRED)

# 设置编译选项
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 源文件
set(SOURCES
    src/context.cpp
    src/engine.cpp
    src/python_bindings.cpp
)

# 创建pybind11模块
pybind11_add_module(cpp_engine ${SOURCES})

# 包含目录
target_include_directories(cpp_engine PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${Python_INCLUDE_DIRS}
)

# 链接库
target_link_libraries(cpp_engine PRIVATE ${Python_LIBRARIES})

# 设置输出属性
set_target_properties(cpp_engine PROPERTIES
    CXX_VISIBILITY_PRESET "hidden"
    VISIBILITY_INLINES_HIDDEN ON
)

# 安装规则（可选）
install(TARGETS cpp_engine
    LIBRARY DESTINATION .
)
