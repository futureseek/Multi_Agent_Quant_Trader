#ifndef BAR_H
#define BAR_H

#include <string>
#include <unordered_map>
#include <memory>

namespace cpp_engine {

/**
 * @brief K线数据结构
 *
 * 对应Tushare返回的日线数据格式
 * 注意：字段名必须与Tushare一致（vol而不是volume）
 */
struct Bar {
    std::string trade_date;  // 交易日期 YYYYMMDD
    double open;             // 开盘价
    double high;             // 最高价
    double low;              // 最低价
    double close;            // 收盘价
    double vol;              // 成交量（注意：不是volume）
    double amount;           // 成交额

    /**
     * @brief 转换为字段字典（兼容Tushare格式）
     */
    std::unordered_map<std::string, double> to_map() const {
        return {
            {"open", open},
            {"high", high},
            {"low", low},
            {"close", close},
            {"vol", vol},
            {"amount", amount}
        };
    }

    /**
     * @brief 从Python字典构造（通过pybind11自动转换）
     */
    static Bar from_dict(const std::unordered_map<std::string, double>& data,
                         const std::string& date) {
        Bar bar;
        bar.trade_date = date;
        bar.open = data.at("open");
        bar.high = data.at("high");
        bar.low = data.at("low");
        bar.close = data.at("close");
        bar.vol = data.at("vol");
        bar.amount = data.at("amount");
        return bar;
    }
};

} // namespace cpp_engine

#endif // BAR_H
