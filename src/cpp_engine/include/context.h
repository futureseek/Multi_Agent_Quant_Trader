#ifndef CONTEXT_H
#define CONTEXT_H

#include <string>
#include <vector>
#include <unordered_map>
#include "bar.h"

namespace cpp_engine {

// 前向声明
class SimpleCppEngine;

/**
 * @brief 策略上下文对象
 *
 * 提供给Python策略的数据访问和交易接口
 * 类似于现有SimpleContext，但由C++实现
 */
class Context {
public:
    explicit Context(SimpleCppEngine* engine);

    // ========== 数据访问接口 ==========

    /**
     * @brief 获取序列数据
     *
     * @param symbol 股票代码（兼容Python接口，当前版本忽略）
     * @param field 字段名（close, open, high, low, vol等）
     * @param count 获取数量
     * @return std::vector<double> 字段值列表，按时间顺序（从旧到新）
     */
    std::vector<double> get_series(const std::string& symbol, const std::string& field, int count);

    /**
     * @brief 获取单个K线字段值
     *
     * @param symbol 股票代码（兼容Python接口，当前版本忽略）
     * @param field 字段名
     * @param offset 偏移量，0表示当前bar，1表示前1根bar
     * @return double 字段值
     */
    double get_bar(const std::string& symbol, const std::string& field, int offset = 0);

    /**
     * @brief 获取当前K线的所有数据
     */
    std::unordered_map<std::string, double> get_current_bar();

    /**
     * @brief 获取当前日期
     */
    std::string get_current_date();

    // ========== 交易接口 ==========

    /**
     * @brief 下买单
     *
     * @param symbol 股票代码（如600000.SH）
     * @param quantity 买入数量
     * @param price 买入价格
     */
    void buy(const std::string& symbol, int quantity, double price);

    /**
     * @brief 下卖单
     *
     * @param symbol 股票代码
     * @param quantity 卖出数量
     * @param price 卖出价格
     */
    void sell(const std::string& symbol, int quantity, double price);

    // ========== 查询接口 ==========

    /**
     * @brief 获取可用资金
     */
    double get_cash();

    /**
     * @brief 获取持仓数量
     *
     * @param symbol 股票代码
     * @return int 持仓数量（正数表示多头）
     */
    int get_position(const std::string& symbol);

private:
    SimpleCppEngine* engine_;  // 引用引擎（不拥有所有权）
};

} // namespace cpp_engine

#endif // CONTEXT_H
