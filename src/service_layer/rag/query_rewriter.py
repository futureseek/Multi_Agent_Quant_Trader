"""
查询改写模块 - 使用LLM优化用户查询

通过LLM扩展用户查询，提升向量检索准确率
"""

from typing import Dict, Optional
import json


class LLMQueryRewriter:
    """基于LLM的查询改写器"""

    def __init__(self, llm):
        """
        初始化查询改写器

        Args:
            llm: LLM实例（支持invoke方法）
        """
        self.llm = llm
        self.rewrite_count = 0
        print("✅ LLMQueryRewriter初始化完成")

    def rewrite(self, query: str, enable: bool = True) -> str:
        """
        改写用户查询

        Args:
            query: 原始查询
            enable: 是否启用改写（可通过配置关闭）

        Returns:
            改写后的查询字符串
        """
        if not enable:
            return query

        # 快速判断：如果查询已经很完整，直接返回
        if self._is_complete_query(query):
            return query

        try:
            # 构建改写Prompt
            prompt = self._build_rewrite_prompt(query)

            # 调用LLM改写
            response = self.llm.invoke(prompt)
            rewritten = response.content.strip() if hasattr(response, 'content') else str(response).strip()

            # 清理结果（去除引号、换行等）
            rewritten = self._clean_response(rewritten)

            # 验证改写结果
            if self._is_valid_rewrite(rewritten):
                self.rewrite_count += 1
                print(f"🔄 查询改写 [{self.rewrite_count}]: {query} → {rewritten}")
                return rewritten
            else:
                # 改写无效，返回原查询
                return query

        except Exception as e:
            print(f"⚠️ 查询改写失败: {e}，使用原查询")
            return query

    def _is_complete_query(self, query: str) -> bool:
        """
        判断查询是否已经完整，无需改写

        完整查询特征：
        - 长度 > 15字符
        - 包含股票代码（如 600519.SH）或完整公司名称（4字以上）
        """
        # 快速判断规则
        if len(query) > 50:
            return True  # 长查询通常已完整

        # 包含股票代码
        if '.SH' in query or '.SZ' in query or '.HK' in query:
            return True

        # 包含完整公司名称（4字以上，且是常见的完整名称模式）
        common_patterns = ['股份', '有限', '集团', '控股', '银行', '保险']
        if any(p in query for p in common_patterns) and len(query) >= 4:
            return True

        return False

    def _build_rewrite_prompt(self, query: str) -> str:
        """
        构建查询改写Prompt

        Args:
            query: 原始查询

        Returns:
            完整Prompt字符串
        """
        prompt = f"""你是一个专业的股票查询助手。请将用户的简写或模糊查询扩展为更完整的查询语句，以提升检索准确率。

改写规则：
1. 股票简称 → 扩展为：全称 + 代码（如果知道）+ 行业 + 地区
2. 模糊概念 → 补充具体关键词
3. 保持查询意图不变，不要添加额外条件

示例：
用户输入：茅台
改写：贵州茅台 600519.SH 白酒行业 贵州茅台镇

用户输入：招行
改写：招商银行 600036.SH 银行股 深圳

用户输入：低估值银行
改写：低市盈率 低市净率 银行股 价值投资

用户输入：深圳的科技公司
改写：深圳地区 科技行业 互联网 电子信息

用户输入：{query}

改写（只返回改写后的查询，不要解释）："""

        return prompt

    def _clean_response(self, response: str) -> str:
        """
        清理LLM响应

        Args:
            response: 原始响应

        Returns:
            清理后的字符串
        """
        # 去除引号
        response = response.strip('"\'""')

        # 去除换行和多余空格
        response = ' '.join(response.split())

        return response

    def _is_valid_rewrite(self, rewritten: str) -> bool:
        """
        验证改写结果是否有效

        Args:
            rewritten: 改写后的查询

        Returns:
            是否有效
        """
        # 基本验证
        if not rewritten or len(rewritten) < 2:
            return False

        # 不能包含解释性文字
        invalid_patterns = ['改写', '原查询', '因为', '所以', '注意', '解释']
        if any(pattern in rewritten for pattern in invalid_patterns):
            return False

        # 不能太短（小于原查询的80%，但不少于5字）
        if len(rewritten) < 5:
            return False

        return True

    def get_stats(self) -> Dict[str, any]:
        """
        获取改写统计信息

        Returns:
            统计数据字典
        """
        return {
            "rewrite_count": self.rewrite_count,
            "rewriter_type": "LLM"
        }


class RuleQueryRewriter:
    """基于规则的查询改写器（预留，后续扩展）"""

    def __init__(self, aliases_path: Optional[str] = None):
        """
        初始化规则改写器

        Args:
            aliases_path: 别名字典文件路径（可选）
        """
        self.aliases = {}
        if aliases_path:
            self._load_aliases(aliases_path)
        print("✅ RuleQueryRewriter初始化完成")

    def _load_aliases(self, path: str):
        """加载别名字典"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.aliases = json.load(f)
            print(f"✅ 加载了 {len(self.aliases)} 个别名规则")
        except FileNotFoundError:
            print(f"⚠️ 别名字典未找到: {path}")

    def rewrite(self, query: str, enable: bool = True) -> str:
        """
        规则改写（待实现）

        Args:
            query: 原始查询
            enable: 是否启用改写

        Returns:
            改写后的查询
        """
        # TODO: 实现规则匹配逻辑
        return query


class HybridQueryRewriter:
    """混合查询改写器（预留，后续扩展）"""

    def __init__(self, llm, aliases_path: Optional[str] = None):
        """
        初始化混合改写器

        Args:
            llm: LLM实例
            aliases_path: 别名字典路径（可选）
        """
        self.rule_rewriter = RuleQueryRewriter(aliases_path)
        self.llm_rewriter = LLMQueryRewriter(llm)
        print("✅ HybridQueryRewriter初始化完成")

    def rewrite(self, query: str, enable: bool = True) -> str:
        """
        混合改写策略

        策略：
        1. 优先使用规则改写（快速）
        2. 规则无效时使用LLM改写（灵活）

        Args:
            query: 原始查询
            enable: 是否启用改写

        Returns:
            改写后的查询
        """
        if not enable:
            return query

        # TODO: 实现混合策略决策逻辑
        # 暂时直接使用LLM改写
        return self.llm_rewriter.rewrite(query, enable)
