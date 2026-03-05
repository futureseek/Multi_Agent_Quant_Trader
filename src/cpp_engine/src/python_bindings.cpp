#include <pybind11/pybind11.h>
#include <pybind11/stl.h>  // STL类型自动转换
#include "engine.h"
#include "context.h"

namespace py = pybind11;

PYBIND11_MODULE(cpp_engine, m) {
    m.doc() = "C++ Backtest Engine for Multi-Agent Quant Trader";

    // ========== Bar结构绑定 ==========
    py::class_<cpp_engine::Bar>(m, "Bar")
        .def(py::init<>())
        .def_readwrite("trade_date", &cpp_engine::Bar::trade_date)
        .def_readwrite("open", &cpp_engine::Bar::open)
        .def_readwrite("high", &cpp_engine::Bar::high)
        .def_readwrite("low", &cpp_engine::Bar::low)
        .def_readwrite("close", &cpp_engine::Bar::close)
        .def_readwrite("vol", &cpp_engine::Bar::vol)
        .def_readwrite("amount", &cpp_engine::Bar::amount);

    // ========== Order结构绑定 ==========
    py::class_<cpp_engine::Order>(m, "Order")
        .def(py::init<>())
        .def_readwrite("symbol", &cpp_engine::Order::symbol)
        .def_readwrite("action", &cpp_engine::Order::action)
        .def_readwrite("quantity", &cpp_engine::Order::quantity)
        .def_readwrite("price", &cpp_engine::Order::price)
        .def_readwrite("date", &cpp_engine::Order::date);

    // ========== Trade结构绑定 ==========
    py::class_<cpp_engine::Trade>(m, "Trade")
        .def(py::init<>())
        .def_readwrite("symbol", &cpp_engine::Trade::symbol)
        .def_readwrite("action", &cpp_engine::Trade::action)
        .def_readwrite("quantity", &cpp_engine::Trade::quantity)
        .def_readwrite("price", &cpp_engine::Trade::price)
        .def_readwrite("date", &cpp_engine::Trade::date)
        .def_readwrite("commission", &cpp_engine::Trade::commission)
        .def_readwrite("cash_before", &cpp_engine::Trade::cash_before)
        .def_readwrite("cash_after", &cpp_engine::Trade::cash_after)
        .def_readwrite("position_before", &cpp_engine::Trade::position_before)
        .def_readwrite("position_after", &cpp_engine::Trade::position_after)
        .def_readwrite("status", &cpp_engine::Trade::status);

    // ========== BacktestResult结构绑定 ==========
    py::class_<cpp_engine::BacktestResult>(m, "BacktestResult")
        .def(py::init<>())
        .def_readwrite("total_return", &cpp_engine::BacktestResult::total_return)
        .def_readwrite("sharpe_ratio", &cpp_engine::BacktestResult::sharpe_ratio)
        .def_readwrite("max_drawdown", &cpp_engine::BacktestResult::max_drawdown)
        .def_readwrite("total_trades", &cpp_engine::BacktestResult::total_trades)
        .def_readwrite("win_rate", &cpp_engine::BacktestResult::win_rate)
        .def_readwrite("equity_curve", &cpp_engine::BacktestResult::equity_curve)
        .def_readwrite("trades", &cpp_engine::BacktestResult::trades);

    // ========== Context类绑定 ==========
    py::class_<cpp_engine::Context>(m, "Context")
        .def("get_series", &cpp_engine::Context::get_series,
             py::arg("symbol"),
             py::arg("field"),
             py::arg("count"),
             "获取历史序列数据，返回list[float]")

        .def("get_bar", &cpp_engine::Context::get_bar,
             py::arg("symbol"),
             py::arg("field"),
             py::arg("offset") = 0,
             "获取单个K线字段值")

        .def("get_current_bar", &cpp_engine::Context::get_current_bar,
             "获取当前K线数据（dict格式）")

        .def("get_current_date", &cpp_engine::Context::get_current_date,
             "获取当前日期")

        .def("buy", &cpp_engine::Context::buy,
             py::arg("symbol"),
             py::arg("quantity"),
             py::arg("price"),
             "下买单")

        .def("sell", &cpp_engine::Context::sell,
             py::arg("symbol"),
             py::arg("quantity"),
             py::arg("price"),
             "下卖单")

        .def("get_cash", &cpp_engine::Context::get_cash,
             "获取可用资金")

        .def("get_position", &cpp_engine::Context::get_position,
             py::arg("symbol"),
             "获取持仓数量");

    // ========== SimpleCppEngine类绑定 ==========
    py::class_<cpp_engine::SimpleCppEngine>(m, "SimpleCppEngine")
        .def(py::init<double, double>(),
             py::arg("initial_capital") = 1000000.0,
             py::arg("commission_rate") = 0.0003,
             "创建C++回测引擎")

        .def("load_data", &cpp_engine::SimpleCppEngine::load_data,
             py::arg("bars_data"),
             "加载K线数据\n"
             "参数: bars_data - list of (date_str, dict) tuples\n"
             "例如: [('20240101', {'open': 10.5, 'close': 10.7, ...}), ...]")

        .def("run", [](cpp_engine::SimpleCppEngine& engine, py::function py_strategy) {
            // 包装Python策略函数为C++ std::function
            engine.run([py_strategy](cpp_engine::Context& ctx) {
                py_strategy(ctx);
            });
        }, py::arg("strategy_callback"),
           "运行回测\n"
           "参数: strategy_callback - Python函数，接收Context参数")

        .def("get_results", &cpp_engine::SimpleCppEngine::get_results,
             "获取回测结果");

    m.attr("__version__") = "0.1.0";
}
