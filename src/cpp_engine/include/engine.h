#ifndef ENGINE_H
#define ENGINE_H

#include "bar.h"
#include <string>
#include <vector>
#include <unordered_map>
#include <functional>
#include <memory>

// 前向声明
namespace cpp_engine {
class Context;
}

namespace cpp_engine {

/**
 * @brief 订单结构
 */
struct Order {
    std::string symbol;
    std::string action;  // "buy" or "sell"
    int quantity;
    double price;
    std::string date;    // 下单日期
};

/**
 * @brief 交易记录
 */
struct Trade {
    std::string symbol;
    std::string action;
    int quantity;
    double price;
    std::string date;
    double commission = 0.0;      // 手续费
    double cash_before = 0.0;     // 交易前资金
    double cash_after = 0.0;      // 交易后资金
    int position_before = 0;      // 交易前持仓
    int position_after = 0;       // 交易后持仓
    std::string status;           // 订单状态（成功/失败）
};

/**
 * @brief 回测结果
 */
struct BacktestResult {
    double total_return = 0.0;
    double sharpe_ratio = 0.0;
    double max_drawdown = 0.0;
    int total_trades = 0;
    double win_rate = 0.0;
    std::vector<double> equity_curve;
    std::vector<Trade> trades;
};

/**
 * @brief C++回测引擎
 *
 * 核心功能：
 * - 加载历史数据
 * - 执行策略回调
 * - 订单匹配和执行
 * - 持仓管理
 */
class SimpleCppEngine {
public:
    SimpleCppEngine(double initial_capital = 1000000.0,
                   double commission_rate = 0.0003);

    // ========== 数据加载 ==========

    /**
     * @brief 加载K线数据
     *
     * @param bars_data 从Python传入的数据列表
     * 每个元素包含：trade_date (string), 数据字段 (map<string, double>)
     */
    void load_data(const std::vector<std::pair<std::string, std::unordered_map<std::string, double>>>& bars_data);

    // ========== 策略执行 ==========

    /**
     * @brief 运行回测
     *
     * @param strategy_callback Python策略回调函数
     *        接收Context&参数，在每个bar上调用
     */
    void run(std::function<void(Context&)> strategy_callback);

    // ========== 数据查询接口（供Context调用）==========

    std::vector<double> get_series(const std::string& field, int count);
    double get_bar(const std::string& field, int offset);
    std::unordered_map<std::string, double> get_current_bar_data();
    std::string get_current_date();
    double get_cash();
    int get_position(const std::string& symbol);

    // ========== 订单接口（供Context调用）==========

    void submit_buy_order(const std::string& symbol, int quantity, double price);
    void submit_sell_order(const std::string& symbol, int quantity, double price);

    // ========== 结果查询 ==========

    BacktestResult get_results() const;

private:
    // 引擎状态
    double initial_capital_;
    double commission_rate_;
    double cash_;
    std::unordered_map<std::string, int> positions_;  // symbol -> quantity

    // K线数据
    std::vector<Bar> bars_;
    int current_bar_index_;

    // 订单和交易
    std::vector<Order> pending_orders_;
    std::vector<Order> all_orders_;
    std::vector<Trade> trades_;

    // 净值曲线
    std::vector<double> equity_curve_;

    // ========== 内部辅助方法 ==========

    void execute_pending_orders();
    void update_equity();
    double calculate_total_asset();
    void reset();
    void save_trades_to_csv();  // 保存交易记录到CSV
    void close_all_positions();  // 平掉所有持仓（回测结束时调用）
};

} // namespace cpp_engine

#endif // ENGINE_H
