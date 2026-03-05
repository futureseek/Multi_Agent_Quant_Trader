#include "engine.h"
#include "context.h"
#include <stdexcept>
#include <algorithm>
#include <cmath>
#include <numeric>  // for std::accumulate
#include <fstream>   // for CSV output
#include <ctime>     // for timestamp
#include <iomanip>   // for time formatting
#include <iostream>  // for cout/cerr

namespace cpp_engine {

SimpleCppEngine::SimpleCppEngine(double initial_capital, double commission_rate)
    : initial_capital_(initial_capital),
      commission_rate_(commission_rate),
      current_bar_index_(-1) {
    reset();
}

void SimpleCppEngine::reset() {
    cash_ = initial_capital_;
    positions_.clear();
    current_bar_index_ = -1;
    pending_orders_.clear();
    all_orders_.clear();
    trades_.clear();
    equity_curve_.clear();
}

void SimpleCppEngine::load_data(
    const std::vector<std::pair<std::string, std::unordered_map<std::string, double>>>& bars_data) {

    bars_.clear();
    bars_.reserve(bars_data.size());

    for (const auto& [date, data] : bars_data) {
        Bar bar = Bar::from_dict(data, date);
        bars_.push_back(bar);
    }

    reset();
}

void SimpleCppEngine::run(std::function<void(Context&)> strategy_callback) {
    // 创建Context对象
    Context context(this);

    // 主循环
    for (size_t i = 0; i < bars_.size(); ++i) {
        current_bar_index_ = static_cast<int>(i);

        try {
            // 调用Python策略
            strategy_callback(context);
        } catch (const std::exception& e) {
            // 捕获策略异常，记录但继续执行
            std::cerr << "策略异常 (bar " << i << "): " << e.what() << std::endl;
            continue;
        }

        // 执行待处理订单
        execute_pending_orders();

        // 更新净值
        update_equity();
    }

    // ========== 回测结束时强制平掉所有持仓 ==========
    std::cout << "\n🔄 回测结束，强制平掉所有持仓..." << std::endl;
    close_all_positions();

    // 更新最后一次净值（反映平仓后的资产）
    update_equity();

    // 保存交易记录到CSV
    save_trades_to_csv();

    // 输出调试信息
    std::cout << "📊 回测统计:" << std::endl;
    std::cout << "   - 初始资金: " << initial_capital_ << std::endl;
    std::cout << "   - 最终现金: " << cash_ << std::endl;
    std::cout << "   - 交易次数: " << trades_.size() << std::endl;

    // 显示各股票持仓
    for (const auto& [symbol, quantity] : positions_) {
        std::cout << "   - " << symbol << " 持仓: " << quantity << " 股" << std::endl;
    }
}

// ========== 数据查询接口实现 ==========

std::vector<double> SimpleCppEngine::get_series(const std::string& field, int count) {
    if (current_bar_index_ < 0) {
        throw std::runtime_error("No current bar");
    }

    if (count > current_bar_index_ + 1) {
        throw std::runtime_error("Not enough bars");
    }

    std::vector<double> result;
    result.reserve(count);

    int start_index = current_bar_index_ - count + 1;
    for (int i = start_index; i <= current_bar_index_; ++i) {
        auto bar_data = bars_[i].to_map();
        if (bar_data.find(field) == bar_data.end()) {
            throw std::runtime_error("Field not found: " + field);
        }
        result.push_back(bar_data[field]);
    }

    return result;
}

double SimpleCppEngine::get_bar(const std::string& field, int offset) {
    if (offset > current_bar_index_) {
        throw std::runtime_error("Offset exceeds available bars");
    }

    int target_index = current_bar_index_ - offset;
    auto bar_data = bars_[target_index].to_map();

    if (bar_data.find(field) == bar_data.end()) {
        throw std::runtime_error("Field not found: " + field);
    }

    return bar_data[field];
}

std::unordered_map<std::string, double> SimpleCppEngine::get_current_bar_data() {
    if (current_bar_index_ < 0 || current_bar_index_ >= static_cast<int>(bars_.size())) {
        throw std::runtime_error("Invalid current bar index");
    }
    return bars_[current_bar_index_].to_map();
}

std::string SimpleCppEngine::get_current_date() {
    if (current_bar_index_ < 0 || current_bar_index_ >= static_cast<int>(bars_.size())) {
        throw std::runtime_error("Invalid current bar index");
    }
    return bars_[current_bar_index_].trade_date;
}

double SimpleCppEngine::get_cash() {
    return cash_;
}

int SimpleCppEngine::get_position(const std::string& symbol) {
    auto it = positions_.find(symbol);
    if (it == positions_.end()) {
        return 0;
    }
    return it->second;
}

// ========== 订单接口实现 ==========

void SimpleCppEngine::submit_buy_order(const std::string& symbol, int quantity, double price) {
    Order order;
    order.symbol = symbol;
    order.action = "buy";
    order.quantity = quantity;
    order.price = price;
    order.date = get_current_date();

    pending_orders_.push_back(order);
    all_orders_.push_back(order);
}

void SimpleCppEngine::submit_sell_order(const std::string& symbol, int quantity, double price) {
    Order order;
    order.symbol = symbol;
    order.action = "sell";
    order.quantity = quantity;
    order.price = price;
    order.date = get_current_date();

    pending_orders_.push_back(order);
    all_orders_.push_back(order);
}

// ========== 内部辅助方法 ==========

void SimpleCppEngine::execute_pending_orders() {
    for (auto& order : pending_orders_) {
        Trade trade;
        trade.symbol = order.symbol;
        trade.action = order.action;
        trade.quantity = order.quantity;
        trade.price = order.price;
        trade.date = order.date;
        trade.cash_before = cash_;
        trade.position_before = positions_[order.symbol];

        if (order.action == "buy") {
            // 买单
            double cost = order.quantity * order.price;
            double commission = cost * commission_rate_;

            if (cash_ >= cost + commission) {
                cash_ -= (cost + commission);
                positions_[order.symbol] += order.quantity;
                trade.commission = commission;
                trade.cash_after = cash_;
                trade.position_after = positions_[order.symbol];
                trade.status = "成功";
                trades_.push_back(trade);
            } else {
                // 资金不足
                trade.status = "失败：资金不足";
                trades_.push_back(trade);
            }
        } else if (order.action == "sell") {
            // 卖单
            int current_position = positions_[order.symbol];
            if (current_position >= order.quantity) {
                double proceeds = order.quantity * order.price;
                double commission = proceeds * commission_rate_;

                cash_ += (proceeds - commission);
                positions_[order.symbol] -= order.quantity;
                trade.commission = commission;
                trade.cash_after = cash_;
                trade.position_after = positions_[order.symbol];
                trade.status = "成功";
                trades_.push_back(trade);
            } else {
                // 持仓不足
                trade.cash_after = cash_;
                trade.position_after = current_position;
                trade.status = "失败：持仓不足";
                trades_.push_back(trade);
            }
        }
    }

    pending_orders_.clear();
}

void SimpleCppEngine::update_equity() {
    double total_asset = calculate_total_asset();
    equity_curve_.push_back(total_asset);
}

double SimpleCppEngine::calculate_total_asset() {
    double total = cash_;

    // 计算持仓市值（使用当前bar的收盘价）
    if (current_bar_index_ >= 0 && current_bar_index_ < static_cast<int>(bars_.size())) {
        double current_price = bars_[current_bar_index_].close;

        for (const auto& [symbol, quantity] : positions_) {
            total += quantity * current_price;
        }
    }

    return total;
}

BacktestResult SimpleCppEngine::get_results() const {
    BacktestResult result;

    if (equity_curve_.empty()) {
        return result;
    }

    // 总收益率
    double final_asset = equity_curve_.back();
    result.total_return = (final_asset - initial_capital_) / initial_capital_;

    // 交易次数
    result.total_trades = static_cast<int>(trades_.size());

    // 净值曲线
    result.equity_curve = equity_curve_;

    // 交易记录
    result.trades = trades_;

    // 计算夏普比率（简化版）
    if (equity_curve_.size() > 1) {
        std::vector<double> returns;
        for (size_t i = 1; i < equity_curve_.size(); ++i) {
            double ret = (equity_curve_[i] - equity_curve_[i-1]) / equity_curve_[i-1];
            returns.push_back(ret);
        }

        if (!returns.empty()) {
            double mean = std::accumulate(returns.begin(), returns.end(), 0.0) / returns.size();
            double variance = 0.0;
            for (double ret : returns) {
                variance += (ret - mean) * (ret - mean);
            }
            variance /= returns.size();
            double std_dev = std::sqrt(variance);

            if (std_dev > 1e-6) {
                result.sharpe_ratio = mean / std_dev * std::sqrt(252);  // 年化
            }
        }
    }

    // 计算最大回撤
    double peak = equity_curve_[0];
    double max_dd = 0.0;
    for (double equity : equity_curve_) {
        if (equity > peak) {
            peak = equity;
        }
        double drawdown = (peak - equity) / peak;
        if (drawdown > max_dd) {
            max_dd = drawdown;
        }
    }
    result.max_drawdown = max_dd;

    // 计算胜率
    if (result.total_trades > 0) {
        int winning_trades = 0;
        // 简化版：只统计成对的买卖
        for (size_t i = 1; i < trades_.size(); i += 2) {
            if (trades_[i].action == "sell" && i > 0) {
                double buy_price = trades_[i-1].price;
                double sell_price = trades_[i].price;
                if (sell_price > buy_price) {
                    winning_trades++;
                }
            }
        }
        result.win_rate = static_cast<double>(winning_trades) / (result.total_trades / 2);
    }

    return result;
}

void SimpleCppEngine::save_trades_to_csv() {
    /* 保存交易记录到CSV文件 */
    if (trades_.empty()) {
        return;
    }

    // 生成文件名（带时间戳）
    std::time_t now = std::time(nullptr);
    char timestamp[64];
    std::strftime(timestamp, sizeof(timestamp), "%Y%m%d_%H%M%S", std::localtime(&now));

    // 使用相对路径（Python wrapper会切换到项目根目录）
    std::string filename = "data/debug_csv/trader_order/trader_order_" + std::string(timestamp) + ".csv";

    // 创建目录（如果不存在）
    std::string dir = "data/debug_csv/trader_order";
    std::string mkdir_cmd = "mkdir -p " + dir;
    system(mkdir_cmd.c_str());

    // 打开文件
    std::ofstream file(filename);
    if (!file.is_open()) {
        std::cerr << "❌ 无法打开文件: " << filename << std::endl;
        return;
    }

    // 写入表头
    file << "trade_date,symbol,action,quantity,price,commission,cash_before,cash_after,position_before,position_after,status\n";

    // 写入交易记录
    for (const auto& trade : trades_) {
        file << trade.date << ","
              << trade.symbol << ","
              << trade.action << ","
              << trade.quantity << ","
              << trade.price << ","
              << trade.commission << ","
              << trade.cash_before << ","
              << trade.cash_after << ","
              << trade.position_before << ","
              << trade.position_after << ","
              << trade.status << "\n";
    }

    file.close();
    std::cout << "📁 交易记录已保存到: " << filename << std::endl;
}

void SimpleCppEngine::close_all_positions() {
    /* 回测结束时强制平掉所有持仓，实现真实收益 */

    if (positions_.empty()) {
        std::cout << "   ✅ 无持仓，无需平仓" << std::endl;
        return;
    }

    // 获取最后一根K线的收盘价
    if (bars_.empty()) {
        std::cerr << "   ⚠️  无K线数据，无法平仓" << std::endl;
        return;
    }

    const Bar& last_bar = bars_.back();
    double last_price = last_bar.close;
    std::string last_date = last_bar.trade_date;

    std::cout << "   📈 最后一根K线收盘价: " << last_price << std::endl;
    std::cout << "   📅 平仓日期: " << last_date << std::endl;

    // 对每个持仓股票创建卖出订单
    for (const auto& [symbol, quantity] : positions_) {
        if (quantity <= 0) {
            continue;
        }

        // 创建Trade记录（直接添加到trades_，不经过pending_orders_）
        Trade trade;
        trade.symbol = symbol;
        trade.action = "sell";
        trade.quantity = quantity;
        trade.price = last_price;
        trade.date = last_date;
        trade.cash_before = cash_;
        trade.position_before = quantity;

        // 计算卖出收入和手续费
        double proceeds = quantity * last_price;
        double commission = proceeds * commission_rate_;

        // 执行卖出
        cash_ += (proceeds - commission);
        positions_[symbol] = 0;

        // 记录交易结果
        trade.commission = commission;
        trade.cash_after = cash_;
        trade.position_after = 0;
        trade.status = "成功（强制平仓）";

        trades_.push_back(trade);

        std::cout << "   💰 卖出 " << symbol << " " << quantity << " 股"
                  << " @ " << last_price << " 元，收入: " << proceeds
                  << " 元，手续费: " << commission << " 元" << std::endl;
    }

    std::cout << "   ✅ 强制平仓完成，最终现金: " << cash_ << " 元" << std::endl;
}

} // namespace cpp_engine
